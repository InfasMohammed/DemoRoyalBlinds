import { ChevronRight } from 'lucide-react'
import { agents } from '../../lib/agentRoster'

export default function AgentStrip() {
  return (
    <div className="agent-strip">
      {agents.map((agent, i) => (
        <div key={agent.name}>
          <div className="agent-strip-icon">
            <agent.icon size={21} />
          </div>
          <h4>{agent.name}</h4>
          <small>{agent.desc}</small>
          {i < agents.length - 1 && <ChevronRight className="strip-arrow" size={15} />}
        </div>
      ))}
    </div>
  )
}
