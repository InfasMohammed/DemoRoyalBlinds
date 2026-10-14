import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowUpRight,
  BookOpen,
  CircleAlert,
  FileText,
  Layers3,
  LoaderCircle,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { api } from '../../api'
import type {
  ProjectInput,
  KnowledgeProduct,
  KnowledgePortfolio,
  KnowledgeAnswer,
  KnowledgeQuestion,
} from '../../types'

export default function KnowledgeStudio({
  onQuote,
  quoteReady,
  refreshVersion = 0,
}: {
  onQuote: (product: ProjectInput['product']) => void
  quoteReady: boolean
  refreshVersion?: number
}) {
  const [portfolio, setPortfolio] = useState<KnowledgePortfolio | null>(null)
  const [category, setCategory] = useState('')
  const [question, setQuestion] = useState('What outdoor shade products does Royal Blinds offer?')
  const [answer, setAnswer] = useState<KnowledgeAnswer | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    try {
      setPortfolio(await api<KnowledgePortfolio>('/knowledge/portfolio'))
      setError('')
    } catch (err) {
      setError((err as Error).message)
    }
  }
  useEffect(() => {
    setAnswer(null)
    void load()
  }, [refreshVersion])

  async function ask(event?: FormEvent, replacement?: KnowledgeQuestion) {
    event?.preventDefault()
    setBusy(true)
    setError('')
    const values = replacement || { question }
    try {
      setAnswer(
        await api<KnowledgeAnswer>('/knowledge/ask', {
          method: 'POST',
          body: JSON.stringify({
            question: values.question,
            category: values.category || null,
            product_id: values.product_id || null,
          }),
        }),
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  function explore(product: KnowledgeProduct) {
    const query = {
      question: `What does the supplied website say about ${product.name}?`,
      category: product.category,
      product_id: product.id,
    }
    setQuestion(query.question)
    void ask(undefined, query)
  }
  const names: Record<string, string> = {
    company: 'Company profile',
    ...Object.fromEntries((portfolio?.categories || []).map((item) => [item.id, item.name])),
  }
  const answerModeNames: Record<string, string> = {
    catalog: 'Catalog answer',
    llm: 'RAG answer',
    extractive: 'Source excerpts',
    extractive_fallback: 'Source excerpts · AI unavailable',
    evidence_gap: 'Human review',
    no_evidence: 'No evidence',
  }
  const retrievalModeNames: Record<string, string> = {
    product_catalog: 'Complete product catalog lookup',
    supabase_vector: 'Supabase vector retrieval',
    local_keyword: 'Local keyword retrieval',
  }
  return (
    <div className="knowledge-studio">
      {error && (
        <div className="error-banner" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
          <button onClick={() => void load()}>Retry</button>
        </div>
      )}
      <section className="card knowledge-intro">
        <div className="icon-box green">
          <BookOpen size={23} />
        </div>
        <div>
          <h2>One portfolio. Three areas of expertise.</h2>
          <p>
            Internal shades, external shades and smart control options, grounded in the content you
            supplied.
          </p>
        </div>
        <span className="pill neutral">
          {portfolio
            ? `${portfolio.products.length} product types · ${portfolio.chunk_count} passages`
            : 'Loading sources'}
        </span>
      </section>
      <section className="card knowledge-assistant">
        <div className="section-heading">
          <div>
            <span className="eyebrow">SOURCE-LINKED PRODUCT DISCOVERY</span>
            <h3>Ask the knowledge assistant</h3>
          </div>
          <Sparkles size={20} />
        </div>
        <form onSubmit={(event) => void ask(event)}>
          <label htmlFor="knowledge-question">
            Your product question
            <textarea
              id="knowledge-question"
              rows={2}
              minLength={3}
              maxLength={2000}
              required
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <div className="knowledge-controls">
            <button className="button primary" disabled={busy || !portfolio} type="submit">
              {busy ? <LoaderCircle className="spin" size={17} /> : <Search size={17} />}
              {busy ? 'Retrieving sources…' : 'Find an answer'}
            </button>
          </div>
        </form>
        <div className="knowledge-examples">
          {[
            { text: 'Outdoor product range', query: 'What outdoor shade products are listed?' },
            {
              text: 'Phone & battery controls',
              query:
                'Can motorized roller blinds use smartphone control and a rechargeable battery?',
            },
            {
              text: 'Missing wind ratings',
              query: 'What is the maximum wind speed rating for awnings?',
            },
          ].map((item) => (
            <button
              disabled={busy || !portfolio}
              key={item.text}
              onClick={() => {
                setQuestion(item.query)
                void ask(undefined, { question: item.query })
              }}
            >
              {item.text}
              <ArrowUpRight size={12} />
            </button>
          ))}
        </div>
        {answer && (
          <div className="knowledge-answer" aria-live="polite">
            <div className="section-heading">
              <h4>
                {answer.needs_review ? 'More evidence required' : 'Findings from your sources'}
              </h4>
              <span className={`pill ${answer.needs_review ? 'amber' : 'green'}`}>
                {answerModeNames[answer.generation_mode]}
              </span>
            </div>
            <p className="answer-question">{answer.question}</p>
            <p className="answer-body">{answer.answer}</p>
            <div className="answer-mode">
              <BookOpen size={14} />
              {retrievalModeNames[answer.retrieval_mode]} ·{' '}
              {answer.knowledge_source === 'supabase'
                ? 'Supabase knowledge records'
                : 'Bundled website copy'}
            </div>
            {answer.warning && (
              <div className="inline-warning">
                <CircleAlert size={16} />
                {answer.warning}
              </div>
            )}
            {answer.generation_warning && (
              <div className="inline-warning">
                <CircleAlert size={16} />
                {answer.generation_warning}
              </div>
            )}
            <div className="knowledge-citations">
              {answer.citations.map((citation) => (
                <article key={citation.id}>
                  <a href={citation.source_url} target="_blank" rel="noopener noreferrer">
                    <FileText size={15} />
                    <span>
                      {citation.title}
                      <small>
                        {citation.heading} · {citation.id}
                      </small>
                    </span>
                    <ArrowUpRight size={15} />
                  </a>
                  <details>
                    <summary>
                      {answer.retrieval_mode === 'product_catalog'
                        ? 'Read catalog evidence'
                        : 'Read retrieved passage'}
                    </summary>
                    <p>{citation.content}</p>
                  </details>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>
      <div className="section-heading portfolio-heading">
        <div>
          <span className="eyebrow">THE COMPANY PRODUCT RANGE</span>
          <h3>Explore the portfolio</h3>
        </div>
        <span className="pill neutral">Website descriptions · model details to confirm</span>
      </div>
      <div className="portfolio-filters" role="group" aria-label="Product category filters">
        <button className={!category ? 'active' : ''} onClick={() => setCategory('')}>
          All products
        </button>
        {portfolio?.categories.map((item) => (
          <button
            className={category === item.id ? 'active' : ''}
            key={item.id}
            onClick={() => setCategory(item.id)}
          >
            {item.name}
          </button>
        ))}
      </div>
      {category === 'smart' ? (
        <div className="scenario-grid smart-options">
          {[
            {
              title: 'Remote control',
              text: 'The supplied copy describes remote operation of motorized blinds and shades.',
            },
            {
              title: 'Smartphone control',
              text: 'Smartphone control is described as an additional option. Supported apps, bridges and models require confirmation.',
            },
            {
              title: 'Battery or mains power',
              text: 'Motorized roller blinds are described with rechargeable battery or mains power options. Electrical specifications are not supplied.',
            },
          ].map((item) => (
            <section className="card" key={item.title}>
              <div className="icon-box green">
                <Sparkles size={23} />
              </div>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
              <button
                className="text-link"
                disabled={busy}
                onClick={() => {
                  const q = {
                    question: item.title + ' for motorized roller blinds',
                    category: 'smart',
                    product_id: '',
                  }
                  setQuestion(q.question)
                  void ask(undefined, q)
                }}
              >
                View source evidence <ArrowUpRight size={14} />
              </button>
            </section>
          ))}
        </div>
      ) : (
        <div className="portfolio-grid">
          {portfolio?.products
            .filter((p) => !category || p.category === category)
            .map((product) => (
              <article className={`card portfolio-card ${product.category}`} key={product.id}>
                <div className="portfolio-card-top">
                  <div className={`icon-box ${product.category === 'external' ? 'blue' : 'green'}`}>
                    <Layers3 size={23} />
                  </div>
                  <span className="eyebrow">{names[product.category]}</span>
                </div>
                <h3>{product.name}</h3>
                <p>
                  Listed in the supplied company portfolio. Model-specific specifications and
                  component requirements need confirmation.
                </p>
                <div className="portfolio-support">
                  <ShieldCheck size={14} />
                  {product.quote_products.length
                    ? 'Demo estimating model available'
                    : 'Technical enquiry · estimating model required'}
                </div>
                <button className="text-link" disabled={busy} onClick={() => explore(product)}>
                  Explore source evidence <ArrowUpRight size={14} />
                </button>
                {product.quote_products.length > 0 && (
                  <button
                    className="button secondary"
                    disabled={!quoteReady}
                    onClick={() =>
                      onQuote(
                        product.quote_products.includes('motorized_roller')
                          ? 'motorized_roller'
                          : product.quote_products[0],
                      )
                    }
                  >
                    Prepare demo estimate
                  </button>
                )}
              </article>
            ))}
        </div>
      )}
      <section className="card source-register">
        <div className="section-heading">
          <h3>Source register</h3>
          <span className="pill neutral">
            {portfolio?.data_source === 'supabase' ? 'Supabase sources' : 'Bundled source copy'}
          </span>
        </div>
        {portfolio?.documents.map((doc) => (
          <a key={doc.id} href={doc.source_url} target="_blank" rel="noopener noreferrer">
            <FileText size={18} />
            <span>
              {doc.title}
              <small>
                {doc.id} · {doc.sections} passages · {names[doc.category]}
              </small>
            </span>
            <ArrowUpRight size={16} />
          </a>
        ))}
        <p className="fine-print">
          Product listing links establish portfolio membership. General marketing claims do not
          verify structural ratings, certifications, motor compatibility or installation procedures.
        </p>
      </section>
    </div>
  )
}
