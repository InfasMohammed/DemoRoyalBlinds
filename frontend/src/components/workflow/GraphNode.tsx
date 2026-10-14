import { agents } from '../../lib/agentRoster'

export default function GraphNode({ index }: { index: number }) {
  const agent = agents[index]
  return (
    <div className="graph-node">
      <span className="icon-box green">
        <agent.icon size={22} />
      </span>
      <div>
        <h4>{agent.name} agent</h4>
        <p>{agent.desc}</p>
      </div>
      <span className="graph-number">0{index + 1}</span>
    </div>
  )
}
