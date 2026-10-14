import { ArrowRight, CheckCircle2, CircleAlert, Package, ShieldCheck, Workflow } from 'lucide-react'
import type { FormEvent } from 'react'
import type { ProjectInput, Report } from '../../types'
import { day } from '../../lib/format'
import type { ReportTab } from '../../lib/navigation'

type Props = {
  report: Report
  busy: boolean
  executionSourceIssue: string | null
  setTab: (tab: ReportTab) => void
  setApproving: (approving: boolean) => void
  analyze: (event?: FormEvent, replacement?: ProjectInput) => Promise<void>
  prepareFreshQuotation: () => Promise<void>
}

export default function ReportOverview({
  report,
  busy,
  executionSourceIssue,
  setTab,
  setApproving,
  analyze,
  prepareFreshQuotation,
}: Props) {
  return (
    <div className="report-grid">
      <div>
        <section className="card decision-card">
          <div className="card-top">
            <div className={`icon-box ${report.status === 'blocked' ? 'amber' : 'green'}`}>
              <Workflow size={22} />
            </div>
            <span className="eyebrow">COORDINATOR'S DECISION</span>
          </div>
          <h2>{report.decision.headline}</h2>
          <p className="muted">
            {report.decision.blockers.length
              ? 'The estimate is prepared. These constraints need a decision before the project can be approved.'
              : 'Material and schedule checks pass under the demo assumptions. Complete the human review before accepting the estimate.'}
          </p>
          {report.decision.blockers.length > 0 && (
            <ul className="blocker-list">
              {report.decision.blockers.map((item) => (
                <li key={item}>
                  <CircleAlert size={17} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="subheading">RECOMMENDED NEXT STEPS</div>
          <ol className="action-list">
            {report.decision.actions.map((item, i) => (
              <li key={item}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                {item}
              </li>
            ))}
          </ol>
          {executionSourceIssue && (
            <div className="inline-warning">
              <CircleAlert size={16} />
              {executionSourceIssue}
            </div>
          )}
          {executionSourceIssue && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void prepareFreshQuotation()}
            >
              Create fresh quotation <ArrowRight size={16} />
            </button>
          )}
          {report.approval ? (
            <div className="approved-note">
              <CheckCircle2 size={18} />
              <span>
                Demo estimate approved by {report.approval.reviewer}. Post-approval actions are
                tracked in the Work order tab.
              </span>
            </div>
          ) : (
            <div className="approval-footer">
              <span>
                <ShieldCheck size={16} /> Human review gate
              </span>
              <button
                className="button primary"
                disabled={report.status === 'blocked' || busy || !!executionSourceIssue}
                onClick={() => setApproving(true)}
              >
                Review estimate <ArrowRight size={16} />
              </button>
            </div>
          )}
        </section>
        <section className="card findings-preview">
          <div className="section-heading">
            <h3>Specialist findings</h3>
            <button className="text-link" onClick={() => setTab('agents')}>
              View evidence <ArrowRight size={15} />
            </button>
          </div>
          {report.traces.slice(0, 3).map((item) => (
            <div className="finding-row" key={item.agent}>
              <span className="finding-dot" />
              <div>
                <h4>{item.agent}</h4>
                <p>{item.summary}</p>
              </div>
            </div>
          ))}
        </section>
      </div>
      <div>
        <section className="card material-card">
          <div className="section-heading">
            <h3>Material intelligence</h3>
            <Package size={18} />
          </div>
          <div className={`fabric-swatch ${report.request.fabric_id}`} />
          <h4>{report.materials.fabric.name}</h4>
          <p className="muted">
            {report.materials.fabric.color} · {report.materials.fabric.sku}
          </p>
          <div className="stock-row">
            <span>Required</span>
            <strong>{report.materials.required_lm} lm</strong>
          </div>
          <div className="stock-row">
            <span>Recorded available</span>
            <strong>{report.materials.fabric.stock_lm} lm</strong>
          </div>
          <div className="stock-track">
            <span
              style={{
                width: `${Math.min(100, (report.materials.fabric.stock_lm / report.materials.required_lm) * 100)}%`,
              }}
            />
          </div>
          <p className="stock-note">
            {report.materials.waste_percent ??
              (report.data_snapshot?.policy.waste_fraction ?? 0.08) * 100}
            % waste allowance included · Snapshot at analysis
          </p>
          {report.materials.alternatives.length > 0 && !report.materials.in_stock && (
            <div className="alternative">
              <span className="eyebrow">AVAILABLE ALTERNATIVE</span>
              {report.materials.alternatives.map((item) => (
                <div key={item.id}>
                  <h4>{item.name}</h4>
                  <p>{item.reason}</p>
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() =>
                      void analyze(undefined, {
                        ...report.request,
                        fabric_id: item.id,
                      })
                    }
                  >
                    Use & re-analyze <ArrowRight size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="card scope-card">
          <h3>Project specification</h3>
          <dl>
            <dt>Product</dt>
            <dd>{report.requirements.product_name}</dd>
            <dt>Opening size</dt>
            <dd>{report.requirements.dimensions}</dd>
            <dt>Total coverage</dt>
            <dd>{report.requirements.area_sqm} m²</dd>
            <dt>Requested completion</dt>
            <dd>{day(report.request.due_date)}</dd>
            <dt>Scope</dt>
            <dd>{report.requirements.scope}</dd>
          </dl>
          <p className="fine-print">
            Form fields drive calculations. Brief text supplies context; measurements are
            provisional.
          </p>
        </section>
      </div>
    </div>
  )
}
