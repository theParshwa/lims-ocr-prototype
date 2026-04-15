/**
 * UploadZone.tsx — Enterprise-grade drag-and-drop upload with live pipeline status.
 */

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  UploadCloud, FileText, AlertCircle, CheckCircle2,
  Loader2, Brain, GitMerge, ShieldCheck, ChevronDown,
} from 'lucide-react'
import clsx from 'clsx'
import { uploadDocuments, pollUntilComplete } from '@/services/api'
import type { JobDetail } from '@/types/lims'

const DOCUMENT_TYPES = ['Auto-detect', 'STP', 'PTP', 'SPEC', 'METHOD', 'SOP', 'OTHER'] as const
type DocType = typeof DOCUMENT_TYPES[number]

interface UploadFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error'
  uploadProgress: number
  pipelineProgress: number
  pipelineStage: string
  pipelineMessage: string
  jobId?: string
  error?: string
  result?: JobDetail
}

interface Props {
  onJobComplete: (job: JobDetail) => void
}

const STAGE_META: Record<string, { label: string; Icon: React.FC<{ className?: string }> }> = {
  pending:    { label: 'Queued',     Icon: Loader2 },
  extracting: { label: 'Extracting', Icon: Brain },
  mapping:    { label: 'Mapping',    Icon: GitMerge },
  validating: { label: 'Validating', Icon: ShieldCheck },
  complete:   { label: 'Complete',   Icon: CheckCircle2 },
  failed:     { label: 'Failed',     Icon: AlertCircle },
}

const STAGE_ORDER = ['pending', 'extracting', 'mapping', 'validating', 'complete']

