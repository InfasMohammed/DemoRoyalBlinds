import { BadgeCheck, ShieldCheck, X } from 'lucide-react'
import type { FormEvent } from 'react'
import type { Report } from '../../types'
import { money } from '../../lib/format'

type Props = {
  report: Report
  busy: boolean
  error: string
  setApproving: (approving: boolean) => void
  approve: (event: FormEvent<HTMLFormElement>) => Promise<void>
}

export default function ApprovalDialog({ report, busy, error, setApproving, approve }: Props) {
  return (
    <div className="modal-backdrop no-print">
      <section
        className="modal approval-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-title"
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">HUMAN REVIEW</span>
            <h2 id="review-title">Review the demo estimate.</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close review"
            onClick={() => setApproving(false)}
          >
            <X size={20} />
          </button>
        </div>
        <p>
          AED {money(report.costing.total)} · {report.request.project_name}
        </p>
        {error && (
          <div className="inline-warning" role="alert">
            {error}
          </div>
        )}
        <form onSubmit={(event) => void approve(event)}>
          <label>
            Reviewer name
            <input name="reviewer" required minLength={2} maxLength={100} placeholder="Your name" />
          </label>
          <div className="approval-checks">
            <label>
              <input type="checkbox" name="measurements" required />I reviewed the sample
              measurements and survey assumptions.
            </label>
            <label>
              <input type="checkbox" name="specification" required />I reviewed the product, fabric
              and installation checklist.
            </label>
            <label>
              <input type="checkbox" name="commercial" required />I reviewed the cost breakdown,
              deadline and exclusions.
            </label>
            <label>
              <input type="checkbox" name="execution" required />I authorize demo material
              reservation and work-order creation.
            </label>
          </div>
          <div className="info-note">
            <ShieldCheck size={20} />
            <p>
              Approval starts the demo workflow: reserve material, book capacity and create a work
              order. Factory progress is recorded separately.
            </p>
          </div>
          <div className="modal-actions">
            <button type="button" className="button secondary" onClick={() => setApproving(false)}>
              Cancel
            </button>
            <button className="button primary" disabled={busy}>
              <BadgeCheck size={17} />
              Approve demo estimate
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
