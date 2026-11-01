import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";
import { start } from "./harness.mjs";

let h;
before(async () => { h = await start(); });
after(async () => { await h?.stop(); });

/** Desbordes, objetivos táctiles < 44 px y botones sin nombre de la pantalla abierta. */
const audit = (page) => page.evaluate(() => ({
  hscroll: document.documentElement.scrollWidth > innerWidth + 1,
  small: [...document.querySelectorAll("a,button,input:not([type=checkbox]),select")].filter((e) => {
    const b = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return b.width > 0 && b.height > 0 && cs.visibility !== "hidden" && (b.height < 44 || b.width < 44)
      && !e.closest(".chips") && !e.closest(".seg") && !e.closest(".cam");
  }).map((e) => `${(e.getAttribute("aria-label") || e.textContent || e.tagName).trim().slice(0, 24)} ${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`),
  unnamed: [...document.querySelectorAll("button,a")].filter((e) => !(e.textContent.trim() || e.getAttribute("aria-label") || e.querySelector("img[alt]"))).length,
}));
const clean = (r) => !(r.hscroll || r.small.length || r.unnamed);

const go = (page, hash, selector) => page.goto(`${h.base}/#/${hash}`).then(() => page.waitForSelector(selector, { timeout: 20000 }));

describe("recorrido en el móvil", () => {
  test("capturar ofrece los dos métodos y trabajos lista las piezas con su miniatura 3D", async () => {
    const { page, errors, close } = await h.page();
    await go(page, "capturar", ".method");
    assert.equal(await page.locator(".method").count(), 2);
    await page.click("text=Trabajos");
    await page.waitForSelector(".job");
    assert.equal(await page.locator(".job").count(), 6);
    await page.waitForFunction(() => { const i = document.querySelector("img.thumb.model"); return i?.complete && i.naturalWidth > 0; });
    assert.deepEqual(errors, []);
    await close();
  });

  test("detalle: medidas correctas tras la corrección de paralaje, visor 3D y corte por plano", async () => {
    const { page, errors, close } = await h.page();
    await go(page, `trabajos/${h.ids.done}`, ".viewer[data-ready]");
    const read = () => page.locator(".spec .v").allInnerTexts().then((t) => t.map((x) => parseFloat(x.replace(",", "."))));
    await page.waitForFunction(() => [...document.querySelectorAll(".spec .v")].map((e) => parseFloat(e.textContent.replace(",", ".")))
      .every((v, i) => Math.abs(v - [40, 20, 30][i]) < 1.5), null, { timeout: 8000 });   // las cifras «cuentan» hasta su valor
    assert.equal((await read()).length, 3);
    await page.waitForSelector("text=Perspectiva corregida");
    const cut = page.getByLabel("Corte para ver el interior"), panel = page.locator(".section-panel");
    assert.equal(await panel.isHidden(), true);
    await cut.click();
    assert.equal(await panel.isVisible(), true);
    for (const a of ["X", "Y", "Z"]) {
      await page.getByLabel(`Cortar en el eje ${a}`).click();
      assert.equal(await page.getByLabel(`Cortar en el eje ${a}`).getAttribute("aria-pressed"), "true");
    }
    await page.locator(".section-panel input[type=range]").fill("20");
    await page.getByLabel("Invertir el lado del corte").click();
    await cut.click();
    assert.equal(await panel.isHidden(), true);
    assert.deepEqual(errors, []);
    await close();
  });

  test("revisión: tres contornos y «Continuar» genera la pieza", async () => {
    const { page, errors, close } = await h.page();
    await go(page, `trabajos/${h.ids.continue}`, ".review img[src]");
    assert.equal(await page.locator(".review img").count(), 3);
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page.waitForSelector(".specs", { timeout: 30000 });
    assert.deepEqual(errors, []);
    await close();
  });

  test("error: dice qué foto falló y ofrece repetirla", async () => {
    const { page, close } = await h.page();
    await go(page, `trabajos/${h.ids.error}`, ".banner.err");
    assert.match(await page.locator(".banner.err").innerText(), /hoja/i);
    assert.equal(await page.getByRole("button", { name: /Repetir foto de planta/i }).count(), 1);
    await close();
  });

  test("una pieza clara sobre el papel avisa de que el contorno es poco fiable", async () => {
    const { page, errors, close } = await h.page();
    await go(page, `trabajos/${h.ids.clear}`, ".note[role=alert]");
    await page.locator(".note summary").first().click();
    const text = await page.locator(".note").first().innerText();
    assert.match(text, /calidad de una foto/);
    assert.match(text, /se distingue poco del papel/);
    assert.deepEqual(errors, []);
    await close();
  });

  test("una ranura y un agujero salen como parámetros medibles", async () => {
    const { page, errors, close } = await h.page();
    await go(page, `trabajos/${h.ids.holes}`, ".holes");
    const text = await page.locator(".holes").innerText();
    assert.match(text, /1 agujero · 1 ranura/i);
    assert.match(text, /Ranura \d+,\d × \d+,\d/);
    await page.getByRole("button", { name: "Ajustar medidas" }).click();
    for (const name of ["d_planta_1", "w_planta_1", "l_planta_1"]) assert.equal(await page.locator(`input[name=${name}]`).count(), 1, name);
    assert.deepEqual(errors, []);
    await close();
  });

  test("ajustes: estado del servidor y almacenamiento", async () => {
    const { page, errors, close } = await h.page();
    await go(page, "ajustes", ".group");
    await page.waitForSelector("text=Trabajos guardados");
    assert.match(await page.locator("body").innerText(), /OpenSCAD/);
    assert.equal(await page.getByRole("button", { name: /Borrar trabajos de más de 30 días/ }).isEnabled(), true);
    assert.deepEqual(errors, []);
    await close();
  });
});

