-- ============================================================================
-- NextStep AI — شبكة الشركاء | 01 — المخطط (الجداول والأعمدة والفهارس)
-- آمن للتشغيل أكثر من مرة (idempotent) ويرقّي الجدول القديم دون فقدان بيانات.
-- شغّله في Supabase ← SQL Editor.
-- ============================================================================

-- رمز متابعة الطلب: NS- + 8 أحرف من الأبجدية A-Z و2-7
create or replace function public.partner_gen_ref_code() returns text
language sql volatile as $$
  select 'NS-' || string_agg(substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567', 1 + floor(random() * 32)::int, 1), '')
  from generate_series(1, 8);
$$;

-- ---------------------------------------------------------------- partners --
create table if not exists public.partners (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  status text not null default 'new',
  notes text,

  -- الجهة
  entity_type text not null,
  name_ar text not null,
  name_en text,
  country text not null,
  city text,
  sector text not null,
  founded_year int,
  team_size text,
  website text,
  social_links text,
  logo_url text,
  description text not null,

  -- جهة الاتصال
  contact_name text not null,
  contact_role text not null,
  email text not null,
  whatsapp text not null,

  -- الشراكة
  interests jsonb not null default '[]'::jsonb,
  offers text,
  needs text,
  reach text,
  past_events text,

  consent boolean not null,
  unique (email, name_ar)
);

-- أعمدة الإدارة والمتابعة (تُضاف للجدول القديم إن وُجد)
alter table public.partners
  add column if not exists ref_code text,
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists reviewed_by text,
  add column if not exists reviewed_at timestamptz,
  add column if not exists priority text not null default 'normal',
  add column if not exists tags text[] not null default '{}';

-- ترقيم الطلبات القديمة التي بلا رمز
update public.partners set ref_code = public.partner_gen_ref_code() where ref_code is null;

-- قيود الصحة (NOT VALID: لا تفحص القديم، وتُطبَّق على كل إدخال/تعديل جديد)
alter table public.partners
  drop constraint if exists partners_status_check,
  drop constraint if exists partners_priority_check,
  drop constraint if exists partners_ref_fmt,
  drop constraint if exists partners_tags_len,
  drop constraint if exists partners_email_fmt,
  drop constraint if exists partners_phone_fmt,
  drop constraint if exists partners_web_fmt,
  drop constraint if exists partners_logo_fmt,
  drop constraint if exists partners_interests_fmt,
  drop constraint if exists partners_len_fmt;

alter table public.partners
  add constraint partners_status_check check (status in ('new','contacted','in_progress','approved','declined','archived')) not valid,
  add constraint partners_priority_check check (priority in ('low','normal','high')) not valid,
  add constraint partners_ref_fmt check (ref_code ~ '^NS-[A-Z2-7]{8}$') not valid,
  add constraint partners_tags_len check (cardinality(tags) <= 10) not valid,
  add constraint partners_email_fmt check (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]{2,}$') not valid,
  add constraint partners_phone_fmt check (whatsapp ~ '^\+[0-9]{9,15}$') not valid,
  add constraint partners_web_fmt check (website is null or website ~* '^https?://') not valid,
  add constraint partners_logo_fmt check (logo_url is null or logo_url ~* '^https?://') not valid,
  add constraint partners_interests_fmt check (jsonb_typeof(interests) = 'array' and jsonb_array_length(interests) between 1 and 8) not valid,
  add constraint partners_len_fmt check (
    char_length(entity_type) <= 60 and char_length(name_ar) between 2 and 160 and char_length(coalesce(name_en,'')) <= 160
    and char_length(country) <= 80 and char_length(coalesce(city,'')) <= 80 and char_length(sector) <= 80
    and (founded_year is null or founded_year between 1900 and 2100) and char_length(coalesce(team_size,'')) <= 40
    and char_length(coalesce(website,'')) <= 300 and char_length(coalesce(social_links,'')) <= 600 and char_length(coalesce(logo_url,'')) <= 300
    and char_length(description) between 20 and 2000
    and char_length(contact_name) between 3 and 120 and char_length(contact_role) <= 120
    and char_length(email) <= 160 and char_length(whatsapp) between 9 and 20
    and char_length(coalesce(offers,'')) <= 2000 and char_length(coalesce(needs,'')) <= 2000
    and char_length(coalesce(reach,'')) <= 60 and char_length(coalesce(past_events,'')) <= 2000
    and char_length(coalesce(notes,'')) <= 5000 and consent = true
  ) not valid;

create unique index if not exists partners_ref_code_key on public.partners (ref_code) where ref_code is not null;
create index if not exists partners_created_idx on public.partners (created_at desc);
create index if not exists partners_status_idx on public.partners (status);
create index if not exists partners_country_idx on public.partners (country);
create index if not exists partners_interests_gin on public.partners using gin (interests);

-- ------------------------------------------------------------------ partner_admins --
-- فريق الإدارة. الأدوار: owner (كل شيء) / admin (قراءة وتعديل) / viewer (قراءة فقط)
create table if not exists public.partner_admins (
  user_id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  role text not null default 'viewer' check (role in ('owner','admin','viewer')),
  created_at timestamptz not null default now()
);

-- ----------------------------------------------------------- partner_audit --
-- سجل تدقيق غير قابل للتعديل من الواجهة: من غيّر ماذا ومتى
create table if not exists public.partner_audit (
  id bigint generated always as identity primary key,
  at timestamptz not null default now(),
  partner_id uuid,
  partner_name text,
  action text not null check (action in ('create','status_change','notes_update','field_update','delete')),
  actor_id uuid,
  actor_email text,
  details jsonb not null default '{}'::jsonb
);
create index if not exists partner_audit_at_idx on public.partner_audit (at desc);
create index if not exists partner_audit_partner_idx on public.partner_audit (partner_id, at desc);
