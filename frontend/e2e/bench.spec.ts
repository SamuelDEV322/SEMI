import { test, expect } from "@playwright/test";
import { createHmac, randomBytes } from "node:crypto";
import { execFileSync } from "node:child_process";
import path from "node:path";

test("pulsación humana hasta la respuesta firmada al dispositivo de prueba", async ({
  page,
  request,
}) => {
  const health = (await (await request.get("/api/health/")).json()).data;
  const headers = { "X-CSRFToken": health.csrf_token };
  const plot = (
    await (
      await request.post("/api/setup/", { headers, data: { action: "start" } })
    ).json()
  ).data;
  await request.post("/api/setup/", { headers, data: { action: "complete" } });
  const registration = execFileSync(
    path.resolve("../.venv/Scripts/python.exe"),
    [
      "../backend/manage.py",
      "register_device",
      "--device-id",
      "e2e-device",
      "--plot",
      String(plot.id),
    ],
    {
      encoding: "utf8",
      env: { ...process.env, SEMI_DATABASE: "e2e.sqlite3" },
    },
  );
  const session = registration.match(/session_id=([\w-]+)/)![1];
  const boot = randomBytes(16).toString("hex");
  const sign = (s: string) =>
    createHmac("sha256", process.env.SEMI_TEST_MOTOR_KEY!)
      .update(s)
      .digest("hex");
  let running = true,
    counter = 0;
  const frames: string[] = [];
  const device = (async () => {
    while (running) {
      const n = ++counter;
      const res = await request.post(
        "http://127.0.0.1:8004/api/device/bench/",
        {
          maxRetries: 1,
          headers: {
            "X-SEMI-Device-ID": "e2e-device",
            "X-SEMI-Device-Token": process.env.SEMI_TEST_DEVICE_TOKEN!,
          },
          data: {
            schema_version: "1.0",
            boot,
            session_id: session,
            counter: n,
            ready: 3,
            mac: sign(["poll", "e2e-device", session, boot, n, 3].join("|")),
          },
        },
      );
      if (res.ok()) {
        const data = (await res.json()).data;
        expect(data.mac).toBe(sign(data.frame));
        frames.push(data.frame);
      }
      await new Promise((resolve) => setTimeout(resolve, 55));
    }
  })();
  try {
    await page.goto("/#control");
    await page
      .getByText("Habilitar control supervisado", { exact: true })
      .click();
    await page
      .getByLabel("Clave del operador")
      .fill(process.env.SEMI_TEST_OPERATOR_KEY!);
    await page.getByRole("button", { name: "Habilitar tracción" }).click();
    await page
      .getByRole("button", { name: "Habilitar recorrido limitado" })
      .click();
    await page
      .getByText("Habilitar control supervisado", { exact: true })
      .click();
    const forward = page.getByRole("button", { name: "Adelante", exact: true });
    await expect(forward).toBeEnabled();
    await page.getByRole("button", { name: "Media", exact: true }).click();
    await forward.focus();
    await page.keyboard.down("Space");
    await expect
      .poll(() => frames.some((s) => s.includes("|forward|medium|")))
      .toBeTruthy();
    await page.keyboard.up("Space");
    await expect.poll(() => frames.at(-1)).toMatch(/\|stop\|medium\|0\|stop\|/);
    const up = page.getByRole("button", { name: "Subir", exact: true });
    await up.focus();
    await page.keyboard.down("Enter");
    await expect
      .poll(() => frames.some((s) => s.match(/\|up\|low\|[1-9]/)))
      .toBeTruthy();
    await page.keyboard.up("Enter");
    await page
      .getByRole("button", { name: "DETENER ROBOT", exact: true })
      .click();
    await expect(forward).toBeDisabled();
    await expect(up).toBeDisabled();
    await expect
      .poll(() => frames.at(-1))
      .toMatch(/\|stop\|medium\|0\|stop\|low\|0$/);
  } finally {
    running = false;
    await device;
  }
});
