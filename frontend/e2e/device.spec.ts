import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { randomUUID } from "node:crypto";
const headers = () => ({
  "X-SEMI-Device-ID": "e2e-device",
  "X-SEMI-Device-Token": process.env.SEMI_TEST_DEVICE_TOKEN!,
});
function command(...args: string[]) {
  return execFileSync(
    path.resolve("../.venv/Scripts/python.exe"),
    [path.resolve("../backend/manage.py"), ...args],
    {
      env: {
        ...process.env,
        SEMI_MODE: "operational",
        SEMI_DEVICE_INTEGRATION: "diagnostic",
        SEMI_DATABASE: "e2e.sqlite3",
      },
      encoding: "utf8",
    },
  );
}
async function fixture(
  page: Page,
  options: { old?: boolean; error?: boolean; empty?: boolean } = {},
) {
  const health = (await (await page.request.get("/api/health/")).json()).data;
  const csrf = { "X-CSRFToken": health.csrf_token };
  const plot = (
    await (
      await page.request.post("/api/setup/", {
        headers: csrf,
        data: { action: "start" },
      })
    ).json()
  ).data;
  await page.request.post("/api/setup/", {
    headers: csrf,
    data: { action: "complete" },
  });
  const registration = command(
    "register_device",
    "--device-id",
    "e2e-device",
    "--plot",
    String(plot.id),
    "--reset-session",
  );
  const session = registration.match(/session_id=([0-9a-f-]+)/)![1];
  const base = {
    schema_version: "1.0",
    session_id: session,
    message_id: randomUUID(),
    seq: 0,
  };
  const status = await page.request.post("/api/device/status/", {
    headers: headers(),
    data: {
      ...base,
      firmware: "test-fixture-only",
      capabilities: { telemetry: true, motion: true },
      firmware_state: "ready",
    },
  });
  expect(status.status()).toBe(201);
  if (!options.empty) {
    const telemetry = await page.request.post("/api/device/telemetry/", {
      headers: headers(),
      data: {
        ...base,
        message_id: randomUUID(),
        measured_at: new Date(
          Date.now() - (options.old ? 300000 : 0),
        ).toISOString(),
        sensors: {
          soil_moisture_adc: {
            value: options.error ? null : 1700,
            adc_max: 4095,
            status: options.error ? "error" : "valid",
          },
        },
      },
    });
    expect(telemetry.status()).toBe(201);
  }
  return session;
}
async function nav(page: Page, name: string) {
  const exit = page.getByRole("button", { name: "Salir del control" });
  if (await exit.isVisible()) await exit.click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}
for (const width of [360, 390, 768, 1440])
  for (const theme of ["light", "dark"])
    test(`diagnostic ${width} ${theme}`, async ({ page }) => {
      const missing: string[] = [];
      const commands: string[] = [];
      page.on("response", (r) => {
        if (r.status() === 404) missing.push(r.url());
      });
      await fixture(page);
      await page.setViewportSize({ width, height: width < 700 ? 640 : 900 });
      await page.goto("/");
      await page.getByLabel("Apariencia").selectOption(theme);
      await expect(
        page.getByText("Robot conectado", { exact: true }).first(),
      ).toBeVisible();
      for (const screen of ["Inicio", "Datos", "Estado", "Control"]) {
        await nav(page, screen);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBeTruthy();
        if (screen === "Estado") {
          await expect(
            page.getByText("Lectura sin calibrar", { exact: true }),
          ).toBeVisible();
          await expect(
            page.getByText(
              "Esta lectura todavía no representa un porcentaje de humedad.",
            ),
          ).toBeVisible();
          await expect(
            page
              .locator(".reading")
              .filter({ hasText: "Lectura del sensor de suelo" }),
          ).toContainText(/1[.,]?700/);
          if (width === 390)
            await page.screenshot({
              path: `../docs/evidence-gate5/${theme}-diagnostic.png`,
              fullPage: true,
            });
        }
        if (screen === "Control") {
          expect(await page.locator("body").innerText()).not.toContain(
            "El vehículo no está conectado",
          );
          page.on("request", (r) => {
            if (r.url().includes("/api/control/command/"))
              commands.push(r.url());
          });
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
          expect(
            await page.evaluate(
              () => document.documentElement.scrollHeight <= innerHeight,
            ),
          ).toBeTruthy();
        }
      }
      const health = (await (await page.request.get("/api/health/")).json())
        .data;
      expect(health.physical_control).toBe(false);
      expect(
        (await (await page.request.get("/api/npk/samples/")).json()).data,
      ).toEqual([]);
      expect(commands).toEqual([]);
      expect(missing).toEqual([]);
    });
