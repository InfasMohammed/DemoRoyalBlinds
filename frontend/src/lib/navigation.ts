import { BookOpen, Box, Layers3, LayoutDashboard, Workflow } from 'lucide-react'

export type Page = 'workspace' | 'knowledge' | 'projects' | 'inventory' | 'workflow'
export type ReportTab = 'overview' | 'agents' | 'quote' | 'delivery' | 'execution'

export const navigation = [
  {
    id: 'workspace',
    name: 'Project studio',
    icon: LayoutDashboard,
    heading: 'From brief to better execution.',
    description: 'Plan blinds and curtains with a transparent, coordinated workflow.',
  },
  {
    id: 'knowledge',
    name: 'Product knowledge',
    icon: BookOpen,
    heading: 'Product expertise, with evidence.',
    description: 'Explore the complete supplied portfolio and retrieve source-linked answers.',
  },
  {
    id: 'projects',
    name: 'Project reports',
    icon: Layers3,
    heading: 'Every project. Every decision.',
    description: 'Revisit saved estimates, evidence and review decisions.',
  },
  {
    id: 'inventory',
    name: 'Material library',
    icon: Box,
    heading: 'The right material, in view.',
    description: 'Material availability, recorded costs and supplier lead times.',
  },
  {
    id: 'workflow',
    name: 'Agent workflow',
    icon: Workflow,
    heading: 'A team of focused specialists.',
    description: 'See how LangGraph connects calculations, evidence and human review.',
  },
] as const

export const reportTabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'agents', label: 'Agent findings' },
  { id: 'quote', label: 'Quotation' },
  { id: 'delivery', label: 'Production & quality' },
  { id: 'execution', label: 'Work order' },
] as const

export function pageDetails(page: Page) {
  return navigation.find((item) => item.id === page)!
}
