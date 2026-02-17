/**
 * UploadZone.tsx - Drag-and-drop upload with detailed live progress tracking.
 */

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, AlertCircle, CheckCircle,
  Loader2, Brain, GitMerge, ShieldCheck, Sparkles,
} from 'lucide-react'
import clsx from 'clsx'
import { uploadDocuments, pollUntilComplete } from '@/services/api'
import type { JobDetail } from '@/types/lims'

interface UploadFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error'
  uploadProgress: number     // 0-100 upload bytes
  pipelineProgress: number   // 0-100 backend pipeline
  pipelineStage: string      // current stage label
  pipelineMessage: string    // current message from backend
  jobId?: string
  error?: string
  result?: JobDetail
}

interface Props {
  onJobComplete: (job: JobDetail) => void
}

// ── Stage metadata ────────────────────────────────────────────────────────────
const STAGE_META: Record<string, { label: string; colour: string; Icon: React.FC<{className?: string}> }> = {
  pending:    { label: 'Queued',      colour: 'text-gray-500',   Icon: Loader2 },
  extracting: { label: 'Extracting',  colour: 'text-blue-600',   Icon: Brain },
  mapping:    { label: 'Mapping',     colour: 'text-purple-600', Icon: GitMerge },
  validating: { label: 'Validating',  colour: 'text-amber-600',  Icon: ShieldCheck },
  complete:   { label: 'Complete',    colour: 'text-green-600',  Icon: CheckCircle },
  failed:     { label: 'Failed',      colour: 'text-red-500',    Icon: AlertCircle },
}

const STAGE_ORDER = ['pending', 'extracting', 'mapping', 'validating', 'complete']

export const UploadZone: React.FC<Props> = ({ onJobComplete }) => {
  const [files, setFiles] = useState<UploadFile[]>([])

  const updateFile = useCallback((id: string, patch: Partial<UploadFile>) => {
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)))
  }, [])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      id: crypto.randomUUID(),
      status: 'pending',
      uploadProgress: 0,
      pipelineProgress: 0,
      pipelineStage: 'pending',
      pipelineMessage: 'Waiting to upload…',
    }))
    setFiles((prev) => [...prev, ...newFiles])

    for (const uf of newFiles) {
      updateFile(uf.id, { status: 'uploading', pipelineMessage: 'Uploading file…' })
      try {
        const jobs = await uploadDocuments([uf.file], (pct) => {
          updateFile(uf.id, { uploadProgress: pct })
        })
        const job = jobs[0]
        updateFile(uf.id, {
          status: 'processing',
          uploadProgress: 100,
          jobId: job.job_id,
          pipelineMessage: 'File uploaded — starting extraction…',
        })

        await pollUntilComplete(job.job_id, (detail) => {
          const backendResult = detail.result
          const stage = detail.status
          const progress = backendResult?.progress ?? 0
          const message = backendResult?.message ?? stageFallbackMessage(stage)

          updateFile(uf.id, {
            status: stage === 'complete' ? 'complete' : stage === 'failed' ? 'error' : 'processing',
            pipelineStage: stage,
            pipelineProgress: progress,
            pipelineMessage: message,
            result: detail,
            error: detail.error_message,
          })

          if (stage === 'complete') onJobComplete(detail)
        })
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Upload failed'
        updateFile(uf.id, { status: 'error', error: message, pipelineMessage: message })
      }
    }
  }, [updateFile, onJobComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxSize: 100 * 1024 * 1024,
  })

  const clearComplete = () => setFiles((prev) => prev.filter((f) => f.status !== 'complete'))

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
          isDragActive
            ? 'border-primary-500 bg-primary-50 scale-[1.01]'
            : 'border-gray-300 bg-gray-50 hover:border-primary-400 hover:bg-primary-50',
        )}
      >
        <input {...getInputProps()} />
        <Upload className={clsx('mx-auto mb-4 h-12 w-12', isDragActive ? 'text-primary-600' : 'text-gray-400')} />
        <p className="text-lg font-semibold text-gray-700">
          {isDragActive ? 'Drop your documents here' : 'Drag & drop documents here'}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          or <span className="text-primary-600 font-medium">click to browse</span>
        </p>
        <p className="mt-2 text-xs text-gray-400">Supported: PDF, DOCX &nbsp;·&nbsp; Max 100 MB</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Files ({files.length})</h3>
            <button onClick={clearComplete} className="text-xs text-gray-400 hover:text-gray-600 underline">
              Clear completed
            </button>
          </div>
          {files.map((uf) => <FileRow key={uf.id} uf={uf} />)}
        </div>
      )}
    </div>
  )
}