test("empty stale error and lost device do not create calibrated measurements", async ({
  page,
}) => {
  await fixture(page, { empty: true });
  await page.goto("/#status");
  await expect(
    page.getByText("Esperando datos del sensor.", { exact: true }),
  ).toBeVisible();
  await fixture(page, { old: true });
  await page.reload();
  await expect(
    page.getByText("Última lectura desactualizada.", { exact: true }),
  ).toBeVisible();
  await fixture(page, { error: true });
  await page.reload();
  await expect(
    page.getByText("No se pudo obtener una lectura válida del suelo."),
  ).toBeVisible();
  // Backdate receipt only in e2e.sqlite3: deterministic clock-loss fixture.
  command(
    "shell",
    "-c",
    "from django.conf import settings; from pathlib import Path; assert Path(settings.DATABASES['default']['NAME']).name == 'e2e.sqlite3'; from apps.devices.models import Device; from django.utils import timezone; Device.objects.update(last_seen=timezone.now()-timezone.timedelta(seconds=20))",
  );
  await page.reload();
  await expect(
    page.getByText("Robot desconectado", { exact: true }).first(),
  ).toBeVisible();
  expect(
    (await (await page.request.get("/api/npk/samples/")).json()).data,
  ).toEqual([]);
});

test("a separate Django process reads the same durable receipt and counters", async ({
  page,
}) => {
  await fixture(page);
  const rows = (
    await (
      await page.request.get("/api/device/telemetry/?schema_version=1.0", {
        headers: headers(),
      })
    ).json()
  ).data;
  const latest = rows[0];
  const output = command(
    "shell",
    "-c",
    `from django.conf import settings; from pathlib import Path; assert Path(settings.DATABASES['default']['NAME']).name == 'e2e.sqlite3'; from apps.devices.models import Device, DeviceMessage; d=Device.objects.get(device_id='e2e-device'); assert DeviceMessage.objects.filter(device=d,message_id='${latest.message_id}').exists(); assert d.telemetry_seq == 0; print('durable receipt verified')`,
  );
  expect(output).toContain("durable receipt verified");
  const retry = await page.request.post("/api/device/telemetry/", {
    headers: headers(),
    data: latest.payload,
  });
  expect(retry.status()).toBe(200);
  expect((await retry.json()).data.duplicate).toBe(true);
});

test("raw soil data does not masquerade as an agricultural sample", async ({
  page,
}) => {
  await fixture(page);
  const token = (await (await page.request.get("/api/health/")).json()).data
    .csrf_token;
  const response = await page.request.post("/api/setup/", {
    headers: { "X-CSRFToken": token },
    data: { action: "point", name: "Lugar de diagnóstico" },
  });
  expect(response.status()).toBe(200);
  await page.goto("/#data");
  await expect(
    page.getByText(
      "No tenemos sensor NPK. Consulta el historial del sensor de humedad en esta pantalla.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Tomar medición", exact: true }),
  ).toBeDisabled();
  expect(
    (await (await page.request.get("/api/npk/samples/")).json()).data,
  ).toEqual([]);
});

test("lectura ADC asociada manualmente y ejemplos N/K estables por sesión", async ({
  page,
}) => {
  await fixture(page);
  const csrf = (await (await page.request.get("/api/health/")).json()).data
    .csrf_token;
  const response = await page.request.post("/api/setup/", {
    headers: { "X-CSRFToken": csrf },
    data: { action: "point", name: "Sombra del cafeto" },
  });
  expect(response.ok()).toBeTruthy();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?semilla=64#home");
  const cards = page.locator(".reading-grid .reading");
  await expect(cards.nth(0)).toContainText("ADC");
  await expect(cards.nth(1)).toContainText("Simulado");
  await expect(cards.nth(2)).toContainText("Simulado");
  const numbers = await cards.locator("strong").allTextContents();
  await page.reload();
  await expect(cards.locator("strong")).toHaveText(numbers);
  async function capture(name: string) {
    const marker = await page.evaluateHandle(() => {
      const el = document.createElement("div");
      el.textContent = "PRUEBA DE INTERFAZ · SIN HARDWARE";
      Object.assign(el.style, {
        position: "fixed",
        right: "4px",
        top: "2px",
        zIndex: "1000",
        background: "#203528",
        color: "white",
        font: "bold 9px sans-serif",
        padding: "4px 7px",
        pointerEvents: "none",
      });
      document.body.append(el);
      return el;
    });
    await page.screenshot({
      path: "../docs/evidence-gate6_4/" + name + ".png",
      fullPage: true,
    });
    await marker.evaluate((el) => el.remove());
  }
  await capture("inicio");
  await nav(page, "Estado");
  await expect(
    page.getByText("Sensor de humedad", { exact: true }).first(),
  ).toBeVisible();
  await capture("estado");
  await nav(page, "Control");
  await expect(page.getByRole("button", { name: "Adelante" })).toBeDisabled();
  await capture("control");
  await nav(page, "Datos");
  const select = page.getByLabel("Lugar para consultar");
  const option = select
    .getByRole("option")
    .filter({ hasText: "Sombra del cafeto" })
    .first();
  await select.selectOption((await option.getAttribute("value")) || "");
  await page
    .getByRole("button", { name: /Asociar a .*Sombra del cafeto/ })
    .first()
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Lectura asociada" }),
  ).toBeVisible();
  const history = page
    .locator(".card")
    .filter({
      has: page.getByRole("heading", {
        name: "Historial del sensor de humedad",
      }),
    });
  await expect(history).toContainText("Sombra del cafeto");
  await capture("datos");
  expect(
    (await (await page.request.get("/api/npk/samples/")).json()).data,
  ).toEqual([]);
});
