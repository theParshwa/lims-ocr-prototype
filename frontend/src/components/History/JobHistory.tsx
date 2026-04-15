/**
 * JobHistory.tsx — Compact dark-sidebar job list.
 */

import React from 'react'
import clsx from 'clsx'
import { CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { JobSummary } from '@/types/lims'

interface Props {
  jobs: JobSummary[]
  selectedJobId?: string
  onSelect: (jobId: string) => void
}

export const JobHistory: React.FC<Props> = ({ jobs, selectedJobId, onSelect }) => {
  if (jobs.length === 0) {
    return (
      <p className="px-2 py-6 text-center text-2xs text-slate-600">No jobs yet</p>
    )
  }

  return (
    <div className="space-y-px">
      {jobs.map((job) => {
        const isSelected   = selectedJobId === job.job_id
        const isProcessing = ['pending','extracting','mapping','validating'].includes(job.status)

        return (
          <button
            key={job.job_id}
            onClick={() => onSelect(job.job_id)}
            className={clsx(
              'group flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors duration-100',
              isSelected ? 'bg-sidebar-active' : 'hover:bg-sidebar-hover',
            )}
          >
            <div className="mt-0.5 shrink-0">
              {job.status === 'complete' && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
              {job.status === 'failed'   && <XCircle      className="h-3.5 w-3.5 text-red-400" />}
              {isProcessing              && <Loader2      className="h-3.5 w-3.5 animate-spin text-blue-400" />}
              {!isProcessing && job.status === 'pending' && <Clock className="h-3.5 w-3.5 text-slate-500" />}
            </div>

            <div className="flex-1 min-w-0">
              <p className={clsx(
                'truncate text-xs font-medium leading-tight',
                isSelected ? 'text-white' : 'text-slate-300 group-hover:text-slate-100',
              )}>
                {job.filename}
              </p>
              <div className="mt-0.5 flex items-center gap-1.5">
                <span className={clsx(
                  'text-2xs font-semibold uppercase tracking-wide',
                  isSelected ? 'text-slate-400' : 'text-slate-600',
                )}>
                  {job.document_type}
                </span>
                {job.created_at && (
                  <span className="text-2xs text-slate-600 truncate">
                    {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                  </span>
                )}
              </div>
            </div>

          </button>
        )
      })}
    </div>
  )
}
