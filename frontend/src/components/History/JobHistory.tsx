/**
 * JobHistory.tsx - Sidebar history panel listing past processing jobs.
 */

import React from 'react'
import clsx from 'clsx'
import { FileText, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'
import type { JobSummary } from '@/types/lims'

interface Props {
  jobs: JobSummary[]
  selectedJobId?: string
  onSelect: (jobId: string) => void
}

export const JobHistory: React.FC<Props> = ({ jobs, selectedJobId, onSelect }) => {
  if (jobs.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-gray-400">
        No history yet
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {jobs.map((job) => (
        <button
          key={job.job_id}
          onClick={() => onSelect(job.job_id)}
          className={clsx(
            'w-full rounded-lg px-3 py-2.5 text-left transition-colors',
            selectedJobId === job.job_id
              ? 'bg-primary-50 border border-primary-200'
              : 'hover:bg-gray-100',
          )}
        >
          <div className="flex items-start gap-2">
            <StatusIcon status={job.status} />
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-gray-800">{job.filename}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-gray-400 font-mono">{job.document_type}</span>
                {job.created_at && (
                  <span className="text-xs text-gray-400" title={job.created_at}>
                    {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                  </span>
                )}
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'complete') return <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
  if (status === 'failed') return <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
  if (['pending', 'extracting', 'mapping', 'validating'].includes(status))
    return <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-blue-500" />
  return <Clock className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
}
