export async function api(path, opts) {
  let r;
  try { r = await fetch("/api" + path, opts); } catch { throw new Error("Sin conexión con el Mac"); }
  if (!r.ok) {
    let d; try { d = (await r.json()).detail; } catch { /* sin cuerpo */ }
    throw new Error(typeof d === "string" ? d : `Error ${r.status}`);
  }
  return r.status === 204 ? null : r.json();
}
export const post = (p, body) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
export const patch = (p, body) => api(p, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
export const del = (p) => api(p, { method: "DELETE" });

/** POST multipart con progreso (0..1). */
export function upload(path, fd, onProgress) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open("POST", "/api" + path);
    x.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    x.onload = () => {
      let b; try { b = JSON.parse(x.responseText); } catch { /* sin cuerpo */ }
      x.status < 300 ? resolve(b) : reject(new Error(typeof b?.detail === "string" ? b.detail : `Error ${x.status}`));
    };
    x.onerror = () => reject(new Error("Sin conexión con el Mac"));
    x.send(fd);
  });
}

export const pref = (k, d) => { try { const v = localStorage.getItem("s2p." + k); return v == null ? d : JSON.parse(v); } catch { return d; } };
export const setPref = (k, v) => { try { localStorage.setItem("s2p." + k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } };
