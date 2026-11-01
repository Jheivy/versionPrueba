import { navigate, route, start } from "./router.js";
import { haptic, toast } from "./ui.js";

// Cada pantalla se carga bajo demanda: el arranque solo trae lo que se ve.
route("/capturar", () => import("./views/capturar.js").then((m) => m.capturar), { tab: "capturar" });
route("/capturar/vistas", () => import("./camera.js").then((m) => m.camaraVistas), { tab: "capturar", immersive: true, depth: 2 });
route("/capturar/video", () => import("./camera.js").then((m) => m.camaraVideo), { tab: "capturar", immersive: true, depth: 2 });
route("/trabajos", () => import("./views/trabajos.js").then((m) => m.trabajos), { tab: "trabajos" });
route("/trabajos/:id", () => import("./views/detalle.js").then((m) => m.detalle), { tab: "trabajos", depth: 1 });
route("/emparejar", () => import("./views/emparejar.js").then((m) => m.emparejar), { tab: "ajustes", immersive: true, depth: 2 });
route("/emparejar/:code", () => import("./views/emparejar.js").then((m) => m.emparejar), { tab: "ajustes", immersive: true, depth: 2 });
route("/ajustes", () => import("./views/ajustes.js").then((m) => m.ajustes), { tab: "ajustes" });
// Sin emparejar, el servidor responde 401: se lleva al usuario a la pantalla de emparejamiento.
addEventListener("s2p:unauthorized", () => { if (!location.hash.startsWith("#/emparejar")) navigate("/emparejar", true); });
start();
// En paralelo (sin retrasar el primer pintado): si este móvil no está emparejado, directo a emparejar.
fetch("/api/auth/status").then((r) => r.json()).then((st) => {
  if (st.required && !st.authenticated && !location.hash.startsWith("#/emparejar")) navigate("/emparejar", true);
}).catch(() => {});
document.querySelector(".tabbar")?.addEventListener("click", (e) => e.target.closest("a") && haptic("tick"));

// Con el navegador en reposo se precargan el resto de pantallas y el visor 3D (three.js, local). Se usa
// `modulepreload` y no `import()`: descarga y compila sin EJECUTAR, así no bloquea el hilo principal
// (ejecutar three.js son ~400 ms en un móvil modesto y retrasaría justo el toque del usuario).
const idle = window.requestIdleCallback || ((f) => setTimeout(f, 1500));
idle(() => {
  for (const m of ["./views/trabajos.js", "./views/detalle.js", "./views/ajustes.js", "./views/capturar.js", "./camera.js", "./viewer.js"]) {
    const link = document.createElement("link");
    link.rel = "modulepreload";
    link.href = new URL(m, import.meta.url).href;
    document.head.append(link);
  }
}, { timeout: 4000 });

if ("serviceWorker" in navigator) {
  const hadController = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // una versión nueva tomó el control: los módulos cargados y los que falten podrían no ser de la misma versión
    if (hadController) toast("Hay una versión nueva de la app", { action: "Actualizar", onAction: () => location.reload() });
  });
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
