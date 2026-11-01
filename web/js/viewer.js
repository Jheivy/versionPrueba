import * as THREE from "three";
import { authFetch } from "./api.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** Visor 3D de una pieza en mm: Z hacia arriba, apoyada en una rejilla de 1 cm. */
export function createViewer(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 10000);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(1, 2, 3);
  scene.add(sun);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.autoRotate = true;            // un giro suave al aparecer; se detiene al tocar o a los 6 s
  controls.autoRotateSpeed = 1.6;
  controls.addEventListener("start", () => { controls.autoRotate = false; });
  const stopSpin = setTimeout(() => { controls.autoRotate = false; }, 6000);
  const helpers = new THREE.Group();
  scene.add(helpers);
  let mesh, radius = 50, raf = 0, alive = true;

  const resetView = () => {
    camera.position.set(radius * 2.4, radius * 1.7, radius * 2.4);
    controls.target.set(0, radius * 0.25, 0);
    controls.update();
  };

  (function loop() {
    if (!alive) return;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (w && h && (canvas.width !== Math.round(w * renderer.getPixelRatio()) || canvas.height !== Math.round(h * renderer.getPixelRatio()))) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    controls.update();
    renderer.render(scene, camera);
    raf = requestAnimationFrame(loop);
  })();

  return {
    async load(url) {
      const geo = new STLLoader().parse(await (await authFetch(url, { cache: "no-store" })).arrayBuffer());
      geo.computeVertexNormals();
      geo.computeBoundingBox();
      const b = geo.boundingBox;
      geo.translate(-(b.min.x + b.max.x) / 2, -(b.min.y + b.max.y) / 2, -b.min.z); // centra y apoya en Z=0
      const size = new THREE.Vector3(); geo.boundingBox.getSize(size);
      mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0x4c8dff, roughness: 0.55, metalness: 0.05 }));
      mesh.rotation.x = -Math.PI / 2; // Z (alto) -> arriba
      scene.add(mesh);
      radius = Math.max(size.x, size.y, size.z) * 0.9;
      const span = Math.max(20, Math.ceil((Math.max(size.x, size.y) * 1.8 + 20) / 10) * 10);
      const grid = new THREE.GridHelper(span, span / 10, 0x8b97a5, 0xb4bcc6);
      grid.material.opacity = 0.55; grid.material.transparent = true;
      const cube = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(10, 10, 10)),
        new THREE.LineBasicMaterial({ color: 0xe5484d })); // cubo de referencia de 1 cm
      cube.position.set(-(size.x / 2 + 15), 5, 0);
      helpers.add(grid, cube);
      resetView();
      return size; // x=ancho, y=fondo, z=alto
    },
    resetView,
    setGrid(on) { helpers.visible = on; },
    dispose() {
      alive = false;
      clearTimeout(stopSpin);
      cancelAnimationFrame(raf);
      controls.dispose();
      mesh?.geometry.dispose();
      renderer.dispose();
    },
  };
}
