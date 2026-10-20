// Edge Function (المستوى الثاني): تتحقق من Cloudflare Turnstile ثم تُدخل الطلب بمفتاح الخدمة.
// الأسرار المطلوبة: TURNSTILE_SECRET  (SUPABASE_URL و SUPABASE_SERVICE_ROLE_KEY متوفرتان تلقائيًا)
// مهم: أوقف "Verify JWT" لهذه الدالة (يتم التحقق عبر Turnstile).
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*", // يُفضّل تقييدها برابط موقعك بعد التجربة
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (b: unknown, status = 200) =>
  new Response(JSON.stringify(b), { status, headers: { ...cors, "Content-Type": "application/json" } });

const ALLOWED = [
  "ref_code",
  "entity_type","name_ar","name_en","country","city","sector","founded_year","team_size",
  "website","social_links","logo_url","description","contact_name","contact_role","email","whatsapp",
  "interests","offers","needs","reach","past_events",
];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);

  let body: Record<string, unknown>;
  try { body = await req.json(); } catch { return json({ error: "bad_json" }, 400); }

  const token = String(body.turnstile_token ?? "");
  if (!token) return json({ error: "captcha_required" }, 403);

  const form = new FormData();
  form.append("secret", Deno.env.get("TURNSTILE_SECRET") ?? "");
  form.append("response", token);
  const ip = req.headers.get("cf-connecting-ip");
  if (ip) form.append("remoteip", ip);

  const verify = await (await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: form })).json();
  if (!verify.success) return json({ error: "captcha_failed" }, 403);

  const row: Record<string, unknown> = {};
  for (const k of ALLOWED) if (k in body) row[k] = body[k];
  row.consent = true;

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { error } = await sb.from("partners").insert(row);
  if (error) {
    if (error.code === "23505") return json({ error: "duplicate" }, 409);
    if (/rate_limited|email_limit/.test(error.message)) return json({ error: error.message }, 429);
    return json({ error: "invalid" }, 400);
  }
  return json({ ok: true }, 201);
});
