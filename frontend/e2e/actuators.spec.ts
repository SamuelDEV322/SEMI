import { test, expect, type Page } from "@playwright/test";

async function state(page: Page) {
  return (await (await page.request.get("/api/robot/status/")).json()).data;
}
async function scenario(page: Page, domain: string, value: string) {
  const token = (await (await page.request.get("/api/health/")).json()).data
    .csrf_token;
  const response = await page.request.post("/api/demo/scenario/", {
    headers: { "X-CSRFToken": token },
    data: { domain, scenario: value },
  });
  expect(response.ok()).toBeTruthy();
}
async function control(page: Page) {
  await page.goto("/");
  await scenario(page, "all", "connected");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Control", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Subir", exact: true }),
  ).toBeEnabled();
}
async function hold(page: Page, name: string) {
  const box = await page
    .getByRole("button", { name, exact: true })
    .boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
}

for (const [width, height] of [
  [360, 640],
  [390, 844],
  [768, 900],
  [1440, 900],
  [740, 360],
]) {
  for (const theme of ["light", "dark"]) {
    test(`three domains visible ${width}x${height} ${theme}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height });
      await control(page);
      if (width > height && height < 500) {
        await page.evaluate((value) => {
          localStorage.setItem("semi-theme", value);
        }, theme);
        // Select the same preference before entering compact landscape.
        await page.setViewportSize({ width: 390, height: 844 });
        await page
          .locator(".drive-top")
          .getByLabel("Apariencia")
          .selectOption(theme);
        await page.setViewportSize({ width, height });
      } else
        await page
          .locator(".drive-top")
          .getByLabel("Apariencia")
          .selectOption(theme);
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      for (const name of [
        "Adelante",
        "Atrás",
        "Izquierda",
        "Derecha",
        "Subir",
        "Bajar",
        "DETENER ROBOT",
      ]) {
        const button = page.getByRole("button", { name, exact: true });
        const box = await button.boundingBox();
        expect(box!.height).toBeGreaterThanOrEqual(44);
        expect(box!.width).toBeGreaterThanOrEqual(44);
        expect(box!.y).toBeGreaterThanOrEqual(0);
        expect(box!.y + box!.height).toBeLessThanOrEqual(height);
      }
      const radar = page.getByRole("img", { name: /Escaneo polar/ });
      await expect(radar).toBeVisible();
      expect((await radar.boundingBox())!.height).toBeGreaterThan(35);
      await expect(
        page.getByText("LiDAR · Simulación", { exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <= innerWidth &&
            document.documentElement.scrollHeight <= innerHeight,
        ),
      ).toBeTruthy();
      await page.screenshot({
        path: `../docs/evidence-gate6_2/control-${width}-${theme}.png`,
      });
    });
  }
}

test("LiDAR outage does not disable traction or rack; rack fault stays isolated", async ({
  page,
}) => {
  await control(page);
  await scenario(page, "lidar", "disconnected");
  await expect(page.getByRole("img", { name: /Escaneo polar/ })).toHaveCount(0);
  await hold(page, "Adelante");
  await expect
    .poll(async () => (await state(page)).control.action)
    .toBe("forward");
  await page.mouse.up();
  await hold(page, "Subir");
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("up");
  await page.mouse.up();
  await scenario(page, "rack", "error");
  await expect(
    page.getByRole("button", { name: "Subir", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Adelante", exact: true }),
  ).toBeEnabled();
  await scenario(page, "rack", "connected");
  await scenario(page, "traction", "disconnected");
  await expect(
    page.getByRole("button", { name: "Adelante", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Subir", exact: true }),
  ).toBeEnabled();
});

for (const reason of [
  "release",
  "blur",
  "pointercancel",
  "hidden",
  "offline",
  "exit",
]) {
  test(`rack cancels on ${reason}`, async ({ page }) => {
    await control(page);
    await hold(page, "Subir");
    await expect
      .poll(async () => (await state(page)).rack.control.action)
      .toBe("up");
    if (reason === "release") await page.mouse.up();
    if (reason === "blur")
      await page.evaluate(() => window.dispatchEvent(new Event("blur")));
    if (reason === "offline")
      await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    if (reason === "pointercancel")
      await page
        .getByRole("button", { name: "Subir", exact: true })
        .evaluate((el) =>
          el.dispatchEvent(
            new PointerEvent("pointercancel", { bubbles: true, pointerId: 1 }),
          ),
        );
    if (reason === "hidden")
      await page.evaluate(() => {
        Object.defineProperty(document, "hidden", {
          value: true,
          configurable: true,
        });
        document.dispatchEvent(new Event("visibilitychange"));
      });
    if (reason === "exit") {
      await page.mouse.up();
      await page.getByRole("button", { name: "Salir del control" }).click();
    }
    await expect
      .poll(async () => (await state(page)).rack.control.action)
      .toBe("stop");
    await page.mouse.up();
  });
}

test("rack keyboard holds, ignores opposite keys and stops on key up", async ({
  page,
}) => {
  await control(page);
  await page.getByRole("button", { name: "Bajar", exact: true }).focus();
  await page.keyboard.down("Enter");
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("down");
  await page
    .getByRole("button", { name: "Subir", exact: true })
    .dispatchEvent("keydown", { key: "Enter" });
  expect((await state(page)).rack.control.action).toBe("down");
  await page.keyboard.up("Enter");
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("stop");
});

test("lost backend cancels rack intent and reconnect does not resume it", async ({
  page,
  context,
}) => {
  await control(page);
  await hold(page, "Subir");
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("up");
  await context.setOffline(true);
  await expect(
    page.getByRole("button", { name: "Subir", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  // The API request client is outside Chromium's offline network emulation.
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("stop");
  await context.setOffline(false);
  await page.mouse.up();
  await expect(
    page.getByRole("button", { name: "Subir", exact: true }),
  ).toBeEnabled();
  expect((await state(page)).rack.control.action).toBe("stop");
});

test("native touch cancellation stops rack without a physical command", async ({
  browser,
}) => {
  const context = await browser.newContext({
    hasTouch: true,
    viewport: { width: 360, height: 640 },
  });
  const page = await context.newPage();
  await control(page);
  const box = (await page
    .getByRole("button", { name: "Bajar", exact: true })
    .boundingBox())!;
  const cdp = await context.newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: box.x + 20, y: box.y + 20 }],
  });
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("down");
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchCancel",
    touchPoints: [],
  });
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("stop");
  expect((await state(page)).rack.physical_authorized).toBe(false);
  await context.close();
});

test("touch domains use independent pointer capture; general stop invalidates both", async ({
  browser,
}) => {
  const context = await browser.newContext({
    hasTouch: true,
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  await control(page);
  const point = async (name: string, id: number) => {
    const box = (await page
      .getByRole("button", { name, exact: true })
      .boundingBox())!;
    return { x: box.x + box.width / 2, y: box.y + box.height / 2, id };
  };
  const traction = await point("Adelante", 11),
    rack = await point("Subir", 12);
  const cdp = await context.newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [traction],
  });
  await expect
    .poll(async () => (await state(page)).control.action)
    .toBe("forward");
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [traction, rack],
  });
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("up");
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [rack],
  });
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("stop");
  expect((await state(page)).control.action).toBe("forward");
  const stop = await point("DETENER ROBOT", 13);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [traction, rack],
  });
  await expect
    .poll(async () => (await state(page)).rack.control.action)
    .toBe("up");
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [traction, rack, stop],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [stop],
  });
  await expect
    .poll(async () => [
      (await state(page)).control.action,
      (await state(page)).rack.control.action,
    ])
    .toEqual(["stop", "stop"]);
  await page.screenshot({ path: "../docs/evidence-gate6_2/general-stop.png" });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchCancel",
    touchPoints: [],
  });
  await context.close();
});
