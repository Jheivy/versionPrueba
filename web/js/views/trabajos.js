import { api, del } from "../api.js";
import { h, icon, toast, confirmSheet, relTime, fmtDims, statusChip, modeLabel, jobName } from "../ui.js";

const FILTERS = [["all", "Todos"], ["run", "En curso"], ["done", "Listos"], ["error", "Con error"]];
const group = (s) => (s === "done" ? "done" : s === "error" ? "error" : "run");

export function trabajos(root) {
  let jobs = null, filter = "all", timer = 0, gone = false;
  const list = h("div", { class: "stack" });
  const chips = h("div", { class: "chips", role: "group", "aria-label": "Filtro" });
  root.append(h("h1", {}, "Trabajos"), chips, list);

  const row = (j) => {
    const thumb = h("img", { class: "thumb", src: `/api/jobs/${j.id}/thumb.jpg`, alt: "", loading: "lazy" });
    const fallback = () => thumb.replaceWith(h("span", { class: "thumb" }, icon(j.mode === "video" ? "film" : "cube")));
    thumb.addEventListener("error", fallback);
    return h("div", { class: "card job" },
      h("a", { href: `#/trabajos/${j.id}`, "aria-label": `Abrir ${jobName(j)}` },
        thumb,
        h("div", { style: "min-width:0" },
          h("div", { class: "name" }, jobName(j)),
          h("div", { class: "meta muted small" }, h("span", {}, modeLabel(j.mode)), h("span", { "aria-hidden": "true" }, "·"), h("span", {}, relTime(j.created))),
          h("div", { class: "meta" }, statusChip(j.status), j.dims && h("span", { class: "small num muted" }, fmtDims(j.dims)))),
      ),
      h("button", { class: "icon-btn", "aria-label": `Eliminar ${jobName(j)}`, onclick: async () => {
        if (!(await confirmSheet(`¿Eliminar «${jobName(j)}»?`, "Eliminar", true))) return;
        try { await del(`/jobs/${j.id}`); toast("Trabajo eliminado"); refresh(); } catch (e) { toast(e.message, { kind: "err" }); }
      } }, icon("trash")));
  };

  const draw = () => {
    chips.replaceChildren(...FILTERS.map(([k, t]) => h("button", { "aria-pressed": String(filter === k), onclick: () => { filter = k; draw(); } }, t)));
    if (jobs === null) return list.replaceChildren(h("p", { class: "muted" }, "Cargando…"));
    const shown = jobs.filter((j) => filter === "all" || group(j.status) === filter);
    if (!jobs.length) {
      return list.replaceChildren(h("div", { class: "empty" },
        h("span", { html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12L4 7.5M12 12v9"/></svg>' }),
        h("strong", {}, "Aún no hay trabajos"),
        h("span", {}, "Fotografía una pieza y aparecerá aquí, lista para imprimir."),
        h("a", { class: "btn btn-primary", href: "#/capturar" }, "Capturar pieza")));
    }
    list.replaceChildren(...(shown.length ? shown.map(row) : [h("p", { class: "muted" }, "Ningún trabajo en este filtro.")]));
  };

  async function refresh() {
    try { jobs = await api("/jobs"); } catch (e) { if (jobs === null) jobs = []; toast(e.message, { kind: "err", action: "Reintentar", onAction: refresh }); }
    if (gone) return;
    draw();
    clearTimeout(timer);
    if (jobs.some((j) => group(j.status) === "run" && j.status !== "review")) timer = setTimeout(refresh, 3000);
  }
  draw();
  refresh();
  return () => { gone = true; clearTimeout(timer); };
}
