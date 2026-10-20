# دليل التشغيل خطوة بخطوة

> الوقت المتوقع: 30–45 دقيقة. نفّذ الخطوات بالترتيب.

## 0) ما تحتاجه
- مشروع Supabase (لديك مشروع قائم: يُستخدم نفسه).
- حساب GitHub.
- (اختياري) بوت تيليغرام للإشعارات، وحساب Cloudflare للحماية المتقدمة.

## 1) قاعدة البيانات — Supabase ← SQL Editor
شغّل الملفات **بهذا الترتيب** (الصق محتوى كل ملف ثم Run). كلها آمنة لإعادة التشغيل، وترقّي جدول `partners` القديم دون فقدان بياناته (تُرقَّم الطلبات القديمة تلقائيًا).

| # | الملف | ماذا يفعل |
|---|---|---|
| 1 | `database/01_schema.sql` | الجداول `partners` و`partner_admins` و`partner_audit` والقيود والفهارس |
| 2 | `database/02_functions_triggers.sql` | التحقق، رمز المتابعة، حدود المعدّل، التدقيق، تتبّع الطلب |
| 3 | `database/03_security_rls.sql` | سياسات الأمان والصلاحيات |
| 4 | `database/04_admin_bootstrap.sql` | أول مدير (انظر الخطوة 2) |
| 5 | `database/05_notifications_telegram.sql` | إشعار تيليغرام (اختياري، انظر الخطوة 6) |

### أسماء الكائنات (لا تتعارض مع مواقعك الأخرى في نفس المشروع)
كل ما تنشئه منظومة الشركاء يحمل بادئة `partner`/`partners`، ولا يلمس أي جدول أو دالة أخرى في مشروعك:
- **جداول:** `partners` · `partner_admins` · `partner_audit` · `private.partner_secrets` (الأخير فقط عند تشغيل `05`)
- **دوال:** `partner_is_admin` · `partner_admin_role` · `partner_admin_email` · `partner_gen_ref_code` · `partner_track` · `purge_old_partners` · `partners_guard` · `partners_before_update` · `partners_audit_fn`
- جدول `admins` ودالة `is_admin` إن كانا موجودين لموقع آخر **لا يُمسّان**.

> إن كنت شغّلت نسخة سابقة من الملفات وظهر الخطأ `column a.user_id does not exist`، فهذا يعني وجود جدول `admins` قديم لموقع آخر. لم يتغير شيء فيه. حمّل الملفات الجديدة وأعد تشغيل `01` ثم `02` ثم `03` ثم `04` بالترتيب (آمنة لإعادة التشغيل). اختياريًا يمكنك حذف الدالة المتبقية من التشغيل القديم إن لم تكن لموقع آخر: `drop function if exists public.gen_ref_code();`

## 2) إنشاء حساب المالك
1. Supabase ← **Authentication ← Users ← Add user ← Create new user**: بريدك + كلمة مرور طويلة وفريدة + فعّل **Auto Confirm User**.
2. افتح `04_admin_bootstrap.sql`، استبدل `PUT_YOUR_ADMIN_EMAIL_HERE` ببريدك، ثم شغّله.
3. تحقق: `select * from public.partner_admins;` يجب أن يظهر صفك بدور `owner`.

## 3) إعدادات Authentication (مهم)
في Supabase ← Authentication ← Sign In / Providers (قد تختلف التسمية قليلًا):
- **عطّل التسجيل العام** (Allow new users to sign up = off). حسابات الإدارة تُنشأ يدويًا فقط.
- أبقِ تسجيل البريد وكلمة المرور مفعّلًا.
- اجعل الحد الأدنى لطول كلمة المرور 12 فأكثر، وفعّل حماية كلمات المرور المسرّبة إن توفرت لخطتك.

## 4) مراجعة الإعدادات في الملفات
- `index.html` ← أول السكربت `CONFIG`: `SUPABASE_URL` و`SUPABASE_ANON_KEY` (مفتاح **publishable/anon** فقط).
- `admin.html` ← `CONFIG` نفسه، **وكذلك** وسم `Content-Security-Policy` في الأعلى: `connect-src` يجب أن يطابق رابط مشروعك. (مضبوط حاليًا على مشروعك.)
- **لا تضع** مفتاح `service_role` في أي ملف أبدًا.
- صورتك: `assets/founder.jpg` (موجودة).
- روابط المعاينة (Open Graph) في `index.html` تفترض العنوان `https://nextstepai12-wq.github.io/nextstep-partners/`. إن اختلف عنوانك فاستبدله في: `og:url` و`og:image` و`twitter:image` و`canonical`، وفي `robots.txt` و`sitemap.xml`.

