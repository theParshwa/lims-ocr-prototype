/**
 * AuditPanel.tsx - Field-level edit history for a job.
 *
 * Shows every manual or AI-driven cell change made after extraction,
 * newest first. Useful for compliance / change-control documentation.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { ClipboardList, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { format, parseISO } from 'date-fns'
import type { AuditLogEntry } from '@/types/lims'
import { getAuditLog } from '@/services/api'

interface Props {
  jobId: string
}

export const AuditPanel: React.FC<Props> = ({ jobId }) => {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAuditLog(jobId)
      setEntries(data.entries)
      setTotal(data.total)
    } catch {
      setError('Failed to load audit log.')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  // Load when panel is first opened
  useEffect(() => {
    if (open && entries.length === 0 && !loading) {
      load()
    }
  }, [open, entries.length, loading, load])

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Header toggle */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-gray-400" />
          Edit History &amp; Audit Trail
          {total > 0 && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
              {total}
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
        <div className="border-t border-gray-100">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-100">
            <p className="text-xs text-gray-500">
              {total === 0
                ? 'No edits recorded yet. Save changes to begin tracking.'
                : `${total} field edit${total !== 1 ? 's' : ''} recorded`}
            </p>
            <button
              onClick={load}
              disabled={loading}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              <RefreshCw className={clsx('h-3 w-3', loading && 'animate-spin')} />
              Refresh
            </button>
          </div>

          {error && (
            <p className="px-4 py-3 text-xs text-red-600">{error}</p>
          )}

          {!error && entries.length === 0 && !loading && (
            <p className="px-4 py-8 text-center text-xs text-gray-400">
              No edits recorded yet.
            </p>
          )}

          {entries.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-gray-500">
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Time</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Sheet</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Field</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Row</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Before</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">After</th>
                    <th className="px-4 py-2 font-medium whitespace-nowrap">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {entries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2 text-gray-400 whitespace-nowrap">
                        {format(parseISO(entry.changed_at), 'dd MMM yyyy HH:mm:ss')}
                      </td>
                      <td className="px-4 py-2 font-medium text-gray-700 whitespace-nowrap">
                        {entry.sheet_name}
                      </td>
                      <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                        {entry.field_name}
                      </td>
                      <td className="px-4 py-2 text-gray-400 max-w-[160px] truncate" title={entry.context_text ?? ''}>
                        {entry.context_text ?? '—'}
                      </td>
                      <td className="px-4 py-2 max-w-[160px] truncate text-red-600" title={entry.old_value ?? ''}>
                        {entry.old_value || <span className="text-gray-300 italic">empty</span>}
                      </td>
                      <td className="px-4 py-2 max-w-[160px] truncate text-green-700 font-medium" title={entry.new_value ?? ''}>
                        {entry.new_value || <span className="text-gray-300 italic">empty</span>}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        <span
                          className={clsx(
                            'rounded-full px-2 py-0.5 text-xs font-medium',
                            entry.change_source === 'ai_refine'
                              ? 'bg-purple-100 text-purple-700'
                              : 'bg-blue-100 text-blue-700',
                          )}
                        >
                          {entry.change_source === 'ai_refine' ? 'AI' : 'Manual'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
