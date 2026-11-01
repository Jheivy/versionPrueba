import { pref, setPref } from "../api.js";
import { h, haptic, icon, openSheet } from "../ui.js";

/** Cómo colocar la hoja de marcadores (ilustración + pasos). */
export function openHelp() {
  const svg = `<svg viewBox="0 0 210 150" role="img" aria-label="Hoja A4 con cuatro marcadores en las esquinas y la pieza en el centro" style="width:100%;border-radius:16px;background:var(--surface-2)">
    <rect x="55" y="8" width="100" height="134" rx="4" fill="#fff" stroke="#9aa6b2"/>
    ${[[60, 13], [135, 13], [60, 122], [135, 122]].map(([x, y]) => `<rect x="${x}" y="${y}" width="15" height="15" fill="#111"/><rect x="${x + 3}" y="${y + 3}" width="9" height="9" fill="#fff"/><rect x="${x + 5}" y="${y + 5}" width="5" height="5" fill="#111"/>`).join("")}
    <path d="M85 55h40v14h-9v26h-14V69h-17z" fill="#1b1f24"/></svg>`;
  const close = openSheet("Cómo colocar la hoja",
    h("div", { html: svg }),
    h("ol", { class: "stack", style: "padding-left:20px;margin:14px 0" },
      h("li", {}, "Imprime la hoja de marcadores al ", h("b", {}, "100 %"), " (sin «ajustar a página») y comprueba con una regla que cada marcador mide 30 mm."),
      h("li", {}, "Ponla plana y sin arrugas. Se deben ver al menos 2 marcadores."),
      h("li", {}, "En cada vista, el contorno va en ", h("b", {}, "negro sobre el papel"), ": apoya la pieza y repasa su silueta con rotulador, o usa tu dibujo."),
      h("li", {}, "Luz difusa, sin sombras fuertes ni reflejos.")),
    h("div", { class: "stack" },
      h("a", { class: "btn btn-block", href: "/api/marker-sheet.pdf", target: "_blank", rel: "noopener" }, icon("download"), "Descargar hoja de marcadores"),
      h("button", { class: "btn btn-primary btn-block", onclick: () => { setPref("helpSeen", true); haptic("tap"); close(); } }, "Entendido")));
}

const ART_VIEWS = `<svg viewBox="0 0 300 150" aria-hidden="true">
  <g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect class="draw" pathLength="1" x="30" y="30" width="60" height="42" rx="2"/><circle class="draw" pathLength="1" cx="48" cy="51" r="7"/>
    <path class="draw" pathLength="1" d="M122 72V30h16v26h36v16z"/>
    <rect class="draw" pathLength="1" x="214" y="26" width="36" height="46" rx="2"/>
  </g>
  <g class="dim" fill="none" stroke-width="1.2" stroke-linecap="round" opacity=".95">
    <path d="M30 88h60M30 84v8M90 84v8"/><path d="M122 88h52M122 84v8M174 84v8"/><path d="M214 88h36M214 84v8M250 84v8"/>
  </g>
  <g class="dimtxt" font-family="IBM Plex Mono,ui-monospace,monospace" font-size="9" font-weight="600" text-anchor="middle"><text x="60" y="104">50</text><text x="148" y="104">50</text><text x="232" y="104">30</text></g>
  <g fill="currentColor" font-family="IBM Plex Sans,system-ui" font-size="8.5" font-weight="600" letter-spacing=".12em" text-anchor="middle" opacity=".55"><text x="60" y="132">PLANTA</text><text x="148" y="132">ALZADO</text><text x="232" y="132">PERFIL</text></g>
</svg>`;
const ART_VIDEO = `<svg viewBox="0 0 300 150" aria-hidden="true">
  <ellipse cx="150" cy="84" rx="100" ry="28" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2 6" stroke-linecap="round" opacity=".5"/>
  <g fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <path class="draw" pathLength="1" d="M150 46l30 17v34l-30 17-30-17V63z"/><path class="draw" pathLength="1" d="M150 80l30-17M150 80l-30-17M150 80v34" opacity=".7"/>
  </g>
  <circle class="orbit-dot" r="5.5" fill="var(--accent)" style="offset-path:path('M 50 84 A 100 28 0 0 1 250 84 A 100 28 0 0 1 50 84')"/>
</svg>`;

export function capturar(root) {
  const card = (art, title, badge, text, href, cta, primary) =>
    h("a", { class: "card card-link method", href, onclick: () => haptic("tap") },
      h("div", { class: "art", html: art }),
      h("div", { class: "body" },
        h("div", { class: "title" }, h("strong", {}, title), badge && h("span", { class: "chip ok" }, badge)),
        h("span", { class: "muted small" }, text),
        h("span", { class: "btn" + (primary ? " btn-primary" : "") }, cta)));
  root.append(h("div", { class: "stack stagger" },
    h("div", {}, h("h1", {}, "Nueva captura"), h("p", { class: "lead" }, "Elige cómo medir la pieza.")),
    card(ART_VIEWS, "3 vistas", "Medidas precisas",
      "Planta, alzado y perfil sobre la hoja de marcadores. Ideal para piezas mecánicas, soportes y tapas. Genera un .scad editable.",
      "#/capturar/vistas", "Empezar con 3 vistas", true),
    card(ART_VIDEO, "Vídeo 3D", null,
      "Gira alrededor de la pieza (30–60 s). Ideal para formas orgánicas. Se reconstruye en el Mac y luego indicas una medida real.",
      "#/capturar/video", "Grabar vídeo"),
    h("button", { class: "btn btn-ghost btn-block", onclick: openHelp }, "¿Cómo coloco la hoja de marcadores?")));
  if (!pref("helpSeen", false)) openHelp();
}
