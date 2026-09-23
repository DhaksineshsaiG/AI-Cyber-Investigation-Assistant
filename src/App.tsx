import { useEffect, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowRight, Bot, CalendarDays, Check, ChevronRight,
  Clock3, FileDown, FileText, FolderOpen, Mail, MapPin, Network, Phone, Plus, RefreshCw,
  ScanText, Search, ShieldCheck, Sparkles, Trash2, Upload, Users, X
} from 'lucide-react'
import { api } from './services/api'
import type { CaseItem, EvidenceItem, DashboardData } from './types/investigation'

const workflow = [
  'Upload Digital Evidence',
  'OCR & Text Extraction',
  'AI & NLP Processing',
  'LLM Analysis',
  'Timeline Generation',
  'Investigation Report'
]

export default function App() {
  const [currentCase, setCurrentCase] = useState<CaseItem | null>(null)
  const [allCases, setAllCases] = useState<CaseItem[]>([])
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([])
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [stage, setStage] = useState<'idle' | 'uploading' | 'processing' | 'complete'>('idle')
  const [dragging, setDragging] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Modals
  const [showCaseFilesModal, setShowCaseFilesModal] = useState(false)
  const [showTimelineModal, setShowTimelineModal] = useState(false)
  const [showNewCaseModal, setShowNewCaseModal] = useState(false)
  const [selectedFilePreview, setSelectedFilePreview] = useState<EvidenceItem | null>(null)

  const fileInput = useRef<HTMLInputElement>(null)

  // Initialize or fetch active case on mount
  useEffect(() => {
    initApp()
  }, [])

  const initApp = async () => {
    try {
      setErrorMessage(null)
      const cases = await api.listCases()
      setAllCases(cases)

      const savedCaseId = localStorage.getItem('active_case_id')
      let active = cases.find(c => c.case_id === savedCaseId)

      if (!active && cases.length > 0) {
        active = cases[0]
      }

      if (!active) {
        // Create initial production case
        active = await api.createCase(
          'Digital Evidence Investigation - Operation Horizon',
          'Lead Cyber Forensics Unit',
          'Primary repository case for digital forensics analysis'
        )
        setAllCases([active])
      }

      await switchCase(active)
    } catch (err: any) {
      console.error('Failed to initialize case:', err)
      setErrorMessage(err.message || 'Unable to connect to investigation backend API. Ensure the backend is running.')
    }
  }

  const switchCase = async (targetCase: CaseItem) => {
    try {
      setCurrentCase(targetCase)
      localStorage.setItem('active_case_id', targetCase.case_id)
      setStage('idle')

      // Load evidence
      const files = await api.listEvidence(targetCase.case_id)
      setEvidenceList(files)

      // Load dashboard state
      const dash = await api.getDashboard(targetCase.case_id)
      setDashboardData(dash)
      if (dash && dash.evidence_count > 0 && dash.keywords.length > 0) {
        setStage('complete')
      }
    } catch (err: any) {
      console.error('Error switching case:', err)
      setErrorMessage('Failed to load case data.')
    }
  }

  const handleCreateCase = async (title: string, investigator: string, description: string) => {
    try {
      setErrorMessage(null)
      const newCase = await api.createCase(title, investigator, description)
      setAllCases(prev => [newCase, ...prev])
      await switchCase(newCase)
      setShowNewCaseModal(false)
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to create new case.')
    }
  }

  const handleFilesUpload = async (incomingFiles: FileList | File[]) => {
    if (!currentCase) return
    const fileArray = Array.from(incomingFiles)
    if (fileArray.length === 0) return

    try {
      setErrorMessage(null)
      setStage('uploading')
      const uploaded = await api.uploadEvidence(currentCase.case_id, fileArray)
      setEvidenceList(prev => [...uploaded, ...prev])
      setStage('idle')

      // Refresh dashboard view
      const updatedDash = await api.getDashboard(currentCase.case_id)
      setDashboardData(updatedDash)
    } catch (err: any) {
      setStage('idle')
      const msg = err.response?.data?.detail || err.message || 'Error uploading evidence files.'
      setErrorMessage(msg)
    }
  }

  const handleDeleteEvidence = async (evidenceId: string) => {
    if (!currentCase) return
    try {
      await api.deleteEvidence(currentCase.case_id, evidenceId)
      setEvidenceList(prev => prev.filter(e => e.evidence_id !== evidenceId))
      const updatedDash = await api.getDashboard(currentCase.case_id)
      setDashboardData(updatedDash)
    } catch (err: any) {
      setErrorMessage('Failed to remove evidence file.')
    }
  }

  const runAnalysis = async () => {
    if (!currentCase) return
    if (evidenceList.length === 0) {
      setErrorMessage('Please upload at least one evidence file to analyze.')
      return
    }

    try {
      setErrorMessage(null)
      setStage('processing')
      const res = await api.analyzeCase(currentCase.case_id)
      setDashboardData(res)
      setStage('complete')
    } catch (err: any) {
      setStage('idle')
      const msg = err.response?.data?.detail || err.message || 'Investigation pipeline failed.'
      setErrorMessage(msg)
    }
  }

  const getEntityIcon = (title: string) => {
    switch (title) {
      case 'Names': return Users
      case 'Dates': return CalendarDays
      case 'Phone Numbers': return Phone
      case 'Email Addresses': return Mail
      default: return MapPin
    }
  }

  return (
    <div className="min-h-screen bg-mist">
      {/* Top Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-navy text-white shadow-lg shadow-slate-300/60">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-ink sm:text-base">
                AI Cyber Investigation Assistant
              </h1>
              <p className="text-xs text-slate-500">Digital evidence intelligence workspace</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {currentCase && (
              <button
                onClick={() => window.open(api.getReportPdfUrl(currentCase.case_id), '_blank')}
                className="hidden items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-teal-500 hover:bg-teal-50 hover:text-teal-800 sm:flex"
                title="Download formal forensic investigation report as PDF"
              >
                <FileDown size={14} className="text-teal-600" /> Export PDF Report
              </button>
            )}

            <button
              onClick={() => setShowNewCaseModal(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800"
            >
              <Plus size={14} /> New Case
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:py-10">
        {errorMessage && (
          <div className="mb-6 flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} className="shrink-0 text-rose-600" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-800">
              <X size={16} />
            </button>
          </div>
        )}

        {/* Hero Banner */}
        <section className="mb-8 rounded-2xl bg-navy px-6 py-7 text-white shadow-xl shadow-slate-300/50 sm:px-8">
          <p className="mb-2 flex items-center gap-2 text-sm font-medium text-teal-300">
            <Sparkles size={16} /> Investigation workspace
          </p>
          <h2 className="max-w-2xl text-2xl font-bold tracking-tight sm:text-3xl">
            Turn complex digital evidence into clear investigative leads.
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
            Upload case materials to extract entities, identify patterns, and build a defensible timeline—all in one place.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-2 text-xs text-slate-300">
            {workflow.map((step, index) => (
              <span key={step} className="flex items-center gap-2">
                <span className={index === 0 ? 'font-semibold text-teal-300' : ''}>{step}</span>
                {index < workflow.length - 1 && <ArrowRight size={13} className="text-slate-500" />}
              </span>
            ))}
          </div>
        </section>

        {/* Evidence Intake Section */}
        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-bold text-ink">Evidence intake</h2>
              <p className="mt-1 text-sm text-slate-500">
                {currentCase?.title || 'Add files to begin your investigation.'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {allCases.length > 1 && (
                <select
                  value={currentCase?.case_id || ''}
                  onChange={e => {
                    const sel = allCases.find(c => c.case_id === e.target.value)
                    if (sel) switchCase(sel)
                  }}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500"
                >
                  {allCases.map(c => (
                    <option key={c.case_id} value={c.case_id}>{c.case_id} - {c.title.substring(0, 30)}</option>
                  ))}
                </select>
              )}
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                Case ID: {currentCase?.case_id || 'INITIALIZING'}
              </span>
            </div>
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleFilesUpload(e.dataTransfer.files) }}
            onClick={() => fileInput.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed px-5 py-9 text-center transition ${
              dragging ? 'border-teal-500 bg-teal-50' : 'border-slate-200 bg-slate-50 hover:border-teal-400 hover:bg-teal-50/40'
            }`}
          >
            <div className="mx-auto mb-3 grid size-11 place-items-center rounded-full bg-teal-100 text-teal-700">
              <Upload size={20} />
            </div>
            <p className="text-sm font-semibold text-slate-700">
              Drop evidence files here, or <span className="text-teal-700">browse files</span>
            </p>
            <p className="mt-2 text-xs text-slate-500">
              PDF, DOCX, TXT, CSV, JSON, images (PNG, JPG), chat logs, and emails
            </p>
            <input
              ref={fileInput}
              type="file"
              multiple
              className="hidden"
              onChange={e => e.target.files && handleFilesUpload(e.target.files)}
            />
          </div>

          {/* Ingested Evidence List */}
          {evidenceList.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Ingested Evidence Vault ({evidenceList.length} files)
              </p>
              {evidenceList.map(ev => (
                <div key={ev.evidence_id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="flex min-w-0 items-center gap-2 text-slate-700">
                    <FileText size={16} className="shrink-0 text-teal-600" />
                    <span className="truncate font-medium">{ev.original_filename}</span>
                    <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                      {ev.file_type}
                    </span>
                    <span className="text-xs text-slate-400">{(ev.file_size / 1024).toFixed(0)} KB</span>
                    <span className="hidden font-mono text-[10px] text-slate-400 md:inline" title={ev.sha256_hash}>
                      SHA-256: {ev.sha256_hash.substring(0, 12)}...
                    </span>
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={e => { e.stopPropagation(); setSelectedFilePreview(ev) }}
                      className="rounded px-2 py-1 text-xs font-semibold text-teal-700 hover:bg-teal-50"
                    >
                      View
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); handleDeleteEvidence(ev.evidence_id) }}
                      className="p-1 text-slate-400 hover:text-rose-500"
                      title="Remove file"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Action Bar */}
          <div className="mt-5 flex flex-col items-stretch justify-between gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center">
            <p className="text-xs text-slate-500">
              Evidence is hashed with SHA-256 and immutably preserved in the case vault.
            </p>
            <button
              disabled={stage === 'processing' || stage === 'uploading' || evidenceList.length === 0}
              onClick={runAnalysis}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-teal-400"
            >
              {stage === 'processing' ? (
                <>
                  <Activity className="animate-spin" size={17} /> Running Forensic Pipeline...
                </>
              ) : stage === 'uploading' ? (
                <>
                  <Activity className="animate-spin" size={17} /> Ingesting & Hashing Evidence...
                </>
              ) : (
                <>
                  <ScanText size={17} /> Analyze Evidence
                </>
              )}
            </button>
          </div>
        </section>

        {/* Processing State Animation */}
        {stage === 'processing' && (
          <section className="mb-8 overflow-hidden rounded-2xl border border-teal-100 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="grid size-11 place-items-center rounded-full bg-teal-100 text-teal-700">
                <Bot className="animate-pulse" />
              </div>
              <div className="flex-1">
                <div className="mb-2 flex justify-between text-sm">
                  <span className="font-semibold text-ink">Processing investigation evidence</span>
                  <span className="text-teal-700 font-medium">Extracting Text, Running spaCy NER & Groq AI</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full w-2/3 animate-pulse rounded-full bg-teal-500" />
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Executing multi-format text extraction, OCR, forensic entity recognition, suspicious keyword taxonomy, and timeline correlation.
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Live Results Dashboard */}
        {stage !== 'processing' && dashboardData && (
          <ResultsSection
            dashboard={dashboardData}
            currentCase={currentCase}
            onOpenCaseFiles={() => setShowCaseFilesModal(true)}
            onOpenTimeline={() => setShowTimelineModal(true)}
          />
        )}
      </main>

      {/* Case Files Modal */}
      {showCaseFilesModal && (
        <CaseFilesModal
          evidenceList={evidenceList}
          onClose={() => setShowCaseFilesModal(false)}
          onSelectPreview={ev => setSelectedFilePreview(ev)}
        />
      )}

      {/* Full Timeline Modal */}
      {showTimelineModal && dashboardData && (
        <FullTimelineModal
          timeline={dashboardData.timeline}
          onClose={() => setShowTimelineModal(false)}
        />
      )}

      {/* New Case Modal */}
      {showNewCaseModal && (
        <NewCaseModal
          onCreate={handleCreateCase}
          onClose={() => setShowNewCaseModal(false)}
        />
      )}

      {/* Extracted Text Preview Modal */}
      {selectedFilePreview && (
        <FilePreviewModal
          evidence={selectedFilePreview}
          onClose={() => setSelectedFilePreview(null)}
        />
      )}
    </div>
  )
}

function ResultsSection({
  dashboard,
  currentCase,
  onOpenCaseFiles,
  onOpenTimeline
}: {
  dashboard: DashboardData
  currentCase: CaseItem | null
  onOpenCaseFiles: () => void
  onOpenTimeline: () => void
}) {
  const hasAnalyzedData = dashboard.stats.documents > 0

  return (
    <section>
      <div className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-sm font-semibold text-teal-700">
            {hasAnalyzedData ? 'Analysis complete' : 'Case workspace initialized'}
          </p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-ink">
            Evidence analysis dashboard
          </h2>
        </div>
        <div className="flex items-center gap-3">
          {currentCase && (
            <button
              onClick={() => window.open(api.getReportPdfUrl(currentCase.case_id), '_blank')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-teal-600 bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 hover:bg-teal-100"
            >
              <FileDown size={14} /> Export Report
            </button>
          )}
          <button
            onClick={onOpenCaseFiles}
            className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-teal-700"
          >
            <FolderOpen size={17} /> View case files <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* 1. Evidence Summary */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-ink">Evidence Summary</h3>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
              {dashboard.sources_reviewed_label}
            </span>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            {dashboard.summary}
          </p>
          <div className="mt-5 grid grid-cols-3 divide-x divide-slate-100 border-y border-slate-100 py-3 text-center">
            <Stat value={String(dashboard.stats.documents)} label="Documents" />
            <Stat value={String(dashboard.stats.key_entities)} label="Key entities" />
            <Stat value={String(dashboard.stats.risk_signals)} label="Risk signals" />
          </div>
        </article>

        {/* 2. Suspicious Keywords */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-500" />
            <h3 className="font-bold text-ink">Suspicious Keywords</h3>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {dashboard.keywords.length > 0 ? (
              dashboard.keywords.slice(0, 10).map((kw) => (
                <span
                  key={kw.keyword}
                  title={`${kw.category} (${kw.count} hits)`}
                  className={`rounded-md px-2.5 py-1.5 text-xs font-semibold ${
                    kw.severity === 'high' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  {kw.keyword} <span className="opacity-75 text-[10px]">({kw.count})</span>
                </span>
              ))
            ) : (
              <p className="text-xs text-slate-400">No suspicious keywords flagged in uploaded files.</p>
            )}
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Extracted from evidence using the 10-category forensic risk taxonomy.
          </p>
        </article>

        {/* 3. Extracted Entities */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="mb-5 flex items-center gap-2">
            <Users size={18} className="text-teal-600" />
            <h3 className="font-bold text-ink">Extracted Entities</h3>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {dashboard.entity_groups.length > 0 ? (
              dashboard.entity_groups.map((group) => {
                const Icon = group.category === 'Names' ? Users :
                             group.category === 'Dates' ? CalendarDays :
                             group.category === 'Phone Numbers' ? Phone :
                             group.category === 'Email Addresses' ? Mail :
                             group.category === 'IP & System Addresses' ? Network : MapPin

                return (
                  <div key={group.title} className="rounded-xl border border-slate-100 p-3">
                    <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                      <span className={`grid size-6 place-items-center rounded-md ${group.tone}`}>
                        <Icon size={14} />
                      </span>
                      {group.title} ({group.items.length})
                    </div>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {group.items.slice(0, 8).map((item) => (
                        <p key={item} className="truncate text-sm text-slate-700" title={item}>
                          {item}
                        </p>
                      ))}
                      {group.items.length > 8 && (
                        <p className="text-xs font-semibold text-teal-700">
                          +{group.items.length - 8} more
                        </p>
                      )}
                    </div>
                  </div>
                )
              })
            ) : (
              <p className="text-sm text-slate-400 sm:col-span-2">
                Upload evidence to extract persons, dates, contact records, and system identifiers.
              </p>
            )}
          </div>
        </article>

        {/* 4. AI Generated Insights (Groq) */}
        <article className="rounded-2xl border border-slate-200 bg-gradient-to-br from-teal-600 to-cyan-700 p-5 text-white shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={18} />
              <h3 className="font-bold">AI Generated Insights</h3>
            </div>
            <p className="mt-4 text-sm leading-6 text-teal-50">
              {dashboard.ai_insights.summary}
            </p>

            {dashboard.ai_insights.findings && dashboard.ai_insights.findings.length > 0 && (
              <div className="mt-4 space-y-1.5 border-t border-teal-500/40 pt-3">
                <p className="text-xs font-bold uppercase tracking-wider text-teal-200">Key Evidence Observations</p>
                {dashboard.ai_insights.findings.slice(0, 3).map((f, i) => (
                  <p key={i} className="text-xs text-teal-100 leading-snug">• {f}</p>
                ))}
              </div>
            )}
          </div>

          <div className="mt-5 flex items-center gap-2 text-xs font-semibold text-teal-100 border-t border-teal-500/40 pt-3">
            <Check size={15} /> {dashboard.ai_insights.confidence_note || 'Evidence grounded analysis'}
          </div>
        </article>

        {/* 5. Cross-Evidence Correlation */}
        {dashboard.correlations && dashboard.correlations.length > 0 && (
          <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-3">
            <div className="mb-4 flex items-center gap-2">
              <Network size={18} className="text-teal-600" />
              <h3 className="font-bold text-ink">Cross-Evidence Correlation</h3>
              <span className="rounded-full bg-teal-50 px-2 py-0.5 text-xs font-semibold text-teal-700">
                Multi-source linkages
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {dashboard.correlations.map((corr, idx) => (
                <div key={idx} className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="rounded bg-slate-200/80 px-1.5 py-0.5 font-bold uppercase tracking-wider text-slate-600 text-[10px]">
                      {corr.entity_type}
                    </span>
                    <span className="font-semibold text-teal-700">{corr.occurrences} occurrence(s)</span>
                  </div>
                  <h4 className="mt-2 text-sm font-bold text-slate-800 truncate" title={corr.entity_value}>
                    {corr.entity_value}
                  </h4>
                  <p className="mt-1 text-xs text-slate-500">
                    Found in: <span className="font-medium text-slate-700">{corr.evidence_names.join(', ')}</span>
                  </p>
                </div>
              ))}
            </div>
          </article>
        )}

        {/* 6. Timeline of Events */}
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-3">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock3 size={18} className="text-teal-600" />
              <h3 className="font-bold text-ink">Timeline of Events</h3>
            </div>
            {dashboard.timeline.length > 3 && (
              <span className="text-xs font-semibold text-slate-500">
                Showing 3 of {dashboard.timeline.length} chronological events
              </span>
            )}
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {dashboard.timeline.length > 0 ? (
              dashboard.timeline.slice(0, 3).map((event, i) => (
                <div
                  key={`${event.time}-${i}`}
                  className="relative border-l border-slate-200 pl-5 md:border-l-0 md:border-t md:pt-5 md:pl-0"
                >
                  <span className={`absolute -left-1.5 top-0 size-3 rounded-full ${event.color} md:-top-1.5 md:left-0`} />
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-400">{event.time}</p>
                  <h4 className="mt-2 text-sm font-bold text-slate-800">{event.title}</h4>
                  <p className="mt-1 text-sm leading-5 text-slate-500 line-clamp-2" title={event.detail}>
                    {event.detail}
                  </p>
                  <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-400">
                    <span className="truncate">Source: {event.source_evidence}</span>
                    {event.has_location && <MapPin size={13} className="shrink-0 text-rose-500" />}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400 md:col-span-3">
                No chronological timestamp markers detected in evidence.
              </p>
            )}
          </div>

          {dashboard.timeline.length > 0 && (
            <button
              onClick={onOpenTimeline}
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-800"
            >
              Open full timeline ({dashboard.timeline.length} events) <ArrowRight size={16} />
            </button>
          )}
        </article>
      </div>
    </section>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="text-lg font-bold text-ink">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  )
}

/* Modals */

function CaseFilesModal({
  evidenceList,
  onClose,
  onSelectPreview
}: {
  evidenceList: EvidenceItem[]
  onClose: () => void
  onSelectPreview: (ev: EvidenceItem) => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-lg font-bold text-ink">Case Evidence Repository & Chain of Custody</h3>
            <p className="text-xs text-slate-500">Verified digital evidence files and cryptographic integrity hashes</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-3 py-2.5">Evidence ID</th>
                <th className="px-3 py-2.5">Original Filename</th>
                <th className="px-3 py-2.5">Format</th>
                <th className="px-3 py-2.5">Size</th>
                <th className="px-3 py-2.5">SHA-256 Hash</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {evidenceList.map(ev => (
                <tr key={ev.evidence_id} className="hover:bg-slate-50/80">
                  <td className="px-3 py-2.5 font-mono text-slate-600">{ev.evidence_id}</td>
                  <td className="px-3 py-2.5 font-medium text-slate-800">{ev.original_filename}</td>
                  <td className="px-3 py-2.5"><span className="rounded bg-slate-100 px-1.5 py-0.5 font-bold text-slate-600">{ev.file_type}</span></td>
                  <td className="px-3 py-2.5 text-slate-500">{(ev.file_size / 1024).toFixed(1)} KB</td>
                  <td className="px-3 py-2.5 font-mono text-[11px] text-slate-500" title={ev.sha256_hash}>
                    {ev.sha256_hash.substring(0, 16)}...
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                      {ev.status}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <button
                      onClick={() => onSelectPreview(ev)}
                      className="text-xs font-semibold text-teal-600 hover:text-teal-800"
                    >
                      View Text
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function FullTimelineModal({
  timeline,
  onClose
}: {
  timeline: any[]
  onClose: () => void
}) {
  const [filterQuery, setFilterQuery] = useState('')

  const filtered = timeline.filter(evt =>
    evt.title.toLowerCase().includes(filterQuery.toLowerCase()) ||
    evt.detail.toLowerCase().includes(filterQuery.toLowerCase()) ||
    evt.source_evidence.toLowerCase().includes(filterQuery.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-lg font-bold text-ink">Chronological Investigation Timeline</h3>
            <p className="text-xs text-slate-500">Complete normalized temporal sequence of events across evidence</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <div className="mb-4 flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
          <Search size={16} className="text-slate-400" />
          <input
            type="text"
            placeholder="Filter timeline by keyword, suspect, or source file..."
            value={filterQuery}
            onChange={e => setFilterQuery(e.target.value)}
            className="w-full bg-transparent text-xs text-slate-800 placeholder-slate-400 focus:outline-none"
          />
        </div>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-2">
          {filtered.length > 0 ? (
            filtered.map((evt, idx) => (
              <div key={idx} className="flex gap-4 rounded-xl border border-slate-100 bg-slate-50/50 p-4">
                <span className={`size-3 shrink-0 rounded-full mt-1.5 ${evt.color}`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">{evt.time}</span>
                    <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                      {evt.source_evidence}
                    </span>
                  </div>
                  <h4 className="mt-1 font-bold text-slate-800 text-sm">{evt.title}</h4>
                  <p className="mt-1 text-sm text-slate-600 leading-relaxed">{evt.detail}</p>
                </div>
              </div>
            ))
          ) : (
            <p className="py-8 text-center text-sm text-slate-400">No events matched your filter.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function NewCaseModal({
  onCreate,
  onClose
}: {
  onCreate: (title: string, investigator: string, description: string) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState('')
  const [investigator, setInvestigator] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onCreate(title.trim(), investigator.trim(), description.trim())
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-bold text-ink">Create New Investigation Case</h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-slate-700">Case Title *</label>
            <input
              type="text"
              required
              placeholder="e.g. Unauthorized Vendor Data Access Investigation"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700">Lead Investigator</label>
            <input
              type="text"
              placeholder="e.g. Detective R. Kumar / Forensics Unit"
              value={investigator}
              onChange={e => setInvestigator(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="font-semibold text-slate-700">Case Description</label>
            <textarea
              rows={3}
              placeholder="Brief context regarding the incident and evidence origin..."
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-2 font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-teal-600 px-4 py-2 font-semibold text-white hover:bg-teal-700"
            >
              Create Case
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function FilePreviewModal({
  evidence,
  onClose
}: {
  evidence: EvidenceItem
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-ink">{evidence.original_filename}</h3>
            <p className="font-mono text-xs text-slate-400">SHA-256: {evidence.sha256_hash}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto rounded-lg bg-slate-50 p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap">
          {evidence.extracted_text_preview ? (
            evidence.extracted_text_preview
          ) : (
            <span className="text-slate-400 italic">
              Extracted text will appear here after clicking "Analyze Evidence".
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
