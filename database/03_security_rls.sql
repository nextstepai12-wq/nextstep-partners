-- ============================================================================
-- 03 — الأمان: RLS والصلاحيات
--   الزائر (anon): إضافة طلب جديد فقط + تتبّع طلبه برمز وبريد. لا قراءة ولا تعديل.
--   viewer: قراءة | admin: قراءة + تعديل | owner: كل شيء + حذف
-- ============================================================================
alter table public.partners enable row level security;
alter table public.partner_admins enable row level security;
alter table public.partner_audit enable row level security;

-- ---- صلاحيات الجداول (طبقة أولى قبل RLS) ----
revoke all on public.partners from anon, authenticated;
revoke all on public.partner_admins from anon, authenticated;
revoke all on public.partner_audit from anon, authenticated;
grant insert on public.partners to anon;
grant select, update, delete on public.partners to authenticated;
grant select on public.partner_admins to authenticated;
grant insert, update, delete on public.partner_admins to authenticated;   -- محكومة بـ RLS (owner فقط)
grant select on public.partner_audit to authenticated;

-- ---- partners ----
drop policy if exists "anon can submit partner" on public.partners;
drop policy if exists "partners_insert_public" on public.partners;
create policy "partners_insert_public" on public.partners for insert to anon
  with check (
    status = 'new' and notes is null and consent = true
    and reviewed_by is null and reviewed_at is null
    and priority = 'normal' and tags = '{}'
  );

drop policy if exists "partners_select_admin" on public.partners;
create policy "partners_select_admin" on public.partners for select to authenticated
  using (public.partner_is_admin('viewer'));

drop policy if exists "partners_update_admin" on public.partners;
create policy "partners_update_admin" on public.partners for update to authenticated
  using (public.partner_is_admin('admin')) with check (public.partner_is_admin('admin'));

drop policy if exists "partners_delete_owner" on public.partners;
create policy "partners_delete_owner" on public.partners for delete to authenticated
  using (public.partner_is_admin('owner'));

-- ---- partner_admins ----
drop policy if exists "admins_select_self_or_owner" on public.partner_admins;
create policy "admins_select_self_or_owner" on public.partner_admins for select to authenticated
  using (user_id = auth.uid() or public.partner_is_admin('owner'));

drop policy if exists "admins_write_owner" on public.partner_admins;
create policy "admins_write_owner" on public.partner_admins for all to authenticated
  using (public.partner_is_admin('owner')) with check (public.partner_is_admin('owner'));

-- ---- partner_audit ----
drop policy if exists "audit_select_admin" on public.partner_audit;
create policy "audit_select_admin" on public.partner_audit for select to authenticated
  using (public.partner_is_admin('viewer'));
-- لا سياسات كتابة: المشغّلات (SECURITY DEFINER) وحدها تكتب في السجل

-- ---- صلاحيات تنفيذ الدوال ----
revoke execute on function public.partner_is_admin(text) from public;
revoke execute on function public.partner_admin_role() from public;
revoke execute on function public.partner_admin_email() from public;
revoke execute on function public.partner_track(text, text) from public;
revoke execute on function public.purge_old_partners(text, int) from public;
grant execute on function public.partner_is_admin(text) to authenticated;
grant execute on function public.partner_admin_role() to authenticated;
grant execute on function public.partner_track(text, text) to anon, authenticated;
grant execute on function public.purge_old_partners(text, int) to authenticated;
