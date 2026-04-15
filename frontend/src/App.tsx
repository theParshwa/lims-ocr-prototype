/**
 * App.tsx — Root component.
 * Dark enterprise sidebar + clean main content area.
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  UploadCloud, LayoutDashboard, Bot, Settings2,
  ChevronRight, Activity, Database, FlaskConical,
} from 'lucide-react'
import clsx from 'clsx'
import { UploadZone }          from '@/components/Upload/UploadZone'
import { ProcessingDashboard } from '@/components/Dashboard/ProcessingDashboard'
import { DataPreview }         from '@/components/DataPreview/DataPreview'
import { ExportControls }      from '@/components/ExportControls/ExportControls'
import { JobHistory }          from '@/components/History/JobHistory'
import { AgentPage }           from '@/components/Agent/AgentPage'
import { ConfigurePage }       from '@/components/Configure/ConfigurePage'
import { LimsSelector }        from '@/components/LimsSelector/LimsSelector'
import { getJob, listJobs, getConfig } from '@/services/api'
import type { ExtractionResult, JobDetail, JobSummary } from '@/types/lims'

type View = 'upload' | 'dashboard' | 'preview' | 'agent' | 'configure'


const NAV = [
  { id: 'upload'    as View, label: 'Upload',      Icon: UploadCloud },
  { id: 'dashboard' as View, label: 'Dashboard',   Icon: LayoutDashboard },
  { id: 'agent'     as View, label: 'Agent',        Icon: Bot },
  { id: 'configure' as View, label: 'Configure',    Icon: Settings2 },
]

export default function App() {
  const [limsSystem, setLimsSystem] = useState<string | null>(
    () => localStorage.getItem('lims_system'),
  )
  const [loadingLims, setLoadingLims] = useState(!localStorage.getItem('lims_system'))
  const [view, setView]               = useState<View>('upload')
  const [jobs, setJobs]               = useState<JobSummary[]>([])
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null)
  const [editedResult, setEditedResult] = useState<ExtractionResult | null>(null)

  // Verify LIMS from backend if not cached
  useEffect(() => {
    if (limsSystem) { setLoadingLims(false); return }
    getConfig()
      .then((cfg) => {
        if (cfg.lims_system) {
          localStorage.setItem('lims_system', cfg.lims_system)
          setLimsSystem(cfg.lims_system)
        }
      })
      .finally(() => setLoadingLims(false))
  }, [limsSystem])

  const refreshJobs = useCallback(async () => {
    try { setJobs(await listJobs()) } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    refreshJobs()
    const t = setInterval(refreshJobs, 5000)
    return () => clearInterval(t)
  }, [refreshJobs])

  const handleJobComplete = useCallback(async (job: JobDetail) => {
    await refreshJobs()
    if (job.result) {
      setSelectedJob(job)
      setEditedResult(job.result)
      setView('preview')
    }
  }, [refreshJobs])

  const handleSelectJob = useCallback(async (jobId: string) => {
    try {
      const detail = await getJob(jobId)
      setSelectedJob(detail)
      setEditedResult(detail.result ?? null)
      setView('preview')
    } catch { /* ignore */ }
  }, [])

  if (loadingLims) return null
  if (!limsSystem) return <LimsSelector onSelect={setLimsSystem} />

  const activeJobs  = jobs.filter(j => ['pending','extracting','mapping','validating'].includes(j.status)).length
  const doneJobs    = jobs.filter(j => j.status === 'complete').length
  const failedJobs  = jobs.filter(j => j.status === 'failed').length

  const viewTitle: Record<View, string> = {
    upload:    'Upload Documents',
    dashboard: 'Processing Dashboard',
    preview:   selectedJob?.filename ?? 'Data Preview',
    agent:     'AI Agent',
    configure: 'Configure',
  }

  return (
    <div className="flex h-screen overflow-hidden bg-page font-sans">

      {/* ── Dark Sidebar ────────────────────────────────────────────── */}
      <aside className="flex w-60 flex-shrink-0 flex-col bg-sidebar overflow-hidden">

        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-sidebar-border">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600 shrink-0">
            <FlaskConical className="text-white" style={{ width: 18, height: 18 }} />
          </div>
          <div>
            <p className="text-sm font-bold text-white tracking-tight">LIMS AI</p>
            <p className="text-2xs text-slate-500 truncate">{limsSystem}</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 px-3 py-4">
          <p className="section-label px-2 mb-2 text-slate-600">Navigation</p>
          {NAV.map(({ id, label, Icon }) => {
            const isActive = view === id || (view === 'preview' && id === 'dashboard')
            const badge = id === 'dashboard' && activeJobs > 0 ? activeJobs : undefined
            return (
              <button
                key={id}
                onClick={() => setView(id)}
                className={clsx(
                  'group flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-sidebar-active text-white border-l-2 border-primary-400 pl-[10px]'
                    : 'text-slate-400 hover:bg-sidebar-hover hover:text-slate-200 border-l-2 border-transparent',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="flex-1 text-left">{label}</span>
                {badge != null && (
                  <span className="rounded-full bg-primary-600 px-1.5 py-0.5 text-2xs font-bold text-white">
                    {badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Stats strip */}
        <div className="mx-3 mb-3 rounded-md border border-sidebar-border bg-sidebar-hover p-3 space-y-1.5">
          <p className="section-label text-slate-600">Session</p>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Processing</span>
            <span className={clsx('font-semibold', activeJobs > 0 ? 'text-blue-400' : 'text-slate-500')}>{activeJobs}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Complete</span>
            <span className="font-semibold text-emerald-400">{doneJobs}</span>
          </div>
          {failedJobs > 0 && (
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Failed</span>
              <span className="font-semibold text-red-400">{failedJobs}</span>
            </div>
          )}
        </div>

        {/* History */}
        <div className="flex-1 overflow-y-auto sidebar-scroll border-t border-sidebar-border px-3 py-3">
          <p className="section-label px-2 mb-2 text-slate-600">Recent Jobs</p>
          <JobHistory
            jobs={jobs}
            selectedJobId={selectedJob?.job_id}
            onSelect={handleSelectJob}
          />
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">

        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm flex-shrink-0">
          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="font-semibold text-slate-500">{limsSystem}</span>
            <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
            <span className="font-semibold text-slate-900">{viewTitle[view]}</span>
            {view === 'preview' && selectedJob && (
              <>
                <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-2xs text-slate-500">
                  {selectedJob.job_id.slice(0, 8)}
                </span>
                <DocTypePill docType={selectedJob.document_type} />
              </>
            )}
          </div>

          {/* Right slot */}
          <div className="flex items-center gap-4">
            {activeJobs > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-blue-600">
                <Activity className="h-3.5 w-3.5 animate-pulse" />
                <span className="font-medium">{activeJobs} processing</span>
              </div>
            )}
            {view === 'preview' && selectedJob?.status === 'complete' && (
              <ExportControls
                jobId={selectedJob.job_id}
                onReprocess={() => { setView('dashboard'); refreshJobs() }}
              />
            )}
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-600">
              <FlaskConical className="text-white" style={{ width: 18, height: 18 }} />
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          <div className={clsx(
            'mx-auto p-6',
            view === 'preview' ? 'max-w-full' : 'max-w-5xl',
          )}>
            {view === 'upload' && (
              <div className="max-w-2xl mx-auto">
                <PageHeader
                  title="Upload Documents"
                  subtitle="Drop laboratory documents to extract structured LIMS Load Sheet data."
                />
                <UploadZone onJobComplete={handleJobComplete} />
              </div>
            )}

            {view === 'dashboard' && (
              <>
                <PageHeader
                  title="Processing Dashboard"
                  subtitle={`${jobs.length} total document${jobs.length !== 1 ? 's' : ''} · ${doneJobs} complete · ${activeJobs} processing`}
                />
                <ProcessingDashboard
                  jobs={jobs}
                  onSelectJob={handleSelectJob}
                  onRefresh={refreshJobs}
                />
              </>
            )}

            {view === 'preview' && selectedJob && editedResult && (
              <DataPreview
                jobId={selectedJob.job_id}
                result={editedResult}
                onResultChange={setEditedResult}
              />
            )}

            {view === 'preview' && !selectedJob && (
              <EmptyState
                title="No document selected"
                subtitle="Select a document from the sidebar or dashboard to preview extracted data."
              />
            )}

            {view === 'agent' && (
              <>
                <PageHeader
                  title="AI Agent"
                  subtitle="Configure extraction agent prompts, normalisation rules, and training examples."
                />
                <AgentPage />
              </>
            )}

            {view === 'configure' && (
              <>
                <PageHeader
                  title="Configure"
                  subtitle="Manage LIMS platform settings, load sheet templates, and AI parameters."
                />
                <ConfigurePage />
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

// ── Shared sub-components ─────────────────────────────────────────────────────

export const PageHeader: React.FC<{ title: string; subtitle?: string }> = ({ title, subtitle }) => (
  <div className="mb-6">
    <h1 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h1>
    {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
  </div>
)

export const EmptyState: React.FC<{ title: string; subtitle: string }> = ({ title, subtitle }) => (
  <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-20 text-center">
    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
      <Database className="h-5 w-5 text-slate-400" />
    </div>
    <p className="text-sm font-semibold text-slate-600">{title}</p>
    <p className="mt-1 text-xs text-slate-400 max-w-xs">{subtitle}</p>
  </div>
)

const DocTypePill: React.FC<{ docType: string }> = ({ docType }) => {
  const map: Record<string, string> = {
    STP: 'chip-blue', PTP: 'chip-purple', SPEC: 'chip-green',
    METHOD: 'chip-amber', SOP: 'chip-teal', OTHER: 'chip-slate',
  }
  return <span className={map[docType?.toUpperCase()] ?? 'chip-slate'}>{docType}</span>
}
