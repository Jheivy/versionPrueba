import * as THREE from "three";
import { authFetch } from "./api.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** Visor 3D de una pieza en mm: Z hacia arriba, apoyada en una rejilla de 1 cm. */
export function createViewer(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
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
  let mesh, inner, planeViz, size0, radius = 50, raf = 0, alive = true, dimsGroup = null;
  const css = () => getComputedStyle(canvas);
  const fmt = (n) => n.toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  /** Etiqueta de cota: una pastilla con el valor en mono, dibujada en un canvas y colocada como sprite. */
  function label(text, unit, h) {
    const c = document.createElement("canvas"), g = c.getContext("2d"), S = 3;
    const font = `600 ${22 * S}px "IBM Plex Mono", ui-monospace, monospace`;
    g.font = font;
    const tw = g.measureText(text).width; g.font = `500 ${14 * S}px "IBM Plex Mono", ui-monospace, monospace`; const uw = g.measureText(unit).width; g.font = font;
    const w = tw + uw + 34 * S, hh = 38 * S;
    c.width = Math.ceil(w); c.height = hh;
    g.font = font;
    const style = css(), pill = style.getPropertyValue("--surface").trim() || "#fff", ink = style.getPropertyValue("--fg").trim() || "#111", acc = style.getPropertyValue("--accent").trim() || "#f2601a";
    g.fillStyle = pill; g.strokeStyle = acc; g.lineWidth = 2 * S;
    g.beginPath(); g.roundRect(S, S, c.width - 2 * S, hh - 2 * S, 8 * S); g.fill(); g.stroke();
    g.fillStyle = ink; g.textBaseline = "middle"; g.fillText(text, 14 * S, hh / 2 + S);
    g.font = `500 ${14 * S}px "IBM Plex Mono", ui-monospace, monospace`; g.fillStyle = style.getPropertyValue("--muted").trim() || "#666";
    g.fillText(unit, 18 * S + tw, hh / 2 + 2 * S);
    const tex = new THREE.CanvasTexture(c); tex.anisotropy = 4;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sp.scale.set(h * (c.width / hh), h, 1); sp.renderOrder = 12;
    return sp;
  }

  /** Cotas al estilo de un plano: línea con marcas a 45°, líneas de referencia y el valor en el centro. */
  function buildDims(size) {
    const w = size.x, d = size.y, ht = size.z, big = Math.max(w, d, ht), o = big * 0.14 + 3, e = big * 0.03, t = big * 0.025;
    const acc = new THREE.Color(css().getPropertyValue("--fg").trim() || "#12151b");   // cotas en tinta, como en un plano
    const pts = [], g = new THREE.Group();
    const V = (x, y, z) => new THREE.Vector3(x, y, z);
    const dim = (a, b, n, value) => {                       // a, b: extremos sobre la pieza; n: dirección de la cota
      const u = b.clone().sub(a).normalize(), a2 = a.clone().addScaledVector(n, o), b2 = b.clone().addScaledVector(n, o);
      const tick = u.clone().add(n).normalize().multiplyScalar(t);
      pts.push(a, a2.clone().addScaledVector(n, e), b, b2.clone().addScaledVector(n, e), a2, b2,
        a2.clone().sub(tick), a2.clone().add(tick), b2.clone().sub(tick), b2.clone().add(tick));
      const sp = label(fmt(value), "mm", big * 0.085);
      sp.position.copy(a2.clone().add(b2).multiplyScalar(0.5)).addScaledVector(n, big * 0.07);
      g.add(sp);
    };
    dim(V(-w / 2, 0, d / 2), V(w / 2, 0, d / 2), V(0, 0, 1), w);       // ancho (X)
    dim(V(w / 2, 0, d / 2), V(w / 2, 0, -d / 2), V(1, 0, 0), d);       // fondo (Y)
    dim(V(-w / 2, 0, d / 2), V(-w / 2, ht, d / 2), V(-1, 0, 0), ht);   // alto (Z)
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const lines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: acc, depthTest: false, transparent: true }));
    lines.renderOrder = 11;
    g.add(lines);
    return g;
  }

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
      mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: new THREE.Color(css().getPropertyValue("--accent").trim() || "#f2601a"), roughness: 0.5, metalness: 0.02 }));
      mesh.rotation.x = -Math.PI / 2; // Z (alto) -> arriba
      inner = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: new THREE.Color(css().getPropertyValue("--accent-ink").trim() || "#b5440a"), side: THREE.BackSide }));
      inner.rotation.x = mesh.rotation.x; // cara de corte: el interior (caras traseras) se pinta plano
      scene.add(mesh, inner);
      size0 = size.clone();
      planeViz = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: new THREE.Color(css().getPropertyValue("--accent").trim() || "#f2601a"), transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }));
      planeViz.visible = false; planeViz.renderOrder = 9;
      scene.add(planeViz);
      radius = Math.max(size.x, size.y, size.z) * 0.9;
      const span = Math.max(20, Math.ceil((Math.max(size.x, size.y) * 1.8 + 20) / 10) * 10);
      const grid = new THREE.GridHelper(span, span / 10, new THREE.Color(css().getPropertyValue("--line-strong").trim() || "#bbb"), new THREE.Color(css().getPropertyValue("--line").trim() || "#ddd"));
      grid.material.opacity = 0.55; grid.material.transparent = true;
      const cube = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(10, 10, 10)),
        new THREE.LineBasicMaterial({ color: new THREE.Color(css().getPropertyValue("--muted").trim() || "#59616f") })); // cubo de referencia de 1 cm
      cube.position.set(-(size.x / 2 + 15), 5, 0);
      helpers.add(grid, cube);
      try { await document.fonts?.load('600 22px "IBM Plex Mono"'); } catch { /* sin Font Loading API */ }
      dimsGroup = buildDims(size);
      scene.add(dimsGroup);
      resetView();
      return size; // x=ancho, y=fondo, z=alto
    },
    resetView,
    setGrid(on) { helpers.visible = on; },
    /** Corte por un plano: axis "x" (ancho), "y" (fondo) o "z" (alto) o null; t 0..1 a lo largo de la pieza; flip invierte el lado. */
    setSection(axis, t = 0.5, flip = false) {
      if (!mesh) return;
      if (!axis) { for (const m of [mesh, inner]) m.material.clippingPlanes = null; planeViz.visible = false; return; }
      const sz = size0, W = { x: [-sz.x / 2, sz.x / 2], y: [-sz.y / 2, sz.y / 2], z: [0, sz.z] }[axis];
      const pos = W[0] + (W[1] - W[0]) * t, k = flip ? 1 : -1;
      // ejes del mundo: X = ancho, Y = alto (Z de la pieza), Z = -fondo (Y de la pieza)
      const n = axis === "x" ? new THREE.Vector3(k, 0, 0) : axis === "z" ? new THREE.Vector3(0, k, 0) : new THREE.Vector3(0, 0, -k);
      const plane = new THREE.Plane(n, -n.dot(axis === "x" ? new THREE.Vector3(pos, 0, 0) : axis === "z" ? new THREE.Vector3(0, pos, 0) : new THREE.Vector3(0, 0, -pos)));
      for (const m of [mesh, inner]) { m.material.clippingPlanes = [plane]; m.material.needsUpdate = true; }
      const pad = 1.15;
      planeViz.visible = true; planeViz.rotation.set(0, 0, 0);
      if (axis === "x") { planeViz.rotation.y = Math.PI / 2; planeViz.scale.set(sz.y * pad, sz.z * pad, 1); planeViz.position.set(pos, sz.z / 2, 0); }
      else if (axis === "z") { planeViz.rotation.x = Math.PI / 2; planeViz.scale.set(sz.x * pad, sz.y * pad, 1); planeViz.position.set(0, pos, 0); }
      else { planeViz.scale.set(sz.x * pad, sz.z * pad, 1); planeViz.position.set(0, sz.z / 2, -pos); }
    },
    setDims(on) { if (dimsGroup) dimsGroup.visible = on; },
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
