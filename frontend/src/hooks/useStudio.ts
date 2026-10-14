import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import { createProjectInput } from '../lib/projectDefaults'
import type { Catalog, Health, ProjectInput, Report } from '../types'
import type { Page, ReportTab } from '../lib/navigation'
import { useModalFocus } from './useModalFocus'

export function useStudio() {
  const [health, setHealth] = useState<Health | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [reports, setReports] = useState<Report[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [page, setPage] = useState<Page>('workspace')
  const [tab, setTab] = useState<ReportTab>('overview')
  const [input, setInput] = useState<ProjectInput | null>(null)
  const [editing, setEditing] = useState(false)
  const [approving, setApproving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [creating, setCreating] = useState<'knowledge' | 'material' | null>(null)
  const [recordSaving, setRecordSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [knowledgeVersion, setKnowledgeVersion] = useState(0)

  async function load() {
    setError('')
    const results = await Promise.allSettled([
      api<Health>('/health'),
      api<Catalog>('/catalog'),
      api<Report[]>('/projects'),
    ])
    const failures: string[] = []
    if (results[0].status === 'fulfilled') {
      const runtime = results[0].value
      setHealth(runtime)
    } else {
      setHealth(null)
      failures.push(results[0].reason.message)
    }
    if (results[1].status === 'fulfilled') setCatalog(results[1].value)
    else {
      setCatalog(null)
      failures.push(results[1].reason.message)
    }
    if (results[2].status === 'fulfilled') setReports(results[2].value)
    else failures.push(results[2].reason.message)
    if (results[0].status === 'fulfilled' && results[1].status === 'fulfilled') {
      const runtime = results[0].value,
        business = results[1].value
      setInput((current) => current || createProjectInput(runtime.today, business))
    }
    if (failures.length) setError([...new Set(failures)].join(' '))
  }
  useEffect(() => {
    void load()
  }, [])

  const closeDialogs = useCallback(() => {
    setEditing(false)
    setApproving(false)
    setCreating(null)
  }, [])
  useModalFocus(editing || approving || !!creating, busy || recordSaving, closeDialogs)

  function recordSaved(message: string) {
    setCreating(null)
    setNotice(message)
    setKnowledgeVersion((value) => value + 1)
    void api<Catalog>('/catalog')
      .then(setCatalog)
      .catch((err) =>
        setError(`The record was saved, but refreshing the catalog failed: ${err.message}`),
      )
  }

  function newQuotation(scenario = 'shortage') {
    if (!health || !catalog) return
    setInput(createProjectInput(health.today, catalog, scenario))
    setEditing(true)
    setError('')
  }
  async function analyze(event?: FormEvent, replacement?: ProjectInput) {
    event?.preventDefault()
    const payload = replacement || input
    if (!payload) return
    setBusy(true)
    setError('')
    setEditing(false)
    try {
      const result = await api<Report>('/projects/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setReport(result)
      setInput(payload)
      setReports((current) => [result, ...current].slice(0, 50))
      setPage('workspace')
      setTab('overview')
    } catch (err) {
      setError((err as Error).message)
      setEditing(true)
    } finally {
      setBusy(false)
    }
  }
  async function prepareFreshQuotation() {
    if (!report) return
    const brief = { ...report.request }
    setBusy(true)
    setError('')
    try {
      const [runtime, business] = await Promise.all([
        api<Health>('/health'),
        api<Catalog>('/catalog'),
      ])
      setHealth(runtime)
      setCatalog(business)
      const expectedSource = runtime.storage_mode === 'supabase' ? 'supabase' : 'demo'
      if (business.data_source !== expectedSource) {
        throw new Error(
          `Switch business data to ${expectedSource === 'supabase' ? 'Supabase' : 'offline demo'} before analyzing a quotation for this execution environment.`,
        )
      }
      setInput(brief)
      setApproving(false)
      setEditing(true)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  function openReport(value: Report) {
    setReport(value)
    setInput(value.request)
    setPage('workspace')
    setTab('overview')
    setError('')
  }
  function download() {
    if (!report) return
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }),
    )
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `royal-blinds-demo-${report.id.slice(0, 8)}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }
  async function approve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!report) return
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      const result = await api<Report>(`/projects/${report.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({
          reviewer: form.get('reviewer'),
          measurements_confirmed: form.get('measurements') === 'on',
          specification_confirmed: form.get('specification') === 'on',
          commercial_terms_confirmed: form.get('commercial') === 'on',
          execution_confirmed: form.get('execution') === 'on',
        }),
      })
      setReport(result)
      setReports((current) => current.map((item) => (item.id === result.id ? result : item)))
      setApproving(false)
      setTab('execution')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const updateExecution = useCallback((value: Report) => {
    setReport((current) => (current?.id === value.id ? value : current))
    setReports((current) => current.map((item) => (item.id === value.id ? value : item)))
  }, [])

  const executionSource = health?.storage_mode === 'supabase' ? 'supabase' : 'demo'
  const executionSourceIssue =
    report &&
    health &&
    !report.execution?.work_order &&
    report.data_snapshot?.data_source !== executionSource
      ? `This saved quotation ${report.data_snapshot ? 'uses a different business data source' : 'has no captured business data'}. Create a fresh quotation using ${executionSource === 'supabase' ? 'Supabase' : 'offline demo'} business data and review it before execution.`
      : null

  return {
    health,
    catalog,
    reports,
    report,
    page,
    tab,
    input,
    busy,
    error,
    notice,
    expanded,
    approving,
    editing,
    recordSaving,
    creating,
    knowledgeVersion,
    executionSourceIssue,
    setPage,
    setTab,
    setInput,
    setEditing,
    setApproving,
    setError,
    setNotice,
    setExpanded,
    setCreating,
    newQuotation,
    load,
    analyze,
    approve,
    prepareFreshQuotation,
    openReport,
    updateExecution,
    download,
    setRecordSaving,
    recordSaved,
  }
}
