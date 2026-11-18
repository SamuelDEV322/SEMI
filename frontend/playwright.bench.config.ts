import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
import base from "./playwright.device.config";
const key = (process.env.SEMI_TEST_MOTOR_KEY ||=
  randomBytes(32).toString("hex"));
const operator = (process.env.SEMI_TEST_OPERATOR_KEY ||=
  randomBytes(32).toString("hex"));
const servers = Array.isArray(base.webServer) ? base.webServer : [];
export default defineConfig({
  ...base,
  testMatch: "bench.spec.ts",
  webServer: servers.map((s, i) =>
    i
      ? s
      : {
          ...s,
          env: {
            ...s.env,
            SEMI_BENCH_DEVICE: "e2e-device",
            SEMI_MOTOR_KEY: key,
            SEMI_OPERATOR_KEY: operator,
            SEMI_BENCH_STORE: "e2e-bench.sqlite3",
          },
        },
  ),
});
