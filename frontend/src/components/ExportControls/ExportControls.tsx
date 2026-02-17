/**
 * ExportControls.tsx - Excel export and reprocess buttons.
 */

import React, { useState } from 'react'
import { Download, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import clsx from 'clsx'
import { exportJob, reprocessJob } from '@/services/api'

interface Props {
  jobId: string
  onReprocess?: () => void
  disabled?: boolean
}

export const ExportControls: React.FC<Props> = ({ jobId, onReprocess, disabled = false }) => {
  const [exporting, setExporting] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')

  const handleExport = async () => {
    setExporting(true)
    setStatus('idle')
    try {
      await exportJob(jobId)
      setStatus('ok')
    } catch {
      setStatus('error')
    } finally {
      setExporting(false)
    }
  }

  const handleReprocess = async () => {
    setReprocessing(true)
    try {
      await reprocessJob(jobId)
      onReprocess?.()
    } catch {
      /* ignore */
    } finally {
      setReprocessing(false)
    }
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        onClick={handleExport}
        disabled={exporting || disabled}
        className={clsx(
          'flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors shadow-sm',
          disabled
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-lims-blue text-white hover:bg-blue-800',
        )}
      >
        {exporting ? (
          <RefreshCw className="h-4 w-4 animate-spin" />
        ) : (
          <Download className="h-4 w-4" />
        )}
        {exporting ? 'Generating Excel…' : 'Download Excel Load Sheet'}
      </button>

      <button
        onClick={handleReprocess}
        disabled={reprocessing || disabled}
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors shadow-sm"
      >
        <RefreshCw className={clsx('h-4 w-4', reprocessing && 'animate-spin')} />
        Reprocess Document
      </button>

      {status === 'ok' && (
        <span className="flex items-center gap-1.5 text-sm text-green-600">
          <CheckCircle className="h-4 w-4" /> Download started
        </span>
      )}
      {status === 'error' && (
        <span className="flex items-center gap-1.5 text-sm text-red-500">
          <AlertCircle className="h-4 w-4" /> Export failed — check console
        </span>
      )}
    </div>
  )
}
