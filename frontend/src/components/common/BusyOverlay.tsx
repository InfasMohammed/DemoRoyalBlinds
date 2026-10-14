import { LoaderCircle } from 'lucide-react'
import type { Health } from '../../types'

type Props = {
  health: Health | null
  approving: boolean
}

export default function BusyOverlay({ health, approving }: Props) {
  return (
    <div className="busy-overlay no-print" role="status" aria-live="polite">
      <div className="card">
        <LoaderCircle size={32} className="spin" />
        <h3>{approving ? 'Recording your review…' : 'Your specialists are working…'}</h3>
        <p>
          {approving
            ? 'Saving the demo approval.'
            : 'LangGraph is evaluating the project and collecting evidence.'}
        </p>
        <span>
          {health?.reasoning_mode === 'live_ai_configured'
            ? 'AI commentary may take a moment.'
            : 'Running validated manufacturing tools.'}
        </span>
      </div>
    </div>
  )
}
