import { CircleAlert, Printer, ShieldCheck } from 'lucide-react'
import type { Report } from '../../types'
import { money } from '../../lib/format'

type Props = {
  report: Report
}

export default function ReportQuotation({ report }: Props) {
  return (
    <div className="report-grid quote-grid">
      <section className="card quote-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">DRAFT · ILLUSTRATIVE RATES</span>
            <h3>Transparent project estimate</h3>
          </div>
          <button
            className="icon-button no-print"
            aria-label="Print quotation"
            onClick={() => window.print()}
          >
            <Printer size={18} />
          </button>
        </div>
        {!report.costing.valid && (
          <div className="inline-warning">
            <CircleAlert size={16} /> Invalid specification: these costs are indicative only.
          </div>
        )}
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Cost component</th>
                <th>Quantity</th>
                <th>Rate (AED)</th>
                <th>Cost (AED)</th>
              </tr>
            </thead>
            <tbody>
              {report.costing.lines.map((line) => (
                <tr key={line.description}>
                  <td>{line.description}</td>
                  <td>
                    {line.quantity} {line.unit}
                  </td>
                  <td>{money(line.unit_cost)}</td>
                  <td>{money(line.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="quote-totals">
          <div>
            <span>Direct cost</span>
            <strong>AED {money(report.costing.direct_cost)}</strong>
          </div>
          <div>
            <span>Sales subtotal · {report.costing.gross_margin_percent}% gross margin</span>
            <strong>AED {money(report.costing.subtotal)}</strong>
          </div>
          <div>
            <span>VAT · {report.costing.vat_percent ?? 5}%</span>
            <strong>AED {money(report.costing.vat)}</strong>
          </div>
          <div className="total">
            <span>Estimated total</span>
            <strong>
              <small>AED</small> {money(report.costing.total)}
            </strong>
          </div>
        </div>
        <p className="fine-print">
          {report.costing.note} Gross margin formula: selling price = direct cost ÷{' '}
          {(1 - report.costing.gross_margin_percent / 100)
            .toFixed(4)
            .replace(/0+$/, '')
            .replace(/\.$/, '')}
          .
        </p>
      </section>
      <section className="card scope-card">
        <h3>Scope & exclusions</h3>
        <p className="muted">
          Includes selected fabric, standard hardware, manufacturing and installation labour.
        </p>
        <div className="subheading">EXCLUDED FROM THIS ESTIMATE</div>
        <ul className="simple-list">
          {report.costing.exclusions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <div className="info-note">
          <ShieldCheck size={20} />
          <p>No quote is sent to a customer. All amounts require commercial review.</p>
        </div>
      </section>
    </div>
  )
}
