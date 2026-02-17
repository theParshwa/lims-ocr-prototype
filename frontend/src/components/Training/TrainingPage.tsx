/**
 * TrainingPage.tsx - Upload completed Load Sheet Excel files to teach the AI.
 *
 * Users can:
 * - Upload a completed Load Sheet (.xlsx) with a name and optional description
 * - View all stored training examples (sheet count, row count, description)
 * - Delete training examples they no longer need
 *
 * These examples are injected as few-shot context into every subsequent
 * AI extraction call, improving accuracy for similar documents.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { BookOpen, Trash2, UploadCloud, X, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import {
  deleteTrainingExample,
  listTrainingExamples,
  uploadTrainingExample,
  type TrainingExample,
} from '@/services/api'

// ── TrainingPage ───────────────────────────────────────────────────────────────

export const TrainingPage: React.FC = () => {
  const [examples, setExamples] = useState<TrainingExample[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const list = await listTrainingExamples()
      setExamples(list)
    } catch {
      setError('Failed to load training examples.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const handleDelete = async (id: number) => {
    try {
      await deleteTrainingExample(id)
      setExamples((prev) => prev.filter((e) => e.id !== id))
    } catch {
      setError('Failed to delete training example.')
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
          <div>
            <p className="text-sm font-semibold text-blue-800">How Training Works</p>
            <p className="mt-1 text-sm text-blue-700">
              Upload completed LIMS Load Sheet Excel files (.xlsx). The AI uses these as reference
              examples when extracting data from new documents — the more examples you add, the
              more accurately the AI will map fields for your specific products and analyses.
            </p>
          </div>
        </div>
      </div>

      {/* Upload form */}
      <UploadForm onUploaded={refresh} />

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button className="ml-auto" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Examples list */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Stored Examples ({examples.length})
        </h2>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : examples.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-10 text-center text-sm text-gray-400">
            No training examples yet. Upload a completed Load Sheet above to get started.
          </div>
        ) : (
          <ul className="space-y-3">
            {examples.map((ex) => (
              <ExampleCard key={ex.id} example={ex} onDelete={() => handleDelete(ex.id)} />
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

// ── UploadForm ─────────────────────────────────────────────────────────────────

const UploadForm: React.FC<{ onUploaded: () => void }> = ({ onUploaded }) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped && /\.xlsx?$/i.test(dropped.name)) setFile(dropped)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !name.trim()) return
    setStatus('uploading')
    setErrorMsg('')
    try {
      await uploadTrainingExample(file, name.trim(), description.trim())
      setStatus('success')
      setName('')
      setDescription('')
      setFile(null)
      onUploaded()
      setTimeout(() => setStatus('idle'), 3000)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Upload failed.'
      setErrorMsg(msg)
      setStatus('error')
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4"
    >
      <h2 className="text-sm font-semibold text-gray-700">Add Training Example</h2>

      {/* Name */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Paracetamol 500mg Load Sheet v2"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      {/* Description */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Description <span className="text-gray-400">(optional)</span>
        </label>
        <textarea
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what product, document type, or analyses this Load Sheet covers..."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
        />
      </div>

      {/* File drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'cursor-pointer rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors',
          file
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <p className="text-sm font-medium text-green-700">
            <CheckCircle2 className="mr-1 inline h-4 w-4" />
            {file.name}
            <button
              type="button"
              className="ml-2 text-gray-400 hover:text-red-500"
              onClick={(e) => { e.stopPropagation(); setFile(null) }}
            >
              <X className="inline h-3.5 w-3.5" />
            </button>
          </p>
        ) : (
          <>
            <UploadCloud className="mx-auto mb-2 h-8 w-8 text-gray-400" />
            <p className="text-sm text-gray-500">
              Drop a completed Load Sheet here or <span className="text-blue-600 underline">browse</span>
            </p>
            <p className="mt-1 text-xs text-gray-400">.xlsx or .xls only</p>
          </>
        )}
      </div>

      {/* Error */}
      {status === 'error' && (
        <p className="text-sm text-red-600"><AlertCircle className="mr-1 inline h-4 w-4" />{errorMsg}</p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={!file || !name.trim() || status === 'uploading'}
        className={clsx(
          'flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors',
          !file || !name.trim() || status === 'uploading'
            ? 'cursor-not-allowed bg-gray-100 text-gray-400'
            : status === 'success'
            ? 'bg-green-500 text-white'
            : 'bg-blue-600 text-white hover:bg-blue-700',
        )}
      >
        {status === 'uploading' && <Loader2 className="h-4 w-4 animate-spin" />}
        {status === 'success' && <CheckCircle2 className="h-4 w-4" />}
        {status === 'uploading' ? 'Uploading…' : status === 'success' ? 'Saved!' : 'Add Training Example'}
      </button>
    </form>
  )
}

// ── ExampleCard ────────────────────────────────────────────────────────────────

const ExampleCard: React.FC<{ example: TrainingExample; onDelete: () => void }> = ({
  example,
  onDelete,
}) => {
  const parsed = example.parsed_content
  const sheets = parsed ? Object.keys(parsed.sheets) : []

  return (
    <li className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-gray-800">{example.name}</p>
          {example.description && (
            <p className="mt-0.5 text-xs text-gray-500">{example.description}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {parsed && (
              <>
                <Chip label={`${parsed.sheet_count} sheets`} color="blue" />
                <Chip label={`${parsed.total_rows} rows`} color="purple" />
              </>
            )}
            {sheets.slice(0, 4).map((s) => (
              <Chip key={s} label={s} color="gray" />
            ))}
            {sheets.length > 4 && (
              <Chip label={`+${sheets.length - 4} more`} color="gray" />
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <p className="text-xs text-gray-400">
            {new Date(example.created_at).toLocaleDateString()}
          </p>
          <button
            onClick={onDelete}
            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </li>
  )
}

const Chip: React.FC<{ label: string; color: 'blue' | 'purple' | 'gray' }> = ({ label, color }) => (
  <span className={clsx(
    'rounded-full px-2 py-0.5 text-xs font-medium',
    color === 'blue' && 'bg-blue-100 text-blue-700',
    color === 'purple' && 'bg-purple-100 text-purple-700',
    color === 'gray' && 'bg-gray-100 text-gray-600',
  )}>
    {label}
  </span>
)
