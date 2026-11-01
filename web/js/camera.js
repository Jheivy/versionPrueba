import { h, haptic, icon, pickFile, toast } from "./ui.js";
import { authFetch, pref, setPref } from "./api.js";
import { submit } from "./outbox.js";
import { prepareImage } from "./image.js";
import { navigate } from "./router.js";

const VIEWS = [
  ["planta", "Planta", "Contorno de la pieza visto desde arriba, en negro sobre la hoja"],
  ["alzado", "Alzado", "Contorno visto de frente (opcional)"],
  ["perfil", "Perfil", "Contorno visto de lado (opcional)"],
];

async function openStream(video) {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" }, width: { ideal: 2560 }, height: { ideal: 1440 } }, audio: false });
  video.srcObject = stream;
  await video.play().catch(() => {});
  return stream;
}

/** Cada ~700 ms manda un fotograma reducido a /api/detect. Devuelve stop(). */
function startDetect(video, onResult) {
  let stop = false, busy = false, t = 0;
  const c = document.createElement("canvas");
  const loop = async () => {
    if (stop) return;
    if (!busy && video.videoWidth) {
      busy = true;
      const s = Math.min(1, 640 / video.videoWidth);
      c.width = Math.round(video.videoWidth * s); c.height = Math.round(video.videoHeight * s);
      c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
      try {
        const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.6));
        const fd = new FormData(); fd.append("file", blob, "f.jpg");
        const r = await authFetch("/api/detect", { method: "POST", body: fd });
        if (!stop) onResult(r.ok ? await r.json() : null);
      } catch { if (!stop) onResult(null); }
      busy = false;
    }
    t = setTimeout(loop, 700);
  };
  loop();
  return () => { stop = true; clearTimeout(t); };
}

/** Tras enviar: al trabajo creado, o a la lista si no hubo red y la captura quedó guardada en el móvil. */
function done(res) {
  if (res.queued) { toast("Sin conexión con el Mac: guardado en el móvil, se enviará solo"); navigate("/trabajos"); }
  else navigate(`/trabajos/${res.job.id}`);
}

const closeBtn = () => h("a", { class: "icon-btn", href: "#/capturar", "aria-label": "Cerrar cámara" }, icon("close"));
const stopStream = (s) => s?.getTracks().forEach((t) => t.stop());

