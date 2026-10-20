-- ============================================================================
-- 04 — إنشاء أول مدير (مالك) — يُشغَّل مرة واحدة
-- ============================================================================
-- 1) من Supabase: Authentication ← Users ← Add user ← Create new user
--    اكتب بريدك وكلمة مرور قوية، وفعّل Auto Confirm User.
-- 2) استبدل البريد أدناه ببريدك ثم شغّل السكربت:
insert into public.partner_admins (user_id, email, role)
select id, email, 'owner' from auth.users where email = 'PUT_YOUR_ADMIN_EMAIL_HERE'
on conflict (user_id) do update set role = 'owner';

-- للتحقق:
-- select * from public.partner_admins;

-- ----------------------------------------------------------------------------
-- إضافة مشرف آخر لاحقًا (أنشئ حسابه من Authentication أولًا):
-- insert into public.partner_admins (user_id, email, role)
-- select id, email, 'admin'   -- أو 'viewer' للقراءة فقط
-- from auth.users where email = 'colleague@example.com'
-- on conflict (user_id) do update set role = excluded.role;
--
-- سحب صلاحية:
-- delete from public.partner_admins where email = 'colleague@example.com';
-- ----------------------------------------------------------------------------
