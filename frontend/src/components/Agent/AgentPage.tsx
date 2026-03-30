/**
 * AgentPage.tsx - AI Agent configuration page.
 *
 * Users can:
 * - View and edit the system prompts for each AI agent
 * - Reset prompts to defaults
 * - Manage training examples (few-shot context for the extraction agent)
 */

import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  Bot, RotateCcw, Save, BookOpen, Trash2, UploadCloud,
  X, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronUp, Eye, Code2,
  Database, Zap, TrendingUp, FileEdit,
} from 'lucide-react'
import clsx from 'clsx'
import {
  getAgentPrompts,
  updateAgentPrompt,
  resetAgentPrompt,
  listTrainingExamples,
  uploadTrainingExample,
  deleteTrainingExample,
  getRagStats,
  listCorrections,
  deleteCorrection,
  type AgentPrompt,
  type TrainingExample,
  type RAGStats,
  type CorrectionRecord,
} from '@/services/api'

type Tab = 'prompts' | 'training' | 'knowledge'

export const AgentPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>('prompts')

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Info banner */}
      <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-5">
        <div className="flex items-start gap-3">
          <Bot className="mt-0.5 h-5 w-5 shrink-0 text-indigo-600" />
          <div>
            <p className="text-sm font-semibold text-indigo-800">AI Agent Architecture</p>
            <p className="mt-1 text-sm text-indigo-700">
              The extraction pipeline uses four specialised agents: <strong>Classifier</strong>,{' '}
              <strong>Extractor</strong>, <strong>Mapper</strong>, and <strong>Validator</strong>. Each
              agent has its own configurable prompt. You can also upload completed Load Sheets as
              training examples — these are injected as few-shot context into the Extractor agent.
            </p>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-gray-200 bg-gray-50 p-1">
        {(['prompts', 'training', 'knowledge'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'flex-1 rounded-lg py-2 text-sm font-medium transition-colors',
              tab === t
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700',
            )}
          >
            {t === 'prompts' ? 'Agent Prompts' : t === 'training' ? 'Training Examples' : 'Knowledge Base'}
          </button>
        ))}
      </div>

      {tab === 'prompts' && <PromptsTab />}
      {tab === 'training' && <TrainingTab />}
      {tab === 'knowledge' && <KnowledgeTab />}
    </div>
  )
}

// ── PromptsTab ─────────────────────────────────────────────────────────────────

const PromptsTab: React.FC = () => {
  const [prompts, setPrompts] = useState<AgentPrompt[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getAgentPrompts()
      setPrompts(data)
    } catch {
      setError('Failed to load agent prompts.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading agents…
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button className="ml-auto" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}
      {prompts.map((p) => (
        <PromptCard key={p.key} prompt={p} onUpdated={refresh} />
      ))}
    </div>
  )
}

// ── PromptCard ─────────────────────────────────────────────────────────────────

