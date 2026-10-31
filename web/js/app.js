import { route, start } from "./router.js";
import { capturar } from "./views/capturar.js";
import { camaraVistas, camaraVideo } from "./camera.js";
import { trabajos } from "./views/trabajos.js";
import { detalle } from "./views/detalle.js";
import { ajustes } from "./views/ajustes.js";

route("/capturar", capturar, { tab: "capturar" });
route("/capturar/vistas", camaraVistas, { tab: "capturar", immersive: true });
route("/capturar/video", camaraVideo, { tab: "capturar", immersive: true });
route("/trabajos", trabajos, { tab: "trabajos" });
route("/trabajos/:id", detalle, { tab: "trabajos" });
route("/ajustes", ajustes, { tab: "ajustes" });
start();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
