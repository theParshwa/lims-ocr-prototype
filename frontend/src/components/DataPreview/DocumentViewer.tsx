/**
 * DocumentViewer.tsx - Inline document viewer with AI mapping annotations.
 *
 * Shown below the data grid after extraction is complete.
 * Left panel: original document rendered inline (PDF via blob object URL) or
 *   a download fallback for DOCX/other formats.
 * Right panel: scrollable AI annotation comments – where each value was found
 *   in the document, what it mapped to, and the extraction confidence.
 *
 * NOTE: The document is fetched via the CORS-aware axios client and turned into
 * a local blob URL so the browser never makes a raw cross-origin embed request.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { renderAsync } from 'docx-preview'
import {
  ChevronDown,
  ChevronUp,
  FileText,
  MessageSquare,
  Filter,
  ExternalLink,
  Loader2,
  AlertCircle,
} from 'lucide-react'
import clsx from 'clsx'
import type { ExtractionResult } from '@/types/lims'
import { SHEET_DEFS } from './sheetDefs'
import { fetchDocumentBlob, getDocumentUrl } from '@/services/api'

interface Props {
  jobId: string
  result: ExtractionResult
  activeSheetName?: string
}

interface Annotation {
  sheet: string
  field: string
  value: string
  sourceText: string
  reviewNotes?: string
  confidence: number
}

function collectAnnotations(result: ExtractionResult, filterSheet?: string): Annotation[] {
  const annotations: Annotation[] = []
  const metaFields = new Set(['confidence', 'confidence_level', 'source_text', 'review_notes'])

  for (const def of SHEET_DEFS) {
    if (filterSheet && def.name !== filterSheet) continue
    const rows = result[def.dataKey] as Record<string, unknown>[] | undefined
    if (!rows?.length) continue

    for (const row of rows) {
      const sourceText = row.source_text as string | undefined
      if (!sourceText) continue

      const confidence = (row.confidence as number) ?? 1
      const reviewNotes = row.review_notes as string | undefined
      const valueField = def.columns.find((c) => !metaFields.has(c.field) && row[c.field])
      const value = valueField ? String(row[valueField.field] ?? '') : ''
      const field = valueField?.headerName ?? valueField?.field ?? def.name

      annotations.push({ sheet: def.name, field, value, sourceText, reviewNotes, confidence })
    }
  }

  return annotations.sort((a, b) => a.confidence - b.confidence)
}

function confidenceColor(c: number) {
  if (c < 0.6) return 'text-red-600 bg-red-50 border-red-200'
  if (c < 0.85) return 'text-amber-600 bg-amber-50 border-amber-200'
  return 'text-green-700 bg-green-50 border-green-200'
}

function confidenceLabel(c: number) {
  if (c < 0.6) return 'Low'
  if (c < 0.85) return 'Medium'
  return 'High'
}

export const DocumentViewer: React.FC<Props> = ({ jobId, result, activeSheetName }) => {
  const [open, setOpen] = useState(false)
  const [filterToSheet, setFilterToSheet] = useState(false)

  // Blob URL state
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [docBlob, setDocBlob] = useState<Blob | null>(null)
  const [isPdf, setIsPdf] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const blobUrlRef = useRef<string | null>(null)
  const [docxContainer, setDocxContainer] = useState<HTMLDivElement | null>(null)

  // Fetch the document blob once when the panel is first opened
  useEffect(() => {
    if (!open || blobUrl || docBlob || loading) return

    setLoading(true)
    setFetchError(null)

    fetchDocumentBlob(jobId)
      .then(({ blob, mimeType }) => {
        const pdf = mimeType === 'application/pdf' || mimeType.includes('pdf')
        setIsPdf(pdf)
        if (pdf) {
          const url = URL.createObjectURL(blob)
          blobUrlRef.current = url
          setBlobUrl(url)
        } else {
          setDocBlob(blob)
        }
      })
      .catch((err) => {
        setFetchError(err?.message ?? 'Failed to load document')
      })
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, jobId])

  // Render DOCX into the container div once we have both the blob and the element
  useEffect(() => {
    if (!docBlob || !docxContainer) return
    renderAsync(docBlob, docxContainer, undefined, {
      className: 'docx-preview',
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      ignoreFonts: false,
      breakPages: true,
      useBase64URL: true,
    }).catch(console.error)
  }, [docBlob, docxContainer])

  // Revoke blob URL on unmount to free memory
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
    }
  }, [])

  const sheetFilter = filterToSheet ? activeSheetName : undefined
  const annotations = useMemo(
    () => collectAnnotations(result, sheetFilter),
    [result, sheetFilter],
  )

  const rawDocUrl = getDocumentUrl(jobId)

  return (
    <div className="mt-2 rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary-600" />
          Source Document &amp; AI Annotations
          {annotations.length > 0 && (
            <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs font-semibold text-primary-700">
              {annotations.length} mapping{annotations.length !== 1 ? 's' : ''}
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
        <div className="border-t border-gray-200">
          <div className="flex h-[680px]">
            {/* ── Left: document viewer ─────────────────────────────────── */}
            <div className="flex-1 min-w-0 border-r border-gray-200 flex flex-col">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-50 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
                <span>Document</span>
                <a
                  href={rawDocUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-primary-600 hover:underline normal-case font-medium"
                >
                  Open <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div className="flex-1 min-h-0 relative">
                {loading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                    <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
                    <span className="ml-2 text-sm text-gray-500">Loading document…</span>
                  </div>
                )}

                {fetchError && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
                    <AlertCircle className="h-10 w-10 text-red-400" />
                    <p className="text-sm text-gray-600">{fetchError}</p>
                    <a
                      href={rawDocUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 transition-colors"
                    >
                      Open in new tab
                    </a>
                  </div>
                )}

                {blobUrl && isPdf && (
                  <iframe
                    src={blobUrl}
                    title="Source document"
                    className="w-full h-full border-0"
                  />
                )}

                {/* DOCX rendered via docx-preview */}
                {docBlob && !isPdf && (
                  <div
                    ref={setDocxContainer}
                    className="w-full h-full overflow-auto bg-gray-100 p-4"
                  />
                )}
              </div>
            </div>

            {/* ── Right: annotations panel ──────────────────────────────── */}
            <div className="w-80 flex-shrink-0 flex flex-col">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-50 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
                <span className="flex items-center gap-1.5">
                  <MessageSquare className="h-3.5 w-3.5" />
                  AI Mapping Comments
                </span>
                {activeSheetName && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setFilterToSheet((v) => !v) }}
                    className={clsx(
                      'flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium transition-colors',
                      filterToSheet
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-500 hover:bg-gray-100',
                    )}
                  >
                    <Filter className="h-3 w-3" />
                    {filterToSheet ? activeSheetName : 'All sheets'}
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
                {annotations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 p-6 text-center text-sm">
                    <MessageSquare className="h-8 w-8 mb-2 text-gray-300" />
                    No source text recorded for this{' '}
                    {filterToSheet ? 'sheet' : 'document'}.
                  </div>
                ) : (
                  annotations.map((ann, i) => (
                    <div key={i} className="px-3 py-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                        <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-xs font-semibold text-indigo-700">
                          {ann.sheet}
                        </span>
                        <span className="text-xs text-gray-500">{ann.field}</span>
                        <span
                          className={clsx(
                            'ml-auto rounded border px-1.5 py-0.5 text-xs font-medium',
                            confidenceColor(ann.confidence),
                          )}
                        >
                          {confidenceLabel(ann.confidence)}{' '}
                          {Math.round(ann.confidence * 100)}%
                        </span>
                      </div>

                      {ann.value && (
                        <p className="text-xs font-semibold text-gray-800 mb-1 truncate" title={ann.value}>
                          → {ann.value}
                        </p>
                      )}

                      <blockquote className="border-l-2 border-gray-300 pl-2 text-xs text-gray-500 italic leading-relaxed line-clamp-3">
                        "{ann.sourceText}"
                      </blockquote>

                      {ann.reviewNotes && (
                        <p className="mt-1.5 text-xs text-amber-700 bg-amber-50 rounded px-2 py-1">
                          {ann.reviewNotes}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
