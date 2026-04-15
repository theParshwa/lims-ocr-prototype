/**
 * ExportControls.tsx — Professional export + reprocess action bar.
 */

import React, { useState } from 'react'
import { Download, RefreshCw, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { exportJob, reprocessJob } from '@/services/api'

interface Props {
  jobId: string
  onReprocess?: () => void
  disabled?: boolean
}

export const ExportControls: React.FC<Props> = ({ jobId, onReprocess, disabled = false }) => {
  const [exporting,    setExporting]    = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleExport = async () => {
    setExporting(true); setStatus('idle'); setErrorMsg(null)
    try { await exportJob(jobId); setStatus('ok') }
    catch (err) {
      setStatus('error')
      setErrorMsg(err instanceof Error ? err.message : 'Export failed')
    }
    finally { setExporting(false) }
  }

  const handleReprocess = async () => {
    setReprocessing(true)
    try { await reprocessJob(jobId); onReprocess?.() }
    catch { /* ignore */ }
    finally { setReprocessing(false) }
  }

  return (
    <div className="flex items-center gap-2">
      {/* Status feedback */}
      {status === 'ok' && (
        <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
          <CheckCircle2 className="h-3.5 w-3.5" /> Downloaded
        </span>
      )}
      {status === 'error' && (
        <span className="flex items-center gap-1 text-xs text-red-500 font-medium" title={errorMsg ?? undefined}>
          <AlertCircle className="h-3.5 w-3.5" /> {errorMsg ?? 'Export failed'}
        </span>
      )}

      {/* Reprocess */}
      <button
        onClick={handleReprocess}
        disabled={reprocessing || disabled}
        className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 transition-colors"
      >
        <RefreshCw className={clsx('h-3.5 w-3.5', reprocessing && 'animate-spin')} />
        Reprocess
      </button>

      {/* Export */}
      <button
        onClick={handleExport}
        disabled={exporting || disabled}
        className="flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-primary-700 disabled:opacity-50 transition-colors"
      >
        {exporting
          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
          : <Download className="h-3.5 w-3.5" />}
        {exporting ? 'Generating…' : 'Export Load Sheet'}
      </button>
    </div>
  )
}
