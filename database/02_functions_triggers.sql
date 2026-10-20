-- ============================================================================
-- 02 — الدوال والمشغّلات (التحقق، تحديد المعدّل، التدقيق، التتبّع للشريك)
-- ============================================================================

-- ---------- صلاحيات الإدارة ----------
create or replace function public.partner_is_admin(min_role text default 'viewer') returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.partner_admins a
    where a.user_id = auth.uid()
      and case a.role when 'owner' then 3 when 'admin' then 2 else 1 end
        >= case min_role when 'owner' then 3 when 'admin' then 2 else 1 end
  );
$$;

create or replace function public.partner_admin_role() returns text
language sql stable security definer set search_path = public as $$
  select a.role from public.partner_admins a where a.user_id = auth.uid();
$$;

create or replace function public.partner_admin_email() returns text
language sql stable security definer set search_path = public as $$
  select a.email from public.partner_admins a where a.user_id = auth.uid();
$$;

-- ---------- قبل الإدخال: توحيد + رمز المتابعة + تحديد المعدّل ----------
create or replace function public.partners_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare tries int := 0;
begin
  new.email := lower(trim(new.email));

  -- رمز المتابعة: نقبل رمز المتصفح إن كان صالحًا وإلا نولّد واحدًا
  if new.ref_code is null or new.ref_code !~ '^NS-[A-Z2-7]{8}$' then
    new.ref_code := public.partner_gen_ref_code();
  end if;
  while exists (select 1 from public.partners where ref_code = new.ref_code) and tries < 8 loop
    new.ref_code := public.partner_gen_ref_code(); tries := tries + 1;
  end loop;

  -- حد عام: 30 طلبًا كل 10 دقائق
  if (select count(*) from public.partners where created_at > now() - interval '10 minutes') >= 30 then
    raise exception 'rate_limited';
  end if;
  -- حد لكل بريد: 3 طلبات يوميًا
  if (select count(*) from public.partners where email = new.email and created_at > now() - interval '1 day') >= 3 then
    raise exception 'email_limit';
  end if;
  return new;
end $$;

drop trigger if exists partners_guard on public.partners;
create trigger partners_guard before insert on public.partners
  for each row execute function public.partners_guard();

-- ---------- قبل التعديل: حماية الحقول الثابتة + ختم المراجعة ----------
create or replace function public.partners_before_update() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.id := old.id;
  new.created_at := old.created_at;
  new.ref_code := old.ref_code;
  new.consent := old.consent;
  new.updated_at := now();
  if new.status is distinct from old.status then
    new.reviewed_by := coalesce(public.partner_admin_email(), 'system');
    new.reviewed_at := now();
  end if;
  return new;
end $$;

drop trigger if exists partners_before_update on public.partners;
create trigger partners_before_update before update on public.partners
  for each row execute function public.partners_before_update();

-- ---------- التدقيق ----------
create or replace function public.partners_audit_fn() returns trigger
language plpgsql security definer set search_path = public as $$
declare diff jsonb; act text;
begin
  if tg_op = 'INSERT' then
    insert into public.partner_audit (partner_id, partner_name, action, details)
    values (new.id, new.name_ar, 'create', jsonb_build_object('ref_code', new.ref_code, 'status', new.status));
    return new;
  elsif tg_op = 'UPDATE' then
    select jsonb_object_agg(n.key, jsonb_build_object('from', o.value, 'to', n.value)) into diff
    from jsonb_each(to_jsonb(new)) n join jsonb_each(to_jsonb(old)) o using (key)
    where n.value is distinct from o.value and n.key not in ('updated_at', 'reviewed_at', 'reviewed_by');
    if diff is null then return new; end if;
    act := case when diff ? 'status' then 'status_change' when diff ? 'notes' then 'notes_update' else 'field_update' end;
    insert into public.partner_audit (partner_id, partner_name, action, actor_id, actor_email, details)
    values (new.id, new.name_ar, act, auth.uid(), public.partner_admin_email(), diff);
    return new;
  else
    insert into public.partner_audit (partner_id, partner_name, action, actor_id, actor_email, details)
    values (old.id, old.name_ar, 'delete', auth.uid(), public.partner_admin_email(), jsonb_build_object('ref_code', old.ref_code, 'status', old.status));
    return old;
  end if;
end $$;

drop trigger if exists partners_audit on public.partners;
create trigger partners_audit after insert or update or delete on public.partners
  for each row execute function public.partners_audit_fn();

-- ---------- تتبّع الطلب للشريك (رمز + بريد) — لا يكشف أي بيانات إلا عند التطابق ----------
create or replace function public.partner_track(p_ref text, p_email text)
returns table (ref_code text, name_ar text, status text, created_at timestamptz, updated_at timestamptz)
language sql stable security definer set search_path = public as $$
  select p.ref_code, p.name_ar, p.status, p.created_at, p.updated_at
  from public.partners p
  where p.ref_code = upper(trim(p_ref)) and p.email = lower(trim(p_email))
  limit 1;
$$;

-- ---------- سياسة الاحتفاظ (للمالك فقط): حذف الطلبات المرفوضة/المؤرشفة القديمة ----------
create or replace function public.purge_old_partners(p_status text default 'declined', p_days int default 365)
returns int language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if not public.partner_is_admin('owner') then raise exception 'forbidden'; end if;
  if p_status not in ('declined', 'archived') then raise exception 'invalid_status'; end if;
  if p_days < 30 then raise exception 'too_short'; end if;
  delete from public.partners
  where status = p_status and coalesce(reviewed_at, created_at) < now() - make_interval(days => p_days);
  get diagnostics n = row_count;
  return n;
end $$;
