import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

export default defineConfig({
  testDir: './tests',
  testMatch: 'auth.spec.ts',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5181',
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8011',
      cwd: '../backend',
      env: {
        UV_CACHE_DIR: fileURLToPath(new URL('../.runtime/uv-cache', import.meta.url)),
        DEMO_STORE_PATH: fileURLToPath(
          new URL(`../.runtime/auth-reports-${randomUUID()}.json`, import.meta.url),
        ),
        BUSINESS_DATA_SOURCE: 'demo',
        SUPABASE_URL: '',
        SUPABASE_SERVICE_ROLE_KEY: '',
        LLM_API_KEY: '',
        NVIDIA_API_KEY: '',
        KNOWLEDGE_RETRIEVAL_MODE: 'local',
        POST_APPROVAL_WORKER_ENABLED: 'false',
        APP_ENV: 'development',
        AUTH_REQUIRED: 'false',
        K_SERVICE: '',
        CORS_ORIGINS: 'http://127.0.0.1:5181',
      },
      url: 'http://127.0.0.1:8011/api/health',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5181',
      env: {
        VITE_REQUIRE_AUTH: 'true',
        VITE_API_BASE_URL: 'http://127.0.0.1:8011',
        VITE_SUPABASE_URL: 'https://demo-auth.supabase.co',
        VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_fake_for_browser_tests',
      },
      url: 'http://127.0.0.1:5181',
      reuseExistingServer: false,
    },
  ],
})
