import { CheckCircle2, CircleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export default function Metric({
  icon: Icon,
  label,
  value,
  detail,
  alert = false,
}: {
  icon: LucideIcon
  label: string
  value: string
  detail: string
  alert?: boolean
}) {
  return (
    <section className="metric card">
      <div>
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <h3>{value}</h3>
      <p className={alert ? 'warning-text' : ''}>
        {alert ? <CircleAlert size={13} /> : <CheckCircle2 size={13} />}
        {detail}
      </p>
    </section>
  )
}