/* =================== 3 vistas =================== */
export function camaraVistas(root) {
  let stream = null, stopDetect = null, step = 0, shots = {}, urls = [], gone = false, last = null, fromSummary = false;
  const video = h("video", { playsInline: true, muted: true, autoplay: true, "aria-hidden": "true" });
  const cam = h("div", { class: "cam" }, video);
  root.append(cam);

  const cleanup = () => { gone = true; stopDetect?.(); stopStream(stream); urls.forEach(URL.revokeObjectURL); };
  const urlOf = (b) => { const u = URL.createObjectURL(b); urls.push(u); return u; };

  async function boot() {
    try { stream = await openStream(video); } catch { stream = null; }
    if (gone) return stopStream(stream);
    if (stream) stopDetect = startDetect(video, (r) => { last = r; paintStatus(); });
    renderCamera();
  }

  /* --- cámara --- */
  let hintEl, lightsEl, guideEl, shutterEl, forceEl;
  function paintStatus() {
    if (!hintEl) return;
    const ok = !!last?.ok;
    hintEl.className = "hint" + (ok ? " ok" : "");
    hintEl.textContent = !last ? "Comprobando cámara…" : last.hint;
    guideEl.classList.toggle("ok", ok);
    shutterEl.disabled = !ok;
    forceEl.hidden = ok || !last;
    const chip = (t, v) => h("span", { class: "chip " + (v ? "ok" : "err") }, t);
    lightsEl.replaceChildren(...(last ? [chip(`Hoja ${last.markers}/4`, last.checks.hoja), chip("Nitidez", last.checks.nitidez), chip("Luz", last.checks.luz)] : []));
  }

  async function accept(blob) {
    blob = await prepareImage(blob);
    shots[VIEWS[step][0]] = blob;
    if (fromSummary || step >= VIEWS.length - 1) { fromSummary = false; return renderSummary(); }
    step++;
    renderCamera();
  }

  async function shoot() {
    const c = document.createElement("canvas");
    c.width = video.videoWidth; c.height = video.videoHeight;
    c.getContext("2d").drawImage(video, 0, 0);
    const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
    haptic("tap");
    accept(blob);
  }

  const pickPhoto = async (nativeCamera) => { const f = await pickFile("image/*", nativeCamera); if (f) accept(f); };

  function renderCamera() {
    last = null;
    const [key, title, desc] = VIEWS[step];
    const taken = Object.keys(shots);
    hintEl = h("div", { class: "hint", role: "status" }, stream ? "Comprobando cámara…" : "No se pudo abrir la cámara");
    lightsEl = h("div", { class: "lights" });
    guideEl = h("div", { class: "guide" });
    forceEl = h("button", { class: "link", hidden: true, onclick: shoot }, "Disparar igualmente");
    shutterEl = h("button", { class: "shutter", "aria-label": "Hacer foto", disabled: true, onclick: shoot });
    const thumbs = h("div", { class: "thumbs" }, taken.map((k) => h("img", { src: urlOf(shots[k]), alt: `Foto de ${k}` })));
    const center = stream ? shutterEl : h("button", { class: "btn btn-primary", onclick: () => pickPhoto(true) }, icon("camera"), "Hacer foto");
    const right = h("div", { class: "side end" },
      step > 0 && h("button", { class: "link", onclick: () => { step < VIEWS.length - 1 ? (step++, renderCamera()) : renderSummary(); } }, "Omitir"),
      shots.planta && step > 0 && h("button", { class: "btn btn-primary", onclick: renderSummary }, "Listo"));
    const layer = h("div", { class: "layer" },
      h("div", { class: "bar" }, closeBtn(),
        h("div", { class: "title" }, `${step + 1}/3 · ${title}`, h("div", { class: "small", style: "font-weight:400" }, desc)),
        h("button", { class: "icon-btn", "aria-label": "Elegir de la galería", onclick: () => pickPhoto(false) }, icon("image"))),
      stream && guideEl,
      h("div", { class: "status" }, stream && lightsEl, hintEl, stream && forceEl),
      h("div", { class: "controls" }, h("div", { class: "side" }, thumbs), center, right));
    cam.replaceChildren(video, layer);
    video.hidden = !stream;
    if (!stream) toast("Sin cámara en el navegador: usa «Hacer foto» o la galería.");
    paintStatus();
  }

  /* --- resumen y envío --- */
  function renderSummary() {
    stopDetect?.(); stopDetect = null;
    let review = pref("review", true), sending = false;
    const bar = h("i"), progress = h("div", { class: "progress", hidden: true }, bar);
    const name = h("input", { type: "text", maxLength: 60, placeholder: "Nombre (opcional), p. ej. Tapa batería", "aria-label": "Nombre de la pieza" });
    const reviewBox = h("input", { type: "checkbox", checked: review, onchange: () => { review = reviewBox.checked; setPref("review", review); } });
    const send = h("button", { class: "btn btn-primary btn-block", onclick: doSend }, "Enviar al Mac");
    async function doSend() {
      if (sending) return;
      sending = true; send.disabled = true; progress.hidden = false;
      const files = [], labels = [];
      for (const [k] of VIEWS) if (shots[k]) { files.push(["files", shots[k], `${k}.jpg`]); labels.push(k); }
      const fields = [["mode", "views"], ["views", labels.join(",")], ["review", review ? "1" : "0"], ["name", name.value]];
      try {
        const res = await submit({ fields, files, name: name.value }, (p) => { bar.style.width = `${Math.round(p * 100)}%`; });
        cleanup(); done(res);
      } catch (e) {
        sending = false; send.disabled = false; progress.hidden = true;
        toast(e.message, { kind: "err", action: "Reintentar", onAction: doSend });
      }
    }
    const fig = ([k, t], i) => h("figure", {},
      shots[k] ? h("img", { src: urlOf(shots[k]), alt: `Foto de ${t}` }) : h("div", { class: "ph muted" }, "Sin foto"),
      h("figcaption", {}, t), h("button", { class: "btn btn-block", style: "min-height:40px;padding:0 8px", onclick: () => {
        step = i; fromSummary = true; cam.replaceChildren(video); boot2(); } }, shots[k] ? "Repetir" : "Añadir"));
    cam.replaceChildren(h("div", { class: "sum" },
      h("div", { style: "max-width:640px;margin:0 auto", class: "stack" },
        h("div", { class: "top" }, h("button", { class: "icon-btn", "aria-label": "Volver a la cámara", onclick: () => { step = Math.min(step, 2); fromSummary = false; boot2(); } }, icon("back")), h("h1", {}, "Revisa las fotos")),
        h("div", { class: "shots" }, VIEWS.map(fig)),
        !shots.planta && h("div", { class: "banner" }, icon("alert"), "Falta la foto de planta: es la única obligatoria."),
        h("label", { class: "toggle" }, h("span", {}, h("b", {}, "Revisar contornos antes de generar"), h("br"), h("span", { class: "muted small" }, "Recomendado: evita imprimir con una detección errónea")), reviewBox),
        name, progress, send)));
    send.disabled = !shots.planta;
  }
  async function boot2() { // volver a la cámara sin reabrir permisos
    if (stream) { cam.replaceChildren(video); stopDetect = startDetect(video, (r) => { last = r; paintStatus(); }); }
    renderCamera();
  }

  boot();
  return cleanup;
}

