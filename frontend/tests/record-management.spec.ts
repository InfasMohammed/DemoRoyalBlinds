import { expect, test } from '@playwright/test'

test('page actions match their purpose and offline saves are unavailable', async ({ page }) => {
  await page.goto('/')
  await expect(
    page.locator('.page-heading').getByRole('button', { name: 'New quotation' }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await page.locator('.page-heading').getByRole('button', { name: 'Add knowledge' }).click()
  await expect(page.getByRole('dialog')).toContainText('Saving requires Supabase business data')
  await expect(page.getByRole('button', { name: 'Save knowledge', exact: true })).toBeDisabled()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Material library', exact: true }).click()
  await page.locator('.page-heading').getByRole('button', { name: 'Add material' }).click()
  await expect(page.getByRole('button', { name: 'Save material', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  for (const name of [/Project reports/, 'Agent workflow']) {
    await page.getByRole('button', { name }).click()
    await expect(page.locator('.page-heading button')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'New quotation', exact: true })).toHaveCount(0)
  }
})

test('material form preserves failed input and refreshes library and quotation choices', async ({
  page,
  request,
}) => {
  const catalog = await (await request.get('/api/catalog')).json()
  catalog.data_source = 'supabase'
  await page.route('**/api/catalog', (route) => route.fulfill({ json: catalog }))
  const payloads: Record<string, any>[] = []
  await page.route('**/api/materials', async (route) => {
    const payload = route.request().postDataJSON()
    payloads.push(payload)
    if (payloads.length === 1) {
      await route.fulfill({ status: 409, json: { detail: 'This material SKU already exists.' } })
      return
    }
    const { request_id, ...fields } = payload
    const record = {
      ...fields,
      id: `mat_${request_id.replaceAll('-', '')}`,
      reserved_lm: 0,
      on_hand_lm: fields.stock_lm,
    }
    catalog.fabrics.push(record)
    await route.fulfill({ status: 201, json: { created: true, data_source: 'supabase', record } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Material library', exact: true }).click()
  await page.getByRole('button', { name: 'Add material', exact: true }).click()
  const dialog = page.getByRole('dialog')
  for (const [label, value] of Object.entries({
    'Material name': 'New ivory demo fabric',
    SKU: 'DUPLICATE-SKU',
    'Roll width (m)': '2.8',
    'Opening stock (linear m)': '25.5',
    'Cost (AED / linear m)': '35',
    'Lead time (days)': '4',
    Colour: 'Ivory',
    'Light transmission / finish': 'Blackout',
    'Stock and cost source': 'Demo supplier quotation',
  }))
    await dialog.getByLabel(label, { exact: true }).fill(value)
  await dialog.getByRole('checkbox').first().check()
  await dialog.getByRole('button', { name: 'Save material' }).click()
  await expect(dialog.getByRole('alert')).toContainText('SKU already exists')
  await expect(dialog.getByLabel('Material name', { exact: true })).toHaveValue(
    'New ivory demo fabric',
  )
  await dialog.getByLabel('SKU', { exact: true }).fill('NEW-IVORY-SKU')
  await dialog.getByRole('button', { name: 'Save material' }).click()
  await expect(dialog).toHaveCount(0)
  await expect(
    page.getByRole('heading', { name: 'New ivory demo fabric', exact: true }),
  ).toBeVisible()
  expect(payloads[0].request_id).toBe(payloads[1].request_id)
  expect(payloads[1].compatible).toHaveLength(1)
  expect(payloads[1].stock_lm).toBe(25.5)
  expect(payloads[1]).not.toHaveProperty('SUPABASE_SERVICE_ROLE_KEY')
  await page.getByRole('button', { name: 'Project studio', exact: true }).click()
  await page.getByRole('button', { name: 'New quotation', exact: true }).click()
  await expect(
    page
      .getByRole('dialog')
      .getByRole('combobox', { name: 'Fabric', exact: true })
      .locator('option'),
  ).toContainText(['New ivory demo fabric'])
})

test('knowledge form saves reviewed text and refreshes sources on mobile', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const catalog = await (await request.get('/api/catalog')).json()
  const portfolio = await (await request.get('/api/knowledge/portfolio')).json()
  await page.route('**/api/catalog', (route) =>
    route.fulfill({ json: { ...catalog, data_source: 'supabase' } }),
  )
  await page.route('**/api/knowledge/portfolio', (route) =>
    route.fulfill({ json: { ...portfolio, data_source: 'supabase' } }),
  )
  let payload: Record<string, any> | null = null
  await page.route('**/api/knowledge/entries', async (route) => {
    payload = route.request().postDataJSON()
    portfolio.documents.push({
      id: `RB-USER-${payload!.request_id}`,
      title: payload!.title,
      category: payload!.category,
      source_url: payload!.source_url,
      sections: 1,
    })
    portfolio.chunk_count += 1
    await route.fulfill({
      status: 201,
      json: { created: true, data_source: 'supabase', indexing_status: 'pending' },
    })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await page.getByRole('button', { name: 'Add knowledge', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Source title', { exact: true }).fill('Reviewed showroom panel guide')
  await dialog.getByLabel('Section heading', { exact: true }).fill('Panel consultation')
  await dialog
    .getByRole('combobox', { name: 'Knowledge category', exact: true })
    .selectOption('smart')
  await dialog
    .getByLabel('Source URL', { exact: true })
    .fill('https://royalblinds.com/showroom-guide/')
  await dialog
    .getByLabel('Source text', { exact: true })
    .fill('The ultramarine showroom panel protocol is used during sample consultations.')
  await dialog.getByRole('checkbox', { name: 'Roller Blinds', exact: true }).check()
  await dialog.getByRole('button', { name: 'Save knowledge' }).click()
  expect(payload).toBeNull()
  await dialog.getByLabel('I reviewed this source text and its source URL.').check()
  await page.screenshot({ path: '../.runtime/knowledge-entry-mobile.png' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await dialog.getByRole('button', { name: 'Save knowledge' }).click()
  await expect(dialog).toHaveCount(0)
  await expect(page.locator('.source-register')).toContainText('Reviewed showroom panel guide')
  expect(payload).toMatchObject({
    category: 'smart',
    product_ids: ['roller_blinds'],
    reviewed: true,
  })
  await page.reload()
  await page.getByRole('button', { name: 'Product knowledge', exact: true }).click()
  await expect(page.locator('.source-register')).toContainText('Reviewed showroom panel guide')
})
