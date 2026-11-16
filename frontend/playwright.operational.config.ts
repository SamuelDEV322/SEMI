import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: "operational.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5175",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py prepare_e2e --empty && ..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:8003 --noreload",
      url: "http://127.0.0.1:8003/api/health/",
      reuseExistingServer: false,
      env: {
        SEMI_MODE: "operational",
        SEMI_LIDAR_SOURCE: "real",
        SEMI_DEV_TOOLS: "0",
        SEMI_DATABASE: "e2e.sqlite3",
        SEMI_LIDAR_SPOOL: "runtime/e2e-reader-absent.json",
        DJANGO_CSRF_TRUSTED_ORIGINS: "http://127.0.0.1:5175",
      },
    },
    {
      command: "npm run dev -- --port 5175",
      url: "http://127.0.0.1:5175",
      reuseExistingServer: false,
      env: { VITE_BACKEND_TARGET: "http://127.0.0.1:8003" },
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
