import { expect, test } from '@playwright/test'

test('full portfolio, source retrieval and engineering evidence gap', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await expect(
    page.getByRole('heading', { name: 'Product expertise, with evidence.' }),
  ).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Category (optional)' })).toHaveValue('')
  await expect(page.locator('.portfolio-card')).toHaveCount(15)
  await page.getByRole('button', { name: 'External Shades', exact: true }).click()
  await expect(page.locator('.portfolio-card')).toHaveCount(7)
  await expect(
    page.getByRole('heading', { name: 'Bioclimatic Pergolas', exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Outdoor product range' }).click()
  await expect(page.getByText('Catalog answer', { exact: true })).toBeVisible()
  await expect(page.locator('.answer-mode')).toContainText('Complete product catalog lookup')
  for (const name of [
    'Car Parking Shades',
    'Sail Shades',
    'Bioclimatic Pergolas',
    'Tensile Shade Structures',
    'Awnings',
    'Outdoor Furniture',
    'Umbrellas',
  ]) {
    await expect(page.locator('.answer-body')).toContainText(`• ${name} [CATALOG-`)
  }
  await expect(page.locator('.knowledge-citations article')).toHaveCount(7)
  await expect(page.locator('.answer-body')).not.toContainText('Transform your outdoor spaces')
  const firstEvidence = page.locator('.knowledge-citations details').first()
  await expect(firstEvidence).not.toHaveAttribute('open', '')
  await firstEvidence.getByText('Read catalog evidence', { exact: true }).click()
  await expect(firstEvidence.locator('p')).toContainText('not specifications or stock availability')
  await expect(page.getByRole('button', { name: 'Find an answer' })).toBeEnabled()
  const pergola = page
    .locator('.portfolio-card')
    .filter({ has: page.getByRole('heading', { name: 'Bioclimatic Pergolas', exact: true }) })
  await pergola.getByRole('button', { name: 'Explore source evidence' }).click()
  await expect(page.locator('.knowledge-answer .answer-question')).toContainText(
    'Bioclimatic Pergolas',
  )
  await expect(page.getByRole('button', { name: 'Find an answer' })).toBeEnabled()
  await page
    .getByLabel('Your question')
    .fill('Can motorized roller blinds use rechargeable battery or mains power?')
  const request = page.waitForRequest(
    (request) => request.url().endsWith('/api/knowledge/ask') && request.method() === 'POST',
  )
  await page.getByRole('button', { name: 'Find an answer' }).click()
  expect((await request).postDataJSON()).toEqual({
    question: 'Can motorized roller blinds use rechargeable battery or mains power?',
    category: null,
    product_id: null,
  })
  await expect(page.locator('.knowledge-answer')).toContainText('rechargeable battery')
  await expect(page.locator('.knowledge-citations')).toContainText('Roller blind power options')
  await expect(page.getByRole('button', { name: 'Phone & battery controls' })).toBeEnabled()
  await page.getByRole('button', { name: 'Phone & battery controls' }).click()
  await expect(page.locator('.knowledge-answer')).toContainText('rechargeable battery')
  await expect(page.locator('.knowledge-citations')).toContainText('Roller blind power options')
  await expect(page.getByText('Source excerpts', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Missing wind ratings' }).click()
  await expect(page.getByRole('heading', { name: 'More evidence required' })).toBeVisible()
  await expect(page.locator('.answer-body')).toContainText(
    'approved datasheet or live business record',
  )
  expect(errors).toEqual([])
})

test('supported product opens estimating form and unsupported products do not', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  const curtain = page
    .locator('.portfolio-card')
    .filter({ has: page.getByRole('heading', { name: 'Curtains', exact: true }) })
  await curtain.getByRole('button', { name: 'Prepare demo estimate' }).click()
  await expect(
    page.getByRole('dialog').getByRole('combobox', { name: 'Product', exact: true }),
  ).toHaveValue('curtain')
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

test('company questions work automatically and Q&A categories are independent of portfolio filters', async ({
  page,
}) => {
  const payloads: { question: string; category: string | null; product_id: string | null }[] = []
  page.on('request', (req) => {
    if (req.url().endsWith('/api/knowledge/ask') && req.method() === 'POST')
      payloads.push(req.postDataJSON())
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  const filter = page.getByRole('combobox', { name: 'Category (optional)' })
  await expect(filter).toBeEnabled()
  await page.getByRole('button', { name: 'External Shades', exact: true }).click()
  await page.getByLabel('Your question').fill('Who is the owner of the company?')
  await page.getByRole('button', { name: 'Find an answer' }).click()
  await expect(page.locator('.answer-body')).toContainText('Al Jallaf Family')
  await expect(page.getByText('Company facts', { exact: true })).toBeVisible()
  expect(payloads.at(-1)?.category).toBeNull()
  await filter.selectOption('company')
  await page.getByLabel('Your question').fill('give me the location of company')
  await page.getByRole('button', { name: 'Find an answer' }).click()
  await expect(page.locator('.answer-body')).toContainText('Al Quoz')
  await expect(page.locator('.answer-body')).toContainText('Abu Dhabi')
  expect(payloads.at(-1)?.category).toBe('company')
  await filter.selectOption('smart')
  await page
    .getByLabel('Your question')
    .fill('Can motorized roller blinds use rechargeable battery power?')
  await page.getByRole('button', { name: 'Find an answer' }).click()
  await expect(page.locator('.answer-body')).toContainText('rechargeable battery')
  expect(payloads.at(-1)?.category).toBe('smart')
  expect(payloads.at(-1)?.product_id).toBeNull()
  await filter.selectOption('internal')
  await page.getByLabel('Your question').fill('Who owns the company?')
  await page.getByRole('button', { name: 'Find an answer' }).click()
  await expect(page.locator('.answer-body')).toContainText(
    'Select All categories or Company profile',
  )
  await page.getByRole('button', { name: 'Company ownership', exact: true }).click()
  await expect(page.locator('.answer-body')).toContainText('Al Jallaf Family')
  await expect(filter).toHaveValue('')
  await expect(page.locator('.portfolio-card')).toHaveCount(7)
})
