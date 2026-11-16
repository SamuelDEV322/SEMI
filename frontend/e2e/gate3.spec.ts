import { test, expect } from "@playwright/test";
for (const width of [360, 390, 768, 1440])
  for (const theme of ["light", "dark"])
    test(`installation ${width} ${theme}`, async ({ page }) => {
      const missing: string[] = [];
      page.on("response", (r) => {
        if (r.url().includes("/api/") && r.status() === 404)
          missing.push(r.url());
      });
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByText("Conectado · simulado", { exact: true }),
      ).toBeVisible();
      await page.getByLabel("Apariencia").selectOption(theme);
      await page
        .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
        .click();
      for (let step = 1; step <= 7; step++) {
        await expect(
          page.getByText(`Paso ${step} de 7`, { exact: false }),
        ).toBeVisible();
        if (step === 2) {
          await page
            .getByLabel("Nombre del terreno")
            .fill("Prueba de tierra y arena");
          await page.reload();
          await expect(page.getByLabel("Nombre del terreno")).toBeVisible();
          await page
            .getByLabel("Nombre del terreno")
            .fill("Prueba de tierra y arena");
        }
        if (step === 3)
          await page
            .getByRole("button", { name: "Usar ejemplo de tierra y arena" })
            .click();
        if (step === 4)
          await page
            .getByRole("button", { name: "Añadir dos puntos de ejemplo" })
            .click();
        if (step === 6) {
          await page
            .getByRole("button", { name: "Tomar medición de prueba" })
            .click();
          await expect(
            page.getByText("Resultado guardado en P1"),
          ).toBeVisible();
        }
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBeTruthy();
        await page.screenshot({
          path: `../docs/evidence-gate3/${width}-${theme}-step${step}.png`,
          fullPage: true,
        });
        if (step === 1)
          await page
            .getByRole("button", { name: "Comenzar", exact: true })
            .click();
        else if (step < 7)
          await page
            .getByRole("button", { name: "Continuar", exact: true })
            .click();
      }
      await page
        .getByRole("button", { name: "Ir a Inicio", exact: true })
        .click();
      await expect(
        page.getByText("Conectado · simulado", { exact: true }),
      ).toBeVisible();
      await page
        .getByRole("navigation")
        .getByRole("button", { name: "Datos", exact: true })
        .click();
      await expect(
        page.getByText("Registro de mediciones", { exact: true }),
      ).toBeVisible();
      await expect(page.locator(".sample-row")).toHaveCount(1);
      await page.screenshot({
        path: `../docs/evidence-gate3/${width}-${theme}-p1-result.png`,
        fullPage: true,
      });
      await page
        .getByLabel("Punto de muestreo", { exact: true })
        .selectOption({ index: 1 });
      await expect(
        page.getByText("Sin lecturas para este punto y periodo.", {
          exact: true,
        }),
      ).toBeVisible();
      await page
        .getByRole("navigation")
        .getByRole("button", { name: "Inicio", exact: true })
        .click();
      await page.getByText("Ensayo tierra y arena · solo simulación").click();
      await page.getByRole("button", { name: "Arena", exact: true }).click();
      await expect(
        page.getByRole("alert").filter({ hasText: "STOP simulado" }),
      ).toBeVisible();
      await page.screenshot({
        path: `../docs/evidence-gate3/${width}-${theme}-sand.png`,
        fullPage: true,
      });
      await page.getByRole("button", { name: "Tierra", exact: true }).click();
      expect(missing).toEqual([]);
    });

test("fresh installation shows welcome and resume after exit", async ({
  page,
}) => {
  await page.route("**/api/setup/", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        json: { schema_version: "1.0", mode: "demonstration", data: null },
      });
      await page.unroute("**/api/setup/");
    } else await route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Bienvenido a SEMI" }),
  ).toBeVisible();
  // Fresh response above verifies automatic entry only; the full writes use an isolated demo.
  await page.getByRole("button", { name: "Salir por ahora" }).click();
  await page
    .getByRole("button", { name: "Repetir bienvenida · demo aislada" })
    .click();
  await page.getByRole("button", { name: "Comenzar", exact: true }).click();
  await page.getByLabel("Nombre del terreno").fill("Mi terreno reanudado");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await page.getByRole("button", { name: "Salir por ahora" }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Identificar mis zonas" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Volver", exact: true }).click();
  await expect(page.getByLabel("Nombre del terreno")).toHaveValue(
    "Mi terreno reanudado",
  );
});
