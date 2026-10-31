import { route, start } from "./router.js";
import { haptic, toast } from "./ui.js";

// Cada pantalla se carga bajo demanda: el arranque solo trae lo que se ve.
route("/capturar", () => import("./views/capturar.js").then((m) => m.capturar), { tab: "capturar" });
route("/capturar/vistas", () => import("./camera.js").then((m) => m.camaraVistas), { tab: "capturar", immersive: true, depth: 2 });
route("/capturar/video", () => import("./camera.js").then((m) => m.camaraVideo), { tab: "capturar", immersive: true, depth: 2 });
route("/trabajos", () => import("./views/trabajos.js").then((m) => m.trabajos), { tab: "trabajos" });
route("/trabajos/:id", () => import("./views/detalle.js").then((m) => m.detalle), { tab: "trabajos", depth: 1 });
route("/ajustes", () => import("./views/ajustes.js").then((m) => m.ajustes), { tab: "ajustes" });
start();
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
