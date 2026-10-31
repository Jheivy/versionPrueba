import { api, pref, setPref } from "../api.js";
import { h, haptic, icon } from "../ui.js";

export function ajustes(root) {
  const status = h("div", {}, h("div", { class: "settings-row" }, h("div", { class: "skeleton sk-line", style: "width:50%" })),
    h("div", { class: "settings-row" }, h("div", { class: "skeleton sk-line", style: "width:35%" })));
  const toggle = (label, sub, key, def, onChange) => {
    const input = h("input", { type: "checkbox", checked: pref(key, def), onchange: () => { setPref(key, input.checked); haptic("tap"); onChange?.(input); } });
    return h("label", { class: "toggle settings-row" }, h("span", {}, h("b", {}, label), h("br"), h("span", { class: "muted small" }, sub)), input);
  };
  // estado: "ok" (verde), "off" (gris: opcional y sin activar) o "err" (rojo: falla algo necesario)
  const srow = (state, label, detail) => h("div", { class: "settings-row" },
    h("span", { class: "row" }, h("span", { class: "dot " + (state === "off" ? "" : state) }), label), h("span", { class: "muted small", style: "text-align:right" }, detail));

  root.append(h("div", { class: "stagger" },
    h("h1", {}, "Ajustes"),
    h("div", { class: "group-title" }, "Servidor"), h("div", { class: "group" }, status),
    h("div", { class: "group-title" }, "Preferencias"),
    h("div", { class: "group" },
      toggle("Revisar contornos", "Ver lo que detecta el sistema antes de generar el modelo", "review", true),
      toggle("Vibración", "Respuesta táctil al disparar, confirmar y terminar", "haptics", true),
      toggle("Avisarme al terminar", "Notificación cuando acabe un trabajo largo", "notify", false, async (i) => {
        if (i.checked && "Notification" in window && (await Notification.requestPermission()) !== "granted") { i.checked = false; setPref("notify", false); }
      })),
    h("div", { class: "group-title" }, "Ayuda"),
    h("div", { class: "card stack" },
      h("a", { class: "btn btn-block", href: "/api/marker-sheet.pdf", target: "_blank", rel: "noopener" }, icon("download"), "Hoja de marcadores (PDF, A4)"),
      h("p", { class: "muted small", style: "margin:0" }, "Imprímela al 100 %. Cada marcador debe medir 30 mm."),
      h("p", { class: "muted small", style: "margin:0" }, "Instalar: menú ⋮ de Chrome → «Instalar app». Si el navegador avisa del certificado, instala la CA de mkcert (ver README)."))));

  api("/health").then((hl) => {
    status.replaceChildren(
      srow("ok", "Conectado al Mac", `v${hl.version}`),
      srow(hl.openscad ? "ok" : "err", "OpenSCAD", hl.openscad ? "Instalado" : "Falta: brew install openscad"),
      srow(hl.object_capture ? "ok" : "off", "Object Capture (vídeo 3D)", hl.object_capture ? "Disponible" : "No disponible"),
      srow("ok", "Carpeta de salida", hl.out_dir),
      srow(hl.webhook ? "ok" : "off", "Webhook", hl.webhook ? "Activo" : "Sin configurar"));
  }).catch(() => status.replaceChildren(srow("err", "Sin conexión con el Mac", "Comprueba la Wi-Fi")));
}
