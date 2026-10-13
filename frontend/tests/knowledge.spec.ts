import { expect, test } from '@playwright/test'

test('full portfolio, source retrieval and engineering evidence gap', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Product expertise, with evidence.' })).toBeVisible()
  await expect(page.locator('.portfolio-card')).toHaveCount(15)
  await page.getByRole('button', { name: 'External Shades', exact: true }).click()
  await expect(page.locator('.portfolio-card')).toHaveCount(7)
  await expect(page.getByRole('heading', { name: 'Bioclimatic Pergolas', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Phone & battery controls' }).click()
  await expect(page.locator('.knowledge-answer')).toContainText('rechargeable battery')
  await expect(page.locator('.knowledge-citations')).toContainText('Roller blind power options')
  await expect(page.getByText('Source excerpts', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Missing wind ratings' }).click()
  await expect(page.getByRole('heading', { name: 'More evidence required' })).toBeVisible()
  await expect(page.locator('.answer-body')).toContainText('approved datasheet or live business record')
  expect(errors).toEqual([])
})

test('supported product opens estimating form and unsupported products do not', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  const curtain = page.locator('.portfolio-card').filter({ has: page.getByRole('heading', { name: 'Curtains', exact: true }) })
  await curtain.getByRole('button', { name: 'Prepare demo estimate' }).click()
  await expect(page.getByRole('dialog').getByRole('combobox', { name: 'Product', exact: true })).toHaveValue('curtain')
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await page.getByRole('button', { name: 'External Shades', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Prepare demo estimate' })).toHaveCount(0)
})

test('knowledge explorer remains usable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await page.getByRole('button', { name: 'Smart Solutions', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Smartphone control', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
})
