const { Readable } = require("node:stream");

const ORIGIN = "https://ethan-erp-lms.onrender.com";
const DROP_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "content-length",
  "accept-encoding",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);
const DROP_RESPONSE_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);

module.exports = async function proxy(req, res) {
  try {
    const incoming = new URL(req.url || "/", "https://lms.ethandigitalacademy.org");
    const originalPath = incoming.searchParams.get("__ethan_proxy_path") || "/";
    incoming.searchParams.delete("__ethan_proxy_path");

    const target = new URL(ORIGIN);
    target.pathname = originalPath.startsWith("/") ? originalPath : "/" + originalPath;
    target.search = incoming.searchParams.toString();

    const headers = new Headers();
    for (const [name, rawValue] of Object.entries(req.headers || {})) {
      const key = name.toLowerCase();
      if (DROP_REQUEST_HEADERS.has(key) || rawValue == null) continue;
      const value = Array.isArray(rawValue) ? rawValue.join(", ") : String(rawValue);
      headers.set(key, value);
    }
    headers.set("accept-encoding", "identity");
    headers.set("x-forwarded-host", String(req.headers.host || "lms.ethandigitalacademy.org"));
    headers.set("x-forwarded-proto", "https");

    const init = {
      method: req.method || "GET",
      headers,
      redirect: "manual"
    };
    if (init.method !== "GET" && init.method !== "HEAD") {
      init.body = req;
      init.duplex = "half";
    }

    const upstream = await fetch(target, init);
    res.statusCode = upstream.status;

    for (const [name, value] of upstream.headers) {
      const key = name.toLowerCase();
      if (DROP_RESPONSE_HEADERS.has(key) || key === "set-cookie") continue;
      if (key === "location") {
        try {
          const location = new URL(value, ORIGIN);
          if (location.origin === ORIGIN) location.host = String(req.headers.host || "lms.ethandigitalacademy.org");
          res.setHeader(name, location.toString());
        } catch {
          res.setHeader(name, value);
        }
      } else {
        res.setHeader(name, value);
      }
    }

    const cookies = typeof upstream.headers.getSetCookie === "function"
      ? upstream.headers.getSetCookie()
      : (upstream.headers.get("set-cookie") ? [upstream.headers.get("set-cookie")] : []);
    if (cookies.length) res.setHeader("set-cookie", cookies);

    if (init.method === "HEAD" || !upstream.body) {
      res.end();
      return;
    }
    Readable.fromWeb(upstream.body).pipe(res);
  } catch (error) {
    console.error("ETHAN LEARN proxy error:", error);
    if (!res.headersSent) {
      res.statusCode = 502;
      res.setHeader("content-type", "text/plain; charset=utf-8");
      res.end("ETHAN LEARN is temporarily unable to reach its application server. Please try again shortly.");
    } else {
      res.destroy(error);
    }
  }
};
