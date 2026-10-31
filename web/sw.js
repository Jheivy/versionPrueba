// Cachea la interfaz para que la PWA abra rápido; la API siempre va a red.
const CACHE = "scan2print-v1";
const SHELL = ["./", "index.html", "app.js", "manifest.json"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))));
self.addEventListener("fetch", (e) => {
  if (new URL(e.request.url).pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
