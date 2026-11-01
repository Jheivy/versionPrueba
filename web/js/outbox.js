/** Bandeja de salida: las capturas se guardan en el móvil (IndexedDB) antes de subirse y se reintentan solas.
 *  Así un corte de Wi-Fi, cerrar la pantalla o recargar la app no hace perder fotos ni vídeos.
 *  Cada envío lleva un `client_id`: si el Mac ya lo recibió y se perdió la respuesta, el reintento no duplica. */
import { authFetch, upload } from "./api.js";

const DB = "s2p-outbox", STORE = "items";
const BACKOFF = [5, 30, 120, 300];                  // segundos entre reintentos automáticos
let dbp = null, cache = [], flushing = false, timer = 0, misses = 0, started = false;
const progress = {};                                // id -> 0..1 mientras se sube
const inflight = new Set();                         // entradas que se están subiendo ahora (flush no las toca)

const openDb = () => (dbp ??= new Promise((ok, fail) => {
  if (!("indexedDB" in self)) return fail(new Error("sin IndexedDB"));
  const r = indexedDB.open(DB, 1);
  r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "id" });
  r.onsuccess = () => ok(r.result);
  r.onerror = () => fail(r.error);
}).catch((e) => { dbp = null; throw e; }));

async function run(mode, fn) {
  const db = await openDb();
  return new Promise((ok, fail) => {
    const t = db.transaction(STORE, mode);
    const req = fn(t.objectStore(STORE));
    t.oncomplete = () => ok(req?.result);
    t.onerror = t.onabort = () => fail(t.error);
  });
}
const put = (item) => run("readwrite", (s) => s.put(item));
const drop = (id) => run("readwrite", (s) => s.delete(id));
const all = () => run("readonly", (s) => s.getAll());

const newId = () => [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
const sizeOf = (e) => e.files.reduce((n, [, blob]) => n + blob.size, 0);

/** Lo que ve la interfaz de cada entrada (sin los blobs). */
const view = (e) => ({ id: e.id, name: e.name, fields: e.fields, created: e.created, state: e.state, error: e.error, size: sizeOf(e), progress: progress[e.id] });

function emit() {
  dispatchEvent(new CustomEvent("s2p:outbox", { detail: { items: cache.map(view), count: cache.length } }));
}
async function refresh() {
  try { cache = (await all()).sort((a, b) => a.created - b.created); } catch { cache = []; }
  emit();
}

/** Sube una entrada. Si ya hubo un intento, primero mira si el Mac ya la tiene (respuesta perdida). */
async function send(entry, onProgress) {
  if (entry.tries > 0) {
    const r = await authFetch(`/api/jobs/${entry.id}`).catch(() => null);
    if (r?.ok) return r.json();
  }
  const fd = new FormData();
  for (const [field, blob, name] of entry.files) fd.append(field, blob, name);
  for (const [k, v] of entry.fields) fd.append(k, v);
  fd.append("client_id", entry.id);
  return upload("/jobs", fd, (p) => { progress[entry.id] = p; onProgress?.(p); emit(); });
}

/** Guarda y envía. Devuelve { job } si subió, o { queued: true, id } si no hubo red y quedó guardado.
 *  Un error del Mac (límite, formato…) no se encola: se lanza para que la pantalla lo muestre. */
export async function submit({ fields, files, name }, onProgress) {
  const entry = { id: newId(), fields, files, name: name || "", created: Date.now(), tries: 0, state: "sending", error: "" };
  let stored = true;
  try { await put(entry); } catch { stored = false; }          // sin almacenamiento: se envía directo, como antes
  await refresh();
  inflight.add(entry.id);
  try {
    const job = await send(entry, onProgress);
    if (stored) await drop(entry.id).catch(() => {});
    delete progress[entry.id];
    inflight.delete(entry.id);
    await refresh();
    return { job };
  } catch (e) {
    delete progress[entry.id];
    inflight.delete(entry.id);
    if (stored && (e.network || e.status === 401)) {
      await put({ ...entry, state: "pending", tries: 1 }).catch(() => {});
      await refresh();
      schedule();
      return { queued: true, id: entry.id };
    }
    if (stored) await drop(entry.id).catch(() => {});
    await refresh();
    throw e;
  }
}

/** Reintenta todo lo pendiente, de uno en uno. Para al primer fallo de red. */
export async function flush() {
  if (flushing) return;
  flushing = true;
  clearTimeout(timer);
  let offline = false;
  try {
    await refresh();
    for (const entry of cache.filter((e) => e.state !== "failed" && !inflight.has(e.id))) {
      inflight.add(entry.id);
      try {
        await put({ ...entry, state: "sending" });
        await refresh();
        await send(entry);
        await drop(entry.id);
        misses = 0;
      } catch (e) {
        if (e.network || e.status === 401) { await put({ ...entry, state: "pending", tries: entry.tries + 1 }); offline = true; break; }
        await put({ ...entry, state: "failed", error: e.message, tries: entry.tries + 1 });   // lo rechazó el Mac: no se reintenta solo
      } finally {
        delete progress[entry.id];
        inflight.delete(entry.id);
      }
    }
  } finally {
    flushing = false;
    await refresh();
    if (offline) misses += 1;
    schedule();
  }
}

function schedule() {
  clearTimeout(timer);
  if (!cache.some((e) => e.state === "pending")) return;
  timer = setTimeout(flush, BACKOFF[Math.min(misses, BACKOFF.length - 1)] * 1000);
}

export const list = () => cache.map(view);
export const load = refresh;                        // lee la bandeja del disco (al abrir Trabajos)
export async function remove(id) { await drop(id).catch(() => {}); await refresh(); }
export async function retry(id) {
  const e = cache.find((x) => x.id === id);
  if (e) { await put({ ...e, state: "pending" }); misses = 0; }
  return flush();
}

/** Arranca los reintentos automáticos: al arrancar, al volver la red y al volver a la app. */
export function startOutbox() {
  if (started) return;
  started = true;
  addEventListener("online", () => { misses = 0; flush(); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && cache.length) flush(); });
  setTimeout(flush, 800);
}
