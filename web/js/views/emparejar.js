import { h, haptic, icon } from "../ui.js";
import { navigate } from "../router.js";

/** Nombre razonable para este dispositivo a partir del navegador (p. ej. «Pixel 7»). */
function guessName() {
  const m = /Android[^;)]*;\s*([^;)]+?)(?:\sBuild|\))/.exec(navigator.userAgent);
  return (m && m[1].trim()) || (/iPhone|iPad/.test(navigator.userAgent) ? "iPhone" : "Móvil");
}

const MESSAGES = { 401: "Código no válido o caducado. Pide uno nuevo en el Mac.", 429: "Demasiados intentos. Espera unos minutos." };

export function emparejar(root, { code: fromLink } = {}) {
  const clean = (v) => v.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
  const pretty = (v) => (v.length > 4 ? `${v.slice(0, 4)}-${v.slice(4)}` : v);
  const code = h("input", { class: "code", type: "text", inputMode: "text", autocapitalize: "characters", autocomplete: "off",
    spellcheck: false, maxLength: 9, placeholder: "ABCD-EFGH", "aria-label": "Código de emparejamiento", value: pretty(clean(fromLink || "")) });
  code.addEventListener("input", () => { code.value = pretty(clean(code.value)); });
  const name = h("input", { type: "text", maxLength: 40, value: guessName(), "aria-label": "Nombre de este dispositivo" });
  const msg = h("p", { class: "small", role: "alert", style: "color:var(--err);margin:0;min-height:1.4em" });
  const go = h("button", { class: "btn btn-primary btn-block", type: "submit" }, "Emparejar");

  async function submit(e) {
    e?.preventDefault();
    const value = clean(code.value);
    if (value.length < 8) { msg.textContent = "El código tiene 8 caracteres."; return code.focus(); }
    msg.textContent = ""; go.setAttribute("aria-busy", "true");
    try {
      const r = await fetch("/api/pair", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: value, name: name.value }) });
      if (!r.ok) throw Object.assign(new Error(), { status: r.status });
      haptic("success");
      navigate("/capturar", true);          // replace: «Atrás» no vuelve a un código ya gastado
    } catch (err) {
      haptic("error");
      msg.textContent = MESSAGES[err.status] || "No se pudo conectar con el Mac. Comprueba la Wi-Fi.";
      go.removeAttribute("aria-busy");
    }
  }

  root.append(h("div", { class: "pair" }, h("div", { class: "stack stagger" },
    h("img", { class: "brand", src: "icons/icon.svg", alt: "", width: 72, height: 72 }),
    h("div", {}, h("h1", {}, "Empareja este móvil"),
      h("p", { class: "lead" }, "Tus piezas son privadas: el Mac solo atiende a dispositivos emparejados.")),
    h("form", { class: "card stack", onsubmit: submit },
      h("label", { class: "field" }, "Código del Mac", code),
      h("label", { class: "field" }, "Nombre de este móvil", name),
      msg, go),
    h("div", { class: "card small muted stack", style: "gap:8px" },
      h("b", { style: "color:var(--fg)" }, "¿De dónde saco el código?"),
      h("span", {}, "En el Mac: ", h("code", {}, "deploy/pair.sh"), " muestra un QR y el código (vale 10 minutos y se usa una vez)."),
      h("span", {}, "O en otro móvil ya emparejado: Ajustes → Emparejar otro dispositivo.")))));
  if (fromLink) setTimeout(submit, 350);      // llegó con el QR: se empareja solo
  else code.focus();
  return () => {};
}
