import { api, pref, setPref } from "../api.js";
import { h, icon } from "../ui.js";

export function ajustes(root) {
  const status = h("div", {}, h("p", { class: "muted" }, "Comprobando el Mac…"));
  const toggle = (label, sub, key, def, onChange) => {
    const input = h("input", { type: "checkbox", checked: pref(key, def), onchange: () => { setPref(key, input.checked); onChange?.(input); } });
    return h("label", { class: "toggle settings-row" }, h("span", {}, h("b", {}, label), h("br"), h("span", { class: "muted small" }, sub)), input);
  };
  const srow = (ok, label, detail) => h("div", { class: "settings-row" },
    h("span", {}, h("span", { class: "dot " + (ok ? "ok" : "err") }), " ", label), h("span", { class: "muted small", style: "text-align:right" }, detail));

  root.append(
    h("h1", {}, "Ajustes"),
    h("h2", { style: "margin-top:16px" }, "Servidor"), h("div", { class: "card" }, status),
    h("h2", { style: "margin-top:16px" }, "Preferencias"),
    h("div", { class: "card" },
      toggle("Revisar contornos", "Ver lo que detecta el sistema antes de generar el modelo", "review", true),
      toggle("Avisarme al terminar", "Notificación cuando acabe un trabajo largo", "notify", false, async (i) => {
        if (i.checked && "Notification" in window && (await Notification.requestPermission()) !== "granted") { i.checked = false; setPref("notify", false); }
      })),
    h("h2", { style: "margin-top:16px" }, "Ayuda"),
    h("div", { class: "card stack" },
      h("a", { class: "btn btn-block", href: "/api/marker-sheet.pdf", target: "_blank", rel: "noopener" }, icon("download"), "Hoja de marcadores (PDF, A4)"),
      h("p", { class: "muted small", style: "margin:0" }, "Imprímela al 100 %. Cada marcador debe medir 30 mm."),
      h("p", { class: "muted small", style: "margin:0" }, "Instalar: menú ⋮ de Chrome → «Instalar app». Si el navegador avisa del certificado, instala la CA de mkcert (ver README).")));

  api("/health").then((hl) => {
    status.replaceChildren(
      srow(true, "Conectado al Mac", `v${hl.version}`),
      srow(hl.openscad, "OpenSCAD", hl.openscad ? "Instalado" : "Falta: brew install openscad"),
      srow(hl.object_capture, "Object Capture (vídeo 3D)", hl.object_capture ? "Disponible" : "No disponible"),
      srow(true, "Carpeta de salida", hl.out_dir),
      srow(hl.webhook, "Webhook", hl.webhook ? "Activo" : "Sin configurar"));
  }).catch(() => status.replaceChildren(srow(false, "Sin conexión con el Mac", "Comprueba la Wi-Fi")));
}
