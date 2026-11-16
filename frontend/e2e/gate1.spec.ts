import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
async function reset(page: Page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "SEMI", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Conectado · simulado", { exact: true }),
  ).toBeVisible();
  await page.locator("details").evaluate((el: HTMLDetailsElement) => {
    el.open = true;
  });
  await page.getByLabel("Escenario de demostración").selectOption("connected");
}
for (const width of [390, 768, 1440]) {
  test(`four screens responsive ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await reset(page);
    for (const [name, title] of [
      ["Inicio", "SEMI"],
      ["Control", "Control de SEMI"],
      ["Datos", "Mediciones del cultivo"],
      ["Estado", "Estado y mantenimiento"],
    ]) {
      await page
        .getByRole("navigation")
        .getByRole("button", { name, exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: title, exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("MODO DEMOSTRACIÓN", { exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      await page.locator("details").evaluate((el: HTMLDetailsElement) => {
        el.open = false;
      });
      await page.screenshot({
        path: `../docs/evidence/${width}-${name}.png`,
        fullPage: true,
      });
    }
  });
}
test("capture persists through reload; schematic and lidar are explicit", async ({
  page,
}) => {
  await reset(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Datos", exact: true })
    .click();
  const label = `Ensayo E2E ${Date.now()}`;
  await page.getByLabel("Punto de muestreo", { exact: true }).fill(label);
  await page.getByRole("button", { name: "Guardar muestra demo" }).click();
  await expect(
    page.getByText("Muestra de demostración guardada en SQLite."),
  ).toBeVisible();
  await expect(page.getByText(label, { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText(label, { exact: true })).toBeVisible();
  await expect(
    page.getByText("PARCELA DEMOSTRATIVA · Sin georreferenciación"),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: /Escaneo polar LiDAR/ }),
  ).toBeVisible();
});
test("hold, release, blur and keyboard", async ({ page }) => {
  await reset(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  const forward = page.getByRole("button", { name: "Adelante", exact: true });
  await forward.hover();
  await page.mouse.down();
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/robot/status/");
      return (await r.json()).data.control.action;
    })
    .toBe("forward");
  await page.mouse.up();
  await expect(
    page.getByText("Parada confirmada por el simulador. Sin actuación física."),
  ).toBeVisible();
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/robot/status/");
      return (await r.json()).data.control.action;
    })
    .toBe("stop");
  await forward.focus();
  await page.keyboard.down("Space");
  await expect(forward).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.up("Space");
  await expect(
    page.getByText("Parada confirmada por el simulador. Sin actuación física."),
  ).toBeVisible();
  await forward.hover();
  await page.mouse.down();
  await expect(forward).toHaveAttribute("aria-pressed", "true");
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await page.mouse.up();
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/robot/status/");
      return (await r.json()).data.control.action;
    })
    .toBe("stop");
});
test("no data, stale, disconnect and acquisition error states", async ({
  page,
}) => {
  await reset(page);
  const scenario = page.getByLabel("Escenario de demostración");
  await scenario.selectOption("no_data");
  await expect(
    page.getByText("No disponible", { exact: true }).first(),
  ).toBeVisible();
  await scenario.selectOption("stale");
  await expect(
    page.getByText("Dato obsoleto · demo", { exact: false }).first(),
  ).toBeVisible();
  await scenario.selectOption("disconnected");
  await expect(
    page.getByText("Desconectado · simulado", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Adelante", exact: true }),
  ).toBeDisabled();
  await scenario.selectOption("error");
  await expect(page.getByRole("alert").first()).toContainText(
    "Error de adquisición simulado",
  );
  await scenario.selectOption("connected");
});
test("touch release requests stop and console has no errors", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true,
  });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await reset(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  const forward = page.getByRole("button", { name: "Adelante", exact: true });
  await forward.evaluate((element) =>
    element.scrollIntoView({ block: "center" }),
  );
  const box = await forward.boundingBox();
  if (!box) throw new Error("Touch target missing");
  const touch = await context.newCDPSession(page);
  await touch.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: box.x + box.width / 2, y: box.y + box.height / 2 }],
  });
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/robot/status/");
      return (await r.json()).data.control.action;
    })
    .toBe("forward");
  await touch.send("Input.dispatchTouchEvent", {
    type: "touchCancel",
    touchPoints: [],
  });
  await expect
    .poll(async () => {
      const r = await page.request.get("/api/robot/status/");
      return (await r.json()).data.control.action;
    })
    .toBe("stop");
  expect(errors).toEqual([]);
  await context.close();
});
test("loading and actual API outage recover without physical activation", async ({
  page,
  context,
}) => {
  await page.route("**/api/robot/status/", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.continue();
  });
  await page.goto("/");
  await expect(page.getByText("Cargando API local…")).toBeVisible();
  await expect(
    page.getByText("Conectado · simulado", { exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/robot/status/");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  await context.setOffline(true);
  await expect(
    page.getByText("Sin conexión con API", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Adelante", exact: true }),
  ).toBeDisabled();
  await context.setOffline(false);
  await expect(
    page.getByText("Conectado · simulado", { exact: true }),
  ).toBeVisible();
  const status = await (await page.request.get("/api/robot/status/")).json();
  expect(status.data.capabilities.physical_motion).toBe(false);
});
