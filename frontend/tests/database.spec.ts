import { expect, test } from '@playwright/test'

test('catalog identifiers and scenario fields come from the API', async ({ page }) => {
  await page.route('**/api/catalog', async (route) => {
    const response = await route.fetch()
    const data = await response.json()
    data.data_source = 'supabase'
    data.products.custom_roller = { ...data.products.manual_roller, name: 'Database custom roller' }
    data.fabrics.push({
      ...data.fabrics[0],
      id: 'custom_material',
      name: 'Database custom textile',
      stock_lm: 250,
    })
    data.scenarios = [
      {
        ...data.scenarios[0],
        title: 'Database custom scenario',
        request: {
          ...data.scenarios[0].request,
          product: 'custom_roller',
          fabric_id: 'custom_material',
          quantity: 12,
        },
      },
    ]
    await route.fulfill({ response, json: data })
  })
  await page.goto('/')
  await expect(page.locator('.demo-strip')).toContainText('Supabase business data')
  await page.getByRole('button', { name: /Database custom scenario/ }).click()
  await expect(page.getByRole('combobox', { name: /^Product/ })).toHaveValue('custom_roller')
  await expect(page.getByRole('combobox', { name: /^Fabric/ })).toHaveValue('custom_material')
  await expect(page.getByLabel('Openings', { exact: true })).toHaveValue('12')
})

test('report displays returned waste margin and VAT percentages', async ({ page }) => {
  await page.route('**/api/projects/analyze', async (route) => {
    const response = await route.fetch()
    const report = await response.json()
    report.materials.waste_percent = 12
    report.costing.gross_margin_percent = 25
    report.costing.vat_percent = 10
    await route.fulfill({ response, json: report })
  })
  await page.goto('/')
  await page.getByRole('button', { name: /The clear-to-review order/ }).click()
  await page.getByRole('button', { name: 'Analyze project' }).click()
  await expect(page.getByText('12% waste allowance included · Snapshot at analysis')).toBeVisible()
  await page.getByRole('tab', { name: 'Quotation', exact: true }).click()
  await expect(page.getByText('Sales subtotal · 25% gross margin')).toBeVisible()
  await expect(page.getByText('VAT · 10%', { exact: true })).toBeVisible()
  await expect(page.getByText(/selling price = direct cost ÷ 0.75/)).toBeVisible()
})
