import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowDown, ArrowRight, ArrowUpRight, BadgeCheck, Box, CalendarDays, Check,
  CheckCircle2, ChevronDown, ChevronRight, CircleAlert, ClipboardCheck, Download, Factory,
  BookOpen, FileText, Layers3, LayoutDashboard, LoaderCircle, Package, Plus, Printer, ScanLine,
  Settings2, ShieldCheck, Sparkles, Workflow, X } from 'lucide-react'
import { api } from './api'
import KnowledgeStudio from './KnowledgeStudio'
import ExecutionPanel from './ExecutionPanel'
import type { Catalog, Health, ProjectInput, Report } from './types'

const money = (value: number) => new Intl.NumberFormat('en-AE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
const day = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
function after(start: string, count: number) {
  const value = new Date(`${start}T12:00:00Z`); value.setUTCDate(value.getUTCDate() + count)
  return value.toISOString().slice(0, 10)
}
const statusLabel = (status: Report['status']) => ({ blocked: 'Needs attention', awaiting_review: 'Awaiting review', demo_approved: 'Demo approved' })[status]
const modeLabel = (mode: string) => ({ rule_based_demo: 'Rule-based demo', live_ai: 'Live AI', ai_with_fallback: 'AI with fallback', live_ai_configured: 'AI configured' })[mode] || mode
const agents = [
  { name: 'Specification', desc: 'Scope & dimensions', icon: ScanLine },
  { name: 'Inventory', desc: 'Yield & availability', icon: Package },
  { name: 'Quality', desc: 'Limits & inspections', icon: ShieldCheck },
  { name: 'Quotation', desc: 'Costs & gross margin', icon: FileText },
  { name: 'Production', desc: 'Capacity & scheduling', icon: Factory },
  { name: 'Coordinator', desc: 'Decision & review', icon: Workflow },
]

function seed(today: string, catalog: Catalog, scenario = 'shortage'): ProjectInput {
  const preset = catalog.scenarios.find(item => item.id === scenario) || catalog.scenarios[0]
  if (preset) return { ...preset.request, due_date: after(today, preset.deadline_days) }
  const product = Object.keys(catalog.products)[0]
  const fabric = catalog.fabrics.find(item => item.compatible.includes(product)) || catalog.fabrics[0]
  return { customer: '', project_name: '', brief: '', site: '', product, fabric_id: fabric.id,
    quantity: 1, width_m: 1, height_m: 1, due_date: today }
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [reports, setReports] = useState<Report[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [page, setPage] = useState('workspace')
  const [tab, setTab] = useState('overview')
  const [input, setInput] = useState<ProjectInput | null>(null)
  const [editing, setEditing] = useState(false)
  const [approving, setApproving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  async function load() {
    setError('')
    const results = await Promise.allSettled([api<Health>('/health'), api<Catalog>('/catalog'), api<Report[]>('/projects')])
    const failures: string[] = []
    if (results[0].status === 'fulfilled') { const runtime = results[0].value; setHealth(runtime) }
    else { setHealth(null); failures.push(results[0].reason.message) }
    if (results[1].status === 'fulfilled') setCatalog(results[1].value)
    else { setCatalog(null); failures.push(results[1].reason.message) }
    if (results[2].status === 'fulfilled') setReports(results[2].value)
    else failures.push(results[2].reason.message)
    if (results[0].status === 'fulfilled' && results[1].status === 'fulfilled') {
      const runtime = results[0].value, business = results[1].value
      setInput(current => current || seed(runtime.today, business))
    }
    if (failures.length) setError([...new Set(failures)].join(' '))
  }
  useEffect(() => { void load() }, [])

  useEffect(() => {
    if (!editing && !approving) return
    const previous = document.activeElement as HTMLElement | null
    const modal = document.querySelector<HTMLElement>('.modal')
    const elements = () => Array.from(modal?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select, textarea, [tabindex="0"]') || [])
    elements()[0]?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) { setEditing(false); setApproving(false) }
      if (event.key !== 'Tab') return
      const focusable = elements(), first = focusable[0], last = focusable.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = overflow; previous?.focus() }
  }, [editing, approving, busy])

  function newProject(scenario = 'shortage') {
    if (!health || !catalog) return
    setInput(seed(health.today, catalog, scenario)); setEditing(true); setError('')
  }
  async function analyze(event?: FormEvent, replacement?: ProjectInput) {
    event?.preventDefault()
    const payload = replacement || input
    if (!payload) return
    setBusy(true); setError(''); setEditing(false)
    try {
      const result = await api<Report>('/projects/analyze', { method: 'POST', body: JSON.stringify(payload) })
      setReport(result); setInput(payload); setReports(current => [result, ...current].slice(0, 50)); setPage('workspace'); setTab('overview')
    } catch (err) { setError((err as Error).message); setEditing(true) }
    finally { setBusy(false) }
  }
  function openReport(value: Report) {
    setReport(value); setInput(value.request); setPage('workspace'); setTab('overview'); setError('')
  }
  function download() {
    if (!report) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `royal-blinds-demo-${report.id.slice(0, 8)}.json`; anchor.click(); URL.revokeObjectURL(url)
  }
  async function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!report) return
    const form = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      const result = await api<Report>(`/projects/${report.id}/approve`, { method: 'POST', body: JSON.stringify({
        reviewer: form.get('reviewer'), measurements_confirmed: form.get('measurements') === 'on',
        specification_confirmed: form.get('specification') === 'on', commercial_terms_confirmed: form.get('commercial') === 'on',
        execution_confirmed: form.get('execution') === 'on',
      }) })
      setReport(result); setReports(current => current.map(item => item.id === result.id ? result : item)); setApproving(false); setTab('execution')
    } catch (err) { setError((err as Error).message) }
    finally { setBusy(false) }
  }

  const updateExecution = useCallback((value: Report) => {
    setReport(current => current?.id === value.id ? value : current)
    setReports(current => current.map(item => item.id === value.id ? value : item))
  }, [])

  return <div className="app-shell">
    <aside className="sidebar no-print">
      <a className="brand" href="#" onClick={event => { event.preventDefault(); setPage('workspace') }} aria-label="Royal Blinds home">
        <picture className="brand-picture">
          <source media="(max-width: 980px)" srcSet="/brand/royal-blinds-icon.png" />
          <img className="brand-logo" src="/brand/royal-blinds-logo.png" alt="Royal Blinds" width="749" height="290" />
        </picture>
        <span className="brand-caption">OPERATIONS STUDIO</span>
      </a>
      <div className="workspace-label">WORKSPACE <span>DEMO</span></div>
      <nav aria-label="Main navigation">
        {[{ id: 'workspace', name: 'Project studio', icon: LayoutDashboard }, { id: 'knowledge', name: 'Product knowledge', icon: BookOpen }, { id: 'projects', name: 'Project reports', icon: Layers3 },
          { id: 'inventory', name: 'Material library', icon: Box }, { id: 'workflow', name: 'Agent workflow', icon: Workflow }].map(item =>
          <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => setPage(item.id)}>
            <item.icon size={19} />{item.name}{item.id === 'projects' && <span className="nav-count">{reports.length}</span>}
          </button>)}
      </nav>
      <div className="sidebar-callout"><Sparkles size={21} /><h4>Built for better decisions.</h4>
        <p>Six specialists. One clear plan. A human stays in control.</p><button onClick={() => setPage('workflow')}>Explore the workflow <ArrowUpRight size={15} /></button></div>
      <div className="sidebar-bottom"><span className="avatar"><img src="/brand/royal-blinds-icon.png" alt="" width="22" height="22" /></span><div>Interview demonstration<small>Synthetic factory data</small></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar no-print"><div className="breadcrumb">Operations <ChevronRight size={14} /><strong>{({ workspace: 'Project studio', knowledge: 'Product knowledge', projects: 'Project reports', inventory: 'Material library', workflow: 'Agent workflow' } as Record<string, string>)[page]}</strong></div>
        <div className="topbar-right"><span className={`connection ${health ? '' : 'offline'}`}><i />{health ? 'Backend connected' : 'Connecting'}</span><span className="topbar-divider" /><span className="location">Dubai, UAE</span><span className="small-avatar"><img src="/brand/royal-blinds-icon.png" alt="" width="23" height="23" /></span></div>
      </header>
      <main>
        {error && <div role="alert" className="error-banner no-print"><CircleAlert size={18} /><span>{error}</span><button onClick={() => void load()}>Retry connection</button><button aria-label="Dismiss error" onClick={() => setError('')}><X size={16} /></button></div>}
        <div className="page-heading no-print"><div><div className="eyebrow">MANUFACTURING INTELLIGENCE</div><h1>{({ workspace: 'From brief to better execution.', knowledge: 'Product expertise, with evidence.', projects: 'Every project. Every decision.', inventory: 'The right material, in view.', workflow: 'A team of focused specialists.' } as Record<string, string>)[page]}</h1>
          <p>{({ workspace: 'Plan blinds and curtains with a transparent, coordinated workflow.', knowledge: 'Explore the complete supplied portfolio and retrieve source-linked answers.', projects: 'Revisit saved estimates, evidence and review decisions.', inventory: 'Material availability, recorded costs and supplier lead times.', workflow: 'See how LangGraph connects calculations, evidence and human review.' } as Record<string, string>)[page]}</p></div>
          <button className="button primary" onClick={() => newProject()} disabled={!health || !catalog || busy}><Plus size={17} />New project</button>
        </div>
        <div className="demo-strip no-print"><span><span className="pill neutral">INTERVIEW DEMO</span>{catalog?.is_sample === false ? 'Configured business records. Human review required.' : 'Sample inventory, rates and capacity.'}</span><span>{catalog?.data_source === 'supabase' ? 'Supabase business data' : 'Offline demo data'}<span className="dot-separator">·</span>{health ? modeLabel(health.reasoning_mode) : 'Checking runtime'}<span className="dot-separator">·</span>{health ? health.storage_mode === 'supabase' ? 'Supabase storage' : 'Local demo storage' : 'Storage unverified'}</span></div>

        {page === 'knowledge' && <KnowledgeStudio quoteReady={!!health && !!catalog && !busy} onQuote={product => {
          if (!health || !catalog) return
          const next = seed(health.today, catalog, 'ready')
          setInput({ ...next, product, brief: `Supply and install ${catalog.products[product]?.name || product}. Confirm the fabric sample, measurements and delivery before approval.` })
          setEditing(true)
        }} />}

        {page === 'workspace' && (!report ? <>
          <section className="hero card"><div className="hero-copy"><span className="pill green"><Sparkles size={13} /> YOUR OPERATIONS COPILOT</span><h2>One customer brief.<br /><em>A complete project picture.</em></h2>
            <p>Check the fabric. Build the estimate. Understand the timeline. Let six specialists connect the details before you commit.</p>
            <button className="button primary" disabled={!catalog || !health || busy} onClick={() => newProject()}>Create a project brief <ArrowRight size={17} /></button>
            <div className="hero-footnote"><ShieldCheck size={15} /> Evidence at every step. Approval in your hands.</div></div>
            <div className="hero-visual" aria-label="Illustration of roller blinds"><div className="window-frame"><div className="blinds"><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /></div><div className="window-light" /><div className="window-pull" /></div>
              <div className="floating-card"><span className="floating-icon"><Check size={18} /></span><div>Clarity before commitment<small>Material · Cost · Delivery</small></div></div><span className="visual-caption">DESIGNED FOR YOUR WORKFLOW</span></div>
          </section>
          <section className="card portfolio-callout"><BookOpen size={24} /><div><h3>Internal. External. Smart.</h3><p>Explore the supplied product range and automation options with source-linked company knowledge.</p></div><button className="button secondary" onClick={() => setPage('knowledge')}>Explore products <ArrowUpRight size={16} /></button></section>
          <div className="section-heading"><h3>Try a manufacturing scenario</h3><span>Start with a brief. See the decisions.</span></div>
          <div className="scenario-grid">{catalog?.scenarios.map(item => {
            const Icon = item.id === 'rush' ? CalendarDays : item.id === 'ready' ? BadgeCheck : Package
            const color = item.id === 'rush' ? 'blue' : item.id === 'ready' ? 'green' : 'amber'
            return <button key={item.id} className="scenario card" disabled={!health || busy} onClick={() => newProject(item.id)}>
            <div className={`icon-box ${color}`}><Icon size={21} /></div><div className="eyebrow">{item.category}</div><h3>{item.title}</h3><p>{item.description}</p><span className="text-link">Open scenario <ArrowUpRight size={16} /></span>
          </button>})}</div>
          <section className="card workflow-preview"><div className="section-heading"><div><span className="eyebrow">COORDINATED BY LANGGRAPH</span><h3>Expertise, connected.</h3></div><button className="text-link" onClick={() => setPage('workflow')}>View workflow <ArrowRight size={15} /></button></div><AgentStrip /></section>
        </> : <>
          <section className="project-bar card"><div><div className="eyebrow">PROJECT {report.id.slice(0, 8).toUpperCase()}</div><h2>{report.request.project_name}</h2><p>{report.request.customer}<span>·</span>{report.request.site}<span>·</span>{report.requirements.quantity} openings</p></div>
            <div className="project-controls no-print"><span className={`pill ${report.status === 'blocked' ? 'amber' : 'green'}`}>{report.status === 'blocked' ? <CircleAlert size={13} /> : <CheckCircle2 size={13} />}{statusLabel(report.status)}</span><button className="icon-button" title="Download report JSON" aria-label="Download report JSON" onClick={download}><Download size={18} /></button><button className="icon-button" title="Print current report view" aria-label="Print current report view" onClick={() => window.print()}><Printer size={18} /></button><button className="button secondary" onClick={() => { setInput(report.request); setEditing(true) }} disabled={busy}>Revise brief</button></div>
          </section>
          <div className="metrics">
            <Metric icon={FileText} label="ILLUSTRATIVE ESTIMATE" value={`AED ${money(report.costing.total)}`} detail={`Incl. ${report.costing.vat_percent ?? 5}% VAT · ${money(report.costing.per_unit_incl_vat)} / unit`} />
            <Metric icon={Package} label="FABRIC REQUIREMENT" value={`${report.materials.required_lm} lm`} detail={report.materials.in_stock ? 'Covered by recorded stock' : `${report.materials.shortage_lm} lm shortfall`} alert={!report.materials.in_stock} />
            <Metric icon={CalendarDays} label="ESTIMATED COMPLETION" value={day(report.production.completion_date)} detail={report.production.on_time ? `${report.production.slack_days} calendar days before deadline` : `${Math.abs(report.production.slack_days)} calendar days beyond deadline`} alert={!report.production.on_time} />
            <Metric icon={ShieldCheck} label="REVIEW GATES" value={report.decision.blockers.length ? `${report.decision.blockers.length} to resolve` : 'Ready for review'} detail={report.data_snapshot?.data_source === 'supabase' ? 'Supabase data · Human approval required' : 'Human approval required'} alert={report.decision.blockers.length > 0} />
          </div>
          <div className="tabs no-print" role="tablist" aria-label="Project report sections">{[{ id: 'overview', label: 'Overview' }, { id: 'agents', label: 'Agent findings' }, { id: 'quote', label: 'Quotation' }, { id: 'delivery', label: 'Production & quality' }, { id: 'execution', label: 'Work order' }].map(item =>
            <button key={item.id} role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}>{item.label}{item.id === 'agents' && <span>6</span>}</button>)}<div className="tabs-meta">{modeLabel(report.reasoning_mode)}<span>·</span>{(report.elapsed_ms / 1000).toFixed(2)} s</div></div>
          {tab === 'overview' && <div className="report-grid"><div>
            <section className="card decision-card"><div className="card-top"><div className={`icon-box ${report.status === 'blocked' ? 'amber' : 'green'}`}><Workflow size={22} /></div><span className="eyebrow">COORDINATOR'S DECISION</span></div><h2>{report.decision.headline}</h2><p className="muted">{report.decision.blockers.length ? 'The estimate is prepared. These constraints need a decision before the project can be approved.' : 'Material and schedule checks pass under the demo assumptions. Complete the human review before accepting the estimate.'}</p>
              {report.decision.blockers.length > 0 && <ul className="blocker-list">{report.decision.blockers.map(item => <li key={item}><CircleAlert size={17} /><span>{item}</span></li>)}</ul>}
              <div className="subheading">RECOMMENDED NEXT STEPS</div><ol className="action-list">{report.decision.actions.map((item, i) => <li key={item}><span>{String(i + 1).padStart(2, '0')}</span>{item}</li>)}</ol>
              {report.approval ? <div className="approved-note"><CheckCircle2 size={18} /><span>Demo estimate approved by {report.approval.reviewer}. Post-approval actions are tracked in the Work order tab.</span></div> : <div className="approval-footer"><span><ShieldCheck size={16} /> Human review gate</span><button className="button primary" disabled={report.status === 'blocked' || busy} onClick={() => setApproving(true)}>Review estimate <ArrowRight size={16} /></button></div>}
            </section>
            <section className="card findings-preview"><div className="section-heading"><h3>Specialist findings</h3><button className="text-link" onClick={() => setTab('agents')}>View evidence <ArrowRight size={15} /></button></div>{report.traces.slice(0, 3).map(item => <div className="finding-row" key={item.agent}><span className="finding-dot" /><div><h4>{item.agent}</h4><p>{item.summary}</p></div></div>)}</section>
          </div><div>
            <section className="card material-card"><div className="section-heading"><h3>Material intelligence</h3><Package size={18} /></div><div className={`fabric-swatch ${report.request.fabric_id}`} /><h4>{report.materials.fabric.name}</h4><p className="muted">{report.materials.fabric.color} · {report.materials.fabric.sku}</p><div className="stock-row"><span>Required</span><strong>{report.materials.required_lm} lm</strong></div><div className="stock-row"><span>Recorded available</span><strong>{report.materials.fabric.stock_lm} lm</strong></div><div className="stock-track"><span style={{ width: `${Math.min(100, report.materials.fabric.stock_lm / report.materials.required_lm * 100)}%` }} /></div><p className="stock-note">{report.materials.waste_percent ?? (report.data_snapshot?.policy.waste_fraction ?? 0.08) * 100}% waste allowance included · Snapshot at analysis</p>
              {report.materials.alternatives.length > 0 && !report.materials.in_stock && <div className="alternative"><span className="eyebrow">AVAILABLE ALTERNATIVE</span>{report.materials.alternatives.map(item => <div key={item.id}><h4>{item.name}</h4><p>{item.reason}</p><button className="button secondary" disabled={busy} onClick={() => void analyze(undefined, { ...report.request, fabric_id: item.id })}>Use & re-analyze <ArrowRight size={15} /></button></div>)}</div>}
            </section>
            <section className="card scope-card"><h3>Project specification</h3><dl><dt>Product</dt><dd>{report.requirements.product_name}</dd><dt>Opening size</dt><dd>{report.requirements.dimensions}</dd><dt>Total coverage</dt><dd>{report.requirements.area_sqm} m²</dd><dt>Requested completion</dt><dd>{day(report.request.due_date)}</dd><dt>Scope</dt><dd>{report.requirements.scope}</dd></dl><p className="fine-print">Form fields drive calculations. Brief text supplies context; measurements are provisional.</p></section>
          </div></div>}
          {tab === 'execution' && <ExecutionPanel report={report} onUpdate={updateExecution} />}
          {tab === 'agents' && <section className="card agent-findings"><div className="section-heading"><div><span className="eyebrow">TRACEABLE EXECUTION</span><h3>What each specialist found</h3></div><span className="pill neutral">{modeLabel(report.reasoning_mode)}</span></div><p className="muted">Validated tools control numbers and approval gates. Optional AI explains the findings using the supplied evidence.</p>{report.traces.map((item, i) => {
            const Icon = agents.find(a => item.agent.startsWith(a.name))?.icon || Workflow
            return <article className="trace-card" key={item.agent}><div className="trace-index">{String(i + 1).padStart(2, '0')}</div><div className="trace-content"><div className="trace-heading"><h3><Icon size={19} />{item.agent}</h3><span className={`pill ${item.mode === 'rules_fallback' ? 'amber' : 'neutral'}`}>{item.mode === 'llm' ? 'AI + tools' : item.mode === 'rules_fallback' ? 'Rules · AI unavailable' : 'Validated rules'}</span></div><div className="trace-role">{item.role} · {item.duration_ms} ms</div><p>{item.summary}</p>{item.fallback_reason && <div className="inline-warning"><CircleAlert size={16} />{item.fallback_reason}</div>}{item.recommendation && <p className="recommendation">{item.recommendation}</p>}<div className="source-tags">{item.sources.map(source => <span key={source}><FileText size={12} />{source}</span>)}</div>{item.citations && item.citations.length > 0 && <div className="trace-citations">{item.citations.map(citation => <a href={citation.source_url} key={citation.id} target="_blank" rel="noopener noreferrer"><BookOpen size={12} />{citation.heading}<ArrowUpRight size={12} /></a>)}</div>}<button className="text-link evidence-toggle" aria-expanded={expanded === item.agent} onClick={() => setExpanded(expanded === item.agent ? null : item.agent)}>Inspect tool evidence <ChevronDown size={15} /></button>{expanded === item.agent && <pre className="evidence">{JSON.stringify(item.facts, null, 2)}</pre>}</div></article>
          })}</section>}
          {tab === 'quote' && <div className="report-grid quote-grid"><section className="card quote-card"><div className="section-heading"><div><span className="eyebrow">DRAFT · ILLUSTRATIVE RATES</span><h3>Transparent project estimate</h3></div><button className="icon-button no-print" aria-label="Print quotation" onClick={() => window.print()}><Printer size={18} /></button></div>{!report.costing.valid && <div className="inline-warning"><CircleAlert size={16} /> Invalid specification: these costs are indicative only.</div>}<div className="table-scroll"><table><thead><tr><th>Cost component</th><th>Quantity</th><th>Rate (AED)</th><th>Cost (AED)</th></tr></thead><tbody>{report.costing.lines.map(line => <tr key={line.description}><td>{line.description}</td><td>{line.quantity} {line.unit}</td><td>{money(line.unit_cost)}</td><td>{money(line.cost)}</td></tr>)}</tbody></table></div><div className="quote-totals"><div><span>Direct cost</span><strong>AED {money(report.costing.direct_cost)}</strong></div><div><span>Sales subtotal · {report.costing.gross_margin_percent}% gross margin</span><strong>AED {money(report.costing.subtotal)}</strong></div><div><span>VAT · {report.costing.vat_percent ?? 5}%</span><strong>AED {money(report.costing.vat)}</strong></div><div className="total"><span>Estimated total</span><strong><small>AED</small> {money(report.costing.total)}</strong></div></div><p className="fine-print">{report.costing.note} Gross margin formula: selling price = direct cost ÷ {(1 - report.costing.gross_margin_percent / 100).toFixed(4).replace(/0+$/, '').replace(/\.$/, '')}.</p></section><section className="card scope-card"><h3>Scope & exclusions</h3><p className="muted">Includes selected fabric, standard hardware, manufacturing and installation labour.</p><div className="subheading">EXCLUDED FROM THIS ESTIMATE</div><ul className="simple-list">{report.costing.exclusions.map(item => <li key={item}>{item}</li>)}</ul><div className="info-note"><ShieldCheck size={20} /><p>No quote is sent to a customer. All amounts require commercial review.</p></div></section></div>}
          {tab === 'delivery' && <div className="report-grid"><div><section className="card timeline-card"><div className="section-heading"><h3>Proposed production plan</h3><span className={`pill ${report.production.on_time ? 'green' : 'amber'}`}>{report.production.on_time ? 'Within deadline' : 'Deadline at risk'}</span></div>{[
            { label: 'Materials available', date: report.production.material_ready, detail: report.materials.in_stock ? 'Subject to stock confirmation' : `${report.materials.lead_days} calendar days supplier lead time` },
            { label: 'Manufacturing', date: report.production.manufacture_start, detail: `Through ${day(report.production.manufacture_end)} · ${report.production.factory_hours} labour hours` },
            { label: 'Quality inspection', date: report.production.quality_date, detail: 'Dimensions, finish and operating checks' },
            { label: 'Site installation', date: report.production.installation_start, detail: `${report.production.installation_hours} labour hours · access subject to survey` },
            { label: 'Estimated completion', date: report.production.completion_date, detail: `Customer deadline: ${day(report.production.due_date)}` },
          ].map((stage, i) => <div className="timeline-item" key={stage.label}><div className="timeline-marker">{i + 1}</div><div><h4>{stage.label}</h4><p>{stage.detail}</p></div><strong>{day(stage.date)}</strong></div>)}<div className="inline-warning"><CalendarDays size={17} /> This is a capacity estimate, not a committed production booking.</div></section><section className="card assumptions"><h3>Scheduling assumptions</h3><ul className="simple-list">{report.production.assumptions.map(item => <li key={item}>{item}</li>)}</ul><p className="fine-print">Plan calculated as of {day(report.production.as_of)}, Dubai time.</p></section></div><section className="card quality-card"><div className="section-heading"><h3>Quality & site checklist</h3><ClipboardCheck size={20} /></div><p className="muted">Proposed checks for the reviewer and installation team.</p>{report.quality.checklist.map(item => <div className="checklist-item" key={item}><span className="empty-check" /><span>{item}</span></div>)}<p className="fine-print">{report.quality.note}</p></section></div>}
        </>)}

        {page === 'projects' && <section className="card projects-card"><div className="section-heading"><h3>Saved project reports</h3><span className="pill neutral">{reports.length} reports · latest 50</span></div>{!reports.length ? <div className="empty-state"><Layers3 size={34} /><h3>Your first project starts here.</h3><p>Analyze a brief to save a report and its complete agent evidence.</p><button className="button primary" disabled={!health || !catalog} onClick={() => newProject()}>Create project <Plus size={16} /></button></div> : <div className="table-scroll"><table><thead><tr><th>Project / customer</th><th>Estimate (AED)</th><th>Completion</th><th>Review status</th><th /></tr></thead><tbody>{reports.map(item => <tr key={item.id}><td><strong>{item.request.project_name}</strong><small>{item.request.customer} · {item.id.slice(0, 8)}</small></td><td>{money(item.costing.total)}</td><td>{day(item.production.completion_date)}</td><td><span className={`pill ${item.status === 'blocked' ? 'amber' : 'green'}`}>{statusLabel(item.status)}</span></td><td><button className="text-link" onClick={() => openReport(item)}>Open <ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div>}</section>}

        {page === 'inventory' && <><div className="inventory-heading"><span className="pill neutral">{catalog?.fabrics.length ?? 0} material records · {catalog?.data_source === 'supabase' ? 'Supabase' : 'Offline demo'}</span><p>Analysis does not reserve or reduce stock.</p><button className="button secondary" onClick={() => void load()}>Refresh records</button></div><div className="scenario-grid">{catalog?.fabrics.map(fabric => <section className="card fabric-card" key={fabric.id}><div className={`fabric-swatch large ${fabric.id}`} /><span className="eyebrow">{fabric.sku}</span><h3>{fabric.name}</h3><p className="muted">{fabric.color} · {fabric.transmission}</p><dl><dt>Available</dt><dd>{fabric.stock_lm.toFixed(2)} lm</dd><dt>On hand / reserved</dt><dd>{(fabric.on_hand_lm ?? fabric.stock_lm).toFixed(2)} / {(fabric.reserved_lm ?? 0).toFixed(2)} lm</dd><dt>Roll width</dt><dd>{fabric.roll_width_m} m</dd><dt>Recorded cost</dt><dd>AED {money(fabric.cost_per_lm)} / lm</dd><dt>Replenishment</dt><dd>{fabric.lead_days} calendar days</dd></dl><p className="fine-print">{fabric.source}</p></section>)}</div><section className="card assumptions"><h3>Material calculations you can explain</h3><p>Product records supply cutting allowances and curtain fullness. The estimating policy supplies waste ({(catalog?.policy.waste_fraction ?? 0) * 100}%). Agents check compatibility and whole-panel yield using those records.</p></section></>}

        {page === 'workflow' && <><section className="card workflow-full"><div className="section-heading"><div><span className="eyebrow">THE ACTUAL EXECUTION GRAPH</span><h3>Specialized tools. Shared state. One review gate.</h3></div><span className="pill green">LangGraph</span></div><div className="graph-flow"><GraphNode index={0} /><ArrowDown className="graph-arrow" /><div className="parallel-nodes"><GraphNode index={1} /><span>IN PARALLEL</span><GraphNode index={2} /></div><ArrowDown className="graph-arrow" /><GraphNode index={3} /><ArrowDown className="graph-arrow" /><GraphNode index={4} /><ArrowDown className="graph-arrow" /><GraphNode index={5} /><ArrowDown className="graph-arrow" /><div className="human-node"><ShieldCheck size={19} />Human approval required</div><ArrowDown className="graph-arrow" /><div className="human-node"><Factory size={19} />Reserve material · Book capacity · Create work order</div></div></section><div className="scenario-grid principles">{[
          { title: 'Calculations stay verifiable', desc: 'Fabric yield, pricing and dates come from Python tools. An LLM can explain results but cannot override constraints.', icon: Settings2 },
          { title: 'AI mode stays transparent', desc: 'Without a provider key, specialists run validated rules. With a key, each specialist adds grounded AI reasoning; failures are labeled.', icon: Sparkles },
          { title: 'Approvals stay bounded', desc: 'Blocked projects cannot be approved. Approval creates a demo work order and reserves material. Human progress updates gate manufacturing, quality and installation.', icon: ShieldCheck },
        ].map(item => <section className="card" key={item.title}><item.icon size={24} /><h3>{item.title}</h3><p>{item.desc}</p></section>)}</div></>}

        <footer className="page-footer"><span>Royal Blinds · Independent interview prototype</span><span>Python / FastAPI / LangGraph / React / Node.js / Supabase</span></footer>
      </main>
    </div>
    {editing && input && catalog && <div className="modal-backdrop no-print"><section className="modal project-modal" role="dialog" aria-modal="true" aria-labelledby="brief-title"><div className="modal-heading"><div><span className="eyebrow">PROJECT INTAKE</span><h2 id="brief-title">Give your specialists a brief.</h2></div><button className="icon-button" aria-label="Close project form" onClick={() => setEditing(false)}><X size={20} /></button></div><p className="muted">Structured fields drive calculations. Use synthetic customer details in this demo.</p>{error && <div className="inline-warning" role="alert">{error}</div>}
      <form onSubmit={event => void analyze(event)}><div className="form-grid"><label>Project name<input required minLength={2} maxLength={120} value={input.project_name} onChange={e => setInput({ ...input, project_name: e.target.value })} /></label><label>Customer / organization<input required minLength={2} maxLength={100} value={input.customer} onChange={e => setInput({ ...input, customer: e.target.value })} /></label><label>Product<select value={input.product} onChange={e => setInput({ ...input, product: e.target.value as ProjectInput['product'] })}>{Object.entries(catalog.products).map(([id, value]) => <option value={id} key={id}>{value.name}</option>)}</select></label><label>Fabric<select value={input.fabric_id} onChange={e => setInput({ ...input, fabric_id: e.target.value as ProjectInput['fabric_id'] })}>{catalog.fabrics.map(f => <option value={f.id} key={f.id}>{f.name} · {f.stock_lm} lm</option>)}</select></label></div><div className="form-grid three"><label>Openings<input type="number" required min={1} max={500} value={input.quantity} onChange={e => setInput({ ...input, quantity: Number(e.target.value) })} /></label><label>Width per opening (m)<input type="number" step="0.01" required min={0.3} max={4} value={input.width_m} onChange={e => setInput({ ...input, width_m: Number(e.target.value) })} /></label><label>Height per opening (m)<input type="number" step="0.01" required min={0.5} max={5} value={input.height_m} onChange={e => setInput({ ...input, height_m: Number(e.target.value) })} /></label></div><div className="form-grid"><label>Installation site<input required minLength={2} maxLength={160} value={input.site} onChange={e => setInput({ ...input, site: e.target.value })} /></label><label>Requested completion<input type="date" required min={health?.today} value={input.due_date} onChange={e => setInput({ ...input, due_date: e.target.value })} /></label></div><label>Customer brief<textarea required minLength={10} maxLength={4000} rows={3} value={input.brief} onChange={e => setInput({ ...input, brief: e.target.value })} /></label><div className="form-note"><ShieldCheck size={16} />Dimensions are provisional. This workflow never places a real order.</div><div className="modal-actions"><button className="button secondary" type="button" onClick={() => setEditing(false)}>Cancel</button><button className="button primary" type="submit" disabled={busy}><Sparkles size={17} />Analyze project</button></div></form></section></div>}
    {approving && report && <div className="modal-backdrop no-print"><section className="modal approval-modal" role="dialog" aria-modal="true" aria-labelledby="review-title"><div className="modal-heading"><div><span className="eyebrow">HUMAN REVIEW</span><h2 id="review-title">Review the demo estimate.</h2></div><button className="icon-button" aria-label="Close review" onClick={() => setApproving(false)}><X size={20} /></button></div><p>AED {money(report.costing.total)} · {report.request.project_name}</p>{error && <div className="inline-warning" role="alert">{error}</div>}<form onSubmit={event => void approve(event)}><label>Reviewer name<input name="reviewer" required minLength={2} maxLength={100} placeholder="Your name" /></label><div className="approval-checks"><label><input type="checkbox" name="measurements" required />I reviewed the sample measurements and survey assumptions.</label><label><input type="checkbox" name="specification" required />I reviewed the product, fabric and installation checklist.</label><label><input type="checkbox" name="commercial" required />I reviewed the cost breakdown, deadline and exclusions.</label><label><input type="checkbox" name="execution" required />I authorize demo material reservation and work-order creation.</label></div><div className="info-note"><ShieldCheck size={20} /><p>Approval starts the demo workflow: reserve material, book capacity and create a work order. Factory progress is recorded separately.</p></div><div className="modal-actions"><button type="button" className="button secondary" onClick={() => setApproving(false)}>Cancel</button><button className="button primary" disabled={busy}><BadgeCheck size={17} />Approve demo estimate</button></div></form></section></div>}
    {busy && <div className="busy-overlay no-print" role="status" aria-live="polite"><div className="card"><LoaderCircle size={32} className="spin" /><h3>{approving ? 'Recording your review…' : 'Your specialists are working…'}</h3><p>{approving ? 'Saving the demo approval.' : 'LangGraph is evaluating the project and collecting evidence.'}</p><span>{health?.reasoning_mode === 'live_ai_configured' ? 'AI commentary may take a moment.' : 'Running validated manufacturing tools.'}</span></div></div>}
  </div>
}

function Metric({ icon: Icon, label, value, detail, alert = false }: { icon: typeof FileText; label: string; value: string; detail: string; alert?: boolean }) {
  return <section className="metric card"><div><span>{label}</span><Icon size={17} /></div><h3>{value}</h3><p className={alert ? 'warning-text' : ''}>{alert ? <CircleAlert size={13} /> : <CheckCircle2 size={13} />}{detail}</p></section>
}
function AgentStrip() {
  return <div className="agent-strip">{agents.map((agent, i) => <div key={agent.name}><div className="agent-strip-icon"><agent.icon size={21} /></div><h4>{agent.name}</h4><small>{agent.desc}</small>{i < agents.length - 1 && <ChevronRight className="strip-arrow" size={15} />}</div>)}</div>
}
function GraphNode({ index }: { index: number }) {
  const agent = agents[index]
  return <div className="graph-node"><span className="icon-box green"><agent.icon size={22} /></span><div><h4>{agent.name} agent</h4><p>{agent.desc}</p></div><span className="graph-number">0{index + 1}</span></div>
}
