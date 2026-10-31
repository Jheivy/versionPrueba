import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

let renderer, scene, camera, controls, mesh;

function init(canvas) {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(40, 1, 0.1, 5000);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(1, 2, 3);
  scene.add(sun);
  controls = new OrbitControls(camera, canvas);
  (function loop() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== w || canvas.height !== h) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  })();
}

export async function showSTL(canvas, url) {
  if (!renderer) init(canvas);
  if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); mesh = null; }
  if (!url) return;
  const geo = new STLLoader().parse(await (await fetch(url, { cache: "no-store" })).arrayBuffer());
  geo.computeVertexNormals();
  geo.center();
  mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0x1f6feb, roughness: 0.6 }));
  mesh.rotation.x = -Math.PI / 2; // Z (alto) hacia arriba
  scene.add(mesh);
  geo.computeBoundingSphere();
  const r = geo.boundingSphere.radius;
  camera.position.set(r * 2.2, r * 1.6, r * 2.2);
  controls.target.set(0, 0, 0);
}
