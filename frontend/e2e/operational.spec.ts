import { test, expect, type Page } from "@playwright/test";
async function nav(page: Page, label: string) {
  const exit = page.getByRole("button", { name: "Salir del control" });
  if (await exit.isVisible()) await exit.click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: label, exact: true })
    .click();
}
async function cleanUI(page: Page) {
  await expect(page.getByLabel("Origen LiDAR")).toHaveCount(0);
  await expect(
    page.getByText("Demostración y ensayos", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Escenario de demostración")).toHaveCount(0);
  await expect(
    page.getByText("Diagnóstico técnico", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: /medición simulada|puntos de ejemplo|Repetir bienvenida/,
    }),
  ).toHaveCount(0);
}
test("first installation creates actual configuration without synthetic readings", async ({
  page,
}) => {
  const missing: string[] = [];
  page.on("response", (r) => {
    if (r.status() === 404) missing.push(r.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Bienvenido a SEMI" }),
  ).toBeVisible();
  await cleanUI(page);
  await page.getByRole("button", { name: "Comenzar", exact: true }).click();
  await page
    .getByLabel("Nombre del cafetal", { exact: true })
    .fill("Mi cafetal");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await page
    .getByLabel("Nombre del lugar (opcional)", { exact: true })
    .fill("Entrada");
  await page
    .getByRole("button", { name: "Guardar lugar", exact: true })
    .click();
  await expect(
    page.getByText("P1 guardado. Aquí podrás consultar sus mediciones."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Tomar medición", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText(
      "Sensor de suelo no conectado. No se ha tomado ninguna medición.",
    ),
  ).toBeVisible();
  await cleanUI(page);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Comprobar y comenzar" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ver mis mediciones", exact: true })
    .click();
  await expect(page.getByLabel("Lugar para consultar")).toContainText(
    "Entrada",
  );
  await expect(
    page.getByRole("button", { name: "Tomar medición", exact: true }),
  ).toBeDisabled();
  const samples = (await (await page.request.get("/api/npk/samples/")).json())
    .data;
  expect(samples).toEqual([]);
  expect(missing).toEqual([]);
});
for (const width of [360, 390, 768, 1440])
  for (const theme of ["light", "dark"])
    test(`MVP ${width} ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width, height: width < 700 ? 640 : 900 });
      await page.goto("/");
      await page.getByLabel("Apariencia").selectOption(theme);
      await expect(
        page.getByText("Vehículo no conectado", { exact: true }),
      ).toBeVisible();
      const commands: string[] = [];
      page.on("request", (r) => {
        if (r.url().includes("/control/command/"))
          commands.push(r.postData() || "");
      });
      for (const screen of ["Inicio", "Datos", "Estado", "Control"]) {
        await nav(page, screen);
        await cleanUI(page);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBeTruthy();
        if (screen === "Control") {
          await expect(page.locator(".drive-status")).toContainText(
            "Estado del vehículo sin confirmar",
          );
          await expect(
            page.getByText("SENSOR USB · REAL", { exact: true }),
          ).toBeVisible();
          for (const name of [
            "Adelante",
            "Atrás",
            "Izquierda",
            "Derecha",
            "DETENER ROBOT",
          ]) {
            const b = page.getByRole("button", { name, exact: true });
            await expect(b).toBeDisabled();
            const rect = await b.boundingBox();
            expect(rect!.height).toBeGreaterThanOrEqual(44);
            expect(rect!.y).toBeGreaterThanOrEqual(0);
            expect(rect!.y + rect!.height).toBeLessThanOrEqual(
              width < 700 ? 640 : 900,
            );
          }
          const radar = await page.locator(".radar-panel").boundingBox();
          expect(radar!.height).toBeGreaterThan(80);
          expect(
            await page.evaluate(
              () => document.documentElement.scrollHeight <= innerHeight,
            ),
          ).toBeTruthy();
        }
        if (width === 390)
          await page.screenshot({
            path: `../docs/evidence/operational/${theme}-${screen}.png`,
            fullPage: screen !== "Control",
          });
      }
      await nav(page, "Inicio");
      expect(commands).toEqual([]);
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      expect(await page.locator("body").innerText()).not.toMatch(/Ã|Â/);
    });
test("source and demo requests cannot enable physical control", async ({
  page,
}) => {
  await page.goto("/");
  const profile = (await (await page.request.get("/api/health/")).json()).data;
  expect(profile.mode).toBe("operational");
  expect(profile.physical_control).toBe(false);
  const token = profile.csrf_token;
  for (const [path, data, status] of [
    ["lidar/source/", { source: "mock" }, 405],
    ["demo/scenario/", { scenario: "connected" }, 403],
    ["measurements/capture/", { sampling_point: 1 }, 503],
    ["setup/", { action: "demo" }, 403],
    [
      "control/command/",
      {
        mode: "operational",
        action: "forward",
        speed: "low",
        session_id: "d4dc3fb6-7b9c-4f57-b3b9-c176a551e095",
        seq: 1,
        epoch: 0,
        window_id: "",
      },
      503,
    ],
  ] as const) {
    const response = await page.request.post(`/api/${path}`, {
      headers: { "X-CSRFToken": token },
      data,
    });
    expect(response.status()).toBe(status);
  }
  const robot = (await (await page.request.get("/api/robot/status/")).json())
    .data;
  expect(robot.control.action).toBeNull();
  expect(robot.hardware_connected).toBe(false);
  expect(robot.telemetry.battery.value).toBeNull();
});
test("USB scan contract becomes stale in the browser without new frames", async ({
  page,
}) => {
  // Contract fixture only. No device opened and no physical measurement claimed.
  await page.route("**/api/lidar/latest/", (r) =>
    r.fulfill({
      json: {
        schema_version: "1.0",
        mode: "operational",
        data: {
          sensor_id: "test-only-a1",
          source: "real",
          captured_at: new Date().toISOString(),
          status: "valid",
          age_ms: 0,
          error: null,
          unit: "mm",
          valid: true,
          freshness: "fresh",
          max_range_mm: 4000,
          angle_convention: "mounting_unverified",
          points: [{ angle_deg: 90, distance: 1000, quality: 20, valid: true }],
        },
      },
    }),
  );
  await page.goto("/#control");
  await expect(page.getByRole("img", { name: /Escaneo polar/ })).toBeVisible();
  await page.route("**/api/lidar/latest/", () => new Promise(() => {}));
  await expect(
    page.getByText("Último escaneo desactualizado", { exact: true }),
  ).toBeVisible({ timeout: 3500 });
  await expect(page.getByRole("img", { name: /Escaneo polar/ })).toHaveCount(0);
});
