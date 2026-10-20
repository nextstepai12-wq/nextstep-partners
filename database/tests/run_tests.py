"""
اختبارات قاعدة البيانات (RLS + المشغّلات + الدوال) على PostgreSQL محلي بعد تشغيل 00_local_stubs.sql
ثم السكربتات 01..03 بالترتيب. الاستخدام:
    python3 run_tests.py <dbname>      # يتصل بـ postgres عبر الـ socket المحلي كمستخدم postgres
"""
import sys, uuid, json
import psycopg2
from psycopg2 import errors

db = sys.argv[1] if len(sys.argv) > 1 else "nsdb"
conn = psycopg2.connect(dbname=db, user="postgres", host="/var/run/postgresql")
conn.autocommit = True
cur = conn.cursor()
passed = failed = 0

def ok(name, cond, extra=""):
    global passed, failed
    if cond: passed += 1; print(f"  PASS  {name}")
    else: failed += 1; print(f"  FAIL  {name} {extra}")

def as_role(role, uid=None):
    cur.execute("reset role")
    cur.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid or "",))
    if role: cur.execute(f"set role {role}")

def expect_error(name, sql, params=None, role=None, uid=None, contains=None):
    as_role(role, uid)
    try:
        cur.execute(sql, params)
        ok(name, False, "(no error raised)")
    except Exception as e:
        msg = str(e)
        ok(name, contains is None or contains in msg, f"got: {msg.strip().splitlines()[0]}")
    finally:
        as_role(None)

def run(sql, params=None, role=None, uid=None):
    as_role(role, uid); cur.execute(sql, params)
    try: r = cur.fetchall()
    except psycopg2.ProgrammingError: r = None
    as_role(None); return r

# ---- تحضير المستخدمين ----
cur.execute("delete from public.partner_audit; delete from public.partners; delete from public.partner_admins; delete from auth.users;")
U = {k: str(uuid.uuid4()) for k in ["owner", "admin", "viewer", "plain"]}
for k, v in U.items(): cur.execute("insert into auth.users (id,email) values (%s,%s)", (v, f"{k}@t.com"))
for k in ["owner", "admin", "viewer"]: cur.execute("insert into public.partner_admins (user_id,email,role) values (%s,%s,%s)", (U[k], f"{k}@t.com", k))

BASE = dict(entity_type="شركة", name_ar="شركة المستقبل", country="فلسطين", sector="التقنية",
            description="وصف طويل بما يكفي لاجتياز قيد العشرين حرفًا", contact_name="أحمد الحايك", contact_role="مدير",
            email="Ahmed@Example.com", whatsapp="+970599123456", interests=json.dumps(["رعاية ودعم"]), consent=True)
def ins(**kw):
    d = {**BASE, **kw}; cols = ",".join(d); ph = ",".join(["%s"] * len(d))
    return f"insert into public.partners ({cols}) values ({ph})", list(d.values())

print("\n[1] الزائر (anon)")
s, p = ins(); run(s, p, role="anon")
r = run("select email, ref_code, status, priority from public.partners where name_ar='شركة المستقبل'")[0]
ok("إدخال صالح ينجح", r is not None)
ok("البريد يُوحَّد إلى lowercase", r[0] == "ahmed@example.com", r)
ok("رمز المتابعة يُولَّد من الخادم عند غيابه", r[1].startswith("NS-") and len(r[1]) == 11, r)
s, p = ins(name_ar="شركة ب", email="b@x.com", ref_code="NS-ABCDEFGH"); run(s, p, role="anon")
ok("رمز صالح من المتصفح يُحفظ كما هو", run("select ref_code from public.partners where name_ar='شركة ب'")[0][0] == "NS-ABCDEFGH")
s, p = ins(name_ar="شركة ج", email="c@x.com", ref_code="bad-code"); run(s, p, role="anon")
ok("رمز غير صالح يُستبدل", run("select ref_code from public.partners where name_ar='شركة ج'")[0][0].startswith("NS-"))
expect_error("الزائر لا يقرأ الجدول", "select * from public.partners", role="anon", contains="permission denied")
expect_error("الزائر لا يعدّل", "update public.partners set status='approved'", role="anon", contains="permission denied")
expect_error("الزائر لا يحذف", "delete from public.partners", role="anon", contains="permission denied")
expect_error("الزائر لا يقرأ partner_admins", "select * from public.partner_admins", role="anon", contains="permission denied")
expect_error("الزائر لا يقرأ التدقيق", "select * from public.partner_audit", role="anon", contains="permission denied")
s, p = ins(name_ar="x1", email="x1@x.com", status="approved"); expect_error("لا يفرض status=approved", s, p, role="anon", contains="row-level security")
s, p = ins(name_ar="x2", email="x2@x.com", notes="ملاحظة"); expect_error("لا يكتب notes", s, p, role="anon", contains="row-level security")
s, p = ins(name_ar="x3", email="x3@x.com", priority="high"); expect_error("لا يفرض priority=high", s, p, role="anon", contains="row-level security")
s, p = ins(name_ar="x4", email="x4@x.com", reviewed_by="admin@t.com"); expect_error("لا يزوّر reviewed_by", s, p, role="anon", contains="row-level security")
s, p = ins(name_ar="x5", email="x5@x.com", consent=False); expect_error("الموافقة إلزامية", s, p, role="anon")
s, p = ins(name_ar="x6", email="not-an-email"); expect_error("بريد غير صالح مرفوض", s, p, role="anon", contains="partners_email_fmt")
s, p = ins(name_ar="x7", email="x7@x.com", whatsapp="0599123456"); expect_error("هاتف بلا مفتاح دولة مرفوض", s, p, role="anon", contains="partners_phone_fmt")
s, p = ins(name_ar="x8", email="x8@x.com", website="javascript:alert(1)"); expect_error("رابط غير http مرفوض", s, p, role="anon", contains="partners_web_fmt")
s, p = ins(name_ar="x9", email="x9@x.com", interests="[]"); expect_error("اهتمامات فارغة مرفوضة", s, p, role="anon", contains="partners_interests_fmt")
s, p = ins(name_ar="x10", email="x10@x.com", description="قصير"); expect_error("نبذة قصيرة مرفوضة", s, p, role="anon", contains="violates check constraint")
s, p = ins(); expect_error("تكرار (بريد+اسم) مرفوض", s, p, role="anon", contains="duplicate key")
for i in range(2):
    s, p = ins(name_ar=f"شركة تحديد {i}", email="limit@x.com"); run(s, p, role="anon")
