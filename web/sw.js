// Service worker de Scan2Print. El servidor rellena VERSION y las listas a partir de los archivos reales
// de web/ (ver `service_worker()` en server/app/main.py), así no hay nada que mantener a mano.
const VERSION = "/*VERSION*/dev";          // hash del contenido de la app: cambia con cualquier edición
const VENDOR_VERSION = "/*VENDOR*/dev";    // hash de los NOMBRES de vendor/, fonts/ e icons/ (inmutables)
const SHELL = /*SHELL*/[];                 // html, css, js...
const VENDOR = /*VENDORLIST*/[];           // three.js, fuente, iconos

const C_SHELL = `s2p-shell-${VERSION}`;
const C_VENDOR = `s2p-vendor-${VENDOR_VERSION}`;
const C_RUNTIME = "s2p-runtime-1";          // modelos STL y miniaturas
const MAX_STL = 40;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    await (await caches.open(C_SHELL)).addAll(SHELL);
    const vendor = await caches.open(C_VENDOR);
    const have = new Set((await vendor.keys()).map((r) => new URL(r.url).pathname));
    await vendor.addAll(VENDOR.filter((u) => !have.has(new URL(u, self.location).pathname)));  // solo lo que falta
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keep = new Set([C_SHELL, C_VENDOR, C_RUNTIME]);
    await Promise.all((await caches.keys()).filter((k) => !keep.has(k)).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

async function cacheFirst(req, cacheName, { trim } = {}) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) {
    cache.put(req, res.clone());
    if (trim) cache.keys().then((ks) => ks.length > trim && cache.delete(ks[0]));
  }
  return res;
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  const fresh = fetch(req).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; }).catch(() => hit);
  return hit || fresh;
}

self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  const p = url.pathname;
  if (req.mode === "navigate") {                                   // la app es una sola página: el shell, al instante
    e.respondWith(caches.match("index.html", { cacheName: C_SHELL }).then((r) => r || fetch(req)));
  } else if (p.startsWith("/api/")) {
    if (p.endsWith("/pieza.stl") && url.searchParams.has("v")) e.respondWith(cacheFirst(req, C_RUNTIME, { trim: MAX_STL }));
    else if (p.endsWith("/thumb.jpg")) e.respondWith(staleWhileRevalidate(req, C_RUNTIME));
    // el resto de la API siempre va a la red
  } else if (p.startsWith("/vendor/") || p.startsWith("/fonts/") || p.startsWith("/icons/")) {
    e.respondWith(cacheFirst(req, C_VENDOR));
  } else {
    e.respondWith(caches.match(req, { cacheName: C_SHELL }).then((r) => r || fetch(req)));
  }
});
