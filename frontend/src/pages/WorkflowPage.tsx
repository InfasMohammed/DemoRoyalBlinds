import { ArrowDown, Factory, Settings2, ShieldCheck, Sparkles } from 'lucide-react'
import GraphNode from '../components/workflow/GraphNode'

export default function WorkflowPage() {
  return (
    <>
      <section className="card workflow-full">
        <div className="section-heading">
          <div>
            <span className="eyebrow">THE ACTUAL EXECUTION GRAPH</span>
            <h3>Specialized tools. Shared state. One review gate.</h3>
          </div>
          <span className="pill green">LangGraph</span>
        </div>
        <div className="graph-flow">
          <GraphNode index={0} />
          <ArrowDown className="graph-arrow" />
          <div className="parallel-nodes">
            <GraphNode index={1} />
            <span>IN PARALLEL</span>
            <GraphNode index={2} />
          </div>
          <ArrowDown className="graph-arrow" />
          <GraphNode index={3} />
          <ArrowDown className="graph-arrow" />
          <GraphNode index={4} />
          <ArrowDown className="graph-arrow" />
          <GraphNode index={5} />
          <ArrowDown className="graph-arrow" />
          <div className="human-node">
            <ShieldCheck size={19} />
            Human approval required
          </div>
          <ArrowDown className="graph-arrow" />
          <div className="human-node">
            <Factory size={19} />
            Reserve material · Book capacity · Create work order
          </div>
        </div>
      </section>
      <div className="scenario-grid principles">
        {[
          {
            title: 'Calculations stay verifiable',
            desc: 'Fabric yield, pricing and dates come from Python tools. An LLM can explain results but cannot override constraints.',
            icon: Settings2,
          },
          {
            title: 'AI mode stays transparent',
            desc: 'Without a provider key, specialists run validated rules. With a key, each specialist adds grounded AI reasoning; failures are labeled.',
            icon: Sparkles,
          },
          {
            title: 'Approvals stay bounded',
            desc: 'Blocked projects cannot be approved. Approval creates a demo work order and reserves material. Human progress updates gate manufacturing, quality and installation.',
            icon: ShieldCheck,
          },
        ].map((item) => (
          <section className="card" key={item.title}>
            <item.icon size={24} />
            <h3>{item.title}</h3>
            <p>{item.desc}</p>
          </section>
        ))}
      </div>
    </>
  )
}