s, p = ins(name_ar="شركة تحديد 3", email="limit@x.com"); run(s, p, role="anon")
s, p = ins(name_ar="شركة تحديد 4", email="limit@x.com"); expect_error("حد 3 طلبات يوميًا لكل بريد", s, p, role="anon", contains="email_limit")

print("\n[2] تتبّع الطلب (partner_track)")
ref = run("select ref_code from public.partners where name_ar='شركة المستقبل'")[0][0]
ok("رمز + بريد صحيحان يعيدان الحالة", len(run("select * from public.partner_track(%s,%s)", (ref, "AHMED@example.com"), role="anon")) == 1)
ok("بريد خاطئ لا يعيد شيئًا", len(run("select * from public.partner_track(%s,%s)", (ref, "other@x.com"), role="anon")) == 0)
ok("رمز خاطئ لا يعيد شيئًا", len(run("select * from public.partner_track(%s,%s)", ("NS-AAAAAAAA", "ahmed@example.com"), role="anon")) == 0)
cols = [d[0] for d in (cur.execute("select * from public.partner_track(%s,%s)", (ref, "ahmed@example.com")) or cur.description)]
ok("التتبّع لا يكشف بيانات شخصية", set(cols) == {"ref_code", "name_ar", "status", "created_at", "updated_at"}, cols)

print("\n[3] مستخدم مسجّل غير إداري")
ok("لا يرى أي صف", run("select count(*) from public.partners", role="authenticated", uid=U["plain"])[0][0] == 0)
as_role("authenticated", U["plain"]); cur.execute("update public.partners set status='approved'"); ok("لا يعدّل أي صف", cur.rowcount == 0); as_role(None)
as_role("authenticated", U["plain"]); cur.execute("delete from public.partners"); ok("لا يحذف أي صف", cur.rowcount == 0); as_role(None)
s, p = ins(name_ar="y1", email="y1@x.com"); expect_error("لا يُدخل كمستخدم مسجّل", s, p, role="authenticated", uid=U["plain"])
ok("لا يرى سجل التدقيق", run("select count(*) from public.partner_audit", role="authenticated", uid=U["plain"])[0][0] == 0)
ok("is_admin=false", run("select public.partner_is_admin()", role="authenticated", uid=U["plain"])[0][0] is False)

print("\n[4] viewer (قراءة فقط)")
ok("يقرأ الطلبات", run("select count(*) from public.partners", role="authenticated", uid=U["viewer"])[0][0] >= 3)
ok("يقرأ سجل التدقيق", run("select count(*) from public.partner_audit", role="authenticated", uid=U["viewer"])[0][0] >= 3)
as_role("authenticated", U["viewer"]); cur.execute("update public.partners set status='contacted'"); ok("لا يعدّل", cur.rowcount == 0); as_role(None)
ok("دوره viewer", run("select public.partner_admin_role()", role="authenticated", uid=U["viewer"])[0][0] == "viewer")
ok("يرى صفه فقط في partner_admins", run("select count(*) from public.partner_admins", role="authenticated", uid=U["viewer"])[0][0] == 1)

