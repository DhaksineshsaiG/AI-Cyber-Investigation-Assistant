import { useEffect, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowRight, Bot, CalendarDays, Check, CheckCircle2, ChevronRight,
  Clock3, Cpu, ExternalLink, FileDown, FileText, FolderOpen, Mail, MapPin, Maximize2, Network,
  Phone, Plus, RefreshCw, ScanText, Search, Shield, ShieldAlert, ShieldCheck, Sparkles, Tag,
  Trash2, Upload, Users, X, LogOut, User as UserIcon, HelpCircle, ChevronDown, ChevronUp,
  FileCheck, Info
} from 'lucide-react'
import { api } from './services/api'
import type { CaseItem, EvidenceItem, DashboardData, User } from './types/investigation'
import LoginScreen from './components/LoginScreen'
import AdminUsersModal from './components/AdminUsersModal'

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(api.getStoredUser())
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(Boolean(api.getStoredToken()))
  const [currentCase, setCurrentCase] = useState<CaseItem | null>(null)
  const [allCases, setAllCases] = useState<CaseItem[]>([])
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([])
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [stage, setStage] = useState<'idle' | 'uploading' | 'processing' | 'complete'>('idle')
  const [dragging, setDragging] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false)

  // Modals
  const [showCaseFilesModal, setShowCaseFilesModal] = useState(false)
  const [showTimelineModal, setShowTimelineModal] = useState(false)
  const [showNewCaseModal, setShowNewCaseModal] = useState(false)
  const [showAiModal, setShowAiModal] = useState(false)
  const [showAdminModal, setShowAdminModal] = useState(false)
  const [showReassignModal, setShowReassignModal] = useState(false)
  const [reassignUserId, setReassignUserId] = useState('')
  const [selectedFilePreview, setSelectedFilePreview] = useState<EvidenceItem | null>(null)
  const [showLearnMore, setShowLearnMore] = useState(false)

  const fileInput = useRef<HTMLInputElement>(null)

  // Register unauthorized response interceptor and validate session
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setIsAuthenticated(false)
      setCurrentUser(null)
      setErrorMessage('Your session has expired. Please sign in again.')
    })

    if (isAuthenticated) {
      api.getMe()
        .then((user) => {
          setCurrentUser(user)
          initApp()
        })
        .catch(() => {
          setIsAuthenticated(false)
          setCurrentUser(null)
        })
    }
  }, [isAuthenticated])

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

      if (active) {
        await switchCase(active)
      } else {
        setCurrentCase(null)
        setEvidenceList([])
        setDashboardData(null)
        setStage('idle')
      }
    } catch (err: any) {
      console.error('Failed to initialize investigation:', err)
      setErrorMessage(err.response?.data?.detail || 'The investigation service is temporarily unavailable.')
    }
  }

  const handleLogout = async () => {
    try {
      await api.logout()
    } finally {
      setIsAuthenticated(false)
      setCurrentUser(null)
      setCurrentCase(null)
      setAllCases([])
      setEvidenceList([])
      setDashboardData(null)
      localStorage.removeItem('active_case_id')
    }
  }

  const handleDownloadPdf = async () => {
    if (!currentCase) return
    try {
      setIsDownloadingPdf(true)
      setErrorMessage(null)
      await api.downloadReportPdf(currentCase.case_id)
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to download investigation report.')
    } finally {
      setIsDownloadingPdf(false)
    }
  }

  const handleDeleteCase = async (caseId: string) => {
    if (currentUser?.role !== 'admin') return
    if (!window.confirm(`Are you sure you want to permanently delete investigation ${caseId}? All associated evidence and analysis records will be permanently erased.`)) {
      return
    }
    try {
      setErrorMessage(null)
      await api.deleteCase(caseId)
      const remaining = allCases.filter(c => c.case_id !== caseId)
      setAllCases(remaining)
      if (remaining.length > 0) {
        await switchCase(remaining[0])
      } else {
        setCurrentCase(null)
        setEvidenceList([])
        setDashboardData(null)
        setStage('idle')
        localStorage.removeItem('active_case_id')
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to delete investigation.')
    }
  }

  const handleReassignCase = async (targetUserId: string) => {
    if (!currentCase || currentUser?.role !== 'admin') return
    try {
      setErrorMessage(null)
      const updated = await api.reassignCase(currentCase.case_id, targetUserId.trim())
      setCurrentCase(updated)
      setAllCases(prev => prev.map(c => c.case_id === updated.case_id ? updated : c))
      setShowReassignModal(false)
      setReassignUserId('')
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to transfer investigation.')
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
      console.error('Error switching investigation:', err)
      setErrorMessage('Failed to load investigation details.')
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
      setErrorMessage(err.response?.data?.detail || 'Failed to create new investigation.')
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
    if (!window.confirm('Are you sure you want to remove this evidence file from the investigation?')) {
      return
    }
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
      setErrorMessage('Please upload at least one evidence file before starting the investigation.')
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

  if (!isAuthenticated || !currentUser) {
    return (
      <LoginScreen
        onLoginSuccess={(user) => {
          setCurrentUser(user)
          setIsAuthenticated(true)
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#1F2937]">
      {/* Top Header */}
      <header className="border-b border-[#E5E7EB] bg-white sticky top-0 z-40 shadow-xs">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          {/* Logo & Platform Name */}
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-[#C8102E] to-[#A50F26] text-white shadow-sm shadow-red-500/20">
              <ShieldCheck size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-tight text-[#1F2937] sm:text-base">
                  AI Cyber Investigation Assistant
                </h1>
                <span className="hidden md:inline-flex items-center rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2 py-0.5 text-[10px] font-bold text-[#C8102E]">
                  Digital Forensics
                </span>
              </div>
              <p className="text-xs text-[#6B7280]">Digital evidence intelligence workspace</p>
            </div>
          </div>

          {/* Action Bar & User Profile */}
          <div className="flex items-center gap-2 sm:gap-3">
            {currentUser.role === 'admin' && (
              <button
                onClick={() => setShowAdminModal(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#FECDD3] bg-[#FFF1F2] px-3 py-1.5 text-xs font-semibold text-[#C8102E] transition hover:bg-[#FFE4E6]"
                title="Manage user accounts and access permissions"
              >
                <Users size={14} className="text-[#C8102E]" />
                <span className="hidden sm:inline">Access Permissions</span>
              </button>
            )}

            {currentCase && (
              <button
                onClick={handleDownloadPdf}
                disabled={isDownloadingPdf}
                className="hidden items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-semibold text-[#1F2937] transition hover:border-[#C8102E] hover:text-[#C8102E] disabled:opacity-50 sm:flex shadow-2xs"
                title="Download formal investigation report as PDF"
              >
                <FileDown size={14} className="text-[#C8102E]" />
                {isDownloadingPdf ? 'Creating Report...' : 'Download Report'}
              </button>
            )}

            <button
              onClick={() => setShowNewCaseModal(true)}
              className="inline-flex items-center gap-1.5 rounded-lg btn-royal px-3.5 py-1.5 text-xs font-semibold shadow-xs transition"
            >
              <Plus size={14} /> Start New Investigation
            </button>

            {/* User Profile Pill */}
            <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-[#E5E7EB]">
              <div className="hidden md:block text-right">
                <div className="text-xs font-bold text-[#1F2937] leading-tight">{currentUser.display_name}</div>
                <div className="text-[10px] text-[#6B7280] font-mono">@{currentUser.user_id}</div>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                  currentUser.role === 'admin'
                    ? 'bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3]'
                    : 'bg-slate-100 text-[#1F2937] border border-[#E5E7EB]'
                }`}
              >
                {currentUser.role === 'admin' ? 'Administrator' : 'Investigator'}
              </span>

              <button
                onClick={handleLogout}
                className="rounded-lg p-1.5 text-[#6B7280] hover:bg-red-50 hover:text-[#C8102E] transition"
                title="Sign out of investigation session"
                aria-label="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {errorMessage && (
          <div className="mb-6 flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 animate-fadeIn">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} className="shrink-0 text-[#C8102E]" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-red-600 hover:text-red-900">
              <X size={16} />
            </button>
          </div>
        )}

        {!currentCase ? (
          <div className="rounded-2xl border border-dashed border-[#E5E7EB] bg-white p-12 text-center shadow-xs">
            <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#FFF1F2] text-[#C8102E] mb-4 border border-[#FECDD3]">
              <FolderOpen size={28} />
            </div>
            <h3 className="text-base font-bold text-[#1F2937]">No Investigations Found</h3>
            <p className="mt-1 text-sm text-[#6B7280] max-w-md mx-auto">
              {currentUser.role === 'admin'
                ? "No investigations are currently registered. Click 'Start New Investigation' to create the first dossier."
                : "You do not currently have any active investigations assigned. Click 'Start New Investigation' to begin."}
            </p>
            <button
              onClick={() => setShowNewCaseModal(true)}
              className="mt-5 inline-flex items-center gap-2 rounded-xl btn-royal px-4 py-2 text-xs font-semibold shadow-xs transition"
            >
              <Plus size={15} /> Start New Investigation
            </button>
          </div>
        ) : (
          <>
            {/* Overview Banner (Pure White + Royal Red Accent) */}
            <section className="mb-6 rounded-2xl bg-white p-6 shadow-xs border border-[#E5E7EB] border-l-4 border-l-[#C8102E]">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#C8102E]">
                    <ShieldCheck size={16} /> Digital Evidence & Investigation Workspace
                  </div>
                  <h2 className="mt-2 text-xl font-bold tracking-tight text-[#1F2937] sm:text-2xl">
                    Turn complex digital evidence into clear investigative leads.
                  </h2>
                  <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-[#6B7280]">
                    Upload documents, images, and chat logs to identify people, places and organisations, uncover possible connections, spot potential warning signs, and build an event timeline backed by grounded AI synthesis.
                  </p>
                </div>
                <div className="flex flex-row md:flex-col gap-2 shrink-0">
                  <button
                    onClick={() => setShowLearnMore(!showLearnMore)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-1.5 text-xs font-semibold text-[#1F2937] hover:border-[#C8102E] hover:text-[#C8102E] transition"
                  >
                    <HelpCircle size={14} className="text-[#C8102E]" />
                    <span>{showLearnMore ? 'Hide Details' : 'Learn More'}</span>
                    {showLearnMore ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* Expandable Educational Details */}
              {showLearnMore && (
                <div className="mt-4 pt-4 border-t border-[#E5E7EB] grid gap-3 sm:grid-cols-3 text-xs">
                  <div className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3.5">
                    <div className="font-bold text-[#1F2937] flex items-center gap-1.5 mb-1 text-[#C8102E]">
                      <FileCheck size={14} /> File Integrity Check
                    </div>
                    <p className="text-[#6B7280] leading-relaxed">
                      Checks whether the file's digital fingerprint matches the recorded value. This can help identify changes to a file.
                    </p>
                  </div>
                  <div className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3.5">
                    <div className="font-bold text-[#1F2937] flex items-center gap-1.5 mb-1 text-[#C8102E]">
                      <AlertTriangle size={14} /> Potential Warning Signs
                    </div>
                    <p className="text-[#6B7280] leading-relaxed">
                      Highlights patterns that may deserve closer examination. These are indicators, not proof of wrongdoing.
                    </p>
                  </div>
                  <div className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3.5">
                    <div className="font-bold text-[#1F2937] flex items-center gap-1.5 mb-1 text-[#C8102E]">
                      <Bot size={14} /> AI Investigation Summary
                    </div>
                    <p className="text-[#6B7280] leading-relaxed">
                      An AI-generated overview of the available evidence, findings and possible connections. Always review supporting evidence before drawing conclusions.
                    </p>
                  </div>
                </div>
              )}

              {/* Feature Pills */}
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[#6B7280]">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F8FAFC] px-3 py-1 font-medium border border-[#E5E7EB]">
                  <Shield size={12} className="text-[#C8102E]" /> Digital File Fingerprints (SHA-256)
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F8FAFC] px-3 py-1 font-medium border border-[#E5E7EB]">
                  <Users size={12} className="text-[#C8102E]" /> People, Places & Organisations
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F8FAFC] px-3 py-1 font-medium border border-[#E5E7EB]">
                  <Sparkles size={12} className="text-[#C8102E]" /> Grounded AI Investigation Summary
                </span>
              </div>
            </section>

            {/* Quick Live Statistics Bar */}
            <section className="mb-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
                <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">My Investigations</div>
                <div className="mt-1 text-2xl font-bold text-[#1F2937]">{allCases.length}</div>
                <div className="mt-0.5 text-[11px] text-[#6B7280]">Active dossiers in system</div>
              </div>
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
                <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Evidence Files</div>
                <div className="mt-1 text-2xl font-bold text-[#C8102E]">{evidenceList.length}</div>
                <div className="mt-0.5 text-[11px] text-[#6B7280]">Uploaded for this case</div>
              </div>
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
                <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Progress</div>
                <div className="mt-1 text-2xl font-bold text-[#1F2937]">
                  {dashboardData && dashboardData.stats.documents > 0 ? 'Examined' : 'Awaiting Review'}
                </div>
                <div className="mt-0.5 text-[11px] text-[#6B7280]">
                  {dashboardData?.stats.documents || 0} files examined
                </div>
              </div>
              <div className="rounded-xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
                <div className="text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider">Potential Warning Signs</div>
                <div className="mt-1 text-2xl font-bold text-[#D97706]">{dashboardData?.stats.risk_signals || 0}</div>
                <div className="mt-0.5 text-[11px] text-[#6B7280]">Flagged for verification</div>
              </div>
            </section>

            {/* Evidence Intake Section */}
            <section className="mb-8 rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs sm:p-6">
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#1F2937]">Upload Evidence</h2>
                  <p className="mt-0.5 text-xs text-[#6B7280]">
                    Upload documents, images and other supported files for examination.
                  </p>
                </div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  {allCases.length > 1 && (
                    <select
                      value={currentCase?.case_id || ''}
                      onChange={e => {
                        const sel = allCases.find(c => c.case_id === e.target.value)
                        if (sel) switchCase(sel)
                      }}
                      className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-2.5 py-1.5 text-xs font-semibold text-[#1F2937] focus:outline-none focus:border-[#C8102E]"
                    >
                      {allCases.map(c => (
                        <option key={c.case_id} value={c.case_id}>
                          {c.case_id} - {c.title.substring(0, 32)}{currentUser.role === 'admin' ? ` (@${c.owner_user_id || 'unassigned'})` : ''}
                        </option>
                      ))}
                    </select>
                  )}
                  <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-3 py-1 text-xs font-bold text-[#C8102E]">
                    Investigation ID: {currentCase?.case_id || 'INITIALIZING'}
                  </span>
                </div>
              </div>

              {/* Drag & Drop Zone */}
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={e => { e.preventDefault(); setDragging(false); handleFilesUpload(e.dataTransfer.files) }}
                onClick={() => fileInput.current?.click()}
                className={`cursor-pointer rounded-xl border-2 border-dashed px-5 py-8 text-center transition ${
                  dragging ? 'border-[#C8102E] bg-[#FFF1F2]' : 'border-[#E5E7EB] bg-[#F8FAFC] hover:border-[#FECDD3] hover:bg-[#FFF1F2]/50'
                }`}
              >
                <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3]">
                  <Upload size={22} />
                </div>
                <p className="text-sm font-semibold text-[#1F2937]">
                  Drop evidence files here, or <span className="text-[#C8102E] underline">browse files</span>
                </p>
                <p className="mt-1.5 text-xs text-[#6B7280]">
                  Supported file formats: PDF, DOCX, TXT, CSV, JSON, images (PNG, JPG), chat logs, and emails (up to 50MB per file)
                </p>
                <input
                  ref={fileInput}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={e => e.target.files && handleFilesUpload(e.target.files)}
                />
              </div>

              {/* Uploaded Evidence Vault */}
              {evidenceList.length > 0 && (
                <div className="mt-5 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">
                      Uploaded Evidence ({evidenceList.length} files)
                    </p>
                    <button
                      onClick={() => setShowCaseFilesModal(true)}
                      className="text-xs font-semibold text-[#C8102E] hover:underline"
                    >
                      View All in Evidence Handling History →
                    </button>
                  </div>
                  {evidenceList.map(ev => (
                    <div key={ev.evidence_id} className="flex items-center justify-between rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-3.5 py-2.5 text-sm hover:bg-white transition">
                      <span className="flex min-w-0 items-center gap-2 text-[#1F2937]">
                        <FileText size={16} className="shrink-0 text-[#C8102E]" />
                        <span className="truncate font-semibold text-xs sm:text-sm">{ev.original_filename}</span>
                        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-[#1F2937]">
                          {ev.file_type}
                        </span>
                        <span className="text-xs text-[#6B7280]">{(ev.file_size / 1024).toFixed(0)} KB</span>
                        <span className="hidden font-mono text-[10px] text-[#6B7280] md:inline" title={ev.sha256_hash}>
                          Fingerprint: {ev.sha256_hash.substring(0, 12)}...
                        </span>
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={e => { e.stopPropagation(); setSelectedFilePreview(ev) }}
                          className="rounded px-2.5 py-1 text-xs font-semibold text-[#C8102E] hover:bg-[#FFF1F2] transition"
                        >
                          View Content
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleDeleteEvidence(ev.evidence_id) }}
                          className="p-1 text-[#6B7280] hover:text-red-600 transition"
                          title="Remove evidence file"
                          aria-label="Remove evidence file"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Action Bar */}
              <div className="mt-5 flex flex-col items-stretch justify-between gap-3 border-t border-[#E5E7EB] pt-5 sm:flex-row sm:items-center">
                <p className="text-xs text-[#6B7280]">
                  Files are assigned a cryptographic digital fingerprint (SHA-256) upon upload and protected in the evidence vault.
                </p>
                <button
                  disabled={stage === 'processing' || stage === 'uploading' || evidenceList.length === 0}
                  onClick={runAnalysis}
                  className="inline-flex items-center justify-center gap-2 rounded-xl btn-royal px-5 py-2.5 text-sm font-semibold shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {stage === 'processing' ? (
                    <>
                      <Activity className="animate-spin" size={17} /> Examining Evidence...
                    </>
                  ) : stage === 'uploading' ? (
                    <>
                      <Activity className="animate-spin" size={17} /> Uploading & Calculating Fingerprints...
                    </>
                  ) : (
                    <>
                      <ScanText size={17} /> Investigate Evidence
                    </>
                  )}
                </button>
              </div>
            </section>

            {/* Processing State Banner */}
            {stage === 'processing' && (
              <section className="mb-8 overflow-hidden rounded-2xl border border-[#FECDD3] bg-white p-6 shadow-xs animate-fadeIn">
                <div className="flex items-center gap-4">
                  <div className="grid size-12 place-items-center rounded-full bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3]">
                    <Bot className="animate-pulse" size={24} />
                  </div>
                  <div className="flex-1">
                    <div className="mb-2 flex justify-between text-sm">
                      <span className="font-bold text-[#1F2937]">Investigating evidence files</span>
                      <span className="text-[#C8102E] font-semibold text-xs">Reading text, identifying entities & synthesizing findings</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full w-2/3 animate-pulse rounded-full bg-[#C8102E]" />
                    </div>
                    <p className="mt-2.5 text-xs text-[#6B7280]">
                      Extracting text from documents and images, identifying people and organisations, scanning for potential warning signs, and correlating chronological events.
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
                onOpenAiModal={() => setShowAiModal(true)}
                onExportPdf={handleDownloadPdf}
                isDownloadingPdf={isDownloadingPdf}
              />
            )}
          </>
        )}
      </main>

      {/* Case Files / Evidence Handling History Modal */}
      {showCaseFilesModal && (
        <CaseFilesModal
          evidenceList={evidenceList}
          currentCase={currentCase}
          currentUser={currentUser}
          onClose={() => setShowCaseFilesModal(false)}
          onSelectPreview={ev => setSelectedFilePreview(ev)}
          onDeleteCase={handleDeleteCase}
          onOpenReassign={() => setShowReassignModal(true)}
        />
      )}

      {/* Full Timeline Modal */}
      {showTimelineModal && dashboardData && (
        <FullTimelineModal
          timeline={dashboardData.timeline}
          onClose={() => setShowTimelineModal(false)}
        />
      )}

      {/* AI Investigation Summary Modal */}
      {showAiModal && dashboardData && (
        <AiInsightsModal
          dashboard={dashboardData}
          currentCase={currentCase}
          onClose={() => setShowAiModal(false)}
          onExportPdf={handleDownloadPdf}
          isDownloadingPdf={isDownloadingPdf}
        />
      )}

      {/* Start New Investigation Modal */}
      {showNewCaseModal && (
        <NewCaseModal
          onCreate={handleCreateCase}
          onClose={() => setShowNewCaseModal(false)}
        />
      )}

      {/* Admin Personnel & Access Modal */}
      {showAdminModal && currentUser?.role === 'admin' && (
        <AdminUsersModal
          currentUser={currentUser}
          onClose={() => setShowAdminModal(false)}
        />
      )}

      {/* Admin Transfer Investigation Modal */}
      {showReassignModal && currentCase && currentUser?.role === 'admin' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-[#E5E7EB]">
            <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <h3 className="text-base font-bold text-[#1F2937]">Transfer Investigation</h3>
              <button
                onClick={() => setShowReassignModal(false)}
                className="rounded-lg p-1 text-[#6B7280] hover:text-[#1F2937]"
              >
                <X size={18} />
              </button>
            </div>
            <p className="text-xs text-[#6B7280] mb-4 leading-relaxed">
              Transfer investigation <strong className="text-[#1F2937] font-mono">{currentCase.case_id}</strong> to another registered investigator or administrator by their User ID.
            </p>
            <form onSubmit={e => { e.preventDefault(); handleReassignCase(reassignUserId) }} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#1F2937] mb-1">Target User ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. inv_kumar or admin"
                  value={reassignUserId}
                  onChange={e => setReassignUserId(e.target.value)}
                  className="w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-xs focus:border-[#C8102E] focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-[#E5E7EB]">
                <button
                  type="button"
                  onClick={() => setShowReassignModal(false)}
                  className="rounded-lg border border-[#E5E7EB] px-3 py-1.5 text-xs font-semibold text-[#6B7280] hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!reassignUserId.trim()}
                  className="rounded-lg btn-royal px-4 py-1.5 text-xs font-semibold shadow-xs disabled:opacity-50"
                >
                  Confirm Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
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

interface ParsedObservation {
  title: string
  filename?: string
  size?: string
  hash?: string
  description: string
  source?: string
}

function parseObservation(text: string): ParsedObservation {
  const fileMatch = text.match(/['"]([^'"]+\.(?:png|jpg|jpeg|pdf|txt|csv|log|docx|json))['"]|\b([\w.-]+\.(?:png|jpg|jpeg|pdf|txt|csv|log|docx|json))\b/i)
  const filename = fileMatch ? (fileMatch[1] || fileMatch[2]) : undefined

  const hashMatch = text.match(/\b([a-f0-9]{64})\b/i)
  const hash = hashMatch ? hashMatch[1] : undefined

  const sizeMatch = text.match(/\b(\d+(?:,\d+)?\s*(?:bytes|KB|MB|GB))\b/i)
  const size = sizeMatch ? sizeMatch[1] : undefined

  let title = filename ? filename : 'Forensic Observation'
  if (!filename && text.includes(':')) {
    title = text.split(':')[0].trim()
  }

  let description = text.trim()
  if (hash) {
    description = description.replace(new RegExp(`\\(?SHA-?256:?\\s*${hash}\\)?`, 'i'), '').trim()
  }

  return {
    title,
    filename,
    size,
    hash,
    description: description || text.trim(),
    source: filename,
  }
}

function ObservationCard({ text, compact = false }: { text: string; compact?: boolean }) {
  const obs = parseObservation(text)

  return (
    <div className={`rounded-xl border border-[#E5E7EB] bg-white shadow-2xs hover:border-[#FECDD3] transition flex flex-col justify-between ${compact ? 'p-3' : 'p-4'}`}>
      <div>
        <div className="flex items-center justify-between gap-2 border-b border-[#E5E7EB] pb-2 mb-2">
          <div className="flex items-center gap-1.5 font-bold text-xs text-[#1F2937] truncate">
            <Search size={14} className="text-[#C8102E] shrink-0" />
            <span className="truncate" title={obs.filename || obs.title}>
              {obs.filename || obs.title}
            </span>
          </div>
          {obs.size && (
            <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-[#6B7280]">
              {obs.size}
            </span>
          )}
        </div>
        <p className={`text-xs leading-relaxed text-[#1F2937] break-words ${compact ? 'line-clamp-3' : ''}`}>
          {obs.description}
        </p>
      </div>

      {obs.hash && (
        <div className="mt-2.5 pt-2 border-t border-[#E5E7EB] text-[10px] font-mono text-[#6B7280]">
          <span className="font-semibold text-[#6B7280] block mb-0.5">Digital Fingerprint:</span>
          <span className="break-all font-mono select-all bg-[#F8FAFC] px-1.5 py-0.5 rounded border border-[#E5E7EB] block text-[#1F2937]" title={obs.hash}>
            {compact ? `${obs.hash.substring(0, 10)}...${obs.hash.substring(obs.hash.length - 8)}` : obs.hash}
          </span>
        </div>
      )}
    </div>
  )
}

function ResultsSection({
  dashboard,
  currentCase,
  onOpenCaseFiles,
  onOpenTimeline,
  onOpenAiModal,
  onExportPdf,
  isDownloadingPdf
}: {
  dashboard: DashboardData
  currentCase: CaseItem | null
  onOpenCaseFiles: () => void
  onOpenTimeline: () => void
  onOpenAiModal: () => void
  onExportPdf?: () => void
  isDownloadingPdf?: boolean
}) {
  const hasAnalyzedData = dashboard.stats.documents > 0

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-[#C8102E]">
            {hasAnalyzedData ? 'Investigation Analysis Complete' : 'Investigation Initialized'}
          </p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-[#1F2937]">
            Investigation Analysis & Findings
          </h2>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          {currentCase && onExportPdf && (
            <button
              onClick={onExportPdf}
              disabled={isDownloadingPdf}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#FECDD3] bg-[#FFF1F2] px-3.5 py-1.5 text-xs font-semibold text-[#C8102E] hover:bg-[#FFE4E6] transition disabled:opacity-50"
            >
              <FileDown size={14} /> {isDownloadingPdf ? 'Creating Report...' : 'Download Report'}
            </button>
          )}
          <button
            onClick={onOpenCaseFiles}
            className="flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-3.5 py-1.5 text-xs font-semibold text-[#1F2937] hover:border-[#C8102E] hover:text-[#C8102E] transition shadow-2xs"
          >
            <FolderOpen size={15} /> Uploaded Evidence <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 1. Investigation Summary */}
        <article className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <div>
                <h3 className="font-bold text-[#1F2937]">Investigation Summary</h3>
                <p className="text-xs text-[#6B7280] mt-0.5">Overview of findings across examined evidence files</p>
              </div>
              <span className="rounded-full bg-[#F8FAFC] border border-[#E5E7EB] px-2.5 py-1 text-xs font-semibold text-[#6B7280]">
                {dashboard.sources_reviewed_label}
              </span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[#1F2937] break-words">
              {dashboard.summary}
            </p>
          </div>
          <div className="mt-5 grid grid-cols-3 divide-x divide-[#E5E7EB] border-t border-[#E5E7EB] pt-4 text-center">
            <Stat value={String(dashboard.stats.documents)} label="Documents Examined" />
            <Stat value={String(dashboard.stats.key_entities)} label="People, Places & Orgs" />
            <Stat value={String(dashboard.stats.risk_signals)} label="Potential Warning Signs" />
          </div>
        </article>

        {/* 2. Potential Warning Signs */}
        <article className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-[#D97706]" />
                <div>
                  <h3 className="font-bold text-[#1F2937]">Potential Warning Signs</h3>
                </div>
              </div>
              <span className="rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-xs font-bold text-amber-700">
                {dashboard.keywords.length} Flagged
              </span>
            </div>
            <p className="text-[11px] text-[#6B7280] mt-2 mb-3">
              Highlights patterns that may deserve closer examination. These are indicators, not proof of wrongdoing.
            </p>
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {dashboard.keywords.length > 0 ? (
                dashboard.keywords.map((kw) => (
                  <div
                    key={kw.keyword}
                    title={`${kw.category} — ${kw.count} occurrences`}
                    className="flex items-center justify-between gap-2 rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] p-2 text-xs hover:border-[#FECDD3] transition"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`inline-block size-2 rounded-full shrink-0 ${kw.severity === 'high' ? 'bg-[#C8102E]' : 'bg-amber-500'}`} />
                      <span className="font-bold text-[#1F2937] truncate">{kw.keyword}</span>
                      <span className="rounded bg-slate-200 px-1.5 py-0.2 text-[10px] text-[#1F2937] font-medium truncate hidden sm:inline-block">
                        {kw.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${kw.severity === 'high' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                        {kw.severity}
                      </span>
                      <span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-mono font-bold text-[#1F2937] border border-[#E5E7EB]">
                        ×{kw.count}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-[#E5E7EB] bg-[#F8FAFC] p-6 text-center text-xs text-[#6B7280]">
                  No suspicious patterns flagged in uploaded evidence.
                </div>
              )}
            </div>
          </div>
          <p className="mt-3 text-[11px] leading-5 text-[#6B7280] border-t border-[#E5E7EB] pt-2.5">
            Classified using standard cyber investigation risk taxonomy.
          </p>
        </article>

        {/* 3. People, Places & Organisations */}
        <article className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Users size={18} className="text-[#C8102E]" />
                  <h3 className="font-bold text-[#1F2937]">People, Places & Organisations</h3>
                </div>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  Review names, locations and organisations identified in the uploaded material.
                </p>
              </div>
              <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-0.5 text-xs font-bold text-[#C8102E]">
                {dashboard.stats.key_entities} Items Found
              </span>
            </div>

            {dashboard.entity_groups && dashboard.entity_groups.some(g => g.items && g.items.length > 0) ? (
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                {dashboard.entity_groups.map((group) => {
                  const Icon = group.category === 'Names' ? Users :
                               group.category === 'Dates' ? CalendarDays :
                               group.category === 'Phone Numbers' ? Phone :
                               group.category === 'Email Addresses' ? Mail :
                               group.category === 'IP & System Addresses' ? Network : Shield

                  if (!group.items || group.items.length === 0) return null

                  return (
                    <div key={group.title} className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3 flex flex-col">
                      <div className="mb-2 flex items-center justify-between text-xs font-bold text-[#1F2937]">
                        <span className="flex items-center gap-1.5 truncate">
                          <Icon size={14} className="text-[#C8102E] shrink-0" />
                          {group.title}
                        </span>
                        <span className="rounded-full bg-slate-200 px-1.5 py-0.2 text-[10px] font-mono text-[#1F2937]">
                          {group.items.length}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto pr-1">
                        {group.items.map((item) => (
                          <span
                            key={item}
                            className="inline-flex items-center gap-1 rounded-md border border-[#E5E7EB] bg-white px-2 py-0.5 text-xs text-[#1F2937] shadow-2xs hover:border-[#FECDD3] transition max-w-full truncate"
                            title={item}
                          >
                            <span className="truncate">{item}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[#E5E7EB] bg-[#F8FAFC] p-8 text-center text-sm text-[#6B7280]">
                <Users size={28} className="mx-auto text-slate-400 mb-2" />
                <p className="font-semibold text-[#1F2937]">No entities detected in evidence.</p>
                <p className="text-xs text-[#6B7280] mt-1">Upload communications, logs, or reports to extract names, addresses, and dates.</p>
              </div>
            )}
          </div>
          <p className="mt-4 text-[11px] text-[#6B7280] border-t border-[#E5E7EB] pt-3">
            Extracted using pattern matching and natural language entity recognition.
          </p>
        </article>

        {/* 4. AI Investigation Summary (Clean Pure White + Royal Red Card) */}
        <article className="rounded-2xl border border-[#FECDD3] bg-white p-5 shadow-xs flex flex-col justify-between relative overflow-hidden">
          <div>
            <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <div className="flex items-center gap-2">
                <div className="size-7 rounded-lg bg-[#FFF1F2] border border-[#FECDD3] flex items-center justify-center text-[#C8102E]">
                  <Sparkles size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-[#1F2937] text-sm">AI Investigation Summary</h3>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2 py-0.5 text-[10px] font-bold text-[#C8102E]">
                  AI Assessment
                </span>
                <button
                  onClick={onOpenAiModal}
                  title="Expand Full AI Investigation Summary"
                  className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937] transition"
                  aria-label="Expand AI summary"
                >
                  <Maximize2 size={15} />
                </button>
              </div>
            </div>

            <p className="text-[11px] text-[#6B7280] mt-2 mb-3">
              An AI-generated overview of available evidence and possible connections. Review supporting evidence before drawing conclusions.
            </p>

            {/* Executive Synthesis */}
            <div className="rounded-xl bg-[#F8FAFC] p-3.5 border border-[#E5E7EB]">
              <p className="text-xs font-bold uppercase tracking-wider text-[#C8102E] mb-1.5 flex items-center gap-1.5">
                <FileText size={13} /> Executive Overview
              </p>
              <p className="text-xs leading-relaxed text-[#1F2937] break-words">
                {dashboard.ai_insights.summary}
              </p>
            </div>

            {/* Key Evidence Observations */}
            {dashboard.ai_insights.findings && dashboard.ai_insights.findings.length > 0 && (
              <div className="mt-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#1F2937]">Key Evidence Observations</p>
                  <span className="text-[10px] text-[#6B7280] font-medium">
                    Showing {Math.min(2, dashboard.ai_insights.findings.length)} of {dashboard.ai_insights.findings.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {dashboard.ai_insights.findings.slice(0, 2).map((finding, idx) => (
                    <ObservationCard key={idx} text={finding} compact={true} />
                  ))}
                </div>
              </div>
            )}

            {/* Recommended Priority Lead */}
            {dashboard.ai_insights.leads && dashboard.ai_insights.leads.length > 0 && (
              <div className="mt-3.5 rounded-xl bg-[#FFF1F2] border border-[#FECDD3] p-3">
                <p className="text-[11px] font-bold uppercase tracking-wider text-[#C8102E] mb-1 flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-[#C8102E]" /> Recommended Next Step
                </p>
                <p className="text-xs text-[#1F2937] leading-snug break-words">
                  {dashboard.ai_insights.leads[0]}
                </p>
              </div>
            )}
          </div>

          <div className="mt-4 flex flex-col gap-2 pt-3 border-t border-[#E5E7EB]">
            <div className="flex items-center justify-between text-xs text-[#6B7280]">
              <span className="flex items-center gap-1.5 text-[11px] text-[#6B7280] truncate max-w-[200px]" title={dashboard.ai_insights.confidence_note}>
                <Check size={14} className="text-[#C8102E] shrink-0" />
                <span className="truncate">{dashboard.ai_insights.confidence_note || 'Evidence grounded assessment'}</span>
              </span>
              <button
                onClick={onOpenAiModal}
                className="text-xs font-semibold text-[#C8102E] hover:underline transition inline-flex items-center gap-1 shrink-0"
              >
                Expand Details <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </article>

        {/* 5. Possible Connections (Cross-Evidence Correlation) */}
        {dashboard.correlations && dashboard.correlations.length > 0 && (
          <article className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs lg:col-span-3">
            <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Network size={18} className="text-[#C8102E]" />
                  <h3 className="font-bold text-[#1F2937]">Possible Connections</h3>
                </div>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  Explore possible relationships between people, events, files and other findings.
                </p>
              </div>
              <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-0.5 text-xs font-bold text-[#C8102E]">
                {dashboard.correlations.length} Shared Linkages
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {dashboard.correlations.map((corr, idx) => (
                <div key={idx} className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3.5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 font-bold uppercase tracking-wider text-[#1F2937] text-[10px]">
                        {corr.entity_type}
                      </span>
                      <span className="font-semibold text-[#C8102E] text-xs">{corr.occurrences} file(s)</span>
                    </div>
                    <h4 className="mt-1 text-sm font-bold text-[#1F2937] break-words" title={corr.entity_value}>
                      {corr.entity_value}
                    </h4>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[#E5E7EB]">
                    <p className="text-[11px] text-[#6B7280] font-medium mb-1">Found in sources:</p>
                    <div className="flex flex-wrap gap-1">
                      {corr.evidence_names.map((name, i) => (
                        <span key={i} className="rounded bg-white border border-[#E5E7EB] px-1.5 py-0.5 text-[10px] text-[#1F2937] font-medium truncate max-w-full">
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </article>
        )}

        {/* 6. Event Timeline */}
        <article className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs lg:col-span-3">
          <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <Clock3 size={18} className="text-[#C8102E]" />
                <h3 className="font-bold text-[#1F2937]">Event Timeline</h3>
              </div>
              <p className="text-xs text-[#6B7280] mt-0.5">
                View events arranged in chronological order based on the available evidence.
              </p>
            </div>
            {dashboard.timeline.length > 3 && (
              <span className="text-xs font-semibold text-[#6B7280]">
                Showing 3 of {dashboard.timeline.length} chronological events
              </span>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {dashboard.timeline.length > 0 ? (
              dashboard.timeline.slice(0, 3).map((event, i) => (
                <div
                  key={`${event.time}-${i}`}
                  className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2 mb-2">
                      <span className="text-xs font-bold text-[#1F2937] uppercase tracking-wide flex items-center gap-1.5">
                        <span className="size-2 rounded-full bg-[#C8102E]" />
                        {event.time}
                      </span>
                      <span className="rounded bg-[#FFF1F2] border border-[#FECDD3] px-1.5 py-0.5 text-[10px] font-bold text-[#C8102E]">
                        {event.title}
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm leading-relaxed text-[#1F2937] break-words mt-2">
                      {event.detail}
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[#E5E7EB] flex items-center justify-between text-[11px] text-[#6B7280]">
                    <span className="truncate max-w-[200px]" title={event.source_evidence}>
                      Source: {event.source_evidence}
                    </span>
                    {event.has_location && <MapPin size={13} className="shrink-0 text-[#C8102E]" />}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-[#E5E7EB] bg-[#F8FAFC] p-8 text-center text-sm text-[#6B7280] md:col-span-3">
                No chronological timestamp markers detected in evidence.
              </div>
            )}
          </div>

          {dashboard.timeline.length > 0 && (
            <div className="mt-4 pt-3 border-t border-[#E5E7EB] flex justify-end">
              <button
                onClick={onOpenTimeline}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#C8102E] hover:underline transition"
              >
                Open complete timeline ({dashboard.timeline.length} events) <ArrowRight size={14} />
              </button>
            </div>
          )}
        </article>
      </div>
    </section>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="px-2">
      <p className="text-xl font-bold text-[#1F2937]">{value}</p>
      <p className="text-xs text-[#6B7280] mt-0.5">{label}</p>
    </div>
  )
}

/* Modals */

function CaseFilesModal({
  evidenceList,
  currentCase,
  currentUser,
  onClose,
  onSelectPreview,
  onDeleteCase,
  onOpenReassign
}: {
  evidenceList: EvidenceItem[]
  currentCase?: CaseItem | null
  currentUser?: User | null
  onClose: () => void
  onSelectPreview: (ev: EvidenceItem) => void
  onDeleteCase?: (caseId: string) => void
  onOpenReassign?: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-2xl bg-white p-6 shadow-2xl border border-[#E5E7EB] flex flex-col max-h-[90vh]">
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-[#E5E7EB] pb-3 gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-[#1F2937]">Uploaded Evidence & Evidence Handling History</h3>
              {currentCase && (
                <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2 py-0.5 font-mono text-[11px] font-bold text-[#C8102E]">
                  Owner: @{currentCase.owner_user_id || 'unassigned'}
                </span>
              )}
            </div>
            <p className="text-xs text-[#6B7280]">
              Verified digital evidence files and digital file fingerprints (SHA-256)
            </p>
          </div>
          <div className="flex items-center gap-2">
            {currentUser?.role === 'admin' && currentCase && (
              <>
                {onOpenReassign && (
                  <button
                    onClick={onOpenReassign}
                    className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-2.5 py-1 text-xs font-semibold text-[#1F2937] hover:bg-slate-100"
                  >
                    Transfer Investigation
                  </button>
                )}
                {onDeleteCase && (
                  <button
                    onClick={() => { onClose(); onDeleteCase(currentCase.case_id); }}
                    className="rounded-lg border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 hover:bg-red-100"
                  >
                    Delete Investigation
                  </button>
                )}
              </>
            )}
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937]"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto rounded-xl border border-[#E5E7EB]">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-[#F8FAFC] border-b border-[#E5E7EB] text-[#6B7280] uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-3.5 py-2.5">Evidence ID</th>
                <th className="px-3.5 py-2.5">File Name</th>
                <th className="px-3.5 py-2.5">File Format</th>
                <th className="px-3.5 py-2.5">Size</th>
                <th className="px-3.5 py-2.5">Digital Fingerprint</th>
                <th className="px-3.5 py-2.5">Status</th>
                <th className="px-3.5 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E5E7EB] bg-white">
              {evidenceList.map(ev => (
                <tr key={ev.evidence_id} className="hover:bg-slate-50/80 transition">
                  <td className="px-3.5 py-2.5 font-mono text-[#6B7280]">{ev.evidence_id}</td>
                  <td className="px-3.5 py-2.5 font-semibold text-[#1F2937]">{ev.original_filename}</td>
                  <td className="px-3.5 py-2.5">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-bold text-[#1F2937]">
                      {ev.file_type}
                    </span>
                  </td>
                  <td className="px-3.5 py-2.5 text-[#6B7280]">{(ev.file_size / 1024).toFixed(1)} KB</td>
                  <td className="px-3.5 py-2.5 font-mono text-[11px] text-[#6B7280]" title={ev.sha256_hash}>
                    {ev.sha256_hash.substring(0, 16)}...
                  </td>
                  <td className="px-3.5 py-2.5">
                    <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                      {ev.status}
                    </span>
                  </td>
                  <td className="px-3.5 py-2.5 text-right">
                    <button
                      onClick={() => onSelectPreview(ev)}
                      className="text-xs font-semibold text-[#C8102E] hover:underline"
                    >
                      View Text
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 pt-3 border-t border-[#E5E7EB] flex items-center justify-between text-xs text-[#6B7280]">
          <span>Files checked for integrity with SHA-256 fingerprint verification</span>
          <button
            onClick={onClose}
            className="rounded-lg border border-[#E5E7EB] px-4 py-1.5 text-xs font-semibold text-[#1F2937] hover:bg-slate-100"
          >
            Close
          </button>
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
      <div className="w-full max-w-4xl rounded-2xl bg-white p-6 shadow-2xl border border-[#E5E7EB] flex flex-col max-h-[90vh]">
        <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
          <div>
            <h3 className="text-base font-bold text-[#1F2937]">Event Timeline</h3>
            <p className="text-xs text-[#6B7280]">
              Chronological sequence of events arranged from examined evidence
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937]"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mb-4 flex items-center gap-2 rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-2 text-sm">
          <Search size={16} className="text-[#6B7280]" />
          <input
            type="text"
            placeholder="Search timeline by keyword, name, or source file..."
            value={filterQuery}
            onChange={e => setFilterQuery(e.target.value)}
            className="w-full bg-transparent text-xs text-[#1F2937] placeholder-[#6B7280] focus:outline-none"
          />
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto pr-1">
          {filtered.length > 0 ? (
            filtered.map((evt, idx) => (
              <div key={idx} className="flex gap-3.5 rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-4">
                <span className="size-2.5 shrink-0 rounded-full bg-[#C8102E] mt-1.5" />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#C8102E] uppercase tracking-wide">{evt.time}</span>
                    <span className="text-xs font-semibold text-[#1F2937] bg-white border border-[#E5E7EB] px-2 py-0.5 rounded">
                      {evt.source_evidence}
                    </span>
                  </div>
                  <h4 className="mt-1 font-bold text-[#1F2937] text-sm">{evt.title}</h4>
                  <p className="mt-1 text-xs sm:text-sm text-[#1F2937] leading-relaxed">{evt.detail}</p>
                </div>
              </div>
            ))
          ) : (
            <p className="py-8 text-center text-sm text-[#6B7280]">No events matched your search.</p>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-[#E5E7EB] flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg border border-[#E5E7EB] px-4 py-1.5 text-xs font-semibold text-[#1F2937] hover:bg-slate-100"
          >
            Close
          </button>
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
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-[#E5E7EB]">
        <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
          <div>
            <h3 className="text-base font-bold text-[#1F2937]">Start New Investigation</h3>
            <p className="text-xs text-[#6B7280]">Create a dossier to organize evidence and analysis</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-[#1F2937]">Investigation Title *</label>
            <input
              type="text"
              required
              placeholder="e.g. Unauthorized Cloud Account Access Investigation"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-xs text-[#1F2937] focus:border-[#C8102E] focus:outline-none"
            />
          </div>

          <div>
            <label className="font-semibold text-[#1F2937]">Lead Investigator</label>
            <input
              type="text"
              placeholder="e.g. Investigator R. Kumar"
              value={investigator}
              onChange={e => setInvestigator(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-xs text-[#1F2937] focus:border-[#C8102E] focus:outline-none"
            />
          </div>

          <div>
            <label className="font-semibold text-[#1F2937]">Investigation Description</label>
            <textarea
              rows={3}
              placeholder="Brief context regarding incident, incident date, and evidence scope..."
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-xs text-[#1F2937] focus:border-[#C8102E] focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#E5E7EB]">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-1.5 font-semibold text-[#6B7280] hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg btn-royal px-4 py-1.5 font-semibold text-xs shadow-xs"
            >
              Start Investigation
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
      <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl border border-[#E5E7EB] flex flex-col max-h-[90vh]">
        <div className="mb-4 flex items-center justify-between border-b border-[#E5E7EB] pb-3">
          <div>
            <h3 className="text-base font-bold text-[#1F2937]">{evidence.original_filename}</h3>
            <p className="font-mono text-xs text-[#6B7280]">Digital Fingerprint: {evidence.sha256_hash}</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto rounded-lg bg-[#F8FAFC] border border-[#E5E7EB] p-4 font-mono text-xs text-[#1F2937] whitespace-pre-wrap">
          {evidence.extracted_text_preview ? (
            evidence.extracted_text_preview
          ) : (
            <span className="text-[#6B7280] italic">
              Extracted text will appear here after clicking "Investigate Evidence".
            </span>
          )}
        </div>

        <div className="mt-4 pt-3 border-t border-[#E5E7EB] flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg border border-[#E5E7EB] px-4 py-1.5 text-xs font-semibold text-[#1F2937] hover:bg-slate-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

function AiInsightsModal({
  dashboard,
  currentCase,
  onClose,
  onExportPdf,
  isDownloadingPdf
}: {
  dashboard: DashboardData
  currentCase: CaseItem | null
  onClose: () => void
  onExportPdf?: () => void
  isDownloadingPdf?: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-3 sm:p-6 backdrop-blur-sm">
      <div className="flex h-full max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-[#E5E7EB] bg-white shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-lg bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3]">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold tracking-tight text-[#1F2937]">
                  AI Investigation Summary & Findings
                </h3>
                <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-0.5 text-[11px] font-mono text-[#C8102E]">
                  Investigation ID: {currentCase?.case_id || dashboard.case_id}
                </span>
              </div>
              <p className="text-xs text-[#6B7280]">
                AI-assisted overview of findings, patterns, and possible connections
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {currentCase && onExportPdf && (
              <button
                onClick={onExportPdf}
                disabled={isDownloadingPdf}
                className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-[#FECDD3] bg-[#FFF1F2] px-3.5 py-1.5 text-xs font-semibold text-[#C8102E] hover:bg-[#FFE4E6] transition disabled:opacity-50"
              >
                <FileDown size={14} /> {isDownloadingPdf ? 'Creating Report...' : 'Download Report'}
              </button>
            )}
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937] transition"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-[#F8FAFC]">
          {/* Notice Banner */}
          <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
            <Info size={16} className="text-amber-600 shrink-0 mt-0.5" />
            <span>
              <strong>AI-Generated Overview:</strong> These findings and connections are generated from uploaded evidence. Always verify supporting evidence before drawing conclusions.
            </span>
          </div>

          {/* 1. Executive Summary */}
          <section className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
            <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-2.5">
              <div className="flex items-center gap-2">
                <FileText size={17} className="text-[#C8102E]" />
                <h4 className="text-sm font-bold uppercase tracking-wider text-[#1F2937]">
                  Executive Overview
                </h4>
              </div>
              <span className="rounded-full bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-0.5 text-xs font-bold text-[#C8102E]">
                Overview
              </span>
            </div>
            <p className="text-sm leading-relaxed text-[#1F2937] break-words whitespace-pre-wrap">
              {dashboard.ai_insights.summary}
            </p>
          </section>

          {/* 2. Key Evidence Observations */}
          <section className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
            <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-2.5">
              <div className="flex items-center gap-2">
                <Search size={17} className="text-[#C8102E]" />
                <h4 className="text-sm font-bold uppercase tracking-wider text-[#1F2937]">
                  Key Evidence Observations ({dashboard.ai_insights.findings?.length || 0})
                </h4>
              </div>
              <span className="text-xs text-[#6B7280]">Verified evidence artifacts</span>
            </div>

            {dashboard.ai_insights.findings && dashboard.ai_insights.findings.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {dashboard.ai_insights.findings.map((item, idx) => (
                  <ObservationCard key={idx} text={item} compact={false} />
                ))}
              </div>
            ) : (
              <p className="text-xs text-[#6B7280] italic py-2">No individual observations recorded.</p>
            )}
          </section>

          {/* 3. Possible Connections */}
          {dashboard.correlations && dashboard.correlations.length > 0 && (
            <section className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-2.5">
                <div className="flex items-center gap-2">
                  <Network size={17} className="text-[#C8102E]" />
                  <h4 className="text-sm font-bold uppercase tracking-wider text-[#1F2937]">
                    Possible Connections ({dashboard.correlations.length})
                  </h4>
                </div>
                <span className="text-xs text-[#C8102E] font-semibold">Shared Linkages</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                {dashboard.correlations.map((corr, idx) => (
                  <div key={idx} className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] p-3 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="rounded bg-slate-200 px-1.5 py-0.2 font-mono text-[10px] font-bold text-[#1F2937] uppercase">
                          {corr.entity_type}
                        </span>
                        <span className="font-semibold text-[#C8102E] text-xs">
                          {corr.occurrences} file(s)
                        </span>
                      </div>
                      <p className="font-bold text-[#1F2937] text-xs break-words">{corr.entity_value}</p>
                    </div>
                    <div className="mt-2.5 pt-2 border-t border-[#E5E7EB] text-[11px] text-[#6B7280]">
                      <span className="block text-[10px] uppercase font-semibold text-[#6B7280] mb-0.5">Found in:</span>
                      <div className="flex flex-wrap gap-1">
                        {corr.evidence_names.map((src, i) => (
                          <span key={i} className="rounded bg-white border border-[#E5E7EB] px-1.5 py-0.2 text-[10px] text-[#1F2937] truncate max-w-full">
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 4. Potential Warning Signs & Patterns */}
          {dashboard.ai_insights.patterns && dashboard.ai_insights.patterns.length > 0 && (
            <section className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-2.5">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={17} className="text-[#D97706]" />
                  <h4 className="text-sm font-bold uppercase tracking-wider text-[#1F2937]">
                    Potential Warning Signs & Patterns ({dashboard.ai_insights.patterns.length})
                  </h4>
                </div>
                <span className="text-xs text-amber-700 font-semibold">Anomalies</span>
              </div>
              <div className="space-y-2">
                {dashboard.ai_insights.patterns.map((pat, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-xs text-[#1F2937]">
                    <AlertTriangle size={15} className="shrink-0 text-amber-600 mt-0.5" />
                    <span className="leading-relaxed break-words">{pat}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 5. Recommended Next Steps */}
          {dashboard.ai_insights.leads && dashboard.ai_insights.leads.length > 0 && (
            <section className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-[#E5E7EB] pb-2.5">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={17} className="text-[#C8102E]" />
                  <h4 className="text-sm font-bold uppercase tracking-wider text-[#1F2937]">
                    Recommended Next Steps ({dashboard.ai_insights.leads.length})
                  </h4>
                </div>
                <span className="text-xs text-[#C8102E] font-semibold">Priority Action Items</span>
              </div>
              <div className="space-y-2.5">
                {dashboard.ai_insights.leads.map((lead, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border border-[#FECDD3] bg-[#FFF1F2] p-3 text-xs text-[#1F2937]">
                    <span className="grid size-5 shrink-0 place-items-center rounded-full btn-royal text-white font-bold text-[10px]">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed break-words">{lead}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#E5E7EB] bg-white px-6 py-3.5">
          <p className="text-[11px] text-[#6B7280] italic text-center sm:text-left">
            AI-generated assistive overview. Findings are indicators and require verification by an investigator.
          </p>
          <div className="flex items-center gap-2">
            {currentCase && onExportPdf && (
              <button
                onClick={onExportPdf}
                disabled={isDownloadingPdf}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-3.5 py-1.5 text-xs font-semibold text-[#1F2937] hover:border-[#C8102E] hover:text-[#C8102E] transition disabled:opacity-50"
              >
                <FileDown size={14} className="text-[#C8102E]" /> {isDownloadingPdf ? 'Creating Report...' : 'Download Report'}
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded-lg border border-[#E5E7EB] hover:bg-slate-100 px-4 py-1.5 text-xs font-semibold text-[#1F2937] transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