// ── FileRow with full progress display ────────────────────────────────────────
const FileRow: React.FC<{ uf: UploadFile }> = ({ uf }) => {
  const meta = STAGE_META[uf.pipelineStage] ?? STAGE_META.pending
  const { Icon } = meta
  const isSpinning = ['pending', 'extracting', 'mapping', 'validating'].includes(uf.pipelineStage)
    && uf.status !== 'error'

  // Overall progress: uploading phase = 0-10%, pipeline = 10-100%
  const displayProgress = uf.status === 'uploading'
    ? Math.round(uf.uploadProgress * 0.1)
    : uf.pipelineProgress

  const barColour =
    uf.status === 'error'    ? 'bg-red-400' :
    uf.status === 'complete' ? 'bg-green-500' :
    uf.pipelineStage === 'extracting' ? 'bg-blue-500' :
    uf.pipelineStage === 'mapping'    ? 'bg-purple-500' :
    uf.pipelineStage === 'validating' ? 'bg-amber-500' :
    'bg-gray-300'

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
      {/* Top row: file info + status */}
      <div className="flex items-start gap-3">
        <FileText className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" />
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-semibold text-gray-800">{uf.file.name}</p>
          <p className="text-xs text-gray-400">{(uf.file.size / 1024).toFixed(0)} KB</p>
        </div>
        <div className={clsx('flex items-center gap-1.5 text-xs font-medium shrink-0', meta.colour)}>
          <Icon className={clsx('h-4 w-4', isSpinning && 'animate-spin')} />
          {meta.label}
        </div>
      </div>

      {/* Progress bar */}
      {uf.status !== 'pending' && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-gray-500">
            <span className={clsx('font-medium', meta.colour)}>{uf.pipelineMessage}</span>
            <span>{displayProgress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className={clsx('h-full rounded-full transition-all duration-500', barColour)}
              style={{ width: `${displayProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stage steps (only while processing) */}
      {uf.status === 'processing' && (
        <div className="flex items-center justify-between pt-1">
          {STAGE_ORDER.map((stage, i) => {
            const currentIdx = STAGE_ORDER.indexOf(uf.pipelineStage)
            const isDone = i < currentIdx
            const isActive = stage === uf.pipelineStage
            const s = STAGE_META[stage]
            const S = s.Icon
            return (
              <React.Fragment key={stage}>
                <div className="flex flex-col items-center gap-1">
                  <div className={clsx(
                    'flex h-7 w-7 items-center justify-center rounded-full border-2 transition-all',
                    isDone   ? 'border-green-500 bg-green-50'  :
                    isActive ? 'border-blue-500 bg-blue-50'    :
                               'border-gray-200 bg-gray-50',
                  )}>
                    <S className={clsx(
                      'h-3.5 w-3.5',
                      isDone   ? 'text-green-500'              :
                      isActive ? clsx('text-blue-500', 'animate-pulse') :
                                 'text-gray-300',
                    )} />
                  </div>
                  <span className={clsx(
                    'text-xs capitalize',
                    isActive ? 'font-semibold text-gray-700' : 'text-gray-400',
                  )}>
                    {s.label}
                  </span>
                </div>
                {i < STAGE_ORDER.length - 1 && (
                  <div className={clsx(
                    'mb-4 h-0.5 flex-1 mx-1 transition-all',
                    i < currentIdx ? 'bg-green-400' : 'bg-gray-200',
                  )} />
                )}
              </React.Fragment>
            )
          })}
        </div>
      )}

      {/* Error message */}
      {uf.error && (
        <p className="flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {uf.error}
        </p>
      )}

      {/* Success summary */}
      {uf.status === 'complete' && uf.result?.result && (
        <div className="flex items-center gap-3 rounded-lg bg-green-50 px-3 py-2">
          <Sparkles className="h-4 w-4 text-green-600 shrink-0" />
          <div className="text-xs text-green-700 flex flex-wrap gap-x-3">
            <span><b>Type:</b> {uf.result.result.document_type}</span>
            <span><b>Confidence:</b> {(uf.result.result.overall_confidence * 100).toFixed(0)}%</span>
            <span><b>Analysis rows:</b> {uf.result.result.analysis?.length ?? 0}</span>
            <span><b>Spec rows:</b> {uf.result.result.product_specs?.length ?? 0}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function stageFallbackMessage(stage: string): string {
  return {
    pending:    'Queued, waiting to start…',
    extracting: 'AI is reading and extracting data from your document…',
    mapping:    'Mapping extracted data to LIMS schema…',
    validating: 'Validating data and checking references…',
    complete:   'Processing complete!',
    failed:     'Processing failed.',
  }[stage] ?? 'Processing…'
}
