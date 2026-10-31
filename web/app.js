async function showSTL(canvas, url) {
  try {
    await (await import("./viewer.js")).showSTL(canvas, url);
  } catch (err) {
    canvas.hidden = true; // sin conexión al CDN: se puede seguir descargando el .stl/.scad
    console.warn("visor 3D no disponible", err);
  }
}
const $ = (id) => document.getElementById(id);

$("views").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData();
  const labels = [];
  for (const v of ["planta", "alzado", "perfil"]) {
    const f = $(v).files[0];
    if (f) { fd.append("files", f); labels.push(v); }
  }
  fd.append("mode", "views");
  fd.append("views", labels.join(","));
  $("status").textContent = "Enviando…";
  try {
    const r = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!r.ok) throw new Error((await r.json()).detail);
    $("status").textContent = "Enviado ✔";
    e.target.reset();
    await loadJobs();
    openJob((await (await fetch("/api/jobs")).json())[0].id);
  } catch (err) {
    $("status").textContent = "Error: " + err.message;
  }
});

async function loadJobs() {
  const jobs = await (await fetch("/api/jobs")).json();
  $("jobs").replaceChildren(...jobs.map((j) => {
    const li = document.createElement("li");
    li.textContent = `${new Date(j.created).toLocaleString()} · ${j.mode} · ${j.status} (${j.inputs.length} fotos)`;
    li.onclick = () => openJob(j.id);
    return li;
  }));
}

let current = null, timer = null;

async function openJob(id) {
  current = id;
  clearTimeout(timer);
  const j = await (await fetch(`/api/jobs/${id}`)).json();
  $("detail").hidden = false;
  $("dtitle").textContent = `Trabajo ${id.slice(0, 8)}`;
  const msg = { done: "Listo ✔", error: "Error: " + j.error, processing: "Procesando…", uploaded: "En cola…" };
  $("dstatus").textContent = msg[j.status] || j.status;
  if (j.status === "uploaded" || j.status === "processing") {
    timer = setTimeout(() => current === id && openJob(id), 1500);
    return;
  }
  const d = j.dims;
  $("ddims").textContent = d ? `Medidas actuales: ${d.ancho.toFixed(1)} × ${d.fondo.toFixed(1)} × ${d.alto.toFixed(1)} mm (X × Y × Z)` : "";
  for (const [k, v] of Object.entries(j.params || {})) $("params").elements[k].value = v;
  $("dlinks").replaceChildren(...j.outputs.map((o) => {
    const a = document.createElement("a");
    a.href = `/api/jobs/${id}/files/${o}`; a.textContent = o; a.download = o; a.style.marginRight = "12px";
    return a;
  }));
  await showSTL($("view"), j.outputs.includes("pieza.stl") ? `/api/jobs/${id}/files/pieza.stl` : null);
}

$("params").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {};
  for (const el of e.target.elements) if (el.name && el.value !== "") body[el.name] = Number(el.value);
  $("dstatus").textContent = "Regenerando…";
  await fetch(`/api/jobs/${current}/params`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  setTimeout(() => openJob(current), 800);
});

loadJobs();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
