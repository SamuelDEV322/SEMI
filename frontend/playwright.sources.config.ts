import { defineConfig } from "@playwright/test";
import base from "./playwright.operational.config";
// Reuse isolated e2e.sqlite3 and temporary ports; run sequentially with other suites.
export default defineConfig({ ...base, testMatch: "sources.spec.ts" });
