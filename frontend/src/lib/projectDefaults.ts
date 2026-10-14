import type { Catalog, ProjectInput } from '../types'

function after(start: string, count: number) {
  const value = new Date(`${start}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate() + count)
  return value.toISOString().slice(0, 10)
}

export function createProjectInput(
  today: string,
  catalog: Catalog,
  scenario = 'shortage',
): ProjectInput {
  const preset = catalog.scenarios.find((item) => item.id === scenario) || catalog.scenarios[0]
  if (preset) return { ...preset.request, due_date: after(today, preset.deadline_days) }
  const product = Object.keys(catalog.products)[0]
  const fabric =
    catalog.fabrics.find((item) => item.compatible.includes(product)) || catalog.fabrics[0]
  return {
    customer: '',
    project_name: '',
    brief: '',
    site: '',
    product,
    fabric_id: fabric.id,
    quantity: 1,
    width_m: 1,
    height_m: 1,
    due_date: today,
  }
}
