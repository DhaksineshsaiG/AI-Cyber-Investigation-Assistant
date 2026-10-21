import { useState, useEffect, useMemo } from 'react';
import {
  Activity, Search, Filter, Calendar, User as UserIcon, FileDown, RefreshCw,
  X, CheckCircle2, AlertTriangle, AlertCircle, FolderOpen, Upload, Cpu,
  Shield, ShieldAlert, FileText, ChevronLeft, ChevronRight, Clock, Info,
  Eye, Users, Check
} from 'lucide-react';
import { api } from '../services/api';
import type { User, AuditEvent, AuditSummary } from '../types/investigation';

interface ActivityMonitorProps {
  currentUser: User;
  onBackToWorkspace?: () => void;
}

export default function ActivityMonitor({ currentUser, onBackToWorkspace }: ActivityMonitorProps) {
  // Users / Investigators list
  const [users, setUsers] = useState<User[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  // Filters
  const [selectedInvestigator, setSelectedInvestigator] = useState<string>('all');
  const [selectedActionType, setSelectedActionType] = useState<string>('all');
  const [dateRangeOption, setDateRangeOption] = useState<string>('all');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Audit Events state
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 20;
  const [totalPages, setTotalPages] = useState(1);

  // Summary state
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Detail Modal state
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  // PDF Download state
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load investigators list once on mount
  useEffect(() => {
    loadInvestigators();
  }, []);

  // Compute effective ISO date range
  const { startDateIso, endDateIso } = useMemo(() => {
    const now = new Date();
    if (dateRangeOption === 'today') {
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      return { startDateIso: start.toISOString(), endDateIso: now.toISOString() };
    }
    if (dateRangeOption === 'last_7_days') {
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return { startDateIso: start.toISOString(), endDateIso: now.toISOString() };
    }
    if (dateRangeOption === 'last_30_days') {
      const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return { startDateIso: start.toISOString(), endDateIso: now.toISOString() };
    }
    if (dateRangeOption === 'custom') {
      const start = customStartDate ? new Date(customStartDate).toISOString() : undefined;
      const end = customEndDate ? new Date(customEndDate + 'T23:59:59.999Z').toISOString() : undefined;
      return { startDateIso: start, endDateIso: end };
    }
    return { startDateIso: undefined, endDateIso: undefined };
  }, [dateRangeOption, customStartDate, customEndDate]);

  // Fetch events & summary whenever filters or page changes
  useEffect(() => {
    loadEvents();
    loadSummary();
  }, [selectedInvestigator, selectedActionType, startDateIso, endDateIso, searchQuery, page]);

  const loadInvestigators = async () => {
    try {
      setLoadingUsers(true);
      const userList = await api.listUsers();
      setUsers(userList);
    } catch (err: any) {
      console.error('Failed to load investigators:', err);
    } finally {
      setLoadingUsers(false);
    }
  };

  const loadEvents = async () => {
    try {
      setLoadingEvents(true);
      setErrorMessage(null);
      const params: any = {
        page,
        limit,
      };
      if (selectedInvestigator !== 'all') {
        params.investigator_id = selectedInvestigator;
      }
      if (selectedActionType !== 'all') {
        params.action_type = selectedActionType;
      }
      if (startDateIso) {
        params.start_date = startDateIso;
      }
      if (endDateIso) {
        params.end_date = endDateIso;
      }
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      const res = await api.getAuditEvents(params);
      setEvents(res.events || []);
      setTotalCount(res.total_count || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to load audit records.');
    } finally {
      setLoadingEvents(false);
    }
  };

  const loadSummary = async () => {
    try {
      setLoadingSummary(true);
      const params: any = {};
      if (selectedInvestigator !== 'all') {
        params.investigator_id = selectedInvestigator;
      }
      if (startDateIso) {
        params.start_date = startDateIso;
      }
      if (endDateIso) {
        params.end_date = endDateIso;
      }

      const res = await api.getAuditSummary(params);
      setSummary(res);
    } catch (err: any) {
      console.error('Failed to load audit summary:', err);
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleClearFilters = () => {
    setSelectedInvestigator('all');
    setSelectedActionType('all');
    setDateRangeOption('all');
    setCustomStartDate('');
    setCustomEndDate('');
    setSearchQuery('');
    setPage(1);
  };

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true);
      setErrorMessage(null);
      await api.downloadAuditReportPdf({
        investigator_id: selectedInvestigator !== 'all' ? selectedInvestigator : undefined,
        start_date: startDateIso,
        end_date: endDateIso,
      });
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to generate audit PDF report.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  // Find selected investigator object if specific
  const selectedUserObj = useMemo(() => {
    if (selectedInvestigator === 'all') return null;
    return users.find((u) => u.user_id === selectedInvestigator) || null;
  }, [users, selectedInvestigator]);

  // Format date helper
  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl bg-white p-6 shadow-xs border border-[#E5E7EB] border-l-4 border-l-[#C8102E]">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#C8102E]">
            <Activity size={16} /> Administrator Audit & Surveillance Center
          </div>
          <h2 className="mt-2 text-xl font-bold tracking-tight text-[#1F2937] sm:text-2xl">
            Investigator Activity Monitor
          </h2>
          <p className="mt-1 text-sm text-[#6B7280]">
            Review investigation activity, evidence handling and important actions performed by your investigators.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onBackToWorkspace && (
            <button
              onClick={onBackToWorkspace}
              className="inline-flex items-center gap-1.5 rounded-xl border border-[#E5E7EB] bg-white px-3.5 py-2 text-xs font-semibold text-[#1F2937] transition hover:border-[#C8102E] hover:text-[#C8102E] shadow-2xs"
            >
              Back to Workspace
            </button>
          )}

          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="inline-flex items-center gap-2 rounded-xl btn-royal px-4 py-2 text-xs font-semibold shadow-xs transition disabled:opacity-50"
            title="Download formatted audit and activity PDF report"
          >
            <FileDown size={15} />
            {downloadingPdf ? 'Exporting PDF...' : 'Download Activity Report'}
          </button>
        </div>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="shrink-0 text-[#C8102E]" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-red-600 hover:text-red-900">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Filter and Selection Card */}
      <div className="rounded-2xl border border-[#E5E7EB] bg-white p-5 shadow-xs">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Investigator Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#1F2937] mb-1.5">
              Select Investigator
            </label>
            <select
              value={selectedInvestigator}
              onChange={(e) => {
                setSelectedInvestigator(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-2 text-xs font-medium text-[#1F2937] focus:border-[#C8102E] focus:bg-white focus:outline-none transition shadow-2xs"
            >
              <option value="all">All Investigators (Organisation-wide)</option>
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.display_name} (@{u.user_id}) — {u.role === 'admin' ? 'Admin' : 'Investigator'} [{u.is_active ? 'Active' : 'Disabled'}]
                </option>
              ))}
            </select>
          </div>

          {/* 2. Reporting Period */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#1F2937] mb-1.5">
              Reporting Period
            </label>
            <select
              value={dateRangeOption}
              onChange={(e) => {
                setDateRangeOption(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-2 text-xs font-medium text-[#1F2937] focus:border-[#C8102E] focus:bg-white focus:outline-none transition shadow-2xs"
            >
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="last_7_days">Last 7 Days</option>
              <option value="last_30_days">Last 30 Days</option>
              <option value="custom">Custom Date Range</option>
            </select>
          </div>

          {/* 3. Action Type Filter */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#1F2937] mb-1.5">
              Action Category
            </label>
            <select
              value={selectedActionType}
              onChange={(e) => {
                setSelectedActionType(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-2 text-xs font-medium text-[#1F2937] focus:border-[#C8102E] focus:bg-white focus:outline-none transition shadow-2xs"
            >
              <option value="all">All Actions</option>
              <option value="investigation_created">Investigation Created</option>
              <option value="investigation_deleted">Investigation Deleted</option>
              <option value="evidence_uploaded">Evidence Uploaded</option>
              <option value="evidence_deleted">Evidence Deleted</option>
              <option value="analysis_completed">Analysis Runs</option>
              <option value="report_downloaded">Report Downloaded</option>
              <option value="case_reassigned">Case Reassigned</option>
              <option value="user_created">User Created</option>
              <option value="user_updated">User Account Updated</option>
              <option value="login_success">Signed In (Success)</option>
              <option value="login_failure">Sign In Failed</option>
              <option value="logout">Signed Out</option>
              <option value="access_denied">Permission Denied</option>
            </select>
          </div>

          {/* 4. Search Filter */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#1F2937] mb-1.5">
              Search Records
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-2.5 text-[#6B7280]" />
              <input
                type="text"
                placeholder="Search action, details, ID..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] pl-8 pr-3 py-2 text-xs font-medium text-[#1F2937] focus:border-[#C8102E] focus:bg-white focus:outline-none transition shadow-2xs"
              />
            </div>
          </div>
        </div>

        {/* Custom date range pickers if 'custom' is active */}
        {dateRangeOption === 'custom' && (
          <div className="mt-4 pt-4 border-t border-[#E5E7EB] flex flex-wrap items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[#6B7280]">From:</span>
              <input
                type="date"
                value={customStartDate}
                onChange={(e) => {
                  setCustomStartDate(e.target.value);
                  setPage(1);
                }}
                className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-2.5 py-1.5 text-xs text-[#1F2937] focus:border-[#C8102E] focus:outline-none"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-[#6B7280]">To:</span>
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => {
                  setCustomEndDate(e.target.value);
                  setPage(1);
                }}
                className="rounded-lg border border-[#E5E7EB] bg-[#F8FAFC] px-2.5 py-1.5 text-xs text-[#1F2937] focus:border-[#C8102E] focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Filter summary and Clear button */}
        <div className="mt-4 pt-3 border-t border-[#E5E7EB] flex items-center justify-between text-xs text-[#6B7280]">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-[#1F2937]">Active Scope:</span>
            <span className="inline-flex items-center gap-1 rounded-md bg-[#FFF1F2] text-[#C8102E] border border-[#FECDD3] px-2 py-0.5 font-medium">
              Investigator: {selectedInvestigator === 'all' ? 'All Investigators' : selectedInvestigator}
            </span>
            {selectedActionType !== 'all' && (
              <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 text-[#1F2937] border border-[#E5E7EB] px-2 py-0.5 font-medium">
                Action: {selectedActionType}
              </span>
            )}
            {dateRangeOption !== 'all' && (
              <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 text-[#1F2937] border border-[#E5E7EB] px-2 py-0.5 font-medium">
                Period: {dateRangeOption.replace(/_/g, ' ')}
              </span>
            )}
            {searchQuery && (
              <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 text-[#1F2937] border border-[#E5E7EB] px-2 py-0.5 font-medium">
                Query: "{searchQuery}"
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadEvents();
                loadSummary();
              }}
              className="inline-flex items-center gap-1 rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-semibold text-[#6B7280] hover:text-[#C8102E] transition"
              title="Refresh audit records"
            >
              <RefreshCw size={12} className={loadingEvents ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
            <button
              onClick={handleClearFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-semibold text-[#6B7280] hover:text-[#C8102E] transition"
            >
              <X size={12} />
              <span>Clear Filters</span>
            </button>
          </div>
        </div>
      </div>

      {/* Investigator Context Profile (when a single investigator is selected) */}
      {selectedUserObj && (
        <div className="rounded-2xl border border-[#FECDD3] bg-[#FFF1F2] p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-white text-[#C8102E] border border-[#FECDD3] shadow-xs">
              <UserIcon size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-[#1F2937] text-sm">{selectedUserObj.display_name}</span>
                <span className="font-mono text-[#6B7280]">@{selectedUserObj.user_id}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    selectedUserObj.role === 'admin'
                      ? 'bg-red-100 text-[#C8102E] border border-red-200'
                      : 'bg-slate-200 text-[#1F2937]'
                  }`}
                >
                  {selectedUserObj.role}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                    selectedUserObj.is_active
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {selectedUserObj.is_active ? 'Active Account' : 'Account Disabled'}
                </span>
              </div>
              <div className="mt-0.5 text-[#6B7280]">
                Account created on {formatTimestamp(selectedUserObj.created_at)}
                {selectedUserObj.last_login_at && (
                  <span> · Last sign in: {formatTimestamp(selectedUserObj.last_login_at)}</span>
                )}
              </div>
            </div>
          </div>
          <div className="text-right sm:text-left text-[#6B7280]">
            Audit records represent factual, server-recorded operations for this individual.
          </div>
        </div>
      )}

      {/* 3. Activity Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Activities */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Total Activities</span>
            <Activity size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.total_activities ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">Logged in period</p>
        </div>

        {/* Investigations Created */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Investigations</span>
            <FolderOpen size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.investigations_created ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">Dossiers opened</p>
        </div>

        {/* Evidence Files Uploaded */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Evidence Uploaded</span>
            <Upload size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.evidence_uploaded ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">Files ingested</p>
        </div>

        {/* Analysis Runs */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Analysis Runs</span>
            <Cpu size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.analysis_runs ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">Correlations executed</p>
        </div>

        {/* Reports Downloaded */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Reports Downloaded</span>
            <FileText size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.reports_downloaded ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">PDF exports</p>
        </div>

        {/* Account and Access Changes */}
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-[#6B7280]">
            <span className="text-xs font-semibold">Account / Access</span>
            <Shield size={16} className="text-[#C8102E]" />
          </div>
          <div className="mt-2 text-2xl font-bold text-[#1F2937]">
            {loadingSummary ? '...' : (summary?.account_changes ?? 0)}
          </div>
          <p className="mt-1 text-[11px] text-[#6B7280]">Reassignments & edits</p>
        </div>
      </div>

      {/* 4. Investigator Activity Timeline & Table */}
      <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-xs overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-[#E5E7EB] px-6 py-4 gap-2">
          <div>
            <h3 className="text-base font-bold text-[#1F2937]">Activity History Timeline</h3>
            <p className="text-xs text-[#6B7280]">
              Showing {events.length} of {totalCount} chronological audit records (page {page} of {totalPages})
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#6B7280] hidden sm:inline">
              Click any row to view complete security metadata
            </span>
          </div>
        </div>

        {loadingEvents ? (
          <div className="py-16 text-center text-[#6B7280]">
            <RefreshCw size={24} className="animate-spin mx-auto text-[#C8102E] mb-2" />
            <p className="text-xs font-medium">Retrieving real server audit log...</p>
          </div>
        ) : events.length === 0 ? (
          <div className="py-16 text-center text-[#6B7280] px-4">
            <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#FFF1F2] text-[#C8102E] mb-3 border border-[#FECDD3]">
              <Info size={22} />
            </div>
            <h4 className="text-sm font-bold text-[#1F2937]">No Activity Records Found</h4>
            <p className="mt-1 text-xs max-w-md mx-auto">
              No audit events matched your selected investigator, date range or filter criteria.
              If the feature was recently deployed, older operations may predate audit event recording.
            </p>
            <button
              onClick={handleClearFilters}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-semibold text-[#1F2937] hover:border-[#C8102E] hover:text-[#C8102E] transition shadow-2xs"
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#1F2937]">
              <thead className="bg-[#F8FAFC] border-b border-[#E5E7EB] text-[11px] font-bold uppercase tracking-wider text-[#6B7280]">
                <tr>
                  <th className="py-3 px-4">Date & Time</th>
                  <th className="py-3 px-4">Investigator</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Investigation ID</th>
                  <th className="py-3 px-4">Details</th>
                  <th className="py-3 px-4 text-center">Result</th>
                  <th className="py-3 px-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E7EB]">
                {events.map((evt) => {
                  const isSuccess = evt.status === 'success';
                  return (
                    <tr
                      key={evt.event_id}
                      onClick={() => setSelectedEvent(evt)}
                      className="hover:bg-slate-50/80 cursor-pointer transition"
                    >
                      {/* Timestamp */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-[#1F2937] font-mono text-[11px]">
                        <div className="font-semibold">{formatTimestamp(evt.timestamp)}</div>
                        <div className="text-[10px] text-[#6B7280]">UTC: {evt.timestamp}</div>
                      </td>

                      {/* Investigator */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-bold text-[#1F2937]">@{evt.actor_user_id}</div>
                        <span className="text-[10px] text-[#6B7280] uppercase tracking-wider font-semibold">
                          {evt.actor_role}
                        </span>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 font-semibold text-[#1F2937]">
                          {evt.action_label}
                        </span>
                        <div className="text-[10px] text-[#6B7280] font-mono">{evt.action_type}</div>
                      </td>

                      {/* Case ID */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {evt.case_id ? (
                          <span className="inline-flex items-center rounded-md bg-slate-100 border border-[#E5E7EB] px-2 py-0.5 text-[11px] font-mono font-medium text-[#1F2937]">
                            {evt.case_id}
                          </span>
                        ) : (
                          <span className="text-[#9CA3AF] italic text-[11px]">—</span>
                        )}
                      </td>

                      {/* Details */}
                      <td className="py-3.5 px-4 max-w-xs truncate text-[#6B7280]" title={evt.details}>
                        {evt.details || '—'}
                      </td>

                      {/* Result */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        {isSuccess ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700">
                            <CheckCircle2 size={12} /> Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2.5 py-0.5 text-[11px] font-bold text-[#C8102E]">
                            <AlertCircle size={12} /> {evt.status}
                          </span>
                        )}
                      </td>

                      {/* Action Link */}
                      <td className="py-3.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedEvent(evt);
                          }}
                          className="rounded-lg p-1 text-[#6B7280] hover:text-[#C8102E] hover:bg-red-50 transition"
                          title="View security audit payload"
                        >
                          <Eye size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-[#E5E7EB] bg-white px-6 py-3 text-xs">
            <div className="text-[#6B7280]">
              Page <span className="font-bold text-[#1F2937]">{page}</span> of{' '}
              <span className="font-bold text-[#1F2937]">{totalPages}</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 font-semibold text-[#1F2937] disabled:opacity-40 hover:border-[#C8102E] transition shadow-2xs"
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-1 rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 font-semibold text-[#1F2937] disabled:opacity-40 hover:border-[#C8102E] transition shadow-2xs"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5. Safe Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-xl border border-[#E5E7EB] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-3 mb-4">
              <div className="flex items-center gap-2 text-[#C8102E] font-bold">
                <Shield size={18} />
                <h3 className="text-base text-[#1F2937]">Audit Event Specification</h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="rounded-lg p-1.5 text-[#6B7280] hover:bg-slate-100 hover:text-[#1F2937] transition"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Top metadata grid */}
              <div className="grid grid-cols-2 gap-3 rounded-xl bg-[#F8FAFC] border border-[#E5E7EB] p-3.5">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block">
                    Event ID
                  </span>
                  <span className="font-mono text-[#1F2937] font-semibold">{selectedEvent.event_id}</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block">
                    Timestamp (UTC)
                  </span>
                  <span className="font-mono text-[#1F2937]">{selectedEvent.timestamp}</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block">
                    Actor User ID
                  </span>
                  <span className="font-bold text-[#1F2937]">@{selectedEvent.actor_user_id}</span>{' '}
                  <span className="text-[#6B7280]">({selectedEvent.actor_role})</span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block">
                    Operation Result
                  </span>
                  <span
                    className={`font-bold ${
                      selectedEvent.status === 'success' ? 'text-emerald-700' : 'text-[#C8102E]'
                    }`}
                  >
                    {selectedEvent.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Action Description */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block mb-1">
                  Action
                </label>
                <div className="text-sm font-bold text-[#1F2937] flex items-center gap-2">
                  <span>{selectedEvent.action_label}</span>
                  <span className="font-mono text-xs text-[#6B7280] font-normal">
                    ({selectedEvent.action_type})
                  </span>
                </div>
              </div>

              {/* Investigation Reference */}
              {selectedEvent.case_id && (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block mb-1">
                    Investigation Dossier
                  </label>
                  <span className="inline-flex items-center rounded-md bg-[#FFF1F2] border border-[#FECDD3] px-2.5 py-1 font-mono font-semibold text-[#C8102E]">
                    {selectedEvent.case_id}
                  </span>
                </div>
              )}

              {/* Details text */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block mb-1">
                  Recorded Details
                </label>
                <div className="rounded-xl border border-[#E5E7EB] bg-white p-3 text-[#1F2937] leading-relaxed">
                  {selectedEvent.details || 'No additional text recorded.'}
                </div>
              </div>

              {/* Safe Metadata Payload (JSON) */}
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block mb-1">
                  Security Metadata Attributes
                </label>
                <pre className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] p-3 text-[11px] font-mono text-[#1F2937] overflow-x-auto">
                  {JSON.stringify(selectedEvent.metadata || {}, null, 2)}
                </pre>
              </div>

              {/* Privacy and sanitisation guarantee */}
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 text-[11px] text-emerald-800 flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 text-emerald-600 mt-0.5" />
                <div>
                  <span className="font-bold">Privacy & Integrity Assurance:</span> All audit records are sanitised. Sensitive credentials, passwords, raw evidence bodies, and tokens are strictly excluded from logging.
                </div>
              </div>
            </div>

            <div className="mt-5 border-t border-[#E5E7EB] pt-3 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="rounded-xl border border-[#E5E7EB] bg-white px-4 py-2 text-xs font-semibold text-[#1F2937] hover:border-[#C8102E] transition shadow-2xs"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
