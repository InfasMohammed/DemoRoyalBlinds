import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Plus,
  Sparkles,
  X,
} from 'lucide-react'
import type { ReactNode } from 'react'
import type { Catalog, Health, Report } from '../../types'
import { modeLabel } from '../../lib/format'
import { navigation, pageDetails } from '../../lib/navigation'
import type { Page } from '../../lib/navigation'
import { SessionControls } from '../../auth/AuthGate'

type Props = {
  health: Health | null
  catalog: Catalog | null
  reports: Report[]
  page: Page
  busy: boolean
  error: string
  notice: string
  setPage: (page: Page) => void
  setError: (error: string) => void
  setNotice: (notice: string) => void
  setCreating: (kind: 'knowledge' | 'material' | null) => void
  newQuotation: (scenario?: string) => void
  load: () => Promise<void>
  children: ReactNode
  dialogs: ReactNode
}

export default function AppShell({
  health,
  catalog,
  reports,
  page,
  busy,
  error,
  notice,
  setPage,
  setError,
  setNotice,
  setCreating,
  newQuotation,
  load,
  children,
  dialogs,
}: Props) {
  const currentPage = pageDetails(page)
  return (
    <div className="app-shell">
      <aside className="sidebar no-print">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault()
            setPage('workspace')
          }}
          aria-label="Royal Blinds home"
        >
          <picture className="brand-picture">
            <source media="(max-width: 980px)" srcSet="/brand/royal-blinds-icon.png" />
            <img
              className="brand-logo"
              src="/brand/royal-blinds-logo.png"
              alt="Royal Blinds"
              width="749"
              height="290"
            />
          </picture>
          <span className="brand-caption">OPERATIONS STUDIO</span>
        </a>
        <div className="workspace-label">
          WORKSPACE <span>DEMO</span>
        </div>
        <nav aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              <item.icon size={19} />
              {item.name}
              {item.id === 'projects' && <span className="nav-count">{reports.length}</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-callout">
          <Sparkles size={21} />
          <h4>Built for better decisions.</h4>
          <p>Six specialists. One clear plan. A human stays in control.</p>
          <button onClick={() => setPage('workflow')}>
            Explore the workflow <ArrowUpRight size={15} />
          </button>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">
            <img src="/brand/royal-blinds-icon.png" alt="" width="22" height="22" />
          </span>
          <div>
            Interview demonstration<small>Synthetic factory data</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar no-print">
          <div className="breadcrumb">
            Operations <ChevronRight size={14} />
            <strong>{currentPage.name}</strong>
          </div>
          <div className="topbar-right">
            <SessionControls />
            <span className={`connection ${health ? '' : 'offline'}`}>
              <i />
              {health ? 'Backend connected' : 'Connecting'}
            </span>
            <span className="topbar-divider" />
            <span className="location">Dubai, UAE</span>
            <span className="small-avatar">
              <img src="/brand/royal-blinds-icon.png" alt="" width="23" height="23" />
            </span>
          </div>
        </header>
        <main>
          {error && (
            <div role="alert" className="error-banner no-print">
              <CircleAlert size={18} />
              <span>{error}</span>
              <button onClick={() => void load()}>Retry connection</button>
              <button aria-label="Dismiss error" onClick={() => setError('')}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="record-success no-print" role="status">
              <CheckCircle2 size={18} />
              <span>{notice}</span>
              <button
                className="icon-button"
                aria-label="Dismiss saved notification"
                onClick={() => setNotice('')}
              >
                <X size={16} />
              </button>
            </div>
          )}
          <div className="page-heading no-print">
            <div>
              <div className="eyebrow">MANUFACTURING INTELLIGENCE</div>
              <h1>{currentPage.heading}</h1>
              <p>{currentPage.description}</p>
            </div>
            {page === 'workspace' && (
              <button
                className="button primary"
                onClick={() => newQuotation()}
                disabled={!health || !catalog || busy}
              >
                <Plus size={17} />
                New quotation
              </button>
            )}
            {(page === 'knowledge' || page === 'inventory') && (
              <button
                className="button primary"
                disabled={!catalog || busy}
                onClick={() => {
                  setNotice('')
                  setCreating(page === 'knowledge' ? 'knowledge' : 'material')
                }}
              >
                <Plus size={17} />
                {page === 'knowledge' ? 'Add knowledge' : 'Add material'}
              </button>
            )}
          </div>
          <div className="demo-strip no-print">
            <span>
              <span className="pill neutral">INTERVIEW DEMO</span>
              {catalog?.is_sample === false
                ? 'Configured business records. Human review required.'
                : 'Sample inventory, rates and capacity.'}
            </span>
            <span>
              {catalog?.data_source === 'supabase' ? 'Supabase business data' : 'Offline demo data'}
              <span className="dot-separator">·</span>
              {health ? modeLabel(health.reasoning_mode) : 'Checking runtime'}
              <span className="dot-separator">·</span>
              {health
                ? health.storage_mode === 'supabase'
                  ? 'Supabase storage'
                  : 'Local demo storage'
                : 'Storage unverified'}
            </span>
          </div>

          {children}

          <footer className="page-footer">
            <span>Royal Blinds · Independent interview prototype</span>
            <span>Python / FastAPI / LangGraph / React / Node.js / Supabase</span>
          </footer>
        </main>
      </div>
      {dialogs}
    </div>
  )
}
