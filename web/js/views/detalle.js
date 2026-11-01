import { api, authFetch, del, patch, post, pref, upload } from "../api.js";
import { animateValue, confirmSheet, fmt, h, haptic, icon, jobName, modeLabel, note, openSheet, pickFile, relTime, slug, statusChip, toast, topBar } from "../ui.js";
import { prepareImage } from "../image.js";
import { navigate } from "../router.js";

const STEPS = {
  views: [["uploaded", "Subida"], ["rectifying", "Corrigiendo perspectiva"], ["contours", "Detectando contornos"], ["modeling", "Generando el modelo"], ["exporting", "Exportando STL"]],
  video: [["uploaded", "Subida"], ["frames", "Eligiendo fotogramas"], ["reconstruction", "Reconstruyendo en 3D"], ["cleaning", "Limpiando la malla"], ["exporting", "Exportando STL"]],
};
const VIEW_LABEL = { planta: "Planta", alzado: "Alzado", perfil: "Perfil" };
const DIM_LABEL = { ancho: "Ancho (X)", fondo: "Fondo (Y)", alto: "Alto (Z)" };
const holeName = (x) => `Ø${fmt(x.diam)} · ${VIEW_LABEL[x.view].toLowerCase()} ${x.n}`;
const mmss = (ms) => { const s = Math.max(0, Math.round(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

export function detalle(root, { id }) {
  let j, timer = 0, tick = 0, viewer = null, gone = false, last = null;
  const head = h("div"), body = h("div", { class: "stack stagger" });
  let prog = null, dimsShown = false;
  body.append(h("div", { class: "viewer" }, h("div", { class: "skeleton" })),
    h("div", { class: "skeleton sk-line", style: "width:55%;height:28px;margin:6px 4px" }));   // mientras llegan los datos
  root.append(head, body);
  const fileUrl = (n) => `/api/jobs/${id}/files/${n}`;

  const stopTimers = () => { clearTimeout(timer); clearInterval(tick); };

  async function load() {
    stopTimers();
    try { j = await api(`/jobs/${id}`); } catch (e) {
      if (gone) return;
      head.replaceChildren(topBar("Trabajo"));
      return body.replaceChildren(h("div", { class: "banner err" }, icon("alert"), h("div", {}, e.message, " ", h("button", { class: "btn", onclick: load }, "Reintentar"))));
    }
    if (gone) return;
    if (last === "processing" && j.status === "done" && pref("notify", false) && document.hidden && Notification?.permission === "granted") {
      new Notification("Pieza lista", { body: jobName(j) });
    }
    if ((last === "processing" || last === "uploaded") && j.status === "done") haptic("success");
    if ((last === "processing" || last === "uploaded") && j.status === "error") haptic("error");
    last = j.status;
    viewer?.dispose(); viewer = null;
    head.replaceChildren(topBar(jobName(j), { actions: [h("button", { class: "icon-btn", "aria-label": "Opciones", onclick: openMenu }, icon("more"))] }),
      h("div", { class: "sub" }, statusChip(j.status), h("span", {}, modeLabel(j.mode)), h("span", { "aria-hidden": "true" }, "·"), h("span", {}, relTime(j.created))));
    if (j.status === "uploaded" || j.status === "processing") { progress(); timer = setTimeout(load, j.mode === "video" ? 4000 : 1500); }
    else if (j.status === "review") review();
    else if (j.status === "error") failed();
    else done();
  }

  /* ---------- Progreso ---------- */
  function progress() {
    const steps = STEPS[j.mode], cur = Math.max(0, steps.findIndex((s) => s[0] === (j.step || "uploaded")));
    if (!prog || !prog.root.isConnected) {                 // se crea una vez y luego se actualiza en el sitio
      const elapsed = h("span", { class: "num muted" });
      const items = steps.map(([, t]) => h("li", {}, h("span", { class: "mark" }), t));
      const root = h("div", { class: "card stack" },
        h("div", { class: "row" }, h("strong", { class: "grow" }, "Procesando…"), elapsed),
        h("ol", { class: "stepper-v", "aria-label": "Pasos" }, items),
        j.mode === "video" && h("p", { class: "muted small", style: "margin:0" }, "La reconstrucción tarda unos 5–10 minutos. Puedes cerrar la app: el trabajo sigue en el Mac."));
      prog = { root, elapsed, items, cur: -1 };
      body.replaceChildren(root);
    }
    prog.items.forEach((li, i) => {
      li.className = i < cur ? "done" : i === cur ? "active" : "";
      if (i === cur) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
      li.firstChild.replaceChildren(i < cur ? icon("check") : "");
    });
    if (prog.cur !== -1 && cur > prog.cur) haptic("tick");
    prog.cur = cur;
    const upd = () => { prog.elapsed.textContent = mmss(Date.now() - new Date(j.created)); };
    upd(); tick = setInterval(upd, 1000);
  }

  /* ---------- Vistas que no cuadran ---------- */
  async function unify() {
    try {
      await post(`/jobs/${id}/params`, { ...(j.params || {}), unificar: 1 });
      toast("Unificando…");
      setTimeout(load, 500);
    } catch (e) { toast(e.message, { kind: "err" }); }
  }

  function mismatchBanner(inReview) {
    if (!j.warnings?.length) return null;
    const n = j.warnings.length;
    return note("warn", n > 1 ? `${n} medidas no cuadran entre las vistas` : "Una medida no cuadra entre las vistas",
      ...j.warnings.map((w) => h("div", { class: "row-m" }, h("b", {}, DIM_LABEL[w.dim]),
        h("span", { class: "mono" }, `${VIEW_LABEL[w.views[0]].toLowerCase()} ${fmt(w.values[0])} · ${VIEW_LABEL[w.views[1]].toLowerCase()} ${fmt(w.values[1])} mm`))),
      h("p", { class: "small muted", style: "margin:4px 0 0" }, inReview
        ? "El modelo se recorta a la vista más pequeña. Repite la foto que falle o unifica con el promedio."
        : "El modelo se recortó a la vista más pequeña. Mide con calibre en «Ajustar medidas» o unifica con el promedio."),
      h("button", { class: "btn btn-sm", style: "justify-self:start", onclick: unify }, "Unificar (promedio)"));
  }

  /* ---------- Revisión de contornos ---------- */
  async function retake(view) {
    const f = await pickFile("image/*", true);
    if (!f) return;
    const fd = new FormData(); fd.append("view", view); fd.append("file", await prepareImage(f), `${view}.jpg`);
    try { await upload(`/jobs/${id}/inputs`, fd); load(); } catch (e) { toast(e.message, { kind: "err" }); }
  }

  function viewCard(v) {
    const info = h("span", { class: "mono muted small", style: "white-space:nowrap;font-size:.7rem" });
    const img = h("img", { alt: `Contorno detectado en ${VIEW_LABEL[v]}` });
    const card = h("div", { class: "card review stack" },
      h("div", { class: "row", style: "gap:10px" }, h("strong", {}, VIEW_LABEL[v]), info, h("span", { class: "grow" }),
        h("button", { class: "btn btn-sm btn-ghost", "aria-label": `Repetir la foto de ${VIEW_LABEL[v].toLowerCase()}`, onclick: () => retake(v) }, icon("camera"), "Repetir")),
      img);
    authFetch(`/api/jobs/${id}/preview/${v}.png`).then(async (r) => {
      if (!r.ok) throw new Error();
      const i = JSON.parse(r.headers.get("X-Preview-Info"));
      info.textContent = `${fmt(i.ancho)} × ${fmt(i.alto)} · ${i.huecos} ${i.huecos === 1 ? "hueco" : "huecos"}`;
      img.src = URL.createObjectURL(await r.blob());
    }).catch(() => img.replaceWith(h("div", { class: "banner err" }, icon("alert"), "No se detectó la hoja o la pieza en esta foto. Repítela.")));
    return card;
  }

  function review() {
    const views = Object.keys(VIEW_LABEL).filter((v) => j.inputs.some((i) => i.startsWith(v + "_")));
    const go = h("button", { class: "btn btn-primary", onclick: async () => {
      go.disabled = true;
      haptic("tap"); try { await post(`/jobs/${id}/confirm`); load(); } catch (e) { go.disabled = false; toast(e.message, { kind: "err" }); }
    } }, "Continuar");
    body.replaceChildren(...[
      h("div", { class: "stack", style: "gap:6px" }, h("h2", { style: "margin:0" }, "Revisa los contornos"),
        h("div", { class: "legend" }, h("span", {}, h("i", { style: "background:var(--accent)" }), "Contorno"), h("span", {}, h("i", { style: "background:#18a5c9" }), "Agujeros"),
          h("span", {}, "Rectas ya enderezadas"))),
      mismatchBanner(true),
      ...views.map(viewCard),
      h("div", { class: "actionbar", style: "grid-template-columns:1fr" }, go)].filter(Boolean));
  }

  /* ---------- Error ---------- */
  function failed() {
    const retry = j.error_view
      ? h("button", { class: "btn btn-primary btn-block", onclick: () => retake(j.error_view) }, icon("camera"), `Repetir foto de ${VIEW_LABEL[j.error_view].toLowerCase()}`)
      : h("button", { class: "btn btn-primary btn-block", onclick: async () => { try { await post(`/jobs/${id}/params`, {}); setTimeout(load, 400); } catch (e) { toast(e.message, { kind: "err" }); } } }, "Reintentar");
    body.replaceChildren(
      h("div", { class: "banner err" }, icon("alert"), h("div", {}, h("b", {}, "No se pudo generar la pieza"), h("br"), j.error)),
      retry, h("a", { class: "btn btn-block btn-ghost", href: "#/trabajos" }, "Volver a trabajos"));
  }

  /* ---------- Resultado ---------- */
  async function done() {
    const hasStl = j.outputs.includes("pieza.stl");
    const canvas = h("canvas", { "aria-label": "Vista 3D de la pieza" });
    const fb = h("div", { class: "fallback", hidden: true }, "No se pudo cargar el visor 3D. Puedes descargar el archivo igualmente.");
    let gridOn = true;
    const gridBtn = h("button", { "aria-label": "Rejilla de 1 cm", "aria-pressed": "true", onclick: () => { gridOn = !gridOn; gridBtn.setAttribute("aria-pressed", String(gridOn)); viewer?.setGrid(gridOn); } }, icon("grid"));
    let dimsOn = true;
    const dimsBtn = h("button", { "aria-label": "Cotas", "aria-pressed": "true", onclick: () => { dimsOn = !dimsOn; dimsBtn.setAttribute("aria-pressed", String(dimsOn)); haptic("tick"); viewer?.setDims(dimsOn); } }, icon("ruler"));
    // Corte: plano perpendicular a X, Y o Z, con deslizador y lado invertible
    let secAxis = "x", secOn = false, secFlip = false;
    const secT = h("input", { type: "range", min: "0", max: "100", value: "50", "aria-label": "Posición del corte" });
    const applySec = () => viewer?.setSection(secOn ? secAxis : null, secT.value / 100, secFlip);
    const axBtns = ["x", "y", "z"].map((a) => h("button", { "aria-pressed": String(a === secAxis), "aria-label": `Cortar en el eje ${a.toUpperCase()}`, onclick: () => { secAxis = a; axBtns.forEach((b, i) => b.setAttribute("aria-pressed", String("xyz"[i] === a))); haptic("tick"); applySec(); } }, h("i", { class: `ax ${a}` }), a.toUpperCase()));
    const flipBtn = h("button", { "aria-label": "Invertir el lado del corte", onclick: () => { secFlip = !secFlip; haptic("tick"); applySec(); } }, "⇄");
    secT.addEventListener("input", applySec);
    const secPanel = h("div", { class: "section-panel", hidden: true }, h("div", { class: "axes" }, ...axBtns, flipBtn), secT);
    const cutBtn = h("button", { "aria-label": "Corte para ver el interior", "aria-pressed": "false", onclick: () => { secOn = !secOn; cutBtn.setAttribute("aria-pressed", String(secOn)); secPanel.hidden = !secOn; haptic("tick"); applySec(); } }, icon("cut"));
    const tools = h("div", { class: "tools" }, h("button", { "aria-label": "Centrar vista", onclick: () => viewer?.resetView() }, icon("reset")), cutBtn, dimsBtn, gridBtn);
    const name = slug(jobName(j));
    const specs = h("div", { class: "specs", role: "group", "aria-label": "Medidas de la pieza" },
      [["ancho", "x", "Ancho"], ["fondo", "y", "Fondo"], ["alto", "z", "Alto"]].map(([k, ax, lab]) => {
        const val = j.dims?.[k] ?? 0, numEl = h("span", {}, fmt(val));
        if (!dimsShown && j.dims) animateValue(numEl, (e) => fmt(val * e));   // las medidas «cuentan» hasta su valor la primera vez
        return h("div", { class: "spec" }, h("span", { class: "k" }, h("i", { class: `ax ${ax}` }), lab), h("span", { class: "v" }, numEl, h("small", {}, "mm")));
      }));
    dimsShown = true;
    const primary = hasStl
      ? h("a", { class: "btn btn-primary", href: fileUrl("pieza.stl"), download: `${name}.stl` }, icon("download"), "Descargar STL")
      : h("a", { class: "btn btn-primary", href: fileUrl("pieza.scad"), download: `${name}.scad` }, icon("download"), "Descargar .scad");
    body.replaceChildren(...[
      hasStl ? h("div", { class: "viewer" }, h("div", { class: "skeleton" }), canvas, fb, tools, secPanel) : h("div", { class: "banner" }, icon("alert"), "OpenSCAD no está instalado en el Mac, así que no se generó el STL. Descarga el .scad o instala OpenSCAD."),
      specs,
      mismatchBanner(false),
      j.holes?.length > 0 && h("div", { class: "holes", "aria-label": "Agujeros detectados" },
        h("div", { class: "eyebrow", style: "margin:2px 0 8px" }, `${j.holes.length} ${j.holes.length === 1 ? "agujero" : "agujeros"}`),
        h("div", { class: "chips" }, j.holes.map((x) => h("span", { class: "chip mono" }, holeName(x), x.std && h("span", { class: "muted" }, ` ${x.std}?`))))),
      j.mesh?.scale_estimated && h("div", { class: "banner info" }, icon("ruler"), h("div", {}, "Escala estimada. Mide la dimensión más larga con un calibre e indícala para ajustar el tamaño real. ",
        h("button", { class: "btn", style: "margin-top:8px", onclick: openAdjust }, "Indicar medida"))),
      j.mesh && !j.mesh.watertight && h("div", { class: "banner" }, icon("alert"), "La malla tiene pequeños huecos. Orca suele repararlos al importar."),
      h("div", { class: "actionbar" }, h("button", { class: "btn", onclick: openAdjust }, icon("edit"), "Ajustar medidas"), primary)].filter(Boolean));
    if (!hasStl) return;
    try {
      viewer = (await import("./../viewer.js")).createViewer(canvas);
      if (gone) { viewer.dispose(); viewer = null; return; }
      await viewer.load(`${fileUrl("pieza.stl")}?v=${j.rev || 0}`); // ?v= => inmutable en la caché del navegador
      const box = canvas.closest(".viewer");
      box.dataset.ready = "1";
      setTimeout(() => box.querySelector(".skeleton")?.remove(), 400);   // fuera del árbol cuando ya no se ve           // el modelo ya se dibuja (lo usan la animación y las pruebas)
    } catch { canvas.hidden = true; fb.hidden = false; viewer?.dispose(); viewer = null; }
  }

  /* ---------- Ajustar medidas ---------- */
  function openAdjust() {
    const p = j.params || {}, det = j.detected || {};
    const num = (name, label, ph, axis, step = "0.1") => h("label", { class: "mfield" },
      h("span", { class: "lab" }, axis ? h("i", { class: `ax ${axis}` }) : null, label),
      h("span", { class: "inp" }, h("input", { name, type: "number", inputMode: "decimal", step, min: name === "holgura" ? undefined : "0", placeholder: ph, value: p[name] ?? "" }), h("em", {}, "mm")));
    const holgura = h("input", { name: "holgura", type: "number", inputMode: "decimal", step: "0.05", value: p.holgura ?? 0, "aria-label": "Holgura en mm" });
    const bump = (d) => { holgura.value = (Math.round((Number(holgura.value || 0) + d) * 100) / 100).toString(); };
    const presets = h("div", { class: "chips" }, [["Exacto", 0], ["Ajustado", 0.1], ["Holgado", 0.2]].map(([t, v]) =>
      h("button", { type: "button", onclick: () => { holgura.value = v; } }, `${t} ${fmt(v)}`)));
    const form = h("form", { class: "stack", onsubmit: async (e) => {
      e.preventDefault();
      const b = {};
      for (const el of form.elements) {
        if (!el.name) continue;
        if (el.type === "checkbox") b[el.name] = Number(el.checked);
        else if (el.value !== "") b[el.name] = el.tagName === "SELECT" ? el.value : Number(el.value);
      }
      close();
      try { await post(`/jobs/${id}/params`, b); toast("Regenerando…"); setTimeout(load, 500); } catch (er) { toast(er.message, { kind: "err" }); }
    } },
      j.mode === "video"
        ? [num("largo", "Dimensión más larga", j.dims ? fmt(Math.max(j.dims.ancho, j.dims.fondo, j.dims.alto)) : "0,0"),
           h("label", { class: "field" }, "Detalle de la reconstrucción", h("select", { name: "detalle" },
             [["medium", "Medio"], ["full", "Alto (más lento)"], ["reduced", "Bajo (rápido)"]].map(([v, t]) => h("option", { value: v, selected: (p.detalle || "medium") === v }, t))))]
        : [h("div", { class: "field-grid" }, num("ancho", "Ancho", fmt(det.ancho ?? 0), "x"), num("fondo", "Fondo", fmt(det.fondo ?? 0), "y"), num("alto", "Alto", fmt(det.alto ?? 0), "z")),
           ...(j.holes || []).map((x) => num(`d_${x.view}_${x.n}`, `Ø ${VIEW_LABEL[x.view].toLowerCase()} ${x.n}`, fmt(x.diam), null, "0.05")),
           h("label", { class: "toggle" }, h("span", {}, h("b", {}, "Enderezar contornos"), h("br"),
             h("span", { class: "muted small" }, "Rectas y ángulos de 90° exactos (hasta ~4° de desvío)")),
             h("input", { type: "checkbox", name: "enderezar", checked: (p.enderezar ?? 1) !== 0 })),
           h("div", { class: "mfield" }, h("span", { class: "lab" }, "Holgura", h("span", { class: "hint" }, "+ agranda · − encoge")), h("div", { class: "stepper" },
             h("button", { type: "button", class: "btn", "aria-label": "Menos", onclick: () => bump(-0.05) }, "−"), holgura,
             h("button", { type: "button", class: "btn", "aria-label": "Más", onclick: () => bump(0.05) }, "+")), presets)],
      h("p", { class: "muted small", style: "margin:0" }, j.holes?.length ? "Deja vacío lo que no hayas medido. Mide los agujeros con calibre: la foto tiene ±0,1 mm de error." : "Deja vacío lo que no hayas medido."),
      h("button", { class: "btn btn-primary btn-block", type: "submit" }, "Regenerar"));
    const close = openSheet(j.mode === "video" ? "Escala real" : "Medidas con calibre", form);
  }

  /* ---------- Menú ---------- */
  function openMenu() {
    const item = (ic, text, fn, cls = "") => h("button", { class: "btn btn-block " + cls, style: "justify-content:flex-start", onclick: () => { close(); fn(); } }, icon(ic), text);
    const items = [item("edit", "Renombrar", rename)];
    if (j.outputs.includes("pieza.scad")) items.push(h("a", { class: "btn btn-block", style: "justify-content:flex-start", href: fileUrl("pieza.scad"), download: `${slug(jobName(j))}.scad`, onclick: () => close() }, icon("file"), "Descargar .scad"));
    if (j.exported?.stl) items.push(item("copy", "Copiar ruta de la carpeta de salida", async () => {
      try { await navigator.clipboard.writeText(j.exported.stl); toast("Ruta copiada"); } catch { toast(j.exported.stl); }
    }));
    items.push(item("trash", "Eliminar", async () => {
      if (!(await confirmSheet(`¿Eliminar «${jobName(j)}»?`, "Eliminar", true))) return;
      try { await del(`/jobs/${id}`); navigate("/trabajos"); } catch (e) { toast(e.message, { kind: "err" }); }
    }, "btn-danger"));
    const close = openSheet("Opciones", h("div", { class: "stack" }, ...items));
  }

  function rename() {
    const input = h("input", { type: "text", value: j.name || "", maxLength: 60, placeholder: "Nombre de la pieza", "aria-label": "Nombre" });
    const form = h("form", { class: "stack", onsubmit: async (e) => {
      e.preventDefault(); close();
      try { await patch(`/jobs/${id}`, { name: input.value }); load(); } catch (er) { toast(er.message, { kind: "err" }); }
    } }, input, h("button", { class: "btn btn-primary btn-block", type: "submit" }, "Guardar"));
    const close = openSheet("Renombrar", form);
    input.focus();
  }

  load();
  return () => { gone = true; stopTimers(); viewer?.dispose(); };
}
