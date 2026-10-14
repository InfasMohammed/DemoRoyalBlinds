import { CalendarDays, ClipboardCheck } from 'lucide-react'
import type { Report } from '../../types'
import { day } from '../../lib/format'

type Props = {
  report: Report
}

export default function ReportDelivery({ report }: Props) {
  return (
    <div className="report-grid">
      <div>
        <section className="card timeline-card">
          <div className="section-heading">
            <h3>Proposed production plan</h3>
            <span className={`pill ${report.production.on_time ? 'green' : 'amber'}`}>
              {report.production.on_time ? 'Within deadline' : 'Deadline at risk'}
            </span>
          </div>
          {[
            {
              label: 'Materials available',
              date: report.production.material_ready,
              detail: report.materials.in_stock
                ? 'Subject to stock confirmation'
                : `${report.materials.lead_days} calendar days supplier lead time`,
            },
            {
              label: 'Manufacturing',
              date: report.production.manufacture_start,
              detail: `Through ${day(report.production.manufacture_end)} · ${report.production.factory_hours} labour hours`,
            },
            {
              label: 'Quality inspection',
              date: report.production.quality_date,
              detail: 'Dimensions, finish and operating checks',
            },
            {
              label: 'Site installation',
              date: report.production.installation_start,
              detail: `${report.production.installation_hours} labour hours · access subject to survey`,
            },
            {
              label: 'Estimated completion',
              date: report.production.completion_date,
              detail: `Customer deadline: ${day(report.production.due_date)}`,
            },
          ].map((stage, i) => (
            <div className="timeline-item" key={stage.label}>
              <div className="timeline-marker">{i + 1}</div>
              <div>
                <h4>{stage.label}</h4>
                <p>{stage.detail}</p>
              </div>
              <strong>{day(stage.date)}</strong>
            </div>
          ))}
          <div className="inline-warning">
            <CalendarDays size={17} /> This is a capacity estimate, not a committed production
            booking.
          </div>
        </section>
        <section className="card assumptions">
          <h3>Scheduling assumptions</h3>
          <ul className="simple-list">
            {report.production.assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="fine-print">
            Plan calculated as of {day(report.production.as_of)}, Dubai time.
          </p>
        </section>
      </div>
      <section className="card quality-card">
        <div className="section-heading">
          <h3>Quality & site checklist</h3>
          <ClipboardCheck size={20} />
        </div>
        <p className="muted">Proposed checks for the reviewer and installation team.</p>
        {report.quality.checklist.map((item) => (
          <div className="checklist-item" key={item}>
            <span className="empty-check" />
            <span>{item}</span>
          </div>
        ))}
        <p className="fine-print">{report.quality.note}</p>
      </section>
    </div>
  )
}
