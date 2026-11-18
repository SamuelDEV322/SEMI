import { test, expect, type Page } from "@playwright/test";
async function prepare(page: Page) {
  const health = (await (await page.request.get("/api/health/")).json()).data;
  const headers = { "X-CSRFToken": health.csrf_token };
  await page.request.post("/api/setup/", {
    headers,
    data: { action: "start" },
  });
  await page.request.post("/api/setup/", {
    headers,
    data: { action: "complete" },
  });
}
const states: Record<string, string> = {
  not_detected: "Sensor de distancias no detectado por USB",
  usb_detected: "Adaptador USB detectado. Falta iniciar el lector",
  waiting: "Sensor conectado, esperando datos",
  active: "Escaneo funcionando",
  interrupted: "Escaneo interrumpido",
  stale: "No recibimos datos recientes del sensor",
  error: "Error de lectura del sensor",
  usb_unidentified: "Hay un adaptador USB por identificar",
};
function scan(state: string) {
  const active = state === "active";
  return {
    schema_version: "1.0",
    mode: "operational",
    server_time: new Date().toISOString(),
    data: {
      sensor_id: "fixture-only",
      source: "real",
      status: active
        ? "valid"
        : state === "waiting"
          ? "no_data"
          : state === "error"
            ? "error"
            : state === "stale"
              ? "stale"
              : "disconnected",
      valid: active,
      unit: "mm",
      captured_at: active ? new Date().toISOString() : null,
      freshness: state === "stale" ? "stale" : "fresh",
      age_ms: state === "stale" ? 3000 : 0,
      max_range_mm: 4000,
      points: active
        ? [{ angle_deg: 90, distance: 1000, quality: 20, valid: true }]
        : [],
      acquisition: {
        state,
        selected_port: null,
        usb_detected: state === "not_detected" ? false : null,
        sensor_identified: state === "active" || state === "waiting",
        reader_running: active || state === "waiting",
        reader_age_ms: 0,
        inventory_status: "ok",
        ports: [],
        reader_start_authorized: false,
      },
    },
  };
}
for (const width of [360, 390, 768, 1440])
  for (const theme of ["light", "dark"])
    test(`source states ${width} ${theme}`, async ({ page }) => {
      await prepare(page);
      await page.setViewportSize({ width, height: width < 700 ? 640 : 900 });
      let selected = "not_detected";
      await page.route("**/api/lidar/latest/", (route) =>
        route.fulfill({ json: scan(selected) }),
      );
      await page.goto("/#status");
      await page.getByLabel("Apariencia").selectOption(theme);
      for (const [state, message] of Object.entries(states)) {
        selected = state;
        await page.reload();
        await expect(
          page.getByText(message, { exact: true }).first(),
        ).toBeVisible();
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBeTruthy();
        expect(await page.locator("body").innerText()).not.toMatch(
          /cámara|batería|carga estimada|medición eléctrica/i,
        );
      }
      await page
        .getByRole("navigation")
        .getByRole("button", { name: "Inicio", exact: true })
        .click();
      expect(await page.locator("body").innerText()).not.toMatch(
        /cámara|batería/i,
      );
      await page
        .getByRole("navigation")
        .getByRole("button", { name: "Control", exact: true })
        .click();
      for (const name of [
        "Adelante",
        "Atrás",
        "Izquierda",
        "Derecha",
        "DETENER ROBOT",
      ])
        await expect(
          page.getByRole("button", { name, exact: true }),
        ).toBeDisabled();
      if (width === 390)
        await page.screenshot({
          path: `../docs/evidence-gate6_1/${theme}-no-scan.png`,
          fullPage: false,
        });
    });
test("device reasons and communication failure stay distinct", async ({
  page,
}) => {
  await prepare(page);
  const original = await (await page.request.get("/api/robot/status/")).json();
  let reason = "device_unregistered";
  await page.route("**/api/robot/status/", (route) =>
    route.fulfill({
      json: {
        ...original,
        data: {
          ...original.data,
          diagnostics: { ...original.data.diagnostics, reason },
        },
      },
    }),
  );
  await page.goto("/");
  for (const [state, message] of Object.entries({
    device_unregistered: "Vehículo sin registrar",
    registered_waiting: "Vehículo registrado, esperando comunicación",
    session_waiting: "Esperando comunicación de la sesión actual",
    credential_missing: "Falta completar la conexión del vehículo",
    disconnected: "Robot desconectado",
  })) {
    reason = state;
    await page.reload();
    await expect(
      page.getByText(message, { exact: true }).first(),
    ).toBeVisible();
  }
  await page.unroute("**/api/robot/status/");
  await page.route("**/api/robot/status/", (route) =>
    route.fulfill({ status: 503, json: { error: { detail: "test-only" } } }),
  );
  await page.reload();
  await expect(
    page.getByText("Sin conexión con el sistema", { exact: true }).first(),
  ).toBeVisible();
});
test("USB status error is not an empty successful reading", async ({
  page,
}) => {
  await prepare(page);
  await page.route("**/api/lidar/latest/", (route) =>
    route.fulfill({ status: 503, json: { error: { detail: "fixture-only" } } }),
  );
  await page.goto("/#status");
  await expect(
    page
      .getByText("No pudimos consultar el sensor de distancias", {
        exact: true,
      })
      .first(),
  ).toBeVisible();
});
