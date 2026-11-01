import { pref } from "./api.js";

const I = {
  camera: '<svg viewBox="0 0 24 24"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  list: '<svg viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>',
  gear: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.3-.9-2 3.4 2 1.5a7 7 0 0 0 0 2.4l-2 1.5 2 3.4 2.3-.9a7 7 0 0 0 2 1.2l.4 2.6h4l.4-2.6a7 7 0 0 0 2-1.2l2.3.9 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"/></svg>',
  back: '<svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  more: '<svg viewBox="0 0 24 24"><path d="M12 5h.01M12 12h.01M12 19h.01"/></svg>',
  download: '<svg viewBox="0 0 24 24"><path d="M12 4v11m0 0l-4-4m4 4l4-4M5 20h14"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M5 7h14M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  cube: '<svg viewBox="0 0 24 24"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12L4 7.5M12 12v9"/></svg>',
  film: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M8 5v14M16 5v14M3 10h5M3 14h5M16 10h5M16 14h5"/></svg>',
  views: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><path d="M13 17h8M17 13v8"/></svg>',
  grid: '<svg viewBox="0 0 24 24"><path d="M4 4h16v16H4zM4 9.3h16M4 14.7h16M9.3 4v16M14.7 4v16"/></svg>',
  reset: '<svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 3-6.2M4 4v5h5"/></svg>',
  image: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 18l5-5 4 4 3-3 4 4"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/></svg>',
  edit: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg>',
  cut: '<svg viewBox="0 0 24 24"><path d="M4 8l8-4 8 4v8l-8 4-8-4z"/><path d="M4 12l8 4 8-4" stroke-dasharray="2 2.5"/></svg>',
  ruler: '<svg viewBox="0 0 24 24"><path d="M3 15l12-12 6 6L9 21z"/><path d="M7 11l2 2M10 8l2 2M13 5l2 2"/></svg>',
  chevron: '<svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>',
  file: '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/></svg>',
};

/* ---------- Hápticos y movimiento ---------- */
const HAPTICS = { tick: 8, tap: 14, success: [14, 50, 22], warn: [24, 60, 24], error: [40, 50, 40] };
export function haptic(kind = "tap") {
  if (!pref("haptics", true)) return;
  try { navigator.vibrate?.(HAPTICS[kind]); } catch { /* sin vibración */ }
}
export const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Anima un valor: `render(e)` recibe 0..1 (con easing) y devuelve el texto. */
export function animateValue(el, render, ms = 650) {
  if (reducedMotion()) { el.textContent = render(1); return; }
  const t0 = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - t0) / ms);
    el.textContent = render(1 - (1 - t) ** 3);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export const icon = (name) => h("span", { class: "icon", "aria-hidden": "true", html: I[name] || "" });
export const iconHTML = (name) => I[name] || "";

/** Crea elementos: h("div", {class:"x", onclick: fn}, hijos...) */
export function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v; // solo SVG propios de este fichero
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k in el && !k.includes("-")) el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  el.append(...kids.flat(Infinity).filter((c) => c != null && c !== false));
  return el;
}

export function toast(msg, { kind = "", action, onAction } = {}) {
  const box = document.getElementById("toasts");
  const t = h("div", { class: "toast " + kind, role: kind === "err" ? "alert" : "status" }, h("span", {}, msg));
  const dismiss = () => { t.classList.add("out"); setTimeout(() => t.remove(), 220); };
  if (action) t.append(h("button", { onclick: () => { dismiss(); onAction?.(); } }, action));
  if (kind === "err") haptic("error");
  box.append(t);
  setTimeout(dismiss, action ? 8000 : 3600);
}

