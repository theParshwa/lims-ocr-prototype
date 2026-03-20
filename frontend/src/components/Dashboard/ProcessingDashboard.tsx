/**
 * ProcessingDashboard.tsx — Data-table style job list.
 */

import React, { useState } from 'react'
import {
  FileText, CheckCircle2, XCircle, Clock, RefreshCw,
  Download, Eye, Trash2,
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

const STATUS_CONFIG = {
  pending:    { label: 'Pending',    cls: 'chip-slate',  dot: 'bg-slate-400',   spin: false },
  extracting: { label: 'Extracting', cls: 'chip-blue',   dot: 'bg-blue-500',    spin: true  },
  mapping:    { label: 'Mapping',    cls: 'chip-purple', dot: 'bg-purple-500',  spin: true  },
  validating: { label: 'Validating', cls: 'chip-amber',  dot: 'bg-amber-500',   spin: true  },
  complete:   { label: 'Complete',   cls: 'chip-green',  dot: 'bg-emerald-500', spin: false },
  failed:     { label: 'Failed',     cls: 'chip-red',    dot: 'bg-red-500',     spin: false },
} as const

const DOC_TYPE_CLS: Record<string, string> = {
  STP: 'chip-blue', PTP: 'chip-purple', SPEC: 'chip-green',
  METHOD: 'chip-amber', SOP: 'chip-teal', OTHER: 'chip-slate',
}

export const ProcessingDashboard: React.FC<Props> = ({ jobs, onSelectJob, onRefresh }) => {
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set())

  const busy = (id: string) => setLoadingIds(s => new Set(s).add(id))
  const idle = (id: string) => setLoadingIds(s => { const n = new Set(s); n.delete(id); return n })

  const handleExport     = async (id: string) => { busy(id); try { await exportJob(id)                  } finally { idle(id) } }
  const handleReprocess  = async (id: string) => { busy(id); try { await reprocessJob(id); onRefresh()  } finally { idle(id) } }
  const handleDelete     = async (id: string) => { busy(id); try { await deleteJob(id);   onRefresh()   } finally { idle(id) } }

  if (jobs.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center py-20 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
          <FileText className="h-5 w-5 text-slate-400" />
        </div>
        <p className="text-sm font-semibold text-slate-600">No documents yet</p>
        <p className="mt-1 text-xs text-slate-400">Upload a PDF or DOCX to begin extraction.</p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      <table className="data-table w-full">
        <thead>
          <tr>
            <th className="w-6 pl-4 pr-0" />
            <th>Document</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
            <th>Job ID</th>
            <th className="text-right pr-4">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const sc = STATUS_CONFIG[job.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending
            const dtc = DOC_TYPE_CLS[job.document_type?.toUpperCase()] ?? 'chip-slate'
            const isLoading    = loadingIds.has(job.job_id)
            const isProcessing = ['pending','extracting','mapping','validating'].includes(job.status)

            return (
              <tr
                key={job.job_id}
                className={clsx(job.status === 'complete' && 'cursor-pointer')}
                onClick={() => job.status === 'complete' && onSelectJob(job.job_id)}
              >
                {/* Status dot */}
                <td className="pl-4 pr-0 w-6">
                  <span className={clsx(
                    'block h-2 w-2 rounded-full',
                    sc.dot,
                    (sc.spin || isProcessing) && 'animate-pulse',
                  )} />
                </td>

                {/* Filename */}
                <td className="max-w-xs">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                    <span className="truncate font-medium text-slate-800" title={job.filename}>
                      {job.filename}
                    </span>
                  </div>
                </td>

                {/* Doc type */}
                <td><span className={dtc}>{job.document_type ?? '—'}</span></td>

                {/* Status */}
                <td>
                  <div className="flex items-center gap-1.5">
                    {isProcessing               && <RefreshCw    className="h-3 w-3 animate-spin text-blue-500" />}
                    {job.status === 'complete'  && <CheckCircle2 className="h-3 w-3 text-emerald-500" />}
                    {job.status === 'failed'    && <XCircle      className="h-3 w-3 text-red-500" />}
                    {job.status === 'pending' && !isProcessing && <Clock className="h-3 w-3 text-slate-400" />}
                    <span className={sc.cls}>{sc.label}</span>
                  </div>
                </td>

                {/* Created */}
                <td className="whitespace-nowrap text-slate-500 tabular-nums">
                  {job.created_at ? format(new Date(job.created_at), 'dd MMM yy · HH:mm') : '—'}
                </td>

                {/* Job ID */}
                <td>
                  <span className="font-mono text-2xs text-slate-400">{job.job_id.slice(0, 8)}</span>
                </td>

                {/* Actions */}
                <td className="pr-3 text-right" onClick={e => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-0.5">
                    {job.status === 'complete' && (
                      <>
                        <TblBtn icon={Eye}      title="View"      onClick={() => onSelectJob(job.job_id)}      cls="hover:text-blue-600" />
                        <TblBtn icon={Download} title="Export"    onClick={() => handleExport(job.job_id)}     cls="hover:text-emerald-600" disabled={isLoading} />
                      </>
                    )}
                    {(job.status === 'failed' || job.status === 'complete') && (
                      <TblBtn icon={RefreshCw} title="Reprocess"  onClick={() => handleReprocess(job.job_id)} cls="hover:text-amber-600"   disabled={isLoading} />
                    )}
                    <TblBtn   icon={Trash2}    title="Delete"     onClick={() => handleDelete(job.job_id)}     cls="hover:text-red-500"     disabled={isLoading} />
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-4 py-2">
        <p className="text-2xs text-slate-400">{jobs.length} record{jobs.length !== 1 ? 's' : ''}</p>
        <button
          onClick={onRefresh}
          className="flex items-center gap-1 text-2xs text-slate-400 hover:text-slate-600 transition-colors"
        >
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
      </div>
    </div>
  )
}

const TblBtn: React.FC<{
  icon: React.FC<{ className?: string }>
  title: string
  onClick: () => void
  cls: string
  disabled?: boolean
}> = ({ icon: Icon, title, onClick, cls, disabled }) => (
  <button
    title={title}
    onClick={onClick}
    disabled={disabled}
    className={clsx('rounded p-1.5 text-slate-400 transition-colors disabled:opacity-30', cls)}
  >
    <Icon className="h-3.5 w-3.5" />
  </button>
)
