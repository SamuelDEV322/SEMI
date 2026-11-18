import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
// Ephemeral test credential; never used for an actual device or bundled in Vite.
const token = (process.env.SEMI_TEST_DEVICE_TOKEN ||=
  randomBytes(32).toString("hex"));
export default defineConfig({
  testDir: "./e2e",
  testMatch: "device.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5176",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command:
        "..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py prepare_e2e --empty && ..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:8004 --noreload",
      url: "http://127.0.0.1:8004/api/health/",
      reuseExistingServer: false,
      env: {
        SEMI_MODE: "operational",
        SEMI_DEVICE_INTEGRATION: "diagnostic",
        SEMI_DEVICE_TOKENS: JSON.stringify({ "e2e-device": token }),
        SEMI_LIDAR_SOURCE: "real",
        SEMI_DATABASE: "e2e.sqlite3",
        DJANGO_CSRF_TRUSTED_ORIGINS: "http://127.0.0.1:5176",
      },
    },
    {
      command: "npm run dev -- --port 5176",
      url: "http://127.0.0.1:5176",
      reuseExistingServer: false,
      env: { VITE_BACKEND_TARGET: "http://127.0.0.1:8004" },
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
