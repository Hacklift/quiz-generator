const CACHE_NAME = "my-site-cache-v4";
const PRECACHE_URLS = ["/", "/offline.html"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.map((key) => (key === CACHE_NAME ? null : caches.delete(key))),
        ),
      )
      .then(() => clients.claim()),
  );
});

// Only cache same-origin static assets and navigations. API responses
// (cross-origin) and any request carrying credentials must never be
// written to Cache Storage: they contain private user data that would
// otherwise persist on disk after logout.
function isCacheable(req) {
  if (req.method !== "GET") return false;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return false;
  if (req.headers.has("Authorization")) return false;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) {
    return false;
  }
  return true;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (!isCacheable(req)) {
    return;
  }
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && res.type === "basic") {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(req, resClone);
          });
        }
        return res;
      })
      .catch(() => {
        return caches.match(req).then((cached) => {
          if (cached) return cached;
          if (req.mode === "navigate") {
            return caches.match("/offline.html");
          }
          return cached;
        });
      }),
  );
});
