import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    baseURL: 'http://localhost:5173'
  },
  webServer: {
    command: 'npm run preview -- --port 5173 --strictPort',
    port: 5173,
    reuseExistingServer: true,
    timeout: 60000
  }
});