/** Hoja inferior modal. Se cierra con Esc, tocando fuera o arrastrándola hacia abajo. Devuelve close(). */
export function openSheet(title, ...content) {
  const prev = document.activeElement;
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    document.removeEventListener("keydown", onKey);
    back.classList.add("out");
    sheet.style.transform = "translateY(100%)";
    setTimeout(() => back.remove(), 200);
    prev?.focus?.();
  };
  const onKey = (e) => e.key === "Escape" && close();
  const grab = h("div", { class: "grab", "aria-hidden": "true" });
  const sheet = h("div", { class: "sheet", role: "dialog", "aria-modal": "true", "aria-label": title, tabIndex: -1 },
    grab, h("h2", {}, title), ...content);
  const back = h("div", { class: "backdrop", onclick: (e) => e.target === back && close() }, sheet);
  let y0 = 0, dy = 0, t0 = 0, drag = false;
  grab.addEventListener("pointerdown", (e) => { drag = true; y0 = e.clientY; t0 = e.timeStamp; sheet.classList.add("dragging"); grab.setPointerCapture(e.pointerId); });
  grab.addEventListener("pointermove", (e) => {
    if (!drag) return;
    dy = Math.max(0, e.clientY - y0);
    sheet.style.transform = `translateY(${dy}px)`;
    back.style.opacity = String(1 - Math.min(dy / 320, 0.85));
  });
  const end = (e) => {
    if (!drag) return;
    drag = false;
    sheet.classList.remove("dragging");
    if (dy > 110 || dy / Math.max(e.timeStamp - t0, 1) > 0.6) { haptic("tick"); close(); }
    else { sheet.style.transform = ""; back.style.opacity = ""; }
    dy = 0;
  };
  grab.addEventListener("pointerup", end);
  grab.addEventListener("pointercancel", end);
  document.body.append(back);
  document.addEventListener("keydown", onKey);
  sheet.focus();
  return close;
}

export function confirmSheet(message, okLabel = "Aceptar", danger = false) {
  return new Promise((resolve) => {
    const done = (v) => { close(); resolve(v); };
    const close = openSheet(message,
      h("div", { class: "stack", style: "margin-top:12px" },
        h("button", { class: "btn btn-block " + (danger ? "btn-danger" : "btn-primary"), onclick: () => done(true) }, okLabel),
        h("button", { class: "btn btn-block btn-ghost", onclick: () => done(false) }, "Cancelar")));
  });
}

export const fmt = (n) => Number(n).toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const fmtDims = (d) => d ? `${fmt(d.ancho)} × ${fmt(d.fondo)} × ${fmt(d.alto)} mm` : "";

export function relTime(iso) {
  const s = (new Date(iso) - Date.now()) / 1000, rtf = new Intl.RelativeTimeFormat("es", { numeric: "auto" });
  for (const [u, n] of [["day", 86400], ["hour", 3600], ["minute", 60]]) if (Math.abs(s) >= n) return rtf.format(Math.round(s / n), u);
  return "ahora";
}

export const STATUS = {
  uploaded: ["En cola", "run"], processing: ["Procesando", "run"], review: ["Revisar", "warn"],
  done: ["Listo", "ok"], error: ["Error", "err"],
};
/** Aviso compacto y desplegable (<details>): una línea cerrada, el detalle al abrirlo. */
export function note(kind, title, ...body) {
  return h("details", { class: "note " + kind, role: "alert" },
    h("summary", {}, icon("alert"), h("span", { class: "grow" }, title), h("span", { class: "chev", html: I.chevron })),
    h("div", { class: "body" }, ...body));
}

export const statusChip = (s) => { const [t, c] = STATUS[s] || [s, ""]; return h("span", { class: "chip " + c }, t); };
export const modeLabel = (m) => (m === "video" ? "Vídeo 3D" : "3 vistas");
export const jobName = (j) => j.name || `${modeLabel(j.mode)} ${j.id.slice(0, 4)}`;
export const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "pieza";
export const topBar = (title, { back = "#/trabajos", actions = [] } = {}) =>
  h("div", { class: "top" },
    h("a", { class: "icon-btn", href: back, "aria-label": "Volver" }, icon("back")), h("h1", {}, title), ...actions);

