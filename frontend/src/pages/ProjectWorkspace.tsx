import {
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Download,
  FileText,
  Package,
  Printer,
  ShieldCheck,
} from 'lucide-react'
import type { FormEvent } from 'react'
import type { ProjectInput, Report } from '../types'
import Metric from '../components/common/Metric'
import ExecutionPanel from '../features/execution/ExecutionPanel'
import ReportOverview from '../components/reports/ReportOverview'
import ReportAgents from '../components/reports/ReportAgents'
import ReportQuotation from '../components/reports/ReportQuotation'
import ReportDelivery from '../components/reports/ReportDelivery'
import { money, day, modeLabel, statusLabel } from '../lib/format'
import { reportTabs } from '../lib/navigation'
import type { ReportTab } from '../lib/navigation'

type Props = {
  report: Report
  tab: ReportTab
  busy: boolean
  expanded: string | null
  executionSourceIssue: string | null
  setTab: (tab: ReportTab) => void
  setInput: (input: ProjectInput) => void
  setEditing: (editing: boolean) => void
  setApproving: (approving: boolean) => void
  setExpanded: (expanded: string | null) => void
  analyze: (event?: FormEvent, replacement?: ProjectInput) => Promise<void>
  prepareFreshQuotation: () => Promise<void>
  updateExecution: (report: Report) => void
  download: () => void
}

export default function ProjectWorkspace({
  report,
  tab,
  busy,
  expanded,
  executionSourceIssue,
  setTab,
  setInput,
  setEditing,
  setApproving,
  setExpanded,
  analyze,
  prepareFreshQuotation,
  updateExecution,
  download,
}: Props) {
  return (
    <>
      <section className="project-bar card">
        <div>
          <div className="eyebrow">PROJECT {report.id.slice(0, 8).toUpperCase()}</div>
          <h2>{report.request.project_name}</h2>
          <p>
            {report.request.customer}
            <span>·</span>
            {report.request.site}
            <span>·</span>
            {report.requirements.quantity} openings
          </p>
        </div>
        <div className="project-controls no-print">
          <span className={`pill ${report.status === 'blocked' ? 'amber' : 'green'}`}>
            {report.status === 'blocked' ? <CircleAlert size={13} /> : <CheckCircle2 size={13} />}
            {statusLabel(report.status)}
          </span>
          <button
            className="icon-button"
            title="Download report JSON"
            aria-label="Download report JSON"
            onClick={download}
          >
            <Download size={18} />
          </button>
          <button
            className="icon-button"
            title="Print current report view"
            aria-label="Print current report view"
            onClick={() => window.print()}
          >
            <Printer size={18} />
          </button>
          <button
            className="button secondary"
            onClick={() => {
              setInput(report.request)
              setEditing(true)
            }}
            disabled={busy}
          >
            Revise brief
          </button>
        </div>
      </section>
      <div className="metrics">
        <Metric
          icon={FileText}
          label="ILLUSTRATIVE ESTIMATE"
          value={`AED ${money(report.costing.total)}`}
          detail={`Incl. ${report.costing.vat_percent ?? 5}% VAT · ${money(report.costing.per_unit_incl_vat)} / unit`}
        />
        <Metric
          icon={Package}
          label="FABRIC REQUIREMENT"
          value={`${report.materials.required_lm} lm`}
          detail={
            report.materials.in_stock
              ? 'Covered by recorded stock'
              : `${report.materials.shortage_lm} lm shortfall`
          }
          alert={!report.materials.in_stock}
        />
        <Metric
          icon={CalendarDays}
          label="ESTIMATED COMPLETION"
          value={day(report.production.completion_date)}
          detail={
            report.production.on_time
              ? `${report.production.slack_days} calendar days before deadline`
              : `${Math.abs(report.production.slack_days)} calendar days beyond deadline`
          }
          alert={!report.production.on_time}
        />
        <Metric
          icon={ShieldCheck}
          label="REVIEW GATES"
          value={
            report.decision.blockers.length
              ? `${report.decision.blockers.length} to resolve`
              : 'Ready for review'
          }
          detail={
            report.data_snapshot?.data_source === 'supabase'
              ? 'Supabase data · Human approval required'
              : 'Human approval required'
          }
          alert={report.decision.blockers.length > 0}
        />
      </div>
      <div className="tabs no-print" role="tablist" aria-label="Project report sections">
        {reportTabs.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? 'active' : ''}
            onClick={() => setTab(item.id)}
          >
            {item.label}
            {item.id === 'agents' && <span>6</span>}
          </button>
        ))}
        <div className="tabs-meta">
          {modeLabel(report.reasoning_mode)}
          <span>·</span>
          {(report.elapsed_ms / 1000).toFixed(2)} s
        </div>
      </div>
      {tab === 'overview' && (
        <ReportOverview
          report={report}
          busy={busy}
          executionSourceIssue={executionSourceIssue}
          setTab={setTab}
          setApproving={setApproving}
          analyze={analyze}
          prepareFreshQuotation={prepareFreshQuotation}
        />
      )}
      {tab === 'execution' && (
        <ExecutionPanel
          report={report}
          onUpdate={updateExecution}
          sourceIssue={executionSourceIssue}
          onReanalyze={() => void prepareFreshQuotation()}
          reanalyzeDisabled={busy}
        />
      )}
      {tab === 'agents' && (
        <ReportAgents report={report} expanded={expanded} setExpanded={setExpanded} />
      )}
      {tab === 'quote' && <ReportQuotation report={report} />}
      {tab === 'delivery' && <ReportDelivery report={report} />}
    </>
  )
}