export const UploadZone: React.FC<Props> = ({ onJobComplete }) => {
  const [files,      setFiles]      = useState<UploadFile[]>([])
  const [docType,    setDocType]    = useState<DocType>('Auto-detect')
  const [userContext, setUserContext] = useState('')

  const updateFile = useCallback((id: string, patch: Partial<UploadFile>) => {
    setFiles(prev => prev.map(f => f.id === id ? { ...f, ...patch } : f))
  }, [])

  const onDrop = useCallback(async (accepted: File[]) => {
    const newFiles: UploadFile[] = accepted.map(file => ({
      file, id: crypto.randomUUID(),
      status: 'pending', uploadProgress: 0, pipelineProgress: 0,
      pipelineStage: 'pending', pipelineMessage: 'Waiting…',
    }))
    setFiles(prev => [...prev, ...newFiles])

    for (const uf of newFiles) {
      updateFile(uf.id, { status: 'uploading', pipelineMessage: 'Uploading…' })
      try {
        const hint = docType === 'Auto-detect' ? undefined : docType
        const jobs = await uploadDocuments([uf.file], pct => updateFile(uf.id, { uploadProgress: pct }), hint, userContext)
        const job  = jobs[0]
        updateFile(uf.id, { status: 'processing', uploadProgress: 100, jobId: job.job_id, pipelineMessage: 'Starting extraction…' })

        await pollUntilComplete(job.job_id, (detail) => {
          const stage    = detail.status
          const progress = detail.result?.progress ?? 0
          const message  = detail.result?.message ?? stageFallback(stage)
          updateFile(uf.id, {
            status: stage === 'complete' ? 'complete' : stage === 'failed' ? 'error' : 'processing',
            pipelineStage: stage, pipelineProgress: progress, pipelineMessage: message,
            result: detail, error: detail.error_message,
          })
          if (stage === 'complete') onJobComplete(detail)
        })
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed'
        updateFile(uf.id, { status: 'error', error: msg, pipelineMessage: msg })
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateFile, onJobComplete, docType])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxSize: 100 * 1024 * 1024,
  })

  const clearDone = () => setFiles(prev => prev.filter(f => f.status !== 'complete'))

  return (
    <div className="space-y-4">

      {/* Document type selector */}
      <div className="card p-4">
        <label className="section-label mb-2 block">Document Type Hint</label>
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <select
              value={docType}
              onChange={e => setDocType(e.target.value as DocType)}
              className="w-full appearance-none rounded-md border border-slate-300 bg-white px-3 py-2 pr-8 text-sm font-medium text-slate-700 shadow-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
            >
              {DOCUMENT_TYPES.map(t => (
                <option key={t} value={t}>{t === 'Auto-detect' ? 'Auto-detect (recommended)' : t}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          </div>
          {docType !== 'Auto-detect' && (
            <p className="text-xs text-primary-600 font-medium whitespace-nowrap">
              Agent will treat as <strong>{docType}</strong>
            </p>
          )}
        </div>
      </div>

      {/* User context / notes */}
      <div className="card p-4">
        <label className="section-label mb-1.5 block">
          Additional Context&nbsp;
          <span className="font-normal text-slate-400 normal-case">(optional)</span>
        </label>
        <textarea
          value={userContext}
          onChange={e => setUserContext(e.target.value)}
          rows={3}
          placeholder={
            'e.g. "This is a mix of an STP and a method document — the first 10 pages are STP, the rest is the analytical method."\n' +
            '"The product name throughout should be Paracetamol 500mg Tablets, the document uses an internal code P-500."\n' +
            '"Ignore Appendix B — it contains superseded limits."'
          }
          className="w-full resize-y rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-400/20"
        />
        <p className="mt-1.5 text-xs text-slate-400">
          Describe exceptions, mixed documents, known quirks, or any context that will help the AI extract more accurately.
        </p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'relative cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition-all duration-150',
          isDragActive
            ? 'border-primary-500 bg-primary-50/50 scale-[1.005]'
            : 'border-slate-300 bg-white hover:border-primary-400 hover:bg-slate-50/50',
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className={clsx(
          'mx-auto mb-3 h-10 w-10 transition-colors',
          isDragActive ? 'text-primary-500' : 'text-slate-300',
        )} />
        <p className="text-sm font-semibold text-slate-700">
          {isDragActive ? 'Release to upload' : 'Drop documents here'}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          or <span className="text-primary-600 font-medium">browse files</span>
          <span className="mx-1.5 text-slate-300">·</span>
          PDF, DOCX up to 100 MB
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-600">{files.length} file{files.length > 1 ? 's' : ''}</p>
            <button onClick={clearDone} className="text-2xs text-slate-400 hover:text-slate-600 underline">
              Clear completed
            </button>
          </div>
          {files.map(uf => <FileRow key={uf.id} uf={uf} />)}
        </div>
      )}
    </div>
  )
}

// ── FileRow ───────────────────────────────────────────────────────────────────

const FileRow: React.FC<{ uf: UploadFile }> = ({ uf }) => {
  const meta     = STAGE_META[uf.pipelineStage] ?? STAGE_META.pending
  const { Icon } = meta
  const isSpinning = ['pending','extracting','mapping','validating'].includes(uf.pipelineStage) && uf.status !== 'error'

  const displayProgress = uf.status === 'uploading'
    ? Math.round(uf.uploadProgress * 0.1)
    : uf.pipelineProgress

  const barCls =
    uf.status === 'error'             ? 'bg-red-400' :
    uf.status === 'complete'          ? 'bg-emerald-500' :
    uf.pipelineStage === 'extracting' ? 'bg-primary-500' :
    uf.pipelineStage === 'mapping'    ? 'bg-violet-500' :
    uf.pipelineStage === 'validating' ? 'bg-amber-500' :
    'bg-slate-300'

  const statusCls =
    uf.status === 'error'    ? 'text-red-500' :
    uf.status === 'complete' ? 'text-emerald-600' :
    uf.pipelineStage === 'extracting' ? 'text-primary-600' :
    uf.pipelineStage === 'mapping'    ? 'text-violet-600' :
    uf.pipelineStage === 'validating' ? 'text-amber-600' :
    'text-slate-500'

  return (
    <div className="card p-4 space-y-3">
      {/* Top row */}
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-100">
          <FileText className="h-4 w-4 text-slate-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-semibold text-slate-800">{uf.file.name}</p>
          <p className="text-xs text-slate-400">{(uf.file.size / 1024).toFixed(0)} KB</p>
        </div>
        <div className={clsx('flex items-center gap-1.5 text-xs font-semibold shrink-0', statusCls)}>
          <Icon className={clsx('h-4 w-4', isSpinning && 'animate-spin')} />
          {meta.label}
        </div>
      </div>

      {/* Progress bar */}
      {uf.status !== 'pending' && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className={clsx('font-medium', statusCls)}>{uf.pipelineMessage}</span>
            <span className="tabular-nums text-slate-400">{displayProgress}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={clsx('h-full rounded-full transition-all duration-500', barCls)}
              style={{ width: `${displayProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stage stepper */}
      {uf.status === 'processing' && (
        <div className="flex items-center gap-1 pt-0.5">
          {STAGE_ORDER.map((stage, i) => {
            const idx     = STAGE_ORDER.indexOf(uf.pipelineStage)
            const isDone  = i < idx
            const isNow   = stage === uf.pipelineStage
            const s       = STAGE_META[stage]
            const S       = s.Icon
            return (
              <React.Fragment key={stage}>
                <div className="flex flex-col items-center gap-0.5">
                  <div className={clsx(
                    'flex h-6 w-6 items-center justify-center rounded-full border-2 transition-all',
                    isDone   ? 'border-emerald-500 bg-emerald-50' :
                    isNow    ? 'border-primary-500 bg-primary-50' :
                               'border-slate-200 bg-slate-50',
                  )}>
                    <S className={clsx(
                      'h-3 w-3',
                      isDone ? 'text-emerald-500' :
                      isNow  ? clsx('text-primary-500 animate-pulse') :
                               'text-slate-300',
                    )} />
                  </div>
                  <span className={clsx(
                    'text-2xs capitalize whitespace-nowrap',
                    isNow ? 'font-semibold text-slate-700' : 'text-slate-400',
                  )}>
                    {s.label}
                  </span>
                </div>
                {i < STAGE_ORDER.length - 1 && (
                  <div className={clsx(
                    'mb-4 h-px flex-1 mx-0.5 transition-all',
                    i < idx ? 'bg-emerald-400' : 'bg-slate-200',
                  )} />
                )}
              </React.Fragment>
            )
          })}
        </div>
      )}

      {/* Error */}
      {uf.error && (
        <div className="flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {uf.error}
        </div>
      )}

      {/* Success summary */}
      {uf.status === 'complete' && uf.result?.result && (
        <div className="flex items-center gap-3 rounded-md bg-emerald-50 px-3 py-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-emerald-700">
            <span><span className="font-semibold">Type:</span> {uf.result.result.document_type}</span>
            <span><span className="font-semibold">Confidence:</span> {(uf.result.result.overall_confidence * 100).toFixed(0)}%</span>
            <span><span className="font-semibold">Analysis rows:</span> {uf.result.result.analysis?.length ?? 0}</span>
            <span><span className="font-semibold">Spec rows:</span> {uf.result.result.product_specs?.length ?? 0}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function stageFallback(stage: string): string {
  return ({
    pending:    'Queued…',
    extracting: 'AI agent reading and extracting data…',
    mapping:    'Mapping to LIMS schema…',
    validating: 'Running validation checks…',
    complete:   'Extraction complete.',
    failed:     'Processing failed.',
  } as Record<string, string>)[stage] ?? 'Processing…'
}
