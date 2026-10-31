// Interfaz en caché para abrir rápido; la API siempre va a red. Sube CACHE al cambiar ficheros.
const CACHE = "scan2print-v2";
const SHELL = ["./", "index.html", "manifest.json", "icons/icon.svg", "css/tokens.css", "css/base.css", "css/components.css",
  "js/app.js", "js/api.js", "js/ui.js", "js/router.js", "js/camera.js", "js/viewer.js",
  "js/views/capturar.js", "js/views/trabajos.js", "js/views/detalle.js", "js/views/ajustes.js"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.startsWith("/api/") || u.origin !== location.origin) return;
  e.respondWith(fetch(e.request).then((r) => { const c = r.clone(); caches.open(CACHE).then((x) => x.put(e.request, c)); return r; })
    .catch(() => caches.match(e.request)));
});
