/**
 * App.tsx - Root application component.
 *
 * Layout:
 *   Left sidebar: job history
 *   Main area: upload zone, processing dashboard, data preview, export
 */

import React, { useCallback, useEffect, useState } from 'react'
import { FlaskConical, History, Upload as UploadIcon, LayoutGrid, GraduationCap } from 'lucide-react'
import clsx from 'clsx'
import { UploadZone } from '@/components/Upload/UploadZone'
import { ProcessingDashboard } from '@/components/Dashboard/ProcessingDashboard'
import { DataPreview } from '@/components/DataPreview/DataPreview'
import { ExportControls } from '@/components/ExportControls/ExportControls'
import { JobHistory } from '@/components/History/JobHistory'
import { TrainingPage } from '@/components/Training/TrainingPage'
import { getJob, listJobs } from '@/services/api'
import type { ExtractionResult, JobDetail, JobSummary } from '@/types/lims'

type View = 'upload' | 'dashboard' | 'preview' | 'training'

export default function App() {
  const [view, setView] = useState<View>('upload')
  const [jobs, setJobs] = useState<JobSummary[]>([])
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null)
  const [editedResult, setEditedResult] = useState<ExtractionResult | null>(null)

  // Load job list on mount and periodically
  const refreshJobs = useCallback(async () => {
    try {
      const list = await listJobs()
      setJobs(list)
    } catch { /* ignore network errors during background refresh */ }
  }, [])

  useEffect(() => {
    refreshJobs()
    const interval = setInterval(refreshJobs, 5000)
    return () => clearInterval(interval)
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

  return (
    <div className="flex h-screen bg-gray-100 font-sans overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="flex w-64 flex-col border-r border-gray-200 bg-white shadow-sm">
        {/* Brand */}
        <div className="flex items-center gap-2.5 border-b border-gray-100 px-4 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-lims-blue">
            <FlaskConical className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-gray-800 leading-tight">LIMS OCR</p>
            <p className="text-xs text-gray-400">Document Processor</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-1 p-3">
          <NavBtn
            icon={UploadIcon}
            label="Upload"
            active={view === 'upload'}
            onClick={() => setView('upload')}
          />
          <NavBtn
            icon={LayoutGrid}
            label="Dashboard"
            active={view === 'dashboard'}
            onClick={() => setView('dashboard')}
            badge={jobs.filter((j) => ['pending','extracting','mapping','validating'].includes(j.status)).length}
          />
          <NavBtn
            icon={GraduationCap}
            label="Training"
            active={view === 'training'}
            onClick={() => setView('training')}
          />
        </nav>

        {/* History */}
        <div className="flex-1 overflow-y-auto border-t border-gray-100 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">
            <History className="h-3.5 w-3.5" />
            History
          </p>
          <JobHistory
            jobs={jobs}
            selectedJobId={selectedJob?.job_id}
            onSelect={handleSelectJob}
          />
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
          <div>
            <h1 className="text-base font-bold text-gray-800">
              {view === 'upload' && 'Upload Documents'}
              {view === 'dashboard' && 'Processing Dashboard'}
              {view === 'preview' && (selectedJob?.filename ?? 'Data Preview')}
              {view === 'training' && 'AI Training'}
            </h1>
            {view === 'preview' && selectedJob && (
              <p className="text-xs text-gray-400">
                Job: {selectedJob.job_id.slice(0, 8)} · Type: {selectedJob.document_type}
              </p>
            )}
          </div>

          {/* Export controls for preview view */}
          {view === 'preview' && selectedJob?.status === 'complete' && (
            <ExportControls
              jobId={selectedJob.job_id}
              onReprocess={() => {
                setView('dashboard')
                refreshJobs()
              }}
            />
          )}
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {view === 'upload' && (
            <div className="mx-auto max-w-2xl">
              <UploadZone onJobComplete={handleJobComplete} />
            </div>
          )}

          {view === 'dashboard' && (
            <div className="mx-auto max-w-4xl">
              <ProcessingDashboard
                jobs={jobs}
                onSelectJob={handleSelectJob}
                onRefresh={refreshJobs}
              />
            </div>
          )}

          {view === 'preview' && selectedJob && editedResult && (
            <DataPreview
              jobId={selectedJob.job_id}
              result={editedResult}
              onResultChange={setEditedResult}
            />
          )}

          {view === 'preview' && !selectedJob && (
            <div className="flex h-64 items-center justify-center text-gray-400">
              Select a document from the sidebar to preview data.
            </div>
          )}

          {view === 'training' && <TrainingPage />}
        </div>
      </main>
    </div>
  )
}

// ── NavBtn ────────────────────────────────────────────────────────────────────
const NavBtn: React.FC<{
  icon: React.FC<{ className?: string }>
  label: string
  active: boolean
  onClick: () => void
  badge?: number
}> = ({ icon: Icon, label, active, onClick, badge }) => (
  <button
    onClick={onClick}
    className={clsx(
      'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
      active
        ? 'bg-primary-50 text-primary-700'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800',
    )}
  >
    <Icon className="h-4 w-4 shrink-0" />
    <span className="flex-1 text-left">{label}</span>
    {badge != null && badge > 0 && (
      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-600">
        {badge}
      </span>
    )}
  </button>
)
