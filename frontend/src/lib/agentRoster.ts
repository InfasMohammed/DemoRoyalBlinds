import { ScanLine, Package, ShieldCheck, FileText, Factory, Workflow } from 'lucide-react'

export const agents = [
  { name: 'Specification', desc: 'Scope & dimensions', icon: ScanLine },
  { name: 'Inventory', desc: 'Yield & availability', icon: Package },
  { name: 'Quality', desc: 'Limits & inspections', icon: ShieldCheck },
  { name: 'Quotation', desc: 'Costs & gross margin', icon: FileText },
  { name: 'Production', desc: 'Capacity & scheduling', icon: Factory },
  { name: 'Coordinator', desc: 'Decision & review', icon: Workflow },
]