/* =================== Vídeo =================== */
export function camaraVideo(root) {
  let stream = null, rec = null, chunks = [], started = 0, ticker = 0, blob = null, gone = false, url = null, mime = "";
  const video = h("video", { playsInline: true, muted: true, autoplay: true, "aria-hidden": "true" });
  const cam = h("div", { class: "cam" }, video);
  root.append(cam);
  const MAX = 90, GOAL = 60;
  const mimes = ["video/webm;codecs=vp9", "video/webm", "video/mp4"];
  const cleanup = () => { gone = true; clearInterval(ticker); if (rec?.state === "recording") rec.stop(); stopStream(stream); if (url) URL.revokeObjectURL(url); };
  const tips = (s) => (s < 25 ? "Órbita 1: gira despacio a la altura de la pieza" : s < 50 ? "Órbita 2: sube a ~45° y vuelve a girar" : "Una vuelta más desde arriba y termina");

  async function boot() {
    try { stream = await openStream(video); mime = window.MediaRecorder ? mimes.find((m) => MediaRecorder.isTypeSupported(m)) || "" : ""; } catch { stream = null; }
    if (gone) return stopStream(stream);
    idle();
  }

  const pick = async () => { const f = await pickFile("video/*", true); if (f) review(f); };

  function idle() {
    video.hidden = !stream;
    const canRec = stream && window.MediaRecorder;
    const shutter = h("button", { class: "shutter", "aria-label": "Empezar a grabar", onclick: start });
    cam.replaceChildren(video, h("div", { class: "layer" },
      h("div", { class: "bar" }, closeBtn(), h("div", { class: "title" }, "Vídeo 3D", h("div", { class: "small", style: "font-weight:400" }, "30–60 s alrededor de la pieza, sobre la hoja de marcadores"))),
      h("div", { class: "status" },
        h("div", { class: "hint" }, "Fondo liso · luz difusa · objeto mate"),
        h("div", { class: "hint small" }, "Dos órbitas: a la altura de la pieza y desde arriba")),
      h("div", { class: "controls" }, h("span"), canRec ? shutter : h("button", { class: "btn btn-primary", onclick: pick }, icon("film"), "Grabar con la cámara"),
        h("div", { class: "side end" }, h("button", { class: "link", onclick: pick }, "Elegir vídeo")))));
  }

  function start() {
    chunks = [];
    rec = new MediaRecorder(stream, { ...(mime ? { mimeType: mime } : {}), videoBitsPerSecond: 8_000_000 });
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => { clearInterval(ticker); if (!gone) review(new Blob(chunks, { type: rec.mimeType || "video/webm" })); };
    rec.start(1000);
    started = Date.now();
    const time = h("span", { class: "num" }), tip = h("div", { class: "hint", role: "status" }), bar = h("i"), prog = h("div", { class: "progress" }, bar);
    const shutter = h("button", { class: "shutter rec", "aria-label": "Detener grabación", onclick: () => rec.stop() });
    cam.replaceChildren(video, h("div", { class: "layer" },
      h("div", { class: "bar" }, h("div", { class: "title" }, "● Grabando ", time, ` / ${mmss(GOAL)}`)),
      h("div", { class: "status" }, tip, h("div", { style: "width:80%" }, prog)),
      h("div", { class: "controls" }, h("span"), shutter, h("span"))));
    const upd = () => {
      const s = (Date.now() - started) / 1000;
      time.textContent = mmss(s); tip.textContent = tips(s); bar.style.width = `${Math.min(100, (s / GOAL) * 100)}%`;
      if (s >= MAX) rec.stop();
    };
    upd(); ticker = setInterval(upd, 500);
  }

  function review(file) {
    blob = file; stopStream(stream); stream = null; url = URL.createObjectURL(blob);
    const bar = h("i"), progress = h("div", { class: "progress", hidden: true }, bar);
    const name = h("input", { type: "text", maxLength: 60, placeholder: "Nombre (opcional)", "aria-label": "Nombre de la pieza" });
    const send = h("button", { class: "btn btn-primary btn-block", onclick: doSend }, "Enviar al Mac");
    async function doSend() {
      send.disabled = true; progress.hidden = false;
      const ext = (blob.type || "").includes("mp4") ? "mp4" : (blob.name || "").split(".").pop() || "webm";
      const fields = [["mode", "video"], ["name", name.value]], files = [["files", blob, `video.${ext}`]];
      try {
        const res = await submit({ fields, files, name: name.value }, (p) => { bar.style.width = `${Math.round(p * 100)}%`; });
        cleanup(); done(res);
      } catch (e) { send.disabled = false; progress.hidden = true; toast(e.message, { kind: "err", action: "Reintentar", onAction: doSend }); }
    }
    cam.replaceChildren(h("div", { class: "sum" },
      h("div", { style: "max-width:640px;margin:0 auto", class: "stack" },
        h("h1", {}, "Revisa el vídeo"),
        h("video", { src: url, controls: true, playsInline: true, style: "width:100%;border-radius:12px;background:#000;max-height:50dvh" }),
        h("p", { class: "muted small", style: "margin:0" }, `${(blob.size / 1e6).toFixed(1)} MB · la subida usa tu Wi-Fi`),
        name, progress, send,
        h("button", { class: "btn btn-block", onclick: async () => { URL.revokeObjectURL(url); url = null; blob = null; cam.replaceChildren(video); try { stream = await openStream(video); } catch { stream = null; } idle(); } }, "Repetir"))));
  }
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  boot();
  return cleanup;
}