/** Abre el selector de archivos / cámara nativa. Devuelve File o null. */
export const pickFile = (accept, capture = false) => new Promise((resolve) => {
  const i = h("input", { type: "file", accept });
  if (capture) i.setAttribute("capture", "environment");
  i.onchange = () => resolve(i.files[0] || null);
  i.addEventListener("cancel", () => resolve(null));
  i.click();
});

/* ---------- Gestos ---------- */

/** Desliza una tarjeta hacia la izquierda para descubrir la acción de borrar.
 *  `onCommit(reset)` se llama al soltar pasado el umbral; `reset()` devuelve la tarjeta a su sitio. */
export function swipeToDelete(wrap, card, onCommit) {
  const TH = 96;
  let x0 = 0, y0 = 0, dx = 0, active = false, locked = false, crossed = false, suppress = false;
  const reset = () => { card.style.transform = ""; wrap.classList.remove("reveal"); };
  card.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    x0 = e.clientX; y0 = e.clientY; dx = 0; active = true; locked = false; crossed = false;
  });
  card.addEventListener("pointermove", (e) => {
    if (!active) return;
    const mx = e.clientX - x0, my = e.clientY - y0;
    if (!locked) {
      if (Math.abs(mx) > 8 && Math.abs(mx) > Math.abs(my) * 1.4) { locked = true; card.classList.add("dragging"); wrap.classList.add("reveal"); card.setPointerCapture(e.pointerId); }
      else if (Math.abs(my) > 10) { active = false; return; }
      else return;
    }
    dx = Math.min(0, mx);
    card.style.transform = `translateX(${dx < -TH ? -TH + (dx + TH) * 0.35 : dx}px)`;
    if (!crossed && dx < -TH) { crossed = true; haptic("tick"); }
    if (crossed && dx > -TH) crossed = false;
  });
  const end = () => {
    if (!active) return;
    active = false;
    card.classList.remove("dragging");
    if (locked) { suppress = true; setTimeout(() => { suppress = false; }, 60); }
    if (locked && dx < -TH) { card.style.transform = `translateX(${-TH}px)`; onCommit(reset); } else reset();
    locked = false;
  };
  card.addEventListener("pointerup", end);
  card.addEventListener("pointercancel", end);
  card.addEventListener("click", (e) => { if (suppress) { e.preventDefault(); e.stopPropagation(); } }, true);
  wrap.querySelector(".swipe-action")?.addEventListener("click", () => onCommit(reset));
}

/** Tirar hacia abajo desde arriba del todo para actualizar. `indicator` es un elemento `.ptr`. Devuelve un limpiador. */
export function pullToRefresh(indicator, onRefresh) {
  let y0 = 0, dy = 0, on = false, busy = false;
  const spinner = indicator.firstElementChild;
  const ts = (e) => { if (busy || scrollY > 0 || e.touches.length !== 1) return; y0 = e.touches[0].clientY; on = true; dy = 0; };
  const tm = (e) => {
    if (!on) return;
    dy = e.touches[0].clientY - y0;
    if (dy <= 0) { indicator.style.height = "0"; return; }
    indicator.style.transition = "none";
    indicator.style.height = `${Math.min(dy * 0.45, 64)}px`;
    spinner.style.transform = `rotate(${Math.min(dy * 2, 240)}deg)`;
  };
  const te = async () => {
    if (!on) return;
    on = false;
    indicator.style.transition = "";
    if (dy > 110 && !busy) {
      busy = true; indicator.classList.add("loading"); indicator.style.height = "52px"; haptic("tick");
      try { await onRefresh(); } finally { busy = false; indicator.classList.remove("loading"); indicator.style.height = "0"; spinner.style.transform = ""; }
    } else { indicator.style.height = "0"; }
  };
  addEventListener("touchstart", ts, { passive: true });
  addEventListener("touchmove", tm, { passive: true });
  addEventListener("touchend", te);
  return () => { removeEventListener("touchstart", ts); removeEventListener("touchmove", tm); removeEventListener("touchend", te); };
}
