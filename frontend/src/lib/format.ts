import type { Report } from '../types'

export const money = (value: number) =>
  new Intl.NumberFormat('en-AE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    value,
  )
export const day = (value: string) =>
  new Date(`${value}T12:00:00`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
export const statusLabel = (status: Report['status']) =>
  ({
    blocked: 'Needs attention',
    awaiting_review: 'Awaiting review',
    demo_approved: 'Demo approved',
  })[status]
export const modeLabel = (mode: string) =>
  ({
    rule_based_demo: 'Rule-based demo',
    live_ai: 'Live AI',
    ai_with_fallback: 'AI with fallback',
    live_ai_configured: 'AI configured',
  })[mode] || mode
