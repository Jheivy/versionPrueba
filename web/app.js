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
    loadJobs();
  } catch (err) {
    $("status").textContent = "Error: " + err.message;
  }
});

async function loadJobs() {
  const jobs = await (await fetch("/api/jobs")).json();
  $("jobs").replaceChildren(...jobs.map((j) => {
    const li = document.createElement("li");
    li.textContent = `${new Date(j.created).toLocaleString()} · ${j.mode} · ${j.status} (${j.inputs.length} fotos)`;
    return li;
  }));
}

loadJobs();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
