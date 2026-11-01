import { api, del, post, pref, setPref } from "../api.js";
import { navigate } from "../router.js";
import { confirmSheet, h, haptic, icon, openSheet, relTime, toast } from "../ui.js";

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

  const security = h("div", {}, h("div", { class: "settings-row" }, h("div", { class: "skeleton sk-line", style: "width:45%" })));

  async function pairAnother() {
    haptic("tap");
    let info;
    try { info = await post("/pairing-code"); } catch (e) { return toast(e.message, { kind: "err" }); }
    const left = h("span", { class: "small muted" });
    const end = Date.now() + info.expires_in * 1000;
    const tick = setInterval(() => {
      const s = Math.max(0, Math.round((end - Date.now()) / 1000));
      left.textContent = s ? `Caduca en ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}` : "Caducado: genera otro";
      if (!s) clearInterval(tick);
    }, 1000);
    const close = openSheet("Emparejar otro dispositivo", h("div", { class: "qr" },
      h("img", { src: `/api/pairing/qr.svg?code=${info.code}`, alt: "QR para emparejar", width: 260, height: 260 }),
      h("div", { class: "qr-code" }, info.display), left,
      h("p", { class: "small muted", style: "margin:0" }, "Escanea el QR con el otro móvil o escribe el código en su pantalla de emparejamiento. Vale una sola vez."),
      h("button", { class: "btn btn-block", onclick: async () => { try { await navigator.clipboard.writeText(info.url); toast("Enlace copiado"); } catch { toast(info.url); } } }, icon("copy"), "Copiar enlace")));
    const obs = new MutationObserver(() => { if (!document.body.contains(left)) { clearInterval(tick); obs.disconnect(); } });
    obs.observe(document.body, { childList: true });
    void close;
  }

  const storageBox = h("div", {}, h("div", { class: "settings-row" }, h("div", { class: "skeleton sk-line", style: "width:40%" })));
  const mb = (b) => !b ? "0 MB" : b >= 1024 ** 3 ? `${(b / 1024 ** 3).toFixed(1)} GB` : `${Math.max(b / 1024 ** 2, 0.1).toFixed(b < 1024 ** 2 * 10 ? 1 : 0)} MB`;
  async function drawStorage() {
    let st;
    try { st = await api("/storage"); } catch { return storageBox.replaceChildren(h("div", { class: "settings-row" }, h("span", { class: "muted small" }, "No disponible"))); }
    const days = st.retention_days || 30;
    storageBox.replaceChildren(
      srow("ok", "Trabajos guardados", `${st.jobs} · ${mb(st.bytes)}`),
      srow("off", "Borrado automático", st.retention_days ? `Tras ${st.retention_days} días sin tocar` : "Desactivado"),
      srow("off", "Tamaño máximo de subida", `Foto ${st.max_photo_mb} MB · vídeo ${st.max_video_mb} MB`),
      h("div", { style: "padding:12px 0" }, h("button", { class: "btn btn-block", disabled: !st.jobs, onclick: async () => {
        if (!(await confirmSheet(`¿Borrar los trabajos que no se han tocado en ${days} días? Los archivos ya exportados no se borran.`, "Borrar", true))) return;
        try { const r = await post("/storage/cleanup", { days }); haptic("success"); toast(r.removed ? `${r.removed} ${r.removed === 1 ? "trabajo borrado" : "trabajos borrados"} · ${mb(r.freed)}` : "Nada que borrar"); drawStorage(); } catch (e) { toast(e.message, { kind: "err" }); }
      } }, icon("trash"), `Borrar trabajos de más de ${days} días`)));
  }

  async function signOut() {
    if (!(await confirmSheet("¿Cerrar la sesión de este móvil? Tendrás que volver a emparejarlo.", "Cerrar sesión", true))) return;
    try { await post("/auth/logout"); } catch { /* ya no autorizado: da igual */ }
    try { await caches.delete("s2p-runtime-1"); } catch { /* sin Cache API */ }   // fuera miniaturas y modelos de este móvil
    navigate("/emparejar", true);
  }

  async function drawSecurity() {
    const st = await (await fetch("/api/auth/status")).json();
    if (!st.required) return security.replaceChildren(h("div", { class: "settings-row" }, h("span", { class: "muted small" }, "La autenticación está desactivada (SCAN2PRINT_AUTH=off): cualquiera en tu Wi-Fi puede usar la app.")));
    let list = [];
    try { list = await api("/devices"); } catch { /* sin permiso */ }
    const rows = list.map((d) => h("div", { class: "device" },
      h("span", { class: "thumb", style: "width:40px;height:40px;border-radius:12px" }, icon(d.kind === "api" ? "file" : "camera")),
      h("div", { class: "meta" }, h("strong", {}, d.name),
        h("span", { class: "muted small" }, `${d.kind === "api" ? "Agente" : "Móvil"} · ${relTime(new Date(d.last_seen * 1000).toISOString())}`)),
      d.current ? h("span", { class: "chip ok" }, "Este móvil") : h("button", { class: "icon-btn", "aria-label": `Revocar ${d.name}`, style: "color:var(--muted)", onclick: async () => {
        if (!(await confirmSheet(`¿Revocar «${d.name}»? Dejará de poder usar la app.`, "Revocar", true))) return;
        try { await del(`/devices/${d.id}`); haptic("success"); drawSecurity(); } catch (e) { toast(e.message, { kind: "err" }); }
      } }, icon("trash"))));
    security.replaceChildren(
      ...(rows.length ? rows : [h("div", { class: "settings-row" }, h("span", { class: "muted small" }, st.local ? "Estás en el propio Mac: no necesita emparejarse." : "Sin dispositivos."))]),
      h("div", { class: "stack", style: "padding:12px 0" },
        h("button", { class: "btn btn-block", onclick: pairAnother }, icon("camera"), "Emparejar otro dispositivo"),
        !st.local && h("button", { class: "btn btn-ghost btn-block", onclick: signOut }, "Cerrar sesión en este móvil")));
  }

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
    h("div", { class: "group-title" }, "Almacenamiento"), h("div", { class: "group" }, storageBox),
    h("div", { class: "group-title" }, "Seguridad"), h("div", { class: "group" }, security),
    h("div", { class: "group-title" }, "Ayuda"),
    h("div", { class: "card stack" },
      h("a", { class: "btn btn-block", href: "/api/marker-sheet.pdf", target: "_blank", rel: "noopener" }, icon("download"), "Hoja de marcadores (PDF, A4)"),
      h("p", { class: "muted small", style: "margin:0" }, "Imprímela al 100 %. Cada marcador debe medir 30 mm."),
      h("p", { class: "muted small", style: "margin:0" }, "Instalar: menú ⋮ de Chrome → «Instalar app». Si el navegador avisa del certificado, instala la CA de mkcert (ver README)."))));

  drawSecurity();
  drawStorage();
  api("/health").then((hl) => {
    status.replaceChildren(
      srow("ok", "Conectado al Mac", `v${hl.version}`),
      srow(hl.openscad ? "ok" : "err", "OpenSCAD", hl.openscad ? "Instalado" : "Falta: brew install openscad"),
      srow(hl.object_capture ? "ok" : "off", "Object Capture (vídeo 3D)", hl.object_capture ? "Disponible" : "No disponible"),
      srow("ok", "Carpeta de salida", hl.out_dir),
      srow(hl.webhook ? "ok" : "off", "Webhook", hl.webhook ? "Activo" : "Sin configurar"));
  }).catch(() => status.replaceChildren(srow("err", "Sin conexión con el Mac", "Comprueba la Wi-Fi")));
}