print("\n[5] admin (قراءة + تعديل)")
as_role("authenticated", U["admin"])
cur.execute("update public.partners set status='contacted', notes='تم الاتصال', priority='high', tags=%s where ref_code=%s", (["مهم", "تقنية"], ref))
ok("يعدّل الحالة والملاحظات", cur.rowcount == 1); as_role(None)
r = run("select status, notes, priority, tags, reviewed_by, reviewed_at is not null, updated_at > created_at from public.partners where ref_code=%s", (ref,))[0]
ok("reviewed_by = بريد المشرف وreviewed_at مُختوم", r[4] == "admin@t.com" and r[5], r)
ok("الوسوم والأولوية تُحفظ", r[2] == "high" and r[3] == ["مهم", "تقنية"], r)
a = run("select action, actor_email, details->'status'->>'to' from public.partner_audit where partner_name='شركة المستقبل' and action='status_change'")
ok("التدقيق يسجّل تغيير الحالة مع المنفّذ", len(a) == 1 and a[0][1] == "admin@t.com" and a[0][2] == "contacted", a)
as_role("authenticated", U["admin"]); cur.execute("update public.partners set ref_code='NS-ZZZZZZZZ', consent=false where ref_code=%s", (ref,)); as_role(None)
r = run("select ref_code, consent from public.partners where name_ar='شركة المستقبل'")[0]
ok("الحقول الثابتة (ref_code/consent) محمية من التعديل", r[0] == ref and r[1] is True, r)
as_role("authenticated", U["admin"]); cur.execute("delete from public.partners where ref_code=%s", (ref,)); ok("لا يحذف (المالك فقط)", cur.rowcount == 0); as_role(None)
expect_error("لا يضيف مديرين", "insert into public.partner_admins (user_id,email,role) values (%s,'z@t.com','owner')", (U["plain"],), role="authenticated", uid=U["admin"], contains="row-level security")
as_role("authenticated", U["admin"]); cur.execute("update public.partner_admins set role='owner' where user_id=%s", (U["admin"],)); ok("لا يرفع صلاحيته", cur.rowcount == 0); as_role(None)
expect_error("حالة غير صالحة مرفوضة", "update public.partners set status='hacked'", role="authenticated", uid=U["admin"], contains="partners_status_check")

print("\n[6] owner")
ok("يرى كل المديرين", run("select count(*) from public.partner_admins", role="authenticated", uid=U["owner"])[0][0] == 3)
as_role("authenticated", U["owner"]); cur.execute("delete from public.partners where ref_code=%s", (ref,)); ok("يحذف طلبًا", cur.rowcount == 1); as_role(None)
ok("التدقيق يسجّل الحذف", len(run("select 1 from public.partner_audit where action='delete' and actor_email='owner@t.com'")) == 1)
expect_error("purge يرفض غير المالك", "select public.purge_old_partners('declined',365)", role="authenticated", uid=U["admin"], contains="forbidden")
expect_error("purge يرفض حالة غير مسموحة", "select public.purge_old_partners('new',365)", role="authenticated", uid=U["owner"], contains="invalid_status")
expect_error("purge يرفض مدة قصيرة", "select public.purge_old_partners('declined',5)", role="authenticated", uid=U["owner"], contains="too_short")
cur.execute("update public.partners set status='declined' where name_ar='شركة ب'")   # المشغّل يختم reviewed_at بالآن
cur.execute("update public.partners set reviewed_at = now() - interval '400 days' where name_ar='شركة ب'")  # نقدّمه لمحاكاة طلب قديم
ok("purge يحذف المرفوض القديم فقط", run("select public.purge_old_partners('declined',365)", role="authenticated", uid=U["owner"])[0][0] == 1)
expect_error("الزائر لا ينفّذ is_admin", "select public.partner_is_admin()", role="anon", contains="permission denied")

print("\n[7] الحد العام (30 كل 10 دقائق)")
cur.execute("delete from public.partners")
for i in range(30):
    cur.execute("insert into public.partners (entity_type,name_ar,country,sector,description,contact_name,contact_role,email,whatsapp,interests,consent) values ('شركة',%s,'فلسطين','تقنية','وصف طويل بما يكفي لاجتياز قيد العشرين','أحمد الحايك','مدير',%s,'+970599123456','[\"رعاية\"]',true)", (f"ش{i}", f"g{i}@x.com"))
s, p = ins(name_ar="الواحد والثلاثون", email="last@x.com"); expect_error("الحد العام يمنع الإغراق", s, p, role="anon", contains="rate_limited")

print(f"\n=== النتيجة: {passed} ناجح، {failed} فاشل ===")
sys.exit(1 if failed else 0)
