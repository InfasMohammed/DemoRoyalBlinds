import { ArrowUpRight, Layers3 } from 'lucide-react'
import type { Report } from '../types'
import { money, day, statusLabel } from '../lib/format'

type Props = {
  reports: Report[]
  openReport: (report: Report) => void
}

export default function ProjectsPage({ reports, openReport }: Props) {
  return (
    <section className="card projects-card">
      <div className="section-heading">
        <h3>Saved project reports</h3>
        <span className="pill neutral">{reports.length} reports · latest 50</span>
      </div>
      {!reports.length ? (
        <div className="empty-state">
          <Layers3 size={34} />
          <h3>Your first report starts in Project studio.</h3>
          <p>
            Analyze a quotation brief in Project studio to save its report and complete agent
            evidence here.
          </p>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Project / customer</th>
                <th>Estimate (AED)</th>
                <th>Completion</th>
                <th>Review status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {reports.map((item) => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.request.project_name}</strong>
                    <small>
                      {item.request.customer} · {item.id.slice(0, 8)}
                    </small>
                  </td>
                  <td>{money(item.costing.total)}</td>
                  <td>{day(item.production.completion_date)}</td>
                  <td>
                    <span className={`pill ${item.status === 'blocked' ? 'amber' : 'green'}`}>
                      {statusLabel(item.status)}
                    </span>
                  </td>
                  <td>
                    <button className="text-link" onClick={() => openReport(item)}>
                      Open <ArrowUpRight size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
