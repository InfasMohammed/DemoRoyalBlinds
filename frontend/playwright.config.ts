import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const reportPath = fileURLToPath(
  new URL(`../.runtime/browser-reports-${randomUUID()}.json`, import.meta.url),
)

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5180',
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8010',
      cwd: '../backend',
      env: {
        UV_CACHE_DIR: fileURLToPath(new URL('../.runtime/uv-cache', import.meta.url)),
        DEMO_STORE_PATH: reportPath,
        BUSINESS_DATA_SOURCE: 'demo',
        SUPABASE_URL: '',
        SUPABASE_SERVICE_ROLE_KEY: '',
        LLM_API_KEY: '',
        NVIDIA_API_KEY: '',
        KNOWLEDGE_RETRIEVAL_MODE: 'local',
        POST_APPROVAL_WORKER_ENABLED: 'true',
      },
      url: 'http://127.0.0.1:8010/api/health',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5180',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8010' },
      url: 'http://127.0.0.1:5180',
      reuseExistingServer: false,
    },
  ],
})
