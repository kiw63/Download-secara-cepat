// Blink Cloudflare Worker starter API.
// This intentionally does not claim to implement TeraBox folder listing or auth.
// Configure D1/R2 and implement a reviewed authentication flow before public launch.
const response = (data, status = 200, headers = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff", ...headers }
  });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const allowed = env.APP_ORIGIN;
    const cors = {};
    if (origin && allowed && origin === allowed) {
      cors["access-control-allow-origin"] = allowed;
      cors["access-control-allow-methods"] = "GET, POST, OPTIONS";
      cors["access-control-allow-headers"] = "content-type, authorization";
      cors["vary"] = "Origin";
    }
    const send = (body, status=200) => response(body,status,cors);
    if (request.method === "OPTIONS") {
      if (!origin || origin !== allowed) return new Response(null,{status:403});
      return new Response(null,{status:204,headers:{...cors,"access-control-max-age":"600"}});
    }
    if (url.pathname === "/api/health" && request.method === "GET") {
      return send({ok:true,service:"Blink API starter",authConfigured:false,storageConfigured:Boolean(env.VIDEOS)});
    }
    if (url.pathname === "/api/videos" && request.method === "GET") {
      if (!env.DB) return send({error:"D1 binding DB belum dikonfigurasi"},503);
      try {
        const result = await env.DB.prepare(
          "SELECT id,title,description,created_at FROM videos WHERE visibility='public' AND storage_status='online' ORDER BY created_at DESC LIMIT 50"
        ).all();
        return send({videos:result.results || []});
      } catch {
        return send({error:"Query database gagal"},500);
      }
    }
    // Deliberately no unauthenticated upload or write endpoints.
    if (url.pathname.startsWith("/api/terabox")) {
      return send({error:"Konektor TeraBox belum tersedia. Jangan menganggap tautan/folder sudah diimpor."},501);
    }
    return send({error:"Not found"},404);
  }
};
