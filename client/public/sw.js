const CACHE_NAME = "my-site-cache-v3";
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

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (
    req.method !== "GET" ||
    !(req.url.startsWith("http://") || req.url.startsWith("https://"))
  ) {
    return;
  }
  event.respondWith(
    fetch(req)
      .then((res) => {
        const resClone = res.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(req, resClone);
        });
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
