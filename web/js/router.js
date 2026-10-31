const routes = [];
let cleanup = null;

/** route("/trabajos/:id", fn(root, params), {tab:"trabajos", immersive:false}) */
export function route(pattern, view, opts = {}) {
  const keys = [];
  const re = new RegExp("^" + pattern.replace(/:(\w+)/g, (_, k) => (keys.push(k), "([^/]+)")) + "$");
  routes.push({ re, keys, view, opts });
}

export function navigate(path) { location.hash = "#" + path; }

export async function go() {
  const path = location.hash.slice(1) || "/capturar";
  const root = document.getElementById("view");
  cleanup?.();
  cleanup = null;
  for (const r of routes) {
    const m = r.re.exec(path);
    if (!m) continue;
    const params = Object.fromEntries(r.keys.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
    document.body.classList.toggle("immersive", !!r.opts.immersive);
    for (const a of document.querySelectorAll(".tabbar a")) {
      if (a.dataset.tab === r.opts.tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    }
    root.replaceChildren();
    window.scrollTo(0, 0);
    cleanup = (await r.view(root, params)) || null;
    return;
  }
  navigate("/capturar");
}

export const start = () => { addEventListener("hashchange", go); go(); };
