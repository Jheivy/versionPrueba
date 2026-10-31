import { api, del } from "../api.js";
import { confirmSheet, fmtDims, h, haptic, icon, jobName, modeLabel, pullToRefresh, relTime, statusChip, swipeToDelete, toast } from "../ui.js";

const FILTERS = [["all", "Todos"], ["run", "En curso"], ["done", "Listos"], ["error", "Error"]];
const group = (s) => (s === "done" ? "done" : s === "error" ? "error" : "run");

const skeletonRow = () => h("div", { class: "card job" },
  h("div", { class: "thumb skeleton" }),
  h("div", { class: "stack", style: "gap:8px" }, h("div", { class: "skeleton sk-line", style: "width:60%" }), h("div", { class: "skeleton sk-line", style: "width:40%" })),
  h("span"));

export function trabajos(root) {
  let jobs = null, filter = "all", timer = 0, gone = false, sig = "", animated = false;
  const list = h("div", { class: "stack" });
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Filtro", style: `--n:${FILTERS.length}` });
  const ptr = h("div", { class: "ptr", "aria-hidden": "true" }, icon("reset"));
  root.append(ptr, h("h1", {}, "Trabajos"), seg, list);
  const stopPtr = pullToRefresh(ptr, () => refresh());

  const remove = async (j, reset) => {
    haptic("warn");
    if (!(await confirmSheet(`¿Eliminar «${jobName(j)}»?`, "Eliminar", true))) return reset?.();
    try { await del(`/jobs/${j.id}`); haptic("success"); toast("Trabajo eliminado"); refresh(); } catch (e) { reset?.(); toast(e.message, { kind: "err" }); }
  };

  const row = (j) => {
    const thumb = h("img", { class: "thumb", src: `/api/jobs/${j.id}/thumb.jpg`, alt: "", loading: "lazy", decoding: "async" });
    thumb.addEventListener("error", () => thumb.replaceWith(h("span", { class: "thumb" }, icon(j.mode === "video" ? "film" : "cube"))));
    const card = h("div", { class: "card job" },
      h("a", { href: `#/trabajos/${j.id}`, "aria-label": `Abrir ${jobName(j)}`, onclick: () => haptic("tick") },
        thumb,
        h("div", { style: "min-width:0" },
          h("div", { class: "name" }, jobName(j)),
          h("div", { class: "meta muted small" }, h("span", {}, modeLabel(j.mode)), h("span", { "aria-hidden": "true" }, "·"), h("span", {}, relTime(j.created))),
          h("div", { class: "meta" }, statusChip(j.status), j.dims && h("span", { class: "small num muted" }, fmtDims(j.dims))))),
      h("button", { class: "icon-btn", style: "color:var(--muted)", "aria-label": `Eliminar ${jobName(j)}`, onclick: () => remove(j) }, icon("trash")));
    const wrap = h("div", { class: "swipe" }, h("div", { class: "swipe-action", "aria-hidden": "true" }, icon("trash")), card);
    swipeToDelete(wrap, card, (reset) => remove(j, reset));
    return wrap;
  };

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
  refresh();
  return () => { gone = true; clearTimeout(timer); stopPtr(); };
}
