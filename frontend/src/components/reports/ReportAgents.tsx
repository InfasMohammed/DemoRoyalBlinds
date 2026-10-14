import { ArrowUpRight, ChevronDown, CircleAlert, BookOpen, FileText, Workflow } from 'lucide-react'
import type { Report } from '../../types'
import { modeLabel } from '../../lib/format'
import { agents } from '../../lib/agentRoster'

type Props = {
  report: Report
  expanded: string | null
  setExpanded: (expanded: string | null) => void
}

export default function ReportAgents({ report, expanded, setExpanded }: Props) {
  return (
    <section className="card agent-findings">
      <div className="section-heading">
        <div>
          <span className="eyebrow">TRACEABLE EXECUTION</span>
          <h3>What each specialist found</h3>
        </div>
        <span className="pill neutral">{modeLabel(report.reasoning_mode)}</span>
      </div>
      <p className="muted">
        Validated tools control numbers and approval gates. Optional AI explains the findings using
        the supplied evidence.
      </p>
      {report.traces.map((item, i) => {
        const Icon = agents.find((a) => item.agent.startsWith(a.name))?.icon || Workflow
        return (
          <article className="trace-card" key={item.agent}>
            <div className="trace-index">{String(i + 1).padStart(2, '0')}</div>
            <div className="trace-content">
              <div className="trace-heading">
                <h3>
                  <Icon size={19} />
                  {item.agent}
                </h3>
                <span className={`pill ${item.mode === 'rules_fallback' ? 'amber' : 'neutral'}`}>
                  {item.mode === 'llm'
                    ? 'AI + tools'
                    : item.mode === 'rules_fallback'
                      ? 'Rules · AI unavailable'
                      : 'Validated rules'}
                </span>
              </div>
              <div className="trace-role">
                {item.role} · {item.duration_ms} ms
              </div>
              <p>{item.summary}</p>
              {item.fallback_reason && (
                <div className="inline-warning">
                  <CircleAlert size={16} />
                  {item.fallback_reason}
                </div>
              )}
              {item.recommendation && <p className="recommendation">{item.recommendation}</p>}
              <div className="source-tags">
                {item.sources.map((source) => (
                  <span key={source}>
                    <FileText size={12} />
                    {source}
                  </span>
                ))}
              </div>
              {item.citations && item.citations.length > 0 && (
                <div className="trace-citations">
                  {item.citations.map((citation) => (
                    <a
                      href={citation.source_url}
                      key={citation.id}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <BookOpen size={12} />
                      {citation.heading}
                      <ArrowUpRight size={12} />
                    </a>
                  ))}
                </div>
              )}
              <button
                className="text-link evidence-toggle"
                aria-expanded={expanded === item.agent}
                onClick={() => setExpanded(expanded === item.agent ? null : item.agent)}
              >
                Inspect tool evidence <ChevronDown size={15} />
              </button>
              {expanded === item.agent && (
                <pre className="evidence">{JSON.stringify(item.facts, null, 2)}</pre>
              )}
            </div>
          </article>
        )
      })}
    </section>
  )
}
