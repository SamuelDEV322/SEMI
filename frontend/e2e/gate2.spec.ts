import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
test("missing stale and error measurements remain explicit", async ({
  page,
}) => {
  await reset(page);
  await page
    .locator(".demo-tools")
    .evaluate((e: HTMLDetailsElement) => (e.open = true));
  await page.getByLabel("Escenario de demostración").selectOption("no_data");
  await expect(
    page.getByText("No disponible", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Escenario de demostración").selectOption("stale");
  await expect(
    page.getByText("Dato obsoleto · demo", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Escenario de demostración").selectOption("error");
  await expect(
    page.getByText("No se pudo obtener la última medición.", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Escenario de demostración").selectOption("connected");
});
test("LiDAR source cannot be changed from the browser", async ({ page }) => {
  await reset(page);
  await nav(page, "Estado");
  await page.getByText("Detalles del sistema", { exact: true }).click();
  await expect(page.getByLabel("Origen LiDAR")).toHaveCount(0);
  const token = (await (await page.request.get("/api/health/")).json()).data
    .csrf_token;
  const response = await page.request.post("/api/lidar/source/", {
    headers: { "X-CSRFToken": token },
    data: { source: "real" },
  });
  expect(response.status()).toBe(405);
  expect((await response.json()).error.code).toBe("source_fixed");
  await nav(page, "Control");
  await expect(
    page.getByText("LiDAR · Simulación", { exact: true }),
  ).toBeVisible();
});
test("theme contrast tokens and no corrupted text", async ({ page }) => {
  await reset(page);
  for (const theme of ["light", "dark"]) {
    await page.getByLabel("Apariencia").selectOption(theme);
    const ratio = await page.evaluate(() => {
      const s = getComputedStyle(document.documentElement);
      const lum = (v: string) => {
        let c = v.trim().replace("#", "");
        if (c.length === 3)
          c = c
            .split("")
            .map((v) => v + v)
            .join("");
        const rgb = [0, 2, 4]
          .map((i) => parseInt(c.slice(i, i + 2), 16) / 255)
          .map((v) =>
            v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4,
          );
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
      };
      const bg = lum(s.getPropertyValue("--surface")),
        tx = lum(s.getPropertyValue("--muted"));
      return (Math.max(bg, tx) + 0.05) / (Math.min(bg, tx) + 0.05);
    });
    expect(ratio).toBeGreaterThanOrEqual(4.5);
    await nav(page, "Datos");
    expect(await page.locator("body").innerText()).not.toMatch(/Ã|Â/);
    await nav(page, "Inicio");
  }
});
async function nav(page: Page, label: string) {
  if (await page.getByRole("button", { name: "Salir del control" }).isVisible())
    await page.getByRole("button", { name: "Salir del control" }).click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: label, exact: true })
    .click();
}
async function reset(page: Page) {
  await page.goto("/");
  await expect(
    page.getByText("Conectado · simulado", { exact: true }),
  ).toBeVisible();
  await page
    .locator(".demo-tools")
    .evaluate((e: HTMLDetailsElement) => (e.open = true));
  await page.getByLabel("Escenario de demostración").selectOption("connected");
  await page
    .locator(".demo-tools")
    .evaluate((e: HTMLDetailsElement) => (e.open = false));
}
for (const [w, h] of [
  [360, 640],
  [390, 844],
  [768, 900],
  [1440, 900],
  [740, 360],
])
  for (const theme of ["light", "dark"])
    test(`layout ${w}x${h} ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await reset(page);
      await page.getByLabel("Apariencia").selectOption(theme);
      for (const view of ["Inicio", "Datos", "Estado", "Control"]) {
        await nav(page, view);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBeTruthy();
        if (view === "Control") {
          for (const name of [
            "Adelante",
            "Atrás",
            "Izquierda",
            "Derecha",
            "DETENER ROBOT",
          ]) {
            const button = page.getByRole("button", { name, exact: true });
            await expect(button).toBeVisible();
            const box = await button.boundingBox();
            expect(box!.height).toBeGreaterThanOrEqual(44);
            expect(box!.y + box!.height).toBeLessThanOrEqual(h);
            expect(box!.y).toBeGreaterThanOrEqual(0);
          }
          await expect(
            page.getByRole("img", { name: /Escaneo polar/ }),
          ).toBeVisible();
          expect(
            await page.evaluate(
              () => document.documentElement.scrollHeight <= innerHeight,
            ),
          ).toBeTruthy();
        }
        await page.screenshot({
          path: `../docs/evidence-gate4-regression/${w}-${theme}-${view}.png`,
          fullPage: view !== "Control",
        });
      }
    });
test("theme persistence and system override", async ({ page }) => {
  await reset(page);
  await page.getByLabel("Apariencia").selectOption("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await page.getByLabel("Apariencia").selectOption("system");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Apariencia").selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
test("create located point capture and latest map", async ({ page }) => {
  await reset(page);
  await nav(page, "Datos");
  await page.getByText("Agregar o modificar lugares", { exact: true }).click();
  const name = `Zona E2E ${Date.now()}`;
  await page
    .getByLabel("Nombre del lugar (opcional)", { exact: true })
    .fill(name);
  await page
    .getByRole("button", { name: "Guardar lugar", exact: true })
    .click();
  await expect(page.getByLabel("Lugar para consultar")).toContainText(name);
  await page
    .getByRole("button", { name: "Guardar medición simulada", exact: true })
    .click();
  await expect(
    page.getByText("Medición simulada guardada en este lugar."),
  ).toBeVisible();
  await expect(page.locator(".sample-row").first()).toContainText("34");
  await page.reload();
  await expect(page.getByLabel("Lugar para consultar")).toContainText(name);
  await page.screenshot({
    path: "../docs/evidence-gate4-regression/npk-flow.png",
    fullPage: true,
  });
});
test("hold release keyboard blur hidden cancellation and offline", async ({
  page,
  context,
}) => {
  await reset(page);
  await nav(page, "Control");
  const forward = page.getByRole("button", { name: "Adelante", exact: true });
  const state = async () => {
    return (await (await page.request.get("/api/robot/status/")).json()).data
      .control.action;
  };
  await forward.hover();
  await page.mouse.down();
  await expect.poll(state).toBe("forward");
  await page.mouse.up();
  await expect.poll(state).toBe("stop");
  await forward.focus();
  await page.keyboard.down("Space");
  await expect.poll(state).toBe("forward");
  await page.keyboard.up("Space");
  await expect.poll(state).toBe("stop");
  for (const event of ["blur", "visibilitychange"]) {
    await forward.hover();
    await page.mouse.down();
    await expect.poll(state).toBe("forward");
    await page.evaluate((event) => {
      if (event === "visibilitychange") {
        Object.defineProperty(document, "hidden", {
          configurable: true,
          value: true,
        });
        document.dispatchEvent(new Event(event));
        Object.defineProperty(document, "hidden", {
          configurable: true,
          value: false,
        });
      } else window.dispatchEvent(new Event(event));
    }, event);
    await page.mouse.up();
    await expect.poll(state).toBe("stop");
  }
  await context.setOffline(true);
  await expect(forward).toBeDisabled();
  await context.setOffline(false);
  await expect(forward).toBeEnabled();
});
test("touch held then cancellation", async ({ browser }) => {
  const context = await browser.newContext({
    viewport: { width: 360, height: 640 },
    hasTouch: true,
    isMobile: true,
  });
  const page = await context.newPage();
  await reset(page);
  await nav(page, "Control");
  const box = await page
    .getByRole("button", { name: "Adelante", exact: true })
    .boundingBox();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: box!.x + 20, y: box!.y + 20 }],
  });
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/robot/status/")).json()).data
          .control.action,
    )
    .toBe("forward");
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchCancel",
    touchPoints: [],
  });
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/robot/status/")).json()).data
          .control.action,
    )
    .toBe("stop");
  await context.close();
});
test("history error stays out of control", async ({ page }) => {
  await page.route("**/api/measurements/history/**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: { detail: "history failure" } }),
    }),
  );
  await reset(page);
  await nav(page, "Control");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await nav(page, "Datos");
  await expect(
    page.getByText(
      "No pudimos cargar tus datos. Comprueba la conexión e inténtalo de nuevo",
    ),
  ).toBeVisible();
});
