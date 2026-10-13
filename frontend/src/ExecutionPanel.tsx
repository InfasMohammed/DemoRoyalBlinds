import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { CalendarDays, CheckCircle2, CircleAlert, ClipboardCheck, Factory, LoaderCircle, Package, RefreshCw } from 'lucide-react'
import { api } from './api'
import type { Report, WorkAction } from './types'

const labels: Record<string, string> = {
  planned: 'Ready for production', in_production: 'In production', awaiting_quality: 'Awaiting quality checks',
  ready_for_installation: 'Ready for installation', completed: 'Completed', cancelled: 'Cancelled',
}
const actions: Record<string, { action: WorkAction; label: string }[]> = {
  planned: [{ action: 'start_production', label: 'Start production' }],
  in_production: [{ action: 'finish_production', label: 'Record manufacturing complete' }],
  awaiting_quality: [{ action: 'pass_quality', label: 'Pass quality checks' }, { action: 'fail_quality', label: 'Record quality issue' }],
  ready_for_installation: [{ action: 'complete_installation', label: 'Record installation complete' }],
}
const day = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString('en-GB')

export default function ExecutionPanel({ report, onUpdate }: { report: Report; onUpdate: (report: Report) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [action, setAction] = useState<{ action: WorkAction; label: string } | null>(null)
  const [checked, setChecked] = useState<string[]>([])
  const execution = report.execution
  const order = execution?.work_order
  const quality = execution?.tasks.filter(t => t.stage === 'quality') || []

  useEffect(() => {
    if (execution?.status !== 'queued') return
    let active = true
    const timer = window.setInterval(() => {
      void api<Report>(`/projects/${report.id}`).then(value => { if (active) onUpdate(value) }).catch(err => { if (active) setError(err.message) })
    }, 2000)
    return () => { active = false; window.clearInterval(timer) }
  }, [report.id, execution?.status, onUpdate])

  async function retry() {
    setBusy(true); setError('')
    try { onUpdate(await api<Report>(`/projects/${report.id}/execute`, { method: 'POST' })) }
    catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!action) return
    const form = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      const value = await api<Report>(`/projects/${report.id}/work-order/actions`, { method: 'POST', body: JSON.stringify({
        action: action.action, actor: form.get('actor'), note: form.get('note'), checked_ids: checked,
      }) })
      onUpdate(value); setAction(null); setChecked([])
    } catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  if (!execution) return <section className="card execution-panel"><ClipboardCheck size={24} /><h3>Human approval opens the next stage.</h3><p>{report.status === 'demo_approved' ? 'This report was approved before execution was available. Analyze and approve a new project to create a work order.' : 'Approve the quotation and authorize demo actions to reserve material, book capacity and create work-order tasks.'}</p></section>

  return <section className="card execution-panel">
    <div className="section-heading"><div><span className="eyebrow">POST-APPROVAL WORKFLOW</span><h3>Work order & execution</h3></div><span className={`pill ${execution.status === 'blocked' || quality.some(t => t.status === 'failed') ? 'amber' : 'green'}`}>{order ? quality.some(t => t.status === 'failed') ? 'Quality hold' : labels[order.status] : execution.status === 'queued' ? 'Queued for execution' : 'Needs attention'}</span></div>
    {error && <div className="inline-warning" role="alert"><CircleAlert size={16} />{error}</div>}
    {execution.reason && <div className="inline-warning"><CircleAlert size={16} />{execution.reason}</div>}
    {!order && <div className="execution-pending"><p>{execution.status === 'queued' ? 'Approval is stored. The worker will recover this job if the backend restarts.' : 'Approval is recorded; actions stopped before resources were committed. Resolve the issue, then retry. Changed quote terms require a fresh analysis and approval.'}</p><button className="button secondary" disabled={busy} onClick={() => void retry()}>{busy ? <LoaderCircle size={16} className="spin" /> : <RefreshCw size={16} />}Retry execution</button></div>}
    {order && <>
      <p className="muted">Work order {order.id.slice(0, 8)} · {report.request.quantity} {report.requirements.product_name.toLowerCase()} · {report.request.site}</p>
      <div className="execution-summary"><div><Package size={18} /><span>Material {execution.reservation?.status === 'active' ? 'reserved' : execution.reservation?.status}</span><strong>{execution.reservation?.quantity_lm} lm</strong></div><div><Factory size={18} /><span>Booked manufacturing</span><strong>{day(order.production_plan.manufacture_start)} – {day(order.production_plan.manufacture_end)}</strong></div><div><CalendarDays size={18} /><span>Booked completion</span><strong>{day(order.production_plan.completion_date)}</strong></div></div>
      <div className="execution-actions">{(actions[order.status] || []).map(item => <button className="button primary" key={item.action} disabled={busy} onClick={() => { setAction(item); setChecked([]); setError('') }}>{item.label}</button>)}{['planned', 'awaiting_quality', 'ready_for_installation'].includes(order.status) && <button className="button secondary" disabled={busy} onClick={() => { setAction({ action: 'cancel', label: 'Cancel work order' }); setChecked([]); setError('') }}>Cancel work order</button>}</div>
      {action && <form className="execution-form" onSubmit={event => void submit(event)}><h4>{action.label}</h4><label>Operator name<input name="actor" required minLength={2} maxLength={100} defaultValue={report.approval?.reviewer || ''} /></label><label>Progress note<textarea name="note" rows={2} maxLength={1000} minLength={['cancel', 'fail_quality'].includes(action.action) ? 5 : undefined} required={['cancel', 'fail_quality'].includes(action.action)} /></label>{action.action === 'pass_quality' && <div className="approval-checks">{quality.map(task => <label key={task.id}><input type="checkbox" required checked={checked.includes(task.id)} onChange={e => setChecked(values => e.target.checked ? [...values, task.id] : values.filter(id => id !== task.id))} />{task.description}</label>)}</div>}<label className="execution-confirm"><input type="checkbox" required />{action.action === 'finish_production' ? 'I confirm manufacturing is finished and authorize consuming the reserved demo material.' : 'I confirm this demo progress record is accurate.'}</label><div className="modal-actions"><button type="button" className="button secondary" onClick={() => setAction(null)}>Close action</button><button className="button primary" disabled={busy || action.action === 'pass_quality' && checked.length !== quality.length}>{busy ? 'Recording…' : `Confirm ${action.label.toLowerCase()}`}</button></div></form>}
      <div className="execution-tasks"><h4>Manufacturing, quality & installation tasks</h4>{execution.tasks.map(task => <div className="execution-task" key={task.id}><span className={`pill ${task.status === 'failed' ? 'amber' : 'neutral'}`}>{task.status.replaceAll('_', ' ')}</span><div><small>{task.stage}</small><p>{task.description}</p></div></div>)}</div>
      <details className="execution-bookings"><summary>Inspect booked capacity</summary><div className="table-scroll"><table><thead><tr><th>Stage</th><th>Date</th><th>Hours</th><th>Status</th></tr></thead><tbody>{execution.bookings.map((booking, i) => <tr key={i}><td>{booking.stage}</td><td>{day(booking.work_date)}</td><td>{booking.hours}</td><td>{booking.released ? 'Released' : 'Allocated'}</td></tr>)}</tbody></table></div></details>
    </>}
    <div className="execution-findings"><h4>Agent handoffs</h4>{execution.agent_findings.map(item => <p key={item.agent}><strong>{item.agent}</strong> · {item.summary}</p>)}</div>
    <div className="execution-events"><h4>Activity log</h4>{execution.events.map(item => <div key={item.id}><CheckCircle2 size={15} /><div><strong>{item.event_type.replaceAll('_', ' ')}</strong><p>{item.detail}</p><small>{item.actor} · {new Date(item.created_at).toLocaleString('en-GB', { timeZone: 'Asia/Dubai' })} Dubai time</small></div></div>)}</div>
    <p className="fine-print">These actions update the interview database. Operators record actual demo progress; no machinery, purchasing or external messaging is connected. Cancelling before production releases material; consumed material is retained in the audit.</p>
  </section>
}
