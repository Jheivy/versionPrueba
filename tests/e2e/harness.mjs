// Arranca el servidor real con un almacenamiento temporal, crea trabajos de ejemplo y abre Chromium.
import { spawn, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PYTHON = process.env.PYTHON || "python3";

const freePort = () => new Promise((ok, fail) => {
  const s = createServer().listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => ok(port)); });
  s.on("error", fail);
});

export async function start() {
  const dir = mkdtempSync(join(tmpdir(), "s2p-e2e-"));
  const port = await freePort(), base = `http://127.0.0.1:${port}`;
  const env = { ...process.env, SCAN2PRINT_AUTH: "off", SCAN2PRINT_STORAGE: join(dir, "jobs"), SCAN2PRINT_OUT: join(dir, "out"),
    SCAN2PRINT_PORT: String(port), SCAN2PRINT_MAX_PHOTO_MB: "2", PYTHONPATH: `${join(ROOT, "server")}:${join(ROOT, "server/tests")}` };
  const server = spawn(PYTHON, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
    { cwd: join(ROOT, "server"), env, stdio: ["ignore", process.env.E2E_VERBOSE ? "inherit" : "ignore", "inherit"] });
  for (let i = 0; ; i++) {
    try { if ((await fetch(`${base}/api/health`)).ok) break; } catch { /* aún arrancando */ }
    if (i > 100) throw new Error("el servidor no arrancó");
    await new Promise((r) => setTimeout(r, 200));
  }
  const ids = JSON.parse(execFileSync(PYTHON, [join(ROOT, "tests/e2e/seed.py"), base], { env, encoding: "utf8" }).trim().split("\n").pop());
  const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  return {
    base, ids, browser,
    /** Página nueva con aspecto de móvil; `errors` recoge los fallos de la consola y de la página. */
    async page({ width = 412, height = 915, dark = false } = {}) {
      const ctx = await browser.newContext({ viewport: { width, height }, hasTouch: true, isMobile: true, colorScheme: dark ? "dark" : "light" });
      await ctx.addInitScript(() => localStorage.setItem("s2p.helpSeen", "true"));
      const page = await ctx.newPage(), errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      page.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 200)));
      return { page, errors, close: () => ctx.close() };
    },
    async stop() {
      await browser.close();
      server.kill("SIGTERM");
      rmSync(dir, { recursive: true, force: true });
    },
  };
}
