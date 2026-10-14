import type { Catalog } from '../types'
import { money } from '../lib/format'

type Props = {
  catalog: Catalog | null
  load: () => Promise<void>
}

export default function MaterialsPage({ catalog, load }: Props) {
  return (
    <>
      <div className="inventory-heading">
        <span className="pill neutral">
          {catalog?.fabrics.length ?? 0} material records ·{' '}
          {catalog?.data_source === 'supabase' ? 'Supabase' : 'Offline demo'}
        </span>
        <p>Analysis does not reserve or reduce stock.</p>
        <button className="button secondary" onClick={() => void load()}>
          Refresh records
        </button>
      </div>
      <div className="scenario-grid">
        {catalog?.fabrics.map((fabric) => (
          <section className="card fabric-card" key={fabric.id}>
            <div className={`fabric-swatch large ${fabric.id}`} />
            <span className="eyebrow">{fabric.sku}</span>
            <h3>{fabric.name}</h3>
            <p className="muted">
              {fabric.color} · {fabric.transmission}
            </p>
            <dl>
              <dt>Available</dt>
              <dd>{fabric.stock_lm.toFixed(2)} lm</dd>
              <dt>On hand / reserved</dt>
              <dd>
                {(fabric.on_hand_lm ?? fabric.stock_lm).toFixed(2)} /{' '}
                {(fabric.reserved_lm ?? 0).toFixed(2)} lm
              </dd>
              <dt>Roll width</dt>
              <dd>{fabric.roll_width_m} m</dd>
              <dt>Recorded cost</dt>
              <dd>AED {money(fabric.cost_per_lm)} / lm</dd>
              <dt>Replenishment</dt>
              <dd>{fabric.lead_days} calendar days</dd>
            </dl>
            <p className="fine-print">{fabric.source}</p>
          </section>
        ))}
      </div>
      <section className="card assumptions">
        <h3>Material calculations you can explain</h3>
        <p>
          Product records supply cutting allowances and curtain fullness. The estimating policy
          supplies waste ({(catalog?.policy.waste_fraction ?? 0) * 100}%). Agents check
          compatibility and whole-panel yield using those records.
        </p>
      </section>
    </>
  )
}
