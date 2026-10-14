import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  CalendarDays,
  Check,
  BookOpen,
  Package,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import type { Catalog, Health } from '../types'
import type { Page } from '../lib/navigation'
import AgentStrip from '../components/workflow/AgentStrip'

type Props = {
  health: Health | null
  catalog: Catalog | null
  busy: boolean
  setPage: (page: Page) => void
  newQuotation: (scenario?: string) => void
}

export default function HomePage({ health, catalog, busy, setPage, newQuotation }: Props) {
  return (
    <>
      <section className="hero card">
        <div className="hero-copy">
          <span className="pill green">
            <Sparkles size={13} /> YOUR OPERATIONS COPILOT
          </span>
          <h2>
            One customer brief.
            <br />
            <em>A complete project picture.</em>
          </h2>
          <p>
            Check the fabric. Build the estimate. Understand the timeline. Let six specialists
            connect the details before you commit.
          </p>
          <button
            className="button primary"
            disabled={!catalog || !health || busy}
            onClick={() => newQuotation()}
          >
            Create a project brief <ArrowRight size={17} />
          </button>
          <div className="hero-footnote">
            <ShieldCheck size={15} /> Evidence at every step. Approval in your hands.
          </div>
        </div>
        <div className="hero-visual" aria-label="Illustration of roller blinds">
          <div className="window-frame">
            <div className="blinds">
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="window-light" />
            <div className="window-pull" />
          </div>
          <div className="floating-card">
            <span className="floating-icon">
              <Check size={18} />
            </span>
            <div>
              Clarity before commitment<small>Material · Cost · Delivery</small>
            </div>
          </div>
          <span className="visual-caption">DESIGNED FOR YOUR WORKFLOW</span>
        </div>
      </section>
      <section className="card portfolio-callout">
        <BookOpen size={24} />
        <div>
          <h3>Internal. External. Smart.</h3>
          <p>
            Explore the supplied product range and automation options with source-linked company
            knowledge.
          </p>
        </div>
        <button className="button secondary" onClick={() => setPage('knowledge')}>
          Explore products <ArrowUpRight size={16} />
        </button>
      </section>
      <div className="section-heading">
        <h3>Try a manufacturing scenario</h3>
        <span>Start with a brief. See the decisions.</span>
      </div>
      <div className="scenario-grid">
        {catalog?.scenarios.map((item) => {
          const Icon =
            item.id === 'rush' ? CalendarDays : item.id === 'ready' ? BadgeCheck : Package
          const color = item.id === 'rush' ? 'blue' : item.id === 'ready' ? 'green' : 'amber'
          return (
            <button
              key={item.id}
              className="scenario card"
              disabled={!health || busy}
              onClick={() => newQuotation(item.id)}
            >
              <div className={`icon-box ${color}`}>
                <Icon size={21} />
              </div>
              <div className="eyebrow">{item.category}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
              <span className="text-link">
                Open scenario <ArrowUpRight size={16} />
              </span>
            </button>
          )
        })}
      </div>
      <section className="card workflow-preview">
        <div className="section-heading">
          <div>
            <span className="eyebrow">COORDINATED BY LANGGRAPH</span>
            <h3>Expertise, connected.</h3>
          </div>
          <button className="text-link" onClick={() => setPage('workflow')}>
            View workflow <ArrowRight size={15} />
          </button>
        </div>
        <AgentStrip />
      </section>
    </>
  )
}
