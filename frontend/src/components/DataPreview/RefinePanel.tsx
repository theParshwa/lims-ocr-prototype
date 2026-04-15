/**
 * RefinePanel.tsx - Natural-language correction interface.
 *
 * The user describes what needs to change in plain English.
 * The instruction is sent to GPT via the /refine endpoint.
 * GPT returns targeted field-level changes which are applied to the live result.
 * A history of all instructions + AI responses is shown in a chat-style feed.
 */

import React, { useRef, useState } from 'react'
import {
  Bot,
  SendHorizontal,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from 'lucide-react'
import clsx from 'clsx'
import type { ExtractionResult } from '@/types/lims'
import { refineJob, type RefineChange } from '@/services/api'

interface Props {
  jobId: string
  onResultChange: (updated: ExtractionResult) => void
}

interface HistoryEntry {
  id: number
  instruction: string
  summary: string
  changes: RefineChange[]
  status: 'ok' | 'error'
  error?: string
}

const PLACEHOLDER_EXAMPLES = [
  'The analysis name in row 2 of ANALYSIS should be ASSAY_HPLC not ASSAY',
  'Change all units from "mg/mL" to "MG_PER_ML" in the UNITS sheet',
  'The product name should be "Paracetamol 500mg Tablets" everywhere',
  'Add confidence 0.95 to all rows in product_specs that have min_value set',
  'The sampling point "Receiving" should be "RECEIVING" (uppercase)',
]

function ChangeList({ changes }: { changes: RefineChange[] }) {
  const [expanded, setExpanded] = useState(false)
  if (changes.length === 0) return null

  const visible = expanded ? changes : changes.slice(0, 3)

  return (
    <div className="mt-2">
      <ul className="space-y-1">
        {visible.map((c, i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
            <span>
              <span className="font-semibold text-indigo-700">{c.sheet}</span>
              {' '}row {c.row_index} · <span className="font-mono">{c.field}</span>
              {' → '}
              <span className="font-semibold">{c.new_value ?? 'null'}</span>
              {' — '}
              <span className="text-gray-500">{c.explanation}</span>
            </span>
          </li>
        ))}
      </ul>
      {changes.length > 3 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-xs text-primary-600 hover:underline flex items-center gap-1"
        >
          {expanded ? (
            <><ChevronUp className="h-3 w-3" /> Show less</>
          ) : (
            <><ChevronDown className="h-3 w-3" /> {changes.length - 3} more change{changes.length - 3 !== 1 ? 's' : ''}</>
          )}
        </button>
      )}
    </div>
  )
}

export const RefinePanel: React.FC<Props> = ({ jobId, onResultChange }) => {
  const [open, setOpen] = useState(false)
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [nextId, setNextId] = useState(1)
  const [placeholder] = useState(
    () => PLACEHOLDER_EXAMPLES[Math.floor(Math.random() * PLACEHOLDER_EXAMPLES.length)],
  )
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const feedEndRef = useRef<HTMLDivElement>(null)

  const handleSubmit = async () => {
    const text = instruction.trim()
    if (!text || loading) return

    setLoading(true)
    setInstruction('')

    try {
      const result = await refineJob(jobId, text)
      const entry: HistoryEntry = {
        id: nextId,
        instruction: text,
        summary: result.summary,
        changes: result.changes,
        status: 'ok',
      }
      setHistory((h) => [...h, entry])
      setNextId((n) => n + 1)
      onResultChange(result.updated_result)
      // Scroll feed to bottom
      setTimeout(() => feedEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      const entry: HistoryEntry = {
        id: nextId,
        instruction: text,
        summary: '',
        changes: [],
        status: 'error',
        error: message,
      }
      setHistory((h) => [...h, entry])
      setNextId((n) => n + 1)
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="mt-2 rounded-xl border border-primary-200 bg-white overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-primary-50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-600" />
          AI Data Refinement
          <span className="text-xs font-normal text-gray-400">
            Describe corrections in plain English
          </span>
          {history.length > 0 && (
            <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs font-semibold text-primary-700">
              {history.length} instruction{history.length !== 1 ? 's' : ''}
            </span>
          )}
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {open && (
        <div className="border-t border-primary-100 flex flex-col" style={{ maxHeight: 520 }}>
          {/* History feed */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 min-h-0">
            {history.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-6 text-center text-gray-400">
                <Bot className="h-8 w-8 text-gray-300" />
                <p className="text-sm">
                  Describe what needs to change and GPT will update the data for you.
                </p>
                <p className="text-xs text-gray-400 italic">e.g. "{placeholder}"</p>
              </div>
            )}

            {history.map((entry) => (
              <div key={entry.id} className="space-y-2">
                {/* User bubble */}
                <div className="flex justify-end">
                  <div className="max-w-[80%] rounded-xl rounded-br-sm bg-primary-600 px-3 py-2 text-sm text-white">
                    {entry.instruction}
                  </div>
                </div>

                {/* AI response bubble */}
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center">
                    <Bot className="h-3.5 w-3.5 text-primary-600" />
                  </div>
                  <div
                    className={clsx(
                      'flex-1 rounded-xl rounded-tl-sm px-3 py-2 text-sm',
                      entry.status === 'ok'
                        ? 'bg-gray-100 text-gray-800'
                        : 'bg-red-50 text-red-700 border border-red-200',
                    )}
                  >
                    {entry.status === 'error' ? (
                      <span className="flex items-center gap-1.5">
                        <AlertCircle className="h-3.5 w-3.5" />
                        {entry.error}
                      </span>
                    ) : (
                      <>
                        <p>{entry.summary}</p>
                        <ChangeList changes={entry.changes} />
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}

            <div ref={feedEndRef} />
          </div>

          {/* Input row */}
          <div className="border-t border-gray-100 px-3 py-3 flex gap-2 items-end bg-gray-50">
            <textarea
              ref={textareaRef}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`e.g. "${placeholder}"`}
              rows={2}
              disabled={loading}
              className="flex-1 resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-50"
            />
            <button
              onClick={handleSubmit}
              disabled={!instruction.trim() || loading}
              className="flex-shrink-0 flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-40 transition-colors"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <SendHorizontal className="h-4 w-4" />
              )}
              {loading ? 'Thinking…' : 'Send'}
            </button>
          </div>

          <p className="px-4 pb-2 text-xs text-gray-400">
            Press <kbd className="rounded bg-gray-200 px-1 py-0.5 font-mono text-xs">Enter</kbd> to send ·{' '}
            <kbd className="rounded bg-gray-200 px-1 py-0.5 font-mono text-xs">Shift+Enter</kbd> for new line
          </p>
        </div>
      )}
    </div>
  )
}