const PromptCard: React.FC<{ prompt: AgentPrompt; onUpdated: () => void }> = ({ prompt, onUpdated }) => {
  const [expanded, setExpanded] = useState(false)
  const [mode, setMode] = useState<'edit' | 'preview'>('edit')
  const [system, setSystem] = useState(prompt.system)
  const [user, setUser] = useState(prompt.user)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')

  const isDirty = system !== prompt.system || user !== prompt.user

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateAgentPrompt(prompt.key, { system, user })
      setSaveStatus('saved')
      onUpdated()
      setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      const fresh = await resetAgentPrompt(prompt.key)
      setSystem(fresh.system)
      setUser(fresh.user)
      onUpdated()
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left"
      >
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50">
          <Bot className="h-5 w-5 text-indigo-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800">{prompt.name}</p>
          <p className="text-xs text-gray-400 truncate">{prompt.description}</p>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        )}
      </button>

      {/* Expanded editor */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 pb-5 pt-4 space-y-4">

          {/* Edit / Preview toggle */}
          <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-gray-50 p-1 w-fit">
            <button
              onClick={() => setMode('edit')}
              className={clsx(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                mode === 'edit' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700',
              )}
            >
              <Code2 className="h-3.5 w-3.5" /> Edit Template
            </button>
            <button
              onClick={() => setMode('preview')}
              className={clsx(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                mode === 'preview' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700',
              )}
            >
              <Eye className="h-3.5 w-3.5" /> Preview (rendered)
            </button>
          </div>

          {mode === 'edit' ? (
            <>
              {/* System prompt editor */}
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  System Prompt
                </label>
                <p className="mb-2 text-xs text-gray-400">
                  Placeholders: <code className="rounded bg-gray-100 px-1">{'{lims_system}'}</code>{' '}
                  <code className="rounded bg-gray-100 px-1">{'{document_type}'}</code>{' '}
                  <code className="rounded bg-gray-100 px-1">{'{load_sheet_template}'}</code>{' '}
                  — filled from Configure at runtime.
                </p>
                <textarea
                  rows={8}
                  value={system}
                  onChange={(e) => setSystem(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs leading-relaxed text-gray-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-y"
                />
              </div>

              {/* User prompt editor */}
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  User Prompt Template
                </label>
                <textarea
                  rows={6}
                  value={user}
                  onChange={(e) => setUser(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs leading-relaxed text-gray-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-y"
                />
              </div>
            </>
          ) : (
            <>
              {/* Rendered preview */}
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-xs text-indigo-700 mb-2">
                This shows the prompt as the agent will receive it — with your current LIMS system
                and load sheet template already filled in.
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">System (rendered)</p>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-gray-900 p-4 font-mono text-xs text-green-300 max-h-72 overflow-y-auto">
                  {prompt.system_preview ?? system}
                </pre>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">User (rendered)</p>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-gray-900 p-4 font-mono text-xs text-green-300 max-h-48 overflow-y-auto">
                  {prompt.user_preview ?? user}
                </pre>
              </div>
            </>
          )}

          {/* Actions */}
          {mode === 'edit' && (
            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={!isDirty || saving}
                className={clsx(
                  'flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition-colors',
                  isDirty && !saving
                    ? saveStatus === 'saved'
                      ? 'bg-green-500 text-white'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'cursor-not-allowed bg-gray-100 text-gray-400',
                )}
              >
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                {saving ? 'Saving…' : saveStatus === 'saved' ? 'Saved!' : 'Save Changes'}
              </button>

              <button
                onClick={handleReset}
                disabled={resetting}
                className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <RotateCcw className={clsx('h-3.5 w-3.5', resetting && 'animate-spin')} />
                Reset to Default
              </button>

              {saveStatus === 'error' && (
                <span className="text-xs text-red-500">Failed to save.</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── TrainingTab ────────────────────────────────────────────────────────────────

const TrainingTab: React.FC = () => {
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
    <div className="space-y-6">
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
          <div>
            <p className="text-sm font-semibold text-blue-800">Few-Shot Training Examples</p>
            <p className="mt-1 text-sm text-blue-700">
              Upload completed LIMS Load Sheet Excel files (.xlsx). The Extractor Agent uses these
              as reference examples when processing new documents — improving field mapping accuracy
              for your specific products and analyses.
            </p>
          </div>
        </div>
      </div>

      <UploadForm onUploaded={refresh} />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button className="ml-auto" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

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
    <form onSubmit={handleSubmit} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
      <h2 className="text-sm font-semibold text-gray-700">Add Training Example</h2>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Paracetamol 500mg Load Sheet v2"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          required
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Description <span className="text-gray-400">(optional)</span>
        </label>
        <textarea
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what product, document type, or analyses this covers…"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none"
        />
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'cursor-pointer rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors',
          file ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-indigo-400 hover:bg-indigo-50',
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
              Drop a completed Load Sheet here or <span className="text-indigo-600 underline">browse</span>
            </p>
            <p className="mt-1 text-xs text-gray-400">.xlsx or .xls only</p>
          </>
        )}
      </div>

      {status === 'error' && (
        <p className="text-sm text-red-600"><AlertCircle className="mr-1 inline h-4 w-4" />{errorMsg}</p>
      )}

      <button
        type="submit"
        disabled={!file || !name.trim() || status === 'uploading'}
        className={clsx(
          'flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors',
          !file || !name.trim() || status === 'uploading'
            ? 'cursor-not-allowed bg-gray-100 text-gray-400'
            : status === 'success'
            ? 'bg-green-500 text-white'
            : 'bg-indigo-600 text-white hover:bg-indigo-700',
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

// ── KnowledgeTab ───────────────────────────────────────────────────────────────

const KnowledgeTab: React.FC = () => {
  const [stats, setStats] = useState<RAGStats | null>(null)
  const [corrections, setCorrections] = useState<CorrectionRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [s, c] = await Promise.all([
        getRagStats(),
        listCorrections(50, 0),
      ])
      setStats(s)
      setCorrections(c.corrections)
      setTotal(c.total)
    } catch {
      setError('Failed to load knowledge base data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const handleDelete = async (id: number) => {
    setDeleting(id)
    try {
      await deleteCorrection(id)
      setCorrections((prev) => prev.filter((c) => c.id !== id))
      setTotal((t) => t - 1)
      if (stats) setStats({ ...stats, correction_examples: stats.correction_examples - 1 })
    } catch {
      setError('Failed to delete correction.')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Explainer */}
      <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-5">
        <div className="flex items-start gap-3">
          <Database className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
          <div>
            <p className="text-sm font-semibold text-emerald-800">RAG Knowledge Base</p>
            <p className="mt-1 text-sm text-emerald-700">
              Every edit you make in the data review screen is captured as a <strong>correction</strong> and
              embedded into the knowledge base. Future extractions automatically retrieve the most relevant
              corrections and training examples, so the AI learns from every review session.
            </p>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            icon={<Database className="h-5 w-5 text-indigo-500" />}
            label="Total Embeddings"
            value={stats.total_embeddings}
            color="indigo"
          />
          <StatCard
            icon={<BookOpen className="h-5 w-5 text-blue-500" />}
            label="Training Embeddings"
            value={stats.training_embeddings}
            color="blue"
          />
          <StatCard
            icon={<TrendingUp className="h-5 w-5 text-emerald-500" />}
            label="Correction Embeddings"
            value={stats.correction_embeddings}
            color="emerald"
          />
          <StatCard
            icon={<FileEdit className="h-5 w-5 text-amber-500" />}
            label="User Corrections"
            value={stats.correction_examples}
            color="amber"
          />
        </div>
      ) : null}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button className="ml-auto" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Corrections table */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Captured Corrections ({total})
          </h2>
          <button
            onClick={refresh}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {!loading && corrections.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-10 text-center text-sm text-gray-400">
            <Zap className="mx-auto mb-2 h-6 w-6 text-gray-300" />
            No corrections captured yet. Edit extracted data in the review screen to start building the knowledge base.
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left">
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide">Sheet</th>
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide">Field</th>
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide">Was</th>
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide">Corrected To</th>
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide hidden sm:table-cell">Doc Type</th>
                  <th className="px-4 py-2.5 font-semibold text-gray-500 uppercase tracking-wide hidden md:table-cell">Date</th>
                  <th className="px-2 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {corrections.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-2.5 font-medium text-gray-700">{c.sheet_name}</td>
                    <td className="px-4 py-2.5 text-gray-600">{c.field_name}</td>
                    <td className="px-4 py-2.5 text-red-500 line-through max-w-[120px] truncate" title={c.original_value ?? ''}>
                      {c.original_value || <span className="text-gray-300 no-underline">(empty)</span>}
                    </td>
                    <td className="px-4 py-2.5 text-emerald-700 font-medium max-w-[120px] truncate" title={c.corrected_value ?? ''}>
                      {c.corrected_value}
                    </td>
                    <td className="px-4 py-2.5 hidden sm:table-cell">
                      {c.document_type && (
                        <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                          {c.document_type}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 hidden md:table-cell whitespace-nowrap">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-2 py-2.5">
                      <button
                        onClick={() => handleDelete(c.id)}
                        disabled={deleting === c.id}
                        className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 transition-colors"
                        title="Remove correction"
                      >
                        {deleting === c.id
                          ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          : <Trash2 className="h-3.5 w-3.5" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

const StatCard: React.FC<{
  icon: React.ReactNode
  label: string
  value: number
  color: 'indigo' | 'blue' | 'emerald' | 'amber'
}> = ({ icon, label, value, color }) => (
  <div className={clsx(
    'rounded-xl border p-4',
    color === 'indigo' && 'border-indigo-100 bg-indigo-50',
    color === 'blue' && 'border-blue-100 bg-blue-50',
    color === 'emerald' && 'border-emerald-100 bg-emerald-50',
    color === 'amber' && 'border-amber-100 bg-amber-50',
  )}>
    <div className="mb-2">{icon}</div>
    <p className={clsx(
      'text-2xl font-bold',
      color === 'indigo' && 'text-indigo-700',
      color === 'blue' && 'text-blue-700',
      color === 'emerald' && 'text-emerald-700',
      color === 'amber' && 'text-amber-700',
    )}>{value.toLocaleString()}</p>
    <p className="mt-0.5 text-xs text-gray-500">{label}</p>
  </div>
)

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
