import asyncio, json, re, sys, os
from playwright.async_api import async_playwright
BASE=os.environ.get("SITE","http://127.0.0.1:8765")+"/index.html"; ROOT=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..")); SBU="https://fwlwkshvrxhctplfbdfq.supabase.co"
res=[]
def ok(n,c,x=""):
    res.append(bool(c)); print(("  PASS  " if c else "  FAIL  ")+n+(f"   {x}" if not c else ""))
async def mk(b,vp,mobile=False):
    ctx=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await ctx.new_page(); pg.errs=[]
    pg.on("pageerror",lambda e:pg.errs.append(str(e)))
    pg.on("console",lambda m: pg.errs.append("console:"+m.text) if m.type=="error" and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    await pg.route("https://fonts.googleapis.com/**",lambda r:r.fulfill(status=200,content_type="text/css",body=""))
    return ctx,pg
async def fill_all(pg, email="Ahmed@Example.com"):
    await pg.evaluate("document.getElementById('register').scrollIntoView()"); await pg.wait_for_timeout(300)
    await pg.select_option("#entity_type",index=1); await pg.select_option("#sector",index=1)
    await pg.fill("#name_ar","شركة المستقبل للتقنية"); await pg.fill("#country","فلسطين"); await pg.fill("#description","شركة تقنية تعمل على تطوير حلول رقمية للشركات الناشئة.")
    await pg.click("#nextBtn"); await pg.wait_for_timeout(400)
    await pg.fill("#contact_name","أحمد الحايك"); await pg.fill("#contact_role","مدير الشراكات"); await pg.fill("#email",email); await pg.fill("#whatsapp","0599 123 456")
    await pg.click("#nextBtn"); await pg.wait_for_timeout(400)
    await pg.click(".cb:nth-child(1) span"); await pg.click("#nextBtn"); await pg.wait_for_timeout(300)
    await pg.check("#consent"); await pg.wait_for_timeout(4600)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        print("\n[1] الصفحة والمحتوى")
        ctx,pg=await mk(b,{"width":1366,"height":900}); seen={}
        async def ins(route):
            if route.request.method=="POST": seen['body']=json.loads(route.request.post_data)
            await route.fulfill(status=int(os.environ.get("INS","201")),body="")
        await pg.route(SBU+"/rest/v1/partners",ins)
        await pg.goto(BASE); await pg.add_style_tag(content="html{scroll-behavior:auto!important}"); await pg.wait_for_timeout(1200)
        ok("بلا تمدد جانبي (ديسكتوب)", await pg.evaluate("document.documentElement.scrollWidth")==1366)
        ok("صورة المؤسس تُحمَّل", await pg.evaluate("document.getElementById('fPhoto').classList.contains('ok') && document.getElementById('fPhoto').naturalWidth>300"))
        ok("رابط لينكدإن المؤسس صحيح", await pg.get_attribute(".founder .f-link","href")=="https://www.linkedin.com/in/ahmedalhayek/")
        ok("روابط لينكدإن/إنستغرام/واتساب في قسم التواصل", all([await pg.locator(f'#connect a[href*="{k}"]').count()==1 for k in ["linkedin.com/in/nextstep-ai","instagram.com/nextstepai12","chat.whatsapp.com/JEzuy1JozEv0ubOZ74QXQs"]]))
        ok("أقسام الأسئلة والتتبّع والتسجيل موجودة", all([await pg.locator(s).count()==1 for s in ["#faq","#track","#register"]]))
        await pg.locator("#faq summary").first.click(); ok("الأسئلة الشائعة تُفتح", await pg.evaluate("document.querySelector('#faq details').open"))
        og=await pg.evaluate("document.querySelector('meta[property=\"og:image\"]').content"); ok("og:image رابط مطلق إلى JPG", og.startswith("https://") and og.endswith(".jpg"), og)
        ok("ملف og-image موجود وأقل من 300KB", os.path.getsize(os.path.join(ROOT,"assets","og-image.jpg"))<300*1024)
        print("\n[2] التسجيل + رمز المتابعة")
        await fill_all(pg); await pg.click("#nextBtn"); await pg.wait_for_timeout(1000)
        bd=seen.get('body',{})
        ok("الإرسال تم", bool(bd))
        ok("ref_code بصيغة NS-XXXXXXXX", re.fullmatch(r"NS-[A-Z2-7]{8}",bd.get("ref_code","")) is not None, bd.get("ref_code"))
        ok("الهاتف E.164", bd.get("whatsapp")=="+970599123456", bd.get("whatsapp"))
        ok("البريد كما أُدخل (التوحيد في الخادم)", bd.get("email")=="ahmed@example.com", bd.get("email"))
        ok("consent=true ولا حقول إدارية في الإرسال", bd.get("consent") is True and not any(k in bd for k in ["status","notes","priority","tags","reviewed_by"]), list(bd))
        ok("شاشة النجاح تعرض نفس الرمز", (await pg.inner_text("#refVal"))==bd["ref_code"])
        await pg.click("#copyRef"); await pg.wait_for_timeout(300)
        ok("نموذج التتبّع يُملأ تلقائيًا من الجهاز", await pg.input_value("#t_ref")==bd["ref_code"] and await pg.input_value("#t_email")=="ahmed@example.com")
        ok("لا أخطاء JS (تسجيل)", not pg.errs, pg.errs); ref=bd["ref_code"]
        print("\n[3] تتبّع الطلب")
        state={"status":"new"}
        async def rpc(route):
            body=json.loads(route.request.post_data)
            if state.get("none") or body["p_ref"]!=ref: return await route.fulfill(status=200,content_type="application/json",body="[]")
            await route.fulfill(status=200,content_type="application/json",body=json.dumps([dict(ref_code=ref,name_ar="شركة المستقبل للتقنية",status=state["status"],created_at="2026-10-10T10:00:00Z",updated_at="2026-10-12T10:00:00Z")]))
        await pg.route(SBU+"/rest/v1/rpc/partner_track",rpc)
        await pg.evaluate("document.getElementById('track').scrollIntoView()")
        exp={"new":(2,False),"contacted":(3,False),"in_progress":(3,False),"approved":(4,False),"declined":(4,True),"archived":(4,True)}
        for st,(on,bad) in exp.items():
            state["status"]=st; await pg.wait_for_timeout(3100); await pg.click("#trackBtn"); await pg.wait_for_selector("#tres.show"); await pg.wait_for_timeout(150)
            n_on=await pg.evaluate("[...document.querySelectorAll('#tl div')].filter(d=>d.classList.contains('on')).length"); has_bad=await pg.evaluate("!!document.querySelector('#tl div.bad')")
            msg=await pg.inner_text("#tMsg")
            ok(f"حالة {st}: {on} مراحل مضيئة{' + مرحلة قرار حمراء' if bad else ''}", n_on==on and has_bad==bad and len(msg)>10, (n_on,has_bad))
        await pg.fill("#t_email","wrong@x.com"); state["none"]=True; await pg.wait_for_timeout(3100); await pg.click("#trackBtn"); await pg.wait_for_timeout(500)
        ok("بيانات غير مطابقة → رسالة 'لم نعثر'", "لم نعثر" in await pg.inner_text("#tName") and await pg.evaluate("document.getElementById('tMsg').classList.contains('nf')"))
        await pg.fill("#t_ref","BAD"); await pg.wait_for_timeout(3100); await pg.click("#trackBtn"); ok("رمز بصيغة خاطئة يُرفض قبل الإرسال", "غير صحيح" in await pg.inner_text("#trackErr"))
        await pg.fill("#t_ref",ref); await pg.fill("#t_email","bad-mail"); await pg.click("#trackBtn"); ok("بريد غير صالح يُرفض", "البريد" in await pg.inner_text("#trackErr"))
        await pg.fill("#t_email","ahmed@example.com"); state["none"]=False; await pg.wait_for_timeout(3100); await pg.click("#trackBtn"); await pg.wait_for_timeout(150); await pg.click("#trackBtn"); await pg.wait_for_timeout(200)
        ok("منع الطلبات المتتالية (3 ثوانٍ)", "انتظر" in await pg.inner_text("#trackErr"))
        ok("لا أخطاء JS (تتبّع)", not pg.errs, pg.errs); await ctx.close()
        print("\n[4] طلب مكرر (409)")
        os.environ["INS"]="409"; ctx,pg=await mk(b,{"width":390,"height":844},True)
        async def ins409(route): await route.fulfill(status=409,body="{}")
        await pg.route(SBU+"/rest/v1/partners",ins409); await pg.goto(BASE); await fill_all(pg); await pg.click("#nextBtn"); await pg.wait_for_timeout(900)
        ok("المكرر: عنوان 'مسجّل مسبقًا' وإخفاء الرمز", "مسبقًا" in await pg.inner_text("#okTitle") and not await pg.is_visible("#refBox"))
        await ctx.close()
        print("\n[5] أحجام الجوال")
        for w,h in [(360,740),(390,844),(768,1024)]:
            ctx,pg=await mk(b,{"width":w,"height":h},True); await pg.goto(BASE); await pg.wait_for_timeout(900)
            sw=await pg.evaluate("document.documentElement.scrollWidth")
            wide=await pg.evaluate("[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return (r.right>innerWidth+1||r.left<-1)&&!e.closest('.chip,.tilt,#sticky,#cv,#dots,.hp,.sc-orb,.showcase')}).map(e=>e.tagName+'.'+e.className).slice(0,4)")
            sway=await pg.evaluate("getComputedStyle(document.querySelector('.tilt')).animationName")
            ok(f"{w}px: بلا تمدد جانبي وبلا عناصر خارجة", sw==w and not wide, (sw,wide))
            ok(f"{w}px: حركة 3D تلقائية على اللمس", sway=="sway", sway)
            if w==390:
                await pg.evaluate("document.querySelector('.founder').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(1400); await pg.screenshot(path="/tmp/pub_m_founder.png")
                await pg.evaluate("document.querySelector('#track').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(1200); await pg.screenshot(path="/tmp/pub_m_track.png")
            ok(f"{w}px: لا أخطاء JS", not pg.errs, pg.errs); await ctx.close()
        print("\n[6] الـ3D على الديسكتوب")
        ctx,pg=await mk(b,{"width":1366,"height":900}); await pg.goto(BASE); await pg.add_style_tag(content="html{scroll-behavior:auto!important}"); await pg.wait_for_timeout(800)
        async def go(sel): await pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{block:'center'}})"); await pg.wait_for_timeout(1700)
        async def tilt(host,el,name,shot=None):
            await go(host); bb=await (await pg.query_selector(host)).bounding_box()
            await pg.mouse.move(bb['x']+bb['width']*.12,bb['y']+bb['height']*.15); await pg.wait_for_timeout(500)
            t1=await pg.evaluate("(s)=>getComputedStyle(document.querySelector(s)).transform",el)
            await pg.mouse.move(bb['x']+bb['width']*.88,bb['y']+bb['height']*.85); await pg.wait_for_timeout(500)
            t2=await pg.evaluate("(s)=>getComputedStyle(document.querySelector(s)).transform",el)
            if shot: await pg.screenshot(path=shot)
            await pg.mouse.move(2,2); await pg.wait_for_timeout(700)
            t3=await pg.evaluate("(s)=>getComputedStyle(document.querySelector(s)).transform",el)
            rest=t3=='none' or t3.startswith('matrix3d(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1') or t3=='matrix(1, 0, 0, 1, 0, 0)'
            ok(f"3D {name}: يميل ويعود لوضعه", 'matrix3d' in t1 and 'matrix3d' in t2 and t1!=t2 and rest, (t1[:30],t3[:30]))
        await tilt('#scene','#tilt','المجسّم الرئيسي','/tmp/pub_tilt_hero.png')
        await tilt('#showcase','#scCard','بطاقة الشعار')
        await tilt('.card','.card','بطاقات الخدمات')
        await tilt('#pcScene','#pcard','بطاقة الشريك')
        ok("لا تمدد جانبي بعد الميل", await pg.evaluate("document.documentElement.scrollWidth")==1366)
        ok("لا أخطاء JS (3D)", not pg.errs, pg.errs); await ctx.close()
        await b.close()
    f=res.count(False); print(f"\n=== {res.count(True)} ناجح، {f} فاشل ==="); sys.exit(1 if f else 0)
asyncio.run(main())
