/**
 * ProcessingDashboard.tsx - Shows active and recent jobs.
 *
 * Displays document type badge, confidence meter, validation error count,
 * and action buttons (View / Export / Reprocess / Delete).
 */

import React from 'react'
import {
  FileText, AlertTriangle, CheckCircle, XCircle,
  Clock, Download, RefreshCw, Trash2, Eye,
} from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import type { JobSummary } from '@/types/lims'
import { deleteJob, exportJob, reprocessJob } from '@/services/api'

interface Props {
  jobs: JobSummary[]
  onSelectJob: (jobId: string) => void
  onRefresh: () => void
}

export const ProcessingDashboard: React.FC<Props> = ({ jobs, onSelectJob, onRefresh }) => {
  if (jobs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 py-16 text-center">
        <FileText className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <p className="text-sm text-gray-500">No documents processed yet.</p>
        <p className="text-xs text-gray-400 mt-1">Upload a PDF or DOCX to get started.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <JobCard
          key={job.job_id}
          job={job}
          onView={() => onSelectJob(job.job_id)}
          onExport={async () => {
            await exportJob(job.job_id)
          }}
          onReprocess={async () => {
            await reprocessJob(job.job_id)
            onRefresh()
          }}
          onDelete={async () => {
            await deleteJob(job.job_id)
            onRefresh()
          }}
        />
      ))}
    </div>
  )
}

// ── Job Card ──────────────────────────────────────────────────────────────────

interface CardProps {
  job: JobSummary
  onView: () => void
  onExport: () => void
  onReprocess: () => void
  onDelete: () => void
}

const JobCard: React.FC<CardProps> = ({ job, onView, onExport, onReprocess, onDelete }) => {
  const statusConfig = {
    pending:    { icon: Clock,        colour: 'text-gray-500',  bg: 'bg-gray-100',   label: 'Pending' },
    extracting: { icon: RefreshCw,    colour: 'text-blue-600',  bg: 'bg-blue-50',    label: 'Extracting' },
    mapping:    { icon: RefreshCw,    colour: 'text-amber-600', bg: 'bg-amber-50',   label: 'Mapping' },
    validating: { icon: RefreshCw,    colour: 'text-purple-600',bg: 'bg-purple-50',  label: 'Validating' },
    complete:   { icon: CheckCircle,  colour: 'text-green-600', bg: 'bg-green-50',   label: 'Complete' },
    failed:     { icon: XCircle,      colour: 'text-red-600',   bg: 'bg-red-50',     label: 'Failed' },
  }[job.status] ?? { icon: Clock, colour: 'text-gray-500', bg: 'bg-gray-100', label: job.status }

  const Icon = statusConfig.icon
  const isProcessing = ['pending', 'extracting', 'mapping', 'validating'].includes(job.status)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        {/* File icon */}
        <div className={clsx('mt-0.5 rounded-lg p-2', statusConfig.bg)}>
          <FileText className={clsx('h-5 w-5', statusConfig.colour)} />
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-gray-800 truncate">{job.filename}</p>
            <DocTypeBadge docType={job.document_type} />
          </div>

          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            {/* Status */}
            <span className={clsx('flex items-center gap-1', statusConfig.colour)}>
              <Icon className={clsx('h-3.5 w-3.5', isProcessing && 'animate-spin')} />
              {statusConfig.label}
            </span>

            {/* Timestamp */}
            {job.created_at && (
              <span>{format(new Date(job.created_at), 'dd MMM yyyy HH:mm')}</span>
            )}

            {/* Job ID */}
            <span className="font-mono text-gray-400">{job.job_id.slice(0, 8)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {job.status === 'complete' && (
            <>
              <ActionBtn icon={Eye} label="View" onClick={onView} variant="primary" />
              <ActionBtn icon={Download} label="Export" onClick={onExport} variant="success" />
            </>
          )}
          {job.status === 'failed' && (
            <ActionBtn icon={RefreshCw} label="Retry" onClick={onReprocess} variant="warning" />
          )}
          <ActionBtn icon={Trash2} label="Delete" onClick={onDelete} variant="danger" />
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

const DocTypeBadge: React.FC<{ docType: string }> = ({ docType }) => {
  const colours: Record<string, string> = {
    STP:    'bg-blue-100 text-blue-700',
    PTP:    'bg-purple-100 text-purple-700',
    SPEC:   'bg-green-100 text-green-700',
    METHOD: 'bg-amber-100 text-amber-700',
    SOP:    'bg-teal-100 text-teal-700',
    OTHER:  'bg-gray-100 text-gray-500',
    unknown:'bg-gray-100 text-gray-400',
  }
  const colour = colours[docType.toUpperCase()] ?? colours.OTHER
  return (
    <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', colour)}>
      {docType.toUpperCase()}
    </span>
  )
}

const ActionBtn: React.FC<{
  icon: React.FC<{ className?: string }>
  label: string
  onClick: () => void
  variant: 'primary' | 'success' | 'warning' | 'danger'
}> = ({ icon: Icon, label, onClick, variant }) => {
  const colours = {
    primary: 'text-blue-600 hover:bg-blue-50',
    success: 'text-green-600 hover:bg-green-50',
    warning: 'text-amber-600 hover:bg-amber-50',
    danger:  'text-red-500 hover:bg-red-50',
  }[variant]

  return (
    <button
      title={label}
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className={clsx(
        'rounded-lg p-1.5 transition-colors',
        colours,
      )}
    >
      <Icon className="h-4 w-4" />
    </button>
  )
}
