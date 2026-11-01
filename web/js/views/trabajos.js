import { api, del } from "../api.js";
import { list as outboxList, load as outboxLoad, remove as outboxRemove, retry as outboxRetry } from "../outbox.js";
import { confirmSheet, fmt, h, haptic, icon, jobName, modeLabel, pullToRefresh, relTime, statusChip, swipeToDelete, toast } from "../ui.js";

const FILTERS = [["all", "Todos"], ["run", "En curso"], ["done", "Listos"], ["error", "Error"]];
const group = (s) => (s === "done" ? "done" : s === "error" ? "error" : "run");

const skeletonRow = () => h("div", { class: "card job" },
  h("div", { class: "thumb skeleton" }),
  h("div", { class: "stack", style: "gap:8px" }, h("div", { class: "skeleton sk-line", style: "width:60%" }), h("div", { class: "skeleton sk-line", style: "width:40%" })),
  h("span"));

export function trabajos(root) {
  let jobs = null, filter = "all", timer = 0, gone = false, sig = "", animated = false;
  const list = h("div", { class: "stack" });
  const pending = h("div", { class: "stack pending", "aria-label": "Pendientes de enviar" });
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Filtro", style: `--n:${FILTERS.length}` });
  const ptr = h("div", { class: "ptr", "aria-hidden": "true" }, icon("reset"));
  root.append(ptr, h("h1", {}, "Trabajos"), pending, seg, list);
  const stopPtr = pullToRefresh(ptr, () => refresh());

  const remove = async (j, reset) => {
    haptic("warn");
    if (!(await confirmSheet(`¿Eliminar «${jobName(j)}»?`, "Eliminar", true))) return reset?.();
    try { await del(`/jobs/${j.id}`); haptic("success"); toast("Trabajo eliminado"); refresh(); } catch (e) { reset?.(); toast(e.message, { kind: "err" }); }
  };

  const row = (j) => {
    const hasModel = j.status === "done" && j.outputs?.includes("pieza.stl");
    const photo = `/api/jobs/${j.id}/thumb.jpg`;
    const thumb = h("img", { class: "thumb" + (hasModel ? " model" : ""), src: hasModel ? `/api/jobs/${j.id}/thumb.png?v=${j.rev || 0}` : photo, alt: "", loading: "lazy", decoding: "async" });
    thumb.addEventListener("error", () => {                       // sin render del modelo: la foto; sin foto: un icono
      if (thumb.src.includes("thumb.png")) { thumb.classList.remove("model"); thumb.src = photo; }
      else thumb.replaceWith(h("span", { class: "thumb" }, icon(j.mode === "video" ? "film" : "cube")));
    });
    const card = h("div", { class: "card job" },
      h("a", { href: `#/trabajos/${j.id}`, "aria-label": `Abrir ${jobName(j)}`, onclick: () => haptic("tick") },
        thumb,
        h("div", { style: "min-width:0" },
          h("div", { class: "name" }, jobName(j)),
          h("div", { class: "meta muted small" }, h("span", {}, modeLabel(j.mode)), h("span", { "aria-hidden": "true" }, "·"), h("span", {}, relTime(j.created))),
          h("div", { class: "meta" }, statusChip(j.status), j.dims && h("span", { class: "dimline" }, `${fmt(j.dims.ancho)} × ${fmt(j.dims.fondo)} × ${fmt(j.dims.alto)}`)))),
      h("button", { class: "icon-btn", style: "color:var(--muted)", "aria-label": `Eliminar ${jobName(j)}`, onclick: () => remove(j) }, icon("trash")));
    const wrap = h("div", { class: "swipe" }, h("div", { class: "swipe-action", "aria-hidden": "true" }, icon("trash")), card);
    swipeToDelete(wrap, card, (reset) => remove(j, reset));
    return wrap;
  };

  /** Capturas guardadas en el móvil que aún no han llegado al Mac (sin red, subiendo o rechazadas). */
  const MB = (n) => `${Math.max(n / 1e6, 0.1).toFixed(1).replace(".", ",")} MB`;
  const pendingRow = (e) => {
    const state = e.state === "failed" ? ["No se envió", "err"] : e.state === "sending"
      ? [e.progress != null ? `Enviando ${Math.round(e.progress * 100)} %` : "Enviando", "run"] : ["Esperando conexión", "warn"];
    return h("div", { class: "card job queued" },
      h("span", { class: "thumb" }, icon(e.fields.some(([k, v]) => k === "mode" && v === "video") ? "film" : "camera")),
      h("div", { style: "min-width:0" },
        h("div", { class: "name" }, e.name || "Captura sin nombre"),
        h("div", { class: "meta muted small" }, h("span", {}, MB(e.size)), h("span", { "aria-hidden": "true" }, "·"), h("span", {}, relTime(new Date(e.created).toISOString()))),
        h("div", { class: "meta" }, h("span", { class: "chip " + state[1] }, state[0]), e.state === "failed" && h("span", { class: "small muted" }, e.error))),
      h("div", { class: "qactions" },
        e.state !== "sending" && h("button", { class: "icon-btn", "aria-label": `Reintentar el envío de ${e.name || "la captura"}`, onclick: () => { haptic("tap"); outboxRetry(e.id); } }, icon("reset")),
        h("button", { class: "icon-btn", style: "color:var(--muted)", "aria-label": `Descartar ${e.name || "la captura"}`, onclick: async () => {
          if (await confirmSheet("¿Descartar esta captura? No se ha enviado al Mac y se perderá.", "Descartar", true)) { haptic("success"); outboxRemove(e.id); }
        } }, icon("trash"))));
  };
  const drawPending = (items = outboxList()) => {
    const sig2 = JSON.stringify(items.map((e) => [e.id, e.state, e.progress && Math.round(e.progress * 20)]));
    if (sig2 === drawPending.sig) return;
    drawPending.sig = sig2;
    pending.replaceChildren(...(items.length ? [h("div", { class: "group-title" }, `Pendientes de enviar · ${items.length}`), ...items.map(pendingRow)] : []));
  };
  const onOutbox = (ev) => { drawPending(ev.detail.items); if (ev.detail.count === 0) refresh(); };
  addEventListener("s2p:outbox", onOutbox);

  const drawFilter = () => {
    seg.style.setProperty("--i", FILTERS.findIndex(([k]) => k === filter));
    seg.replaceChildren(...FILTERS.map(([k, t]) => h("button", { "aria-pressed": String(filter === k), onclick: () => { filter = k; haptic("tick"); draw(); } }, t)));
  };

  const draw = () => {
    drawFilter();
    if (jobs === null) return list.replaceChildren(skeletonRow(), skeletonRow(), skeletonRow());
    const shown = jobs.filter((j) => filter === "all" || group(j.status) === filter);
    if (!jobs.length) {
      return list.replaceChildren(h("div", { class: "empty" },
        h("span", { html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12L4 7.5M12 12v9"/></svg>' }),
        h("strong", {}, "Aún no hay trabajos"),
        h("span", {}, "Fotografía una pieza y aparecerá aquí, lista para imprimir."),
        h("a", { class: "btn btn-primary", href: "#/capturar" }, "Capturar pieza")));
    }
    if (!animated) { animated = true; list.classList.add("stagger"); setTimeout(() => list.classList.remove("stagger"), 900); }
    list.replaceChildren(...(shown.length ? shown.map(row) : [h("p", { class: "muted" }, "Ningún trabajo en este filtro.")]));
  };

  async function refresh() {
    try { jobs = await api("/jobs"); } catch (e) { if (jobs === null) jobs = []; toast(e.message, { kind: "err", action: "Reintentar", onAction: refresh }); }
    if (gone) return;
    const now = JSON.stringify(jobs) + filter;
    if (now !== sig) { sig = now; draw(); }      // solo se repinta si algo cambió (sin parpadeos al sondear)
    clearTimeout(timer);
    if (jobs.some((j) => group(j.status) === "run" && j.status !== "review")) timer = setTimeout(refresh, 3000);
  }
  draw();
  drawPending();
  outboxLoad();
  refresh();
  return () => { gone = true; clearTimeout(timer); stopPtr(); removeEventListener("s2p:outbox", onOutbox); };
}
