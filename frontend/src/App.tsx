import HomePage from './pages/HomePage'
import ProjectWorkspace from './pages/ProjectWorkspace'
import ProjectsPage from './pages/ProjectsPage'
import MaterialsPage from './pages/MaterialsPage'
import WorkflowPage from './pages/WorkflowPage'
import ProjectForm from './components/forms/ProjectForm'
import ApprovalDialog from './components/forms/ApprovalDialog'
import BusyOverlay from './components/common/BusyOverlay'
import AppShell from './components/layout/AppShell'
import KnowledgeStudio from './features/knowledge/KnowledgeStudio'
import RecordDialog from './components/forms/RecordDialog'
import { createProjectInput } from './lib/projectDefaults'
import { useStudio } from './hooks/useStudio'

export default function App() {
  const {
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
  } = useStudio()
  return (
    <AppShell
      health={health}
      catalog={catalog}
      reports={reports}
      page={page}
      busy={busy}
      error={error}
      notice={notice}
      setPage={setPage}
      setError={setError}
      setNotice={setNotice}
      setCreating={setCreating}
      newQuotation={newQuotation}
      load={load}
      dialogs={
        <>
          {creating && catalog && (
            <RecordDialog
              kind={creating}
              catalog={catalog}
              databaseEnabled={catalog.data_source === 'supabase'}
              onClose={() => setCreating(null)}
              onSaved={recordSaved}
              onSaving={setRecordSaving}
            />
          )}
          {editing && input && catalog && (
            <ProjectForm
              health={health}
              catalog={catalog}
              input={input}
              busy={busy}
              error={error}
              setInput={setInput}
              setEditing={setEditing}
              analyze={analyze}
            />
          )}
          {approving && report && (
            <ApprovalDialog
              report={report}
              busy={busy}
              error={error}
              setApproving={setApproving}
              approve={approve}
            />
          )}
          {busy && <BusyOverlay health={health} approving={approving} />}
        </>
      }
    >
      {page === 'knowledge' && (
        <KnowledgeStudio
          refreshVersion={knowledgeVersion}
          quoteReady={!!health && !!catalog && !busy}
          onQuote={(product) => {
            if (!health || !catalog) return
            const next = createProjectInput(health.today, catalog, 'ready')
            setInput({
              ...next,
              product,
              brief: `Supply and install ${catalog.products[product]?.name || product}. Confirm the fabric sample, measurements and delivery before approval.`,
            })
            setEditing(true)
          }}
        />
      )}
      {page === 'workspace' &&
        (!report ? (
          <HomePage
            health={health}
            catalog={catalog}
            busy={busy}
            setPage={setPage}
            newQuotation={newQuotation}
          />
        ) : (
          <ProjectWorkspace
            report={report}
            tab={tab}
            busy={busy}
            expanded={expanded}
            executionSourceIssue={executionSourceIssue}
            setTab={setTab}
            setInput={setInput}
            setEditing={setEditing}
            setApproving={setApproving}
            setExpanded={setExpanded}
            analyze={analyze}
            prepareFreshQuotation={prepareFreshQuotation}
            updateExecution={updateExecution}
            download={download}
          />
        ))}
      {page === 'projects' && <ProjectsPage reports={reports} openReport={openReport} />}
      {page === 'inventory' && <MaterialsPage catalog={catalog} load={load} />}
      {page === 'workflow' && <WorkflowPage />}
    </AppShell>
  )
}
