import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: "actuators.spec.ts",
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report-gate6_2", open: "never" }],
  ],
});
