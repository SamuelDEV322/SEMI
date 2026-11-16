import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["gate2.spec.ts", "gate4.spec.ts"],
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report-gate4", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5174",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py prepare_e2e && ..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:8002 --noreload",
      url: "http://127.0.0.1:8002/api/health/",
      reuseExistingServer: false,
      env: {
        SEMI_MODE: "demonstration",
        SEMI_DEV_TOOLS: "1",
        SEMI_LIDAR_SOURCE: "mock",
        SEMI_DATABASE: "e2e.sqlite3",
        DJANGO_CSRF_TRUSTED_ORIGINS: "http://127.0.0.1:5174",
      },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: { VITE_BACKEND_TARGET: "http://127.0.0.1:8002" },
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
