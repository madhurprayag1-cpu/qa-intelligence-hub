import { defineConfig, devices } from "@playwright/test";

const isWindows = process.platform === "win32";
const backendCmd = isWindows
  ? 'powershell -Command "$env:PYTHONPATH=\'..;../qa-engine;../ai-engine\'; if (-not $env:DATABASE_URL) { $env:DATABASE_URL=\'sqlite:///./test_local.db\' }; & .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000"'
  : "PYTHONPATH=..:../qa-engine:../ai-engine DATABASE_URL=${DATABASE_URL:-sqlite:///./test_local.db} uvicorn app.main:app --port 8000";

const targetURL = process.env.BASE_URL || "http://localhost:5173";

export default defineConfig({
  testDir: "./tests/ui",
  timeout: 30000,
  expect: {
    timeout: 6000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["json", { outputFile: "test-results/playwright-report.json" }],
  ],
  use: {
    baseURL: targetURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: process.env.BASE_URL
    ? undefined
    : [
        {
          command: backendCmd,
          cwd: "./backend",
          url: "http://127.0.0.1:8000/health",
          reuseExistingServer: true,
          timeout: 30000,
        },
        {
          command: "npm run dev --prefix frontend -- --port 5173",
          url: "http://localhost:5173",
          reuseExistingServer: true,
          timeout: 30000,
        },
      ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
