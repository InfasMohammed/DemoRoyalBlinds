import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  email: 'reviewer@example.com',
  aud: 'authenticated',
  role: 'authenticated',
  email_confirmed_at: new Date().toISOString(),
  app_metadata: {},
  user_metadata: {},
  created_at: new Date().toISOString(),
}
const token =
  [
    { alg: 'HS256', typ: 'JWT' },
    { sub: user.id, role: 'authenticated', exp: Math.floor(Date.now() / 1000) + 3600 },
  ]
    .map((part) => Buffer.from(JSON.stringify(part)).toString('base64url'))
    .join('.') + '.fake-signature'

async function mockSignIn(page: Page, success: boolean) {
  await page.route('https://demo-auth.supabase.co/auth/v1/**', async (route) => {
    const request = route.request()
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST,GET,OPTIONS',
      'Access-Control-Allow-Headers': request.headers()['access-control-request-headers'] || '*',
    }
    if (request.method() === 'OPTIONS' || request.url().includes('/logout')) {
      await route.fulfill({ status: 204, headers })
    } else if (request.url().includes('/token')) {
      await route.fulfill({
        status: success ? 200 : 400,
        headers,
        json: success
          ? {
              access_token: token,
              refresh_token: 'fake-refresh-token',
              token_type: 'bearer',
              expires_in: 3600,
              user,
            }
          : { error_code: 'invalid_credentials', msg: 'Invalid login credentials' },
      })
    } else await route.fulfill({ headers, json: user })
  })
}

test('sign-in gate blocks API reads and handles invalid credentials on mobile', async ({
  page,
}) => {
  await mockSignIn(page, false)
  const requests: string[] = []
  page.on('request', (req) => {
    if (req.url().includes('/api/')) requests.push(req.url())
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Sign in to explore the demo.' })).toBeVisible()
  await page.getByLabel('Email', { exact: true }).fill(user.email)
  await page.getByLabel('Password', { exact: true }).fill('incorrect-demo-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Sign-in failed')
  expect(requests).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
})

test('signed-in requests use the configured API origin and token; sign-out clears access', async ({
  page,
}) => {
  await mockSignIn(page, true)
  const requests: { url: string; token: string | undefined }[] = []
  page.on('request', (req) => {
    if (req.url().includes('/api/'))
      requests.push({ url: req.url(), token: req.headers().authorization })
  })
  await page.goto('/')
  await page.getByLabel('Email', { exact: true }).fill(user.email)
  await page.getByLabel('Password', { exact: true }).fill('fake-demo-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByText('Backend connected')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Backend connected')).toBeVisible()
  await page.getByRole('button', { name: 'New quotation', exact: true }).click()
  await page.getByRole('button', { name: 'Analyze project', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Resolve constraints before approval' }),
  ).toBeVisible()
  expect(requests.some((req) => req.url.endsWith('/api/projects/analyze'))).toBe(true)
  expect(requests.every((req) => req.url.startsWith('http://127.0.0.1:8011/api/'))).toBe(true)
  expect(requests.every((req) => req.token === `Bearer ${token}`)).toBe(true)
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in to explore the demo.' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Sign in to explore the demo.' })).toBeVisible()
})