describe("auditoría de interfaz (2 anchos × 2 temas)", () => {
  const routes = (ids) => [["capturar", "capturar", ".method"], ["trabajos", "trabajos", ".job"], ["detalle", `trabajos/${ids.done}`, ".viewer[data-ready]"],
    ["revision", `trabajos/${ids.review}`, ".review img[src]"], ["calidad", `trabajos/${ids.clear}`, ".note[role=alert]"], ["error", `trabajos/${ids.error}`, ".banner.err"], ["ajustes", "ajustes", ".group"]];

  for (const width of [360, 412]) for (const dark of [false, true]) {
    test(`${width} px ${dark ? "oscuro" : "claro"}: sin desbordes, sin objetivos < 44 px y sin botones sin nombre`, async () => {
      const { page, close } = await h.page({ width, dark });
      const problems = [];
      for (const [name, hash, sel] of routes(h.ids)) {
        await go(page, hash, sel);
        await page.waitForTimeout(600);
        const r = await audit(page);
        if (!clean(r)) problems.push({ name, ...r });
      }
      assert.deepEqual(problems, []);
      await close();
    });
  }
});


describe("bandeja de salida (sin red no se pierde nada)", () => {
  const jobsCount = async () => (await (await fetch(`${h.base}/api/jobs`)).json()).length;
  // Sube una captura mínima desde la propia página, con el módulo real de la app
  const submitFromPage = (page, { name, file = "v.mp4", bytes = 4000 }) => page.evaluate(async ({ name, file, bytes }) => {
    const { submit } = await import("/js/outbox.js");
    const blob = new Blob([new Uint8Array(bytes)], { type: file.endsWith("jpg") ? "image/jpeg" : "video/mp4" });
    try { return await submit({ fields: [["mode", "video"], ["name", name]], files: [["files", blob, file]], name }); }
    catch (e) { return { error: e.message, status: e.status, network: !!e.network }; }
  }, { name, file, bytes });

  test("sin red queda guardada, sobrevive a recargar, y se envía sola al volver la red", async () => {
    const { page, errors, close } = await h.page();
    await go(page, "trabajos", ".job");
    const before = await jobsCount();
    await page.route("**/api/jobs", (route) => (route.request().method() === "POST" ? route.abort() : route.continue()));
    const res = await submitFromPage(page, { name: "Captura sin red" });
    assert.equal(res.queued, true);
    await page.waitForSelector(".pending .job.queued");
    assert.match(await page.locator(".pending").innerText(), /Captura sin red/);
    assert.match(await page.locator(".pending").innerText(), /Esperando conexión/i);
    assert.equal(await page.locator('.tabbar a[data-tab="trabajos"]').getAttribute("data-pending"), "1");
    assert.ok(clean(await audit(page)), "la tarjeta pendiente cumple la auditoría táctil");

    await page.reload();                                            // cerrar y volver a abrir la app
    await page.waitForSelector(".pending .job.queued");
    assert.equal(await jobsCount(), before);

    await page.unroute("**/api/jobs");                              // vuelve la red
    await page.getByRole("button", { name: /Reintentar el envío/ }).click();
    await page.waitForFunction(() => !document.querySelector(".pending .job.queued"), null, { timeout: 15000 });
    assert.equal(await jobsCount(), before + 1);
    assert.equal(await page.locator('.tabbar a[data-tab="trabajos"]').getAttribute("data-pending"), null);
    assert.deepEqual(errors.filter((e) => !/ERR_FAILED|Failed to load resource/.test(e)), []);
    await close();
  });

  test("si el Mac recibió la subida pero se perdió la respuesta, el reintento no duplica el trabajo", async () => {
    const { page, close } = await h.page();
    await go(page, "trabajos", ".job");
    const before = await jobsCount();
    await page.route("**/api/jobs", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      await route.fetch();                                          // el servidor lo procesa…
      return route.abort();                                         // …pero el móvil no recibe la respuesta
    });
    assert.equal((await submitFromPage(page, { name: "Respuesta perdida" })).queued, true);
    assert.equal(await jobsCount(), before + 1, "el Mac sí creó el trabajo");
    await page.unroute("**/api/jobs");
    await page.getByRole("button", { name: /Reintentar el envío/ }).click();
    await page.waitForFunction(() => !document.querySelector(".pending .job.queued"), null, { timeout: 15000 });
    assert.equal(await jobsCount(), before + 1, "sin duplicado");
    await close();
  });

  test("un rechazo del Mac (límite de tamaño) no se encola: se avisa al momento", async () => {
    const { page, close } = await h.page();
    await go(page, "trabajos", ".job");
    const res = await submitFromPage(page, { name: "Demasiado grande", file: "grande.jpg", bytes: 3 * 1024 * 1024 });
    assert.equal(res.status, 413);
    assert.match(res.error, /límite/);
    assert.equal(await page.evaluate(async () => (await import("/js/outbox.js")).list().length), 0);
    await close();
  });
});
