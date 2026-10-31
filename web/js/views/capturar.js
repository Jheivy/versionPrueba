import { h, icon, openSheet } from "../ui.js";
import { pref, setPref } from "../api.js";

/** Cómo colocar la hoja de marcadores (ilustración + pasos). */
export function openHelp() {
  const svg = `<svg viewBox="0 0 210 150" role="img" aria-label="Hoja A4 con cuatro marcadores en las esquinas y la pieza en el centro" style="width:100%;border-radius:10px;background:var(--surface-2)">
    <rect x="55" y="8" width="100" height="134" rx="3" fill="#fff" stroke="#9aa6b2"/>
    ${[[60, 13], [135, 13], [60, 122], [135, 122]].map(([x, y]) => `<rect x="${x}" y="${y}" width="15" height="15" fill="#111"/><rect x="${x + 3}" y="${y + 3}" width="9" height="9" fill="#fff"/><rect x="${x + 5}" y="${y + 5}" width="5" height="5" fill="#111"/>`).join("")}
    <path d="M85 55h40v14h-9v26h-14V69h-17z" fill="#1b1f24"/></svg>`;
  const close = openSheet("Cómo colocar la hoja",
    h("div", { html: svg }),
    h("ol", { class: "stack", style: "padding-left:20px;margin:12px 0" },
      h("li", {}, "Imprime la hoja de marcadores al ", h("b", {}, "100 %"), " (sin «ajustar a página») y comprueba con una regla que cada marcador mide 30 mm."),
      h("li", {}, "Ponla plana y sin arrugas. Se deben ver al menos 2 marcadores."),
      h("li", {}, "En cada vista, el contorno va en ", h("b", {}, "negro sobre el papel"), ": apoya la pieza y repasa su silueta con rotulador, o usa tu dibujo."),
      h("li", {}, "Luz difusa, sin sombras fuertes ni reflejos.")),
    h("div", { class: "stack" },
      h("a", { class: "btn btn-block", href: "/api/marker-sheet.pdf", target: "_blank", rel: "noopener" }, icon("download"), "Descargar hoja de marcadores"),
      h("button", { class: "btn btn-primary btn-block", onclick: () => { setPref("helpSeen", true); close(); } }, "Entendido")));
}

export function capturar(root) {
  const card = (ic, title, badge, text, href, cta) =>
    h("a", { class: "card card-link", href },
      h("div", { class: "row" }, icon(ic), h("strong", { class: "grow" }, title), badge && h("span", { class: "chip ok" }, badge)),
      h("span", { class: "muted small" }, text),
      h("span", { class: "btn btn-primary" }, cta));
  root.append(
    h("h1", {}, "Nueva captura"),
    h("p", { class: "muted" }, "Elige cómo quieres escanear la pieza."),
    h("div", { class: "stack" },
      card("views", "3 vistas", "Medidas precisas",
        "Planta, alzado y perfil sobre la hoja de marcadores. Ideal para piezas mecánicas, soportes y tapas. Genera un .scad editable.",
        "#/capturar/vistas", "Empezar con 3 vistas"),
      card("film", "Vídeo 3D", null,
        "Gira alrededor de la pieza (30–60 s). Ideal para formas orgánicas. Se reconstruye en el Mac y luego indicas una medida real.",
        "#/capturar/video", "Grabar vídeo"),
      h("button", { class: "btn btn-ghost btn-block", onclick: openHelp }, "¿Cómo coloco la hoja de marcadores?")));
  if (!pref("helpSeen", false)) openHelp();
}
