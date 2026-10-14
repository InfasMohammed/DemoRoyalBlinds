import { ShieldCheck, Sparkles, X } from 'lucide-react'
import type { FormEvent } from 'react'
import type { Catalog, Health, ProjectInput } from '../../types'

type Props = {
  health: Health | null
  catalog: Catalog
  input: ProjectInput
  busy: boolean
  error: string
  setInput: (input: ProjectInput) => void
  setEditing: (editing: boolean) => void
  analyze: (event?: FormEvent, replacement?: ProjectInput) => Promise<void>
}

export default function ProjectForm({
  health,
  catalog,
  input,
  busy,
  error,
  setInput,
  setEditing,
  analyze,
}: Props) {
  return (
    <div className="modal-backdrop no-print">
      <section
        className="modal project-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="brief-title"
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">PROJECT INTAKE</span>
            <h2 id="brief-title">Create a new quotation.</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close project form"
            onClick={() => setEditing(false)}
          >
            <X size={20} />
          </button>
        </div>
        <p className="muted">
          Structured fields drive calculations. Use synthetic customer details in this demo.
        </p>
        {error && (
          <div className="inline-warning" role="alert">
            {error}
          </div>
        )}
        <form onSubmit={(event) => void analyze(event)}>
          <div className="form-grid">
            <label>
              Project name
              <input
                required
                minLength={2}
                maxLength={120}
                value={input.project_name}
                onChange={(e) => setInput({ ...input, project_name: e.target.value })}
              />
            </label>
            <label>
              Customer / organization
              <input
                required
                minLength={2}
                maxLength={100}
                value={input.customer}
                onChange={(e) => setInput({ ...input, customer: e.target.value })}
              />
            </label>
            <label>
              Product
              <select
                value={input.product}
                onChange={(e) =>
                  setInput({ ...input, product: e.target.value as ProjectInput['product'] })
                }
              >
                {Object.entries(catalog.products).map(([id, value]) => (
                  <option value={id} key={id}>
                    {value.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Fabric
              <select
                value={input.fabric_id}
                onChange={(e) =>
                  setInput({ ...input, fabric_id: e.target.value as ProjectInput['fabric_id'] })
                }
              >
                {catalog.fabrics.map((f) => (
                  <option value={f.id} key={f.id}>
                    {f.name} · {f.stock_lm} lm
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-grid three">
            <label>
              Openings
              <input
                type="number"
                required
                min={1}
                max={500}
                value={input.quantity}
                onChange={(e) => setInput({ ...input, quantity: Number(e.target.value) })}
              />
            </label>
            <label>
              Width per opening (m)
              <input
                type="number"
                step="0.01"
                required
                min={0.3}
                max={4}
                value={input.width_m}
                onChange={(e) => setInput({ ...input, width_m: Number(e.target.value) })}
              />
            </label>
            <label>
              Height per opening (m)
              <input
                type="number"
                step="0.01"
                required
                min={0.5}
                max={5}
                value={input.height_m}
                onChange={(e) => setInput({ ...input, height_m: Number(e.target.value) })}
              />
            </label>
          </div>
          <div className="form-grid">
            <label>
              Installation site
              <input
                required
                minLength={2}
                maxLength={160}
                value={input.site}
                onChange={(e) => setInput({ ...input, site: e.target.value })}
              />
            </label>
            <label>
              Requested completion
              <input
                type="date"
                required
                min={health?.today}
                value={input.due_date}
                onChange={(e) => setInput({ ...input, due_date: e.target.value })}
              />
            </label>
          </div>
          <label>
            Customer brief
            <textarea
              required
              minLength={10}
              maxLength={4000}
              rows={3}
              value={input.brief}
              onChange={(e) => setInput({ ...input, brief: e.target.value })}
            />
          </label>
          <div className="form-note">
            <ShieldCheck size={16} />
            Dimensions are provisional. This workflow never places a real order.
          </div>
          <div className="modal-actions">
            <button className="button secondary" type="button" onClick={() => setEditing(false)}>
              Cancel
            </button>
            <button className="button primary" type="submit" disabled={busy}>
              <Sparkles size={17} />
              Analyze project
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
