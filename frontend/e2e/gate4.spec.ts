import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
const evidence = "../docs/evidence-gate4";
async function nav(page: Page, name: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}
async function demoTools(page: Page) {
  await page
    .locator(".session-tools")
    .evaluate((e: HTMLDetailsElement) => (e.open = true));
}
async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: `${evidence}/${name}.png`, fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
}
const cases = [360, 390, 768, 1440].flatMap((width) =>
  ["light", "dark"].map((theme) => ({ width, theme })),
);
for (const [index, { width, theme }] of cases.entries())
  test(`cafetal ${width} ${theme}`, async ({ page }) => {
    const missing: string[] = [];
    page.on("response", (r) => {
      if (r.url().includes("/api/") && r.status() === 404)
        missing.push(r.url());
    });
    if (index === 0)
      execFileSync(
        path.resolve("../.venv/Scripts/python.exe"),
        [path.resolve("../backend/manage.py"), "prepare_e2e", "--empty"],
        {
          env: { ...process.env, SEMI_DATABASE: "e2e.sqlite3" },
          stdio: "pipe",
        },
      );
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    if (index > 0) {
      await expect(
        page.getByText("Conectado · simulado", { exact: true }),
      ).toBeVisible();
      await demoTools(page);
      await page
        .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
        .click();
    }
    await page.getByLabel("Apariencia").selectOption(theme);
    await expect(
      page.getByRole("heading", { name: "Bienvenido a SEMI" }),
    ).toBeVisible();
    await screenshot(page, `${width}-${theme}-stage1`);
    await page.getByRole("button", { name: "Comenzar", exact: true }).click();
    await page
      .getByLabel("Nombre del cafetal", { exact: true })
      .fill("Mi cafetal");
    await screenshot(page, `${width}-${theme}-stage2`);
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page
      .getByLabel("Nombre del lugar (opcional)", { exact: true })
      .fill("Entrada");
    await page
      .getByRole("button", { name: "Guardar lugar", exact: true })
      .click();
    await expect(
      page.getByText("P1 guardado. Ya puedes tomar una medición."),
    ).toBeVisible();
    await page
      .getByLabel("Nombre del lugar (opcional)", { exact: true })
      .fill("Centro");
    await page
      .getByLabel("Marcar ubicación en el esquema (opcional)", { exact: true })
      .check();
    const plane = page.getByRole("button", {
      name: "Elegir ubicación del lugar",
      exact: true,
    });
    await plane.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("ArrowRight");
    await page
      .getByRole("button", { name: "Guardar lugar", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Modificar P2", exact: true }),
    ).toBeVisible();
    expect(await page.locator(".setup-shell").innerText()).not.toMatch(
      /arena|tipo de tierra|tipo descriptivo|UART|provider/i,
    );
    await screenshot(page, `${width}-${theme}-stage3`);
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page
      .getByRole("button", { name: "Guardar medición simulada", exact: true })
      .click();
    await expect(
      page.getByText("Resultado guardado en P1", { exact: true }),
    ).toBeVisible();
    await screenshot(page, `${width}-${theme}-stage4`);
    const original = await page.evaluate(() =>
      localStorage.getItem("semi-plot"),
    );
    await page
      .getByRole("button", { name: "Ver mis mediciones", exact: true })
      .click();
    await expect(page.locator(".sample-row")).toHaveCount(1);
    await expect(
      page.getByRole("img", { name: /Gráfica temporal/ }),
    ).toBeVisible();
    await screenshot(page, `${width}-${theme}-result`);
    await page
      .getByLabel("Lugar para consultar", { exact: true })
      .selectOption({ index: 1 });
    await expect(
      page.locator("section.card").filter({
        has: page.getByRole("heading", { name: "Resultados", exact: true }),
      }),
    ).toContainText("Todavía no tienes mediciones en este lugar");
    await page
      .getByLabel("Lugar para consultar", { exact: true })
      .selectOption({ index: 0 });
    await page.getByText("Administrar sectores", { exact: true }).click();
    await page
      .getByLabel("Nombre del sector", { exact: true })
      .fill("Zona alta");
    await page
      .getByRole("button", { name: "Agregar sector", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Renombrar Zona alta", exact: true }),
    ).toBeVisible();
    await page
      .getByText("Agregar o modificar lugares", { exact: true })
      .click();
    await page
      .getByRole("button", { name: "Modificar P1", exact: true })
      .click();
    await page
      .getByLabel("Sector (opcional)", { exact: true })
      .selectOption({ label: "Zona alta" });
    await page
      .getByRole("button", { name: "Guardar cambios del lugar", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Renombrar Zona alta", exact: true })
      .click();
    await page
      .getByLabel("Nombre del sector", { exact: true })
      .fill("Parte alta");
    await page
      .getByRole("button", { name: "Guardar nombre del sector", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Archivar Parte alta", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("combobox", {
        name: "Sector para consultar (opcional)",
        exact: true,
      })
      .selectOption({ label: "Parte alta" });
    await page
      .getByRole("button", { name: "Archivar Parte alta", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await screenshot(page, `${width}-${theme}-confirm`);
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByRole("combobox", {
        name: "Sector para consultar (opcional)",
        exact: true,
      }),
    ).toHaveValue("");
    await expect(page.locator(".sample-row")).toHaveCount(1);
    // Empty-sector deletion is explicit, cancellable and never cascades to readings.
    await page
      .getByLabel("Nombre del sector", { exact: true })
      .fill("Temporal");
    await page
      .getByRole("button", { name: "Agregar sector", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Eliminar Temporal", exact: true })
      .click();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("button", { name: "Eliminar Temporal", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Eliminar Temporal", exact: true })
      .click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Eliminar Temporal", exact: true }),
    ).toHaveCount(0);
    await page
      .getByRole("button", { name: "Modificar P1", exact: true })
      .click();
    await page
      .getByLabel("Sector (opcional)", { exact: true })
      .selectOption("");
    await page
      .getByRole("button", { name: "Guardar cambios del lugar", exact: true })
      .click();
    await expect(page.locator(".sample-row")).toHaveCount(1);
    await page.reload();
    await expect(page.locator(".sample-row")).toHaveCount(1);
    await screenshot(page, `${width}-${theme}-archived`);
    await demoTools(page);
    await page
      .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
      .click();
    await expect(
      page.getByRole("heading", { name: "Bienvenido a SEMI" }),
    ).toBeVisible();
    const old = await page.request.get("/api/setup/", {
      headers: { "X-SEMI-Plot": original! },
    });
    const saved = (await old.json()).data;
    expect(saved.points).toHaveLength(2);
    expect(saved.points[0].latest_sample).not.toBeNull();
    expect(missing).toEqual([]);
  });
for (const theme of ["light", "dark"])
  test(`surface trial ${theme} stops active command without physical action`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await demoTools(page);
    await page
      .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
      .click();
    await page.getByLabel("Apariencia").selectOption(theme);
    await page.getByRole("button", { name: "Comenzar", exact: true }).click();
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page.getByRole("button", { name: "Continuar", exact: true }).click();
    await page
      .getByRole("button", { name: "Ir al inicio", exact: true })
      .click();
    const plot = (await page.evaluate(() =>
      localStorage.getItem("semi-plot"),
    ))!;
    const health = (await (await page.request.get("/api/health/")).json()).data;
    const headers = { "X-SEMI-Plot": plot, "X-CSRFToken": health.csrf_token };
    const inject = async (state: string) => {
      const r = await page.request.post("/api/demo/surface/", {
        headers,
        data: { state, conservative: true },
      });
      expect(r.status()).toBe(200);
    };
    const status = async () =>
      (await (await page.request.get("/api/robot/status/", { headers })).json())
        .data;
    const sent: string[] = [];
    page.on("request", (r) => {
      if (r.url().endsWith("/api/control/command/") && r.postDataJSON()?.mode)
        sent.push(r.postDataJSON().mode);
    });
    await inject("soil");
    await nav(page, "Control");
    const forward = page.getByRole("button", { name: "Adelante", exact: true });
    await forward.hover();
    await page.mouse.down();
    await expect
      .poll(async () => (await status()).control.action)
      .toBe("forward");
    await inject("sand");
    await expect.poll(async () => (await status()).control.action).toBe("stop");
    await expect(forward).toHaveAttribute("aria-pressed", "false");
    await page.mouse.up();
    await inject("soil");
    expect((await status()).control.action).toBe("stop");
    await forward.hover();
    await page.mouse.down();
    await expect
      .poll(async () => (await status()).control.action)
      .toBe("forward");
    await inject("lost");
    await expect.poll(async () => (await status()).control.action).toBe("stop");
    await page.mouse.up();
    expect((await status()).hardware_connected).toBe(false);
    expect(sent.every((mode) => mode === "demonstration")).toBeTruthy();
    const c = (await status()).control;
    const physical = await page.request.post("/api/control/command/", {
      headers,
      data: {
        mode: "hardware",
        action: "forward",
        speed: "low",
        session_id: "11111111-1111-4111-8111-111111111111",
        seq: 10,
        epoch: c.epoch,
        window_id: c.window_id,
      },
    });
    expect(physical.status()).toBe(403);
    await page.getByRole("button", { name: "Salir del control" }).click();
    await demoTools(page);
    await page
      .getByRole("button", {
        name: "Arena detectada (simulación)",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("alert").filter({ hasText: "STOP simulado" }),
    ).toBeVisible();
    await screenshot(page, `trial-${theme}`);
  });
test("server errors do not become empty records and configuration resumes", async ({
  page,
}) => {
  await page.route("**/api/setup/", (r) =>
    r.fulfill({
      status: 503,
      json: { error: { detail: "internal test fault" } },
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "No pudimos cargar tus datos",
  );
  await expect(
    page.getByRole("heading", { name: "Bienvenido a SEMI" }),
  ).toHaveCount(0);
  await page.unroute("**/api/setup/");
  await page
    .getByRole("button", { name: "Intentar de nuevo", exact: true })
    .click();
  await demoTools(page);
  await page
    .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
    .click();
  await page.getByRole("button", { name: "Comenzar", exact: true }).click();
  await page.getByLabel("Nombre del cafetal").fill("Mi cafetal reanudado");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await page.getByRole("button", { name: "Salir por ahora" }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Lugares para medir" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Volver", exact: true }).click();
  await expect(page.getByLabel("Nombre del cafetal")).toHaveValue(
    "Mi cafetal reanudado",
  );
});
