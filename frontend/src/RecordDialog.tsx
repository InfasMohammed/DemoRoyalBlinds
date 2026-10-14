import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { CircleAlert, LoaderCircle, Plus, X } from 'lucide-react'
import { api } from './api'
import type { Catalog } from './types'
import './record-dialog.css'

type Product = { id: string; name: string; category: string }
type Props = {
  kind: 'knowledge' | 'material'; catalog: Catalog; databaseEnabled: boolean;
  onClose: () => void; onSaved: (message: string) => void; onSaving: (saving: boolean) => void;
}

export default function RecordDialog({ kind, catalog, databaseEnabled, onClose, onSaved, onSaving }: Props) {
  const [requestId] = useState(() => crypto.randomUUID())
  const [category, setCategory] = useState('company')
  const [products, setProducts] = useState<Product[]>([])
  const [ready, setReady] = useState(kind === 'material')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function loadProducts() {
    setError('')
    try {
      const portfolio = await api<{ products: Product[] }>('/knowledge/portfolio')
      setProducts(portfolio.products); setReady(true)
    } catch (err) { setError((err as Error).message) }
  }
  useEffect(() => { if (kind === 'knowledge') void loadProducts() }, [kind])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!databaseEnabled || !ready || saving) return
    const form = new FormData(event.currentTarget)
    const text = (name: string) => String(form.get(name) || '').trim()
    const number = (name: string) => Number(form.get(name))
    const payload = kind === 'material' ? {
      request_id: requestId, name: text('name'), sku: text('sku'),
      roll_width_m: number('roll_width_m'), stock_lm: number('stock_lm'), cost_per_lm: number('cost_per_lm'),
      lead_days: number('lead_days'), transmission: text('transmission'), color: text('color'),
      compatible: form.getAll('compatible'), source: text('source'),
    } : {
      request_id: requestId, title: text('title'), heading: text('heading'), category,
      product_ids: form.getAll('product_ids'), content: text('content'), source_url: text('source_url'),
      reviewed: form.get('reviewed') === 'on',
    }
    if (kind === 'material' && !form.getAll('compatible').length) {
      setError('Select at least one compatible manufacturing profile.'); return
    }
    setSaving(true); onSaving(true); setError('')
    try {
      const result = await api<{ created: boolean }>(kind === 'material' ? '/materials' : '/knowledge/entries', {
        method: 'POST', body: JSON.stringify(payload),
      })
      onSaved(kind === 'material'
        ? `Material ${result.created ? 'saved' : 'already saved'} in Supabase.`
        : `Knowledge ${result.created ? 'saved' : 'already saved'} in Supabase. Available for keyword retrieval; vector search requires indexing.`)
    } catch (err) { setError((err as Error).message) }
    finally { setSaving(false); onSaving(false) }
  }

  return <div className="modal-backdrop no-print"><section className="modal record-modal" role="dialog" aria-modal="true" aria-labelledby="record-title">
    <div className="modal-heading"><div><span className="eyebrow">{kind === 'knowledge' ? 'COMPANY KNOWLEDGE' : 'MATERIAL LIBRARY'}</span><h2 id="record-title">{kind === 'knowledge' ? 'Add knowledge' : 'Add material'}</h2></div><button type="button" className="icon-button" aria-label="Close creation form" disabled={saving} onClick={onClose}><X size={20} /></button></div>
    <p className="muted">{kind === 'knowledge' ? 'Add reviewed source text for the assistant to retrieve and cite.' : 'Record a new material and its opening stock for future quotations.'}</p>
    {!databaseEnabled && <div className="inline-warning"><CircleAlert size={16} />Saving requires Supabase business data. Refresh the page after connecting Supabase.</div>}
    {error && <div className="inline-warning" role="alert"><CircleAlert size={16} />{error}</div>}
    {!ready && error && <button type="button" className="button secondary" onClick={() => void loadProducts()}>Reload products</button>}
    <form onSubmit={event => void submit(event)}>
      <fieldset disabled={saving}>
      {kind === 'knowledge' ? <>
        <div className="form-grid"><label>Source title<input name="title" required minLength={2} maxLength={200} /></label><label>Section heading<input name="heading" required minLength={2} maxLength={200} /></label></div>
        <div className="form-grid"><label>Knowledge category<select name="category" value={category} onChange={event => setCategory(event.target.value)}>{Object.entries({ company: 'Company profile', internal: 'Internal shades', external: 'External shades', smart: 'Smart Solutions' }).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><label>Source URL<input name="source_url" type="url" required placeholder="https://www.royalblinds.com/…" /></label></div>
        <label>Source text<textarea name="content" required rows={6} minLength={10} maxLength={30000} /></label>
        <fieldset className="record-options" key={category}><legend>Related products (optional)</legend><div className="approval-checks">{products.filter(product => !['internal', 'external'].includes(category) || product.category === category).map(product => <label key={product.id}><input type="checkbox" name="product_ids" value={product.id} />{product.name}</label>)}</div></fieldset>
        <label className="record-confirm"><input type="checkbox" name="reviewed" required />I reviewed this source text and its source URL.</label>
      </> : <>
        <div className="form-grid"><label>Material name<input name="name" required minLength={2} maxLength={120} /></label><label>SKU<input name="sku" required minLength={2} maxLength={80} /></label></div>
        <div className="form-grid three"><label>Roll width (m)<input name="roll_width_m" type="number" required min="0.01" step="0.01" /></label><label>Opening stock (linear m)<input name="stock_lm" type="number" required min="0" step="0.01" /></label><label>Cost (AED / linear m)<input name="cost_per_lm" type="number" required min="0" step="0.01" /></label></div>
        <div className="form-grid"><label>Lead time (days)<input name="lead_days" type="number" required min="0" max="3650" step="1" /></label><label>Colour<input name="color" required minLength={2} maxLength={80} /></label></div>
        <label>Light transmission / finish<input name="transmission" required minLength={2} maxLength={120} placeholder="For example, blackout or translucent" /></label>
        <fieldset className="record-options"><legend>Compatible manufacturing profiles</legend><div className="approval-checks">{Object.entries(catalog.products).map(([id, product]) => <label key={id}><input type="checkbox" name="compatible" value={id} />{product.name}</label>)}</div></fieldset>
        <label>Stock and cost source<input name="source" required minLength={3} maxLength={500} placeholder="Supplier quote or stock record reference" /></label>
      </>}
      </fieldset>
      <div className="modal-actions"><button className="button secondary" type="button" disabled={saving} onClick={onClose}>Cancel</button><button className="button primary" type="submit" disabled={saving || !databaseEnabled || !ready}>{saving ? <LoaderCircle className="spin" size={17} /> : <Plus size={17} />}{saving ? 'Saving…' : kind === 'knowledge' ? 'Save knowledge' : 'Save material'}</button></div>
    </form>
  </section></div>
}
