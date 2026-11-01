import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL:
      process.env.PLAYWRIGHT_BASE_URL ||
      (process.env.CI ? "http://127.0.0.1:8000" : "http://127.0.0.1:5173"),
    browserName: "chromium",
    channel: process.env.CI ? undefined : "msedge",
    headless: true,
    trace: "retain-on-failure",
  },
  reporter: "list",
});
