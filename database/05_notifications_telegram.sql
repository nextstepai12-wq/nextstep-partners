-- ============================================================
-- 05 (اختياري) — إشعار تيليغرام فوري عند وصول شريك جديد
-- ============================================================
-- قبل التشغيل:
--  1) في تيليغرام افتح @BotFather ← /newbot ← احصل على TOKEN.
--  2) افتح بوتك وأرسل له أي رسالة (أو أضفه لمجموعة وأرسل فيها رسالة).
--  3) افتح في المتصفح: https://api.telegram.org/bot<TOKEN>/getUpdates
--     وانسخ قيمة chat.id (للمجموعات تبدأ بـ -).
--  4) استبدل القيمتين أدناه ثم شغّل الملف كاملًا.

create extension if not exists pg_net;

create schema if not exists private;
revoke all on schema private from anon, authenticated;

create table if not exists private.partner_secrets (key text primary key, value text not null);
revoke all on private.partner_secrets from anon, authenticated;

insert into private.partner_secrets (key, value) values
  ('telegram_bot_token', 'PUT_BOT_TOKEN_HERE'),
  ('telegram_chat_id',   'PUT_CHAT_ID_HERE')
on conflict (key) do update set value = excluded.value;

create or replace function public.notify_new_partner() returns trigger
language plpgsql security definer set search_path = public, private as $$
declare
  tok text; chat text; msg text; ints text;
begin
  select value into tok  from private.partner_secrets where key = 'telegram_bot_token';
  select value into chat from private.partner_secrets where key = 'telegram_chat_id';
  if tok is null or tok like 'PUT_%' or chat is null or chat like 'PUT_%' then return new; end if;

  select string_agg(x, '، ') into ints from jsonb_array_elements_text(new.interests) x;

  msg := E'🤝 طلب شراكة جديد — NextStep AI\nالرمز: ' || coalesce(new.ref_code, '—') || E'\n\n'
      || E'الجهة: ' || new.name_ar || ' (' || new.entity_type || E')\n'
      || E'المجال: ' || new.sector || E'\n'
      || E'الموقع: ' || coalesce(new.city || '، ', '') || new.country || E'\n\n'
      || E'المسؤول: ' || new.contact_name || ' — ' || new.contact_role || E'\n'
      || E'البريد: ' || new.email || E'\n'
      || E'واتساب: ' || new.whatsapp || E'\n\n'
      || E'الاهتمامات: ' || coalesce(ints, '—');

  begin
    perform net.http_post(
      url     := 'https://api.telegram.org/bot' || tok || '/sendMessage',
      headers := '{"Content-Type":"application/json"}'::jsonb,
      body    := jsonb_build_object('chat_id', chat, 'text', msg)
    );
  exception when others then
    null;  -- فشل الإشعار لا يمنع حفظ الطلب أبدًا
  end;

  return new;
end $$;

drop trigger if exists notify_new_partner on public.partners;
create trigger notify_new_partner after insert on public.partners
  for each row execute function public.notify_new_partner();

-- للتجربة: سجّل شريكًا تجريبيًا من الصفحة، يصلك إشعار خلال ثوانٍ.
-- لتعطيل الإشعار: drop trigger notify_new_partner on public.partners;
