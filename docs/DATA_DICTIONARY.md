# قاموس البيانات

## الجدول `public.partners`
| العمود | النوع | إلزامي | المصدر | ملاحظات |
|---|---|:--:|---|---|
| `id` | uuid | تلقائي | النظام | مفتاح أساسي |
| `ref_code` | text | تلقائي | المتصفح/الخادم | `NS-` + 8 أحرف (A–Z و2–7)، فريد. يُولَّد من المتصفح ويُعاد توليده في الخادم إن كان غير صالح |
| `created_at` / `updated_at` | timestamptz | تلقائي | النظام | `updated_at` يتحدث مع كل تعديل |
| `status` | text | ✓ | الإدارة | `new` ← افتراضي، `contacted`، `in_progress`، `approved`، `declined`، `archived` |
| `priority` | text | ✓ | الإدارة | `low` / `normal` (افتراضي) / `high` |
| `tags` | text[] | ✓ | الإدارة | حتى 10 وسوم |
| `notes` | text | — | الإدارة | داخلية، حتى 5000 حرف، لا يراها الشريك |
| `reviewed_by` / `reviewed_at` | text / timestamptz | — | تلقائي | يُختمان عند تغيير الحالة (بريد المشرف) |
| `entity_type` | text | ✓ | النموذج | شركة، فريق، جامعة / كلية، مؤسسة / منظمة، مبادرة، شركة ناشئة، أخرى |
| `name_ar` | text | ✓ | النموذج | 2–160 حرفًا |
| `name_en` | text | — | النموذج | حتى 160 |
| `country` | text | ✓ | النموذج | حتى 80 |
| `city` | text | — | النموذج | حتى 80 |
| `sector` | text | ✓ | النموذج | قائمة اختيار |
| `founded_year` | int | — | النموذج | 1900–2100 |
| `team_size` | text | — | النموذج | 1–5، 6–20، 21–50، 51–200، أكثر من 200 |
| `website` / `logo_url` | text | — | النموذج | يجب أن يبدأ بـ http(s):// |
| `social_links` | text | — | النموذج | حتى 600 حرف |
| `description` | text | ✓ | النموذج | 20–2000 حرف |
| `contact_name` | text | ✓ | النموذج | 3–120 |
| `contact_role` | text | ✓ | النموذج | حتى 120 |
| `email` | text | ✓ | النموذج | يُحوَّل إلى أحرف صغيرة في الخادم |
| `whatsapp` | text | ✓ | النموذج | بصيغة E.164: `+` ثم 9–15 رقمًا |
| `interests` | jsonb (مصفوفة) | ✓ | النموذج | 1–8 قيم |
| `offers` / `needs` / `past_events` | text | — | النموذج | حتى 2000 لكلٍّ |
| `reach` | text | — | النموذج | أقل من 100، 100–500، 500–2000، أكثر من 2000، لا أعلم بعد |
| `consent` | boolean | ✓ | النموذج | يجب أن تكون `true` |

**قيد التفرّد:** (`email`, `name_ar`). **الفهارس:** تاريخ الإنشاء، الحالة، الدولة، الاهتمامات (GIN)، رمز المتابعة (فريد).

## الجدول `public.partner_admins`
`user_id` (مفتاح، مرتبط بـ `auth.users`) · `email` · `role` (`owner`/`admin`/`viewer`) · `created_at`.

## الجدول `public.partner_audit`
سجل لا يُعدَّل من الواجهة: `at` · `partner_id` · `partner_name` · `action` (`create`/`status_change`/`notes_update`/`field_update`/`delete`) · `actor_id` · `actor_email` · `details` (jsonb بالقيم القديمة والجديدة).

## الدوال
| الدالة | من يستدعيها | الغرض |
|---|---|---|
| `partner_is_admin(min_role)` · `partner_admin_role()` | سياسات RLS والواجهة | فحص الدور |
| `partner_track(ref, email)` | الزائر | تُرجع (الرمز، الاسم، الحالة، تاريخي الإنشاء والتحديث) عند تطابق الرمز والبريد فقط |
| `purge_old_partners(status, days)` | المالك عبر API | حذف الطلبات المرفوضة/المؤرشفة الأقدم من مدة (≥ 30 يومًا) |
| `partner_gen_ref_code()` | المشغّلات | توليد رمز المتابعة |

## المشغّلات
- `partners_guard` (قبل الإدخال): توحيد البريد، رمز المتابعة، **30 طلبًا/10 دقائق** عامًا، **3 طلبات/يوم** لكل بريد (رسالتا الخطأ: `rate_limited` و`email_limit`).
- `partners_before_update`: حماية `id` و`created_at` و`ref_code` و`consent` من التعديل، وختم المراجعة.
- `partners_audit`: كتابة سجل التدقيق بعد الإدخال والتعديل والحذف.
- `notify_new_partner` (اختياري): إشعار تيليغرام.
