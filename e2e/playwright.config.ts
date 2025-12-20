import { defineConfig } from '@playwright/test';

/**
 * Playwright configuration for API E2E tests.
 *
 * These tests verify end-to-end user flows through the API:
 * - Channel creation → Document upload → Chat
 * - Channel list → Search
 * - Document management
 */
export default defineConfig({
  testDir: './tests',

  // Run tests in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI for stability
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    ...(process.env.CI ? [['github'] as const] : []),
  ],

  // Global timeout for each test
  timeout: 60000,

  // Expect timeout
  expect: {
    timeout: 10000,
  },

  use: {
    // Base URL for API requests
    baseURL: process.env.API_BASE_URL || 'http://localhost:8000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Extra HTTP headers for all requests
    extraHTTPHeaders: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
  },

  // Configure projects for different environments
  projects: [
    {
      name: 'api-tests',
      testMatch: '**/*.spec.ts',
    },
  ],

  // Run local dev server before starting the tests (optional)
  // Uncomment if you want to auto-start the server
  // webServer: {
  //   command: 'cd .. && uvicorn src.main:app --host 0.0.0.0 --port 8000',
  //   url: 'http://localhost:8000/api/v1/health',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});