## 5) النشر على GitHub Pages
1. أنشئ ريبو باسم `nextstep-partners`.
2. ارفع **محتويات** المجلد إلى جذر الريبو (يشمل الملفات المخفية `.nojekyll`). عبر المتصفح: Add file ← Upload files ← اسحب كل شيء (احرص أن يُرفع مجلد `assets` بمحتوياته).
3. Settings ← Pages ← Source: Deploy from a branch ← Branch: `main` / root ← Save.
4. بعد دقيقة أو اثنتين: الصفحة العامة على `…github.io/nextstep-partners/` ولوحة الإدارة على `…/admin.html`.

> ريبو عام = الكود وملفات SQL والتوثيق ظاهرة للجميع. هذا مقبول لأنها لا تحتوي أسرارًا، لكن **لا تلصق** فيها توكن تيليغرام أو أي مفتاح سري. (يمكنك حذف مجلدي `docs` و`tests` من الريبو العام إن أردت.)

## 6) إشعار تيليغرام (اختياري)
اتبع التعليقات أعلى `database/05_notifications_telegram.sql` (BotFather ← token ← chat id) واستبدل القيمتين `PUT_...` **في SQL Editor فقط (لا في الريبو)**، ثم شغّله.

## 7) اختبار ما بعد النشر (إلزامي — 10 دقائق)
1. افتح الصفحة العامة على جوالك وابحث عن أي مشكلة بصرية.
2. سجّل شريكًا تجريبيًا كاملًا ببريد حقيقي لديك (انتظر ثوانٍ قبل الإرسال؛ الإرسال السريع جدًا يُرفض كسلوك آلي). تأكد من ظهور **رقم المتابعة**.
3. Supabase ← Table Editor ← `partners`: يجب أن يظهر الصف مع `ref_code`.
4. في الصفحة العامة: قسم «تتبّع طلبك» ← أدخل الرمز والبريد ← يجب أن تظهر الحالة «قيد المراجعة».
5. افتح `admin.html` وادخل بحساب المالك: يجب أن يظهر الطلب في اللوحة. غيّر حالته واحفظ، ثم تحقق من «سجل النشاط» ومن تغيّر الحالة في التتبّع العام.
6. جرّب الدخول بحساب لا يملك صفًا في `partner_admins`: يجب أن يُرفض.
7. إن فعّلت تيليغرام: تأكد من وصول الإشعار.
8. احذف الطلب التجريبي من اللوحة (دور المالك).
9. شارك الرابط في واتساب وتحقق من الصورة المصغّرة (قد تحتاج دقائق؛ استخدم Facebook Sharing Debugger لتحديث الكاش).

## 8) إضافة أعضاء للفريق
أنشئ حساب العضو من Authentication ← Users ثم شغّل في SQL Editor:
```sql
insert into public.partner_admins (user_id, email, role)
select id, email, 'admin'   -- أو 'viewer' للقراءة فقط
from auth.users where email = 'colleague@example.com'
on conflict (user_id) do update set role = excluded.role;
```
لسحب الصلاحية: `delete from public.partner_admins where email = '…';`

## 9) المستوى الثاني من الحماية (اختياري — فعّله عند ظهور إغراق بالطلبات)
المستوى الأول (حدود المعدّل في قاعدة البيانات + فخ الروبوتات + فحص السرعة) فعّال دون إعداد. للمستوى الثاني (Cloudflare Turnstile):
1. أنشئ موقع Turnstile مجانًا في Cloudflare وخذ **Site key** و**Secret key**.
2. Supabase ← Edge Functions: أنشئ دالة `submit-partner` بمحتوى `supabase/functions/submit-partner/index.ts` و**أوقف Verify JWT** لها، وأضف السر `TURNSTILE_SECRET`.
3. في `index.html` عبّئ `TURNSTILE_SITE_KEY` و`FUNCTION_URL` (`https://<ref>.supabase.co/functions/v1/submit-partner`).
4. جرّب تسجيلًا كاملًا. وبعد نجاحه فقط أغلق الإدخال المباشر:
```sql
drop policy if exists "partners_insert_public" on public.partners;
revoke insert on public.partners from anon;
```
(للتراجع: أعد تشغيل `03_security_rls.sql`.)

## 10) صيانة دورية
- **أسبوعيًا:** راجع الطلبات الجديدة و«تحتاج متابعة».
- **شهريًا:** نزّل «نسخة احتياطية JSON» من اللوحة واحفظها في مكان آمن (النسخ التلقائية في Supabase تعتمد على خطتك).
- **سنويًا:** طبّق سياسة الاحتفاظ بحذف الطلبات المرفوضة/المؤرشفة القديمة. من SQL Editor:
  ```sql
  delete from public.partners
  where status in ('declined','archived') and coalesce(reviewed_at, created_at) < now() - interval '365 days';
  ```
  (الدالة `purge_old_partners` موجودة لاستدعائها عبر API بجلسة المالك، وغير معروضة في اللوحة حاليًا. الحذف من SQL Editor يُسجَّل في سجل التدقيق بلا اسم منفّذ.)
- راجع [docs/SECURITY.md](docs/SECURITY.md) قبل الإطلاق العام.
