import { defineConfig, devices } from '@playwright/test';

const externalUrl = process.env.PLAYWRIGHT_EXTERNAL_URL;
const basePath = process.env.VITE_BASE_PATH || '/';
const normalizedPath = basePath.endsWith('/') ? basePath : `${basePath}/`;
const baseUrl = externalUrl || process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:4173${normalizedPath}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: baseUrl,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  ...(externalUrl
    ? {}
    : {
        webServer: {
          command: 'npm run preview -- --port 4173 --host 127.0.0.1 --strictPort',
          url: baseUrl,
          reuseExistingServer: false,
          timeout: 60000,
        },
      }),
});
