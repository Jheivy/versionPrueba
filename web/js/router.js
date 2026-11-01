const routes = [];
let cleanup = null;
let token = 0;
let prevDepth = 0;
let started = false;

/** route("/trabajos/:id", () => import("./views/detalle.js").then(m => m.detalle), {tab, immersive, depth}) */
export function route(pattern, load, opts = {}) {
  const keys = [];
  const re = new RegExp("^" + pattern.replace(/:(\w+)/g, (_, k) => (keys.push(k), "([^/]+)")) + "$");
  routes.push({ re, keys, load, opts });
}

export function navigate(path, replace = false) {
  if (replace) location.replace("#" + path); else location.hash = "#" + path;
}

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export async function go() {
  const my = ++token;
  const path = location.hash.slice(1) || "/capturar";
  const root = document.getElementById("view");
  for (const r of routes) {
    const m = r.re.exec(path);
    if (!m) continue;
    const params = Object.fromEntries(r.keys.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
    const view = await r.load();            // módulo de la pantalla (suele estar ya precargado)
    if (my !== token) return;               // una navegación más reciente gana
    const swap = async () => {
      cleanup?.();
      cleanup = null;
      for (const sheet of document.querySelectorAll(".backdrop")) sheet.remove(); // cierra hojas modales abiertas
      document.body.classList.toggle("immersive", !!r.opts.immersive);
      const tabs = [...document.querySelectorAll(".tabbar a")];
      const at = tabs.findIndex((a) => a.dataset.tab === r.opts.tab);
      if (at >= 0) document.querySelector(".tabbar").style.setProperty("--i", at);   // mueve la pastilla
      for (const a of tabs) {
        if (a.dataset.tab === r.opts.tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
      }
      root.replaceChildren();
      window.scrollTo(0, 0);
      cleanup = (await view(root, params)) || null;
    };
    const depth = r.opts.depth ?? 0;
    const dir = depth > prevDepth ? "forward" : depth < prevDepth ? "back" : "tab";
    prevDepth = depth;
    if (started && document.startViewTransition && !reducedMotion()) {
      document.documentElement.dataset.nav = dir;   // el CSS elige la animación según la dirección
      try { await document.startViewTransition(swap).updateCallbackDone; } catch { /* transición cancelada */ }
    } else {
      await swap();
    }
    started = true;
    return;
  }
  navigate("/capturar");
}

export const start = () => { addEventListener("hashchange", go); go(); };
