import json, re, time, uuid, random, urllib.parse
SB="https://fwlwkshvrxhctplfbdfq.supabase.co"
USERS={"owner@t.com":("pass1","owner"),"admin@t.com":("pass2","admin"),"viewer@t.com":("pass3","viewer"),"plain@t.com":("pass4",None)}
def make_data():
    random.seed(7); types=["شركة","فريق","جامعة / كلية","مؤسسة / منظمة","مبادرة","شركة ناشئة"]; countries=["فلسطين","الأردن","مصر","السعودية","تركيا"]
    sectors=["التقنية والمعلومات","التعليم والتدريب","الصحة","الإعلام والتسويق"]; ints=["ورش وفعاليات مشتركة","تدريب وتأهيل","توظيف وتدريب ميداني","رعاية ودعم","مشاريع تقنية مشتركة","محتوى وتوعية"]
    sts=["new","new","new","contacted","in_progress","approved","declined","archived"]
    rows=[]
    for i in range(40):
        d=time.time()-random.randint(0,40)*86400-random.randint(0,80000)
        rows.append(dict(id=str(uuid.UUID(int=i+1)),created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(d)),updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(d)),
          status=random.choice(sts),notes=None,priority=random.choice(["normal","normal","high","low"]),tags=[],reviewed_by=None,reviewed_at=None,
          ref_code="NS-"+"".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567") for _ in range(8)),
          entity_type=random.choice(types),name_ar=f"جهة رقم {i+1}",name_en=f"Org {i+1}",country=random.choice(countries),city="غزة",sector=random.choice(sectors),
          founded_year=2015+i%10,team_size="6–20",website="https://example.com",social_links="https://linkedin.com/company/x",logo_url=None,
          description="وصف طويل بما يكفي لعرضه في لوحة الإدارة للاختبار.",contact_name="أحمد الحايك",contact_role="مدير",email=f"p{i}@x.com",whatsapp="+970599123456",
          interests=random.sample(ints,random.randint(1,3)),offers="نقدّم تدريبًا",needs="نحتاج دعمًا",reach="100–500",past_events=None,consent=True))
    # صفوف خبيثة
    rows[0].update(name_ar='<img src=x onerror="window.__xss=1">XSS-TEST',website="javascript:alert(1)",social_links="javascript:alert(2) و https://ok.example.com",email='a"><script>window.__xss=2</script>@x.com',status="new",
                   created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(time.time()-9*86400)))
    rows[1].update(name_ar='=HYPERLINK("http://evil","click")',description="+cmd|' /C calc'!A0 وصف طويل بما يكفي")
    return rows
class Backend:
    def __init__(s): s.P=make_data(); s.AUD=[]; s.token_user={}; s.calls=[]; s.refreshes=0
    def user_for(s,req):
        a=req.headers.get("authorization","").replace("Bearer ","")
        return s.token_user.get(a)
    async def handle(s,route):
        req=route.request; u=urllib.parse.urlparse(req.url); path=u.path; q=urllib.parse.parse_qs(u.query); m=req.method
        s.calls.append((m,path+("?"+u.query if u.query else "")))
        H={"access-control-allow-origin":"*","access-control-allow-headers":"*","access-control-allow-methods":"*","content-type":"application/json"}
        if m=="OPTIONS": return await route.fulfill(status=204,headers=H)
        def J(code,obj,extra=None): return route.fulfill(status=code,headers={**H,**(extra or {})},body=json.dumps(obj))
        if path=="/auth/v1/token":
            body=json.loads(req.post_data or "{}")
            if q["grant_type"][0]=="password":
                e=body.get("email"); 
                if e in USERS and USERS[e][0]==body.get("password"):
                    tok="at-"+uuid.uuid4().hex; s.token_user[tok]=dict(id=str(uuid.uuid5(uuid.NAMESPACE_DNS,e)),email=e,role=USERS[e][1])
                    return await J(200,dict(access_token=tok,refresh_token="rt-"+e,expires_in=3600,user=dict(id=s.token_user[tok]["id"],email=e)))
                return await J(400,dict(error_code="invalid_credentials",msg="bad"))
            else:
                e=body["refresh_token"].replace("rt-",""); s.refreshes+=1
                tok="at-"+uuid.uuid4().hex; s.token_user[tok]=dict(id=str(uuid.uuid5(uuid.NAMESPACE_DNS,e)),email=e,role=USERS[e][1])
                return await J(200,dict(access_token=tok,refresh_token="rt-"+e,expires_in=3600,user=dict(id=s.token_user[tok]["id"],email=e)))
        if path=="/auth/v1/logout": return await route.fulfill(status=204,headers=H)
        usr=s.user_for(req)
        if not usr: return await J(401,dict(message="JWT expired"))
        if path=="/rest/v1/partner_admins":
            return await J(200,[dict(role=usr["role"],email=usr["email"])] if usr["role"] else [])
        if not usr["role"]: return await J(200,[])
        if path=="/rest/v1/partners":
            if m=="GET":
                rng=req.headers.get("range","0-999").split("-"); a,b=int(rng[0]),int(rng[1])
                rows=sorted(s.P,key=lambda r:r["created_at"],reverse=True)[a:b+1]; return await J(200,rows)
            ids=None
            if "id" in q:
                v=q["id"][0]
                if v.startswith("eq."): ids=[v[3:]]
                elif v.startswith("in."): ids=v[4:-1].split(",")
            if m=="PATCH":
                if usr["role"]=="viewer": return await J(200,[])
                body=json.loads(req.post_data); out=[]
                for r in s.P:
                    if r["id"] in ids:
                        old=dict(r); r.update(body); r["updated_at"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
                        if body.get("status") and body["status"]!=old["status"]: r["reviewed_by"]=usr["email"]; r["reviewed_at"]=r["updated_at"]
                        diff={k:{"from":old[k],"to":r[k]} for k in body if old.get(k)!=r.get(k)}
                        if diff: s.AUD.insert(0,dict(id=len(s.AUD)+1,at=r["updated_at"],partner_id=r["id"],partner_name=r["name_ar"],action="status_change" if "status" in diff else ("notes_update" if "notes" in diff else "field_update"),actor_email=usr["email"],details=diff))
                        out.append(r)
                return await J(200,out)
            if m=="DELETE":
                if usr["role"]!="owner": return await J(200,[])
                out=[r for r in s.P if r["id"] in ids]; s.P=[r for r in s.P if r["id"] not in ids]
                for r in out: s.AUD.insert(0,dict(id=len(s.AUD)+1,at=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),partner_id=r["id"],partner_name=r["name_ar"],action="delete",actor_email=usr["email"],details={}))
                return await J(200,out)
        if path=="/rest/v1/partner_audit": return await J(200,s.AUD[:500])
        return await J(404,dict(message="nf"))
