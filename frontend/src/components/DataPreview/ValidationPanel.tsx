import React, { useState } from 'react'
import { AlertTriangle, XCircle, ChevronDown, ChevronRight } from 'lucide-react'
import type { ValidationIssue } from '@/types/lims'

interface Props {
  issues: ValidationIssue[]
}

export const ValidationPanel: React.FC<Props> = ({ issues }) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  // Group by sheet
  const grouped: Record<string, ValidationIssue[]> = {}
  for (const issue of issues) {
    ;(grouped[issue.sheet] ??= []).push(issue)
  }

  const toggle = (sheet: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(sheet)) { next.delete(sheet) } else { next.add(sheet) }
      return next
    })

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-2">
      <p className="text-sm font-semibold text-amber-800 mb-2">Validation Issues</p>
      {Object.entries(grouped).map(([sheet, items]) => (
        <div key={sheet} className="rounded-md border border-amber-100 bg-white overflow-hidden">
          <button
            onClick={() => toggle(sheet)}
            className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <span className="flex items-center gap-2">
              {expanded.has(sheet) ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
              {sheet}
            </span>
            <span className="flex items-center gap-1.5">
              {items.filter((i) => i.severity === 'error').length > 0 && (
                <span className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-600">
                  <XCircle className="h-3 w-3" />
                  {items.filter((i) => i.severity === 'error').length}
                </span>
              )}
              {items.filter((i) => i.severity === 'warning').length > 0 && (
                <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                  <AlertTriangle className="h-3 w-3" />
                  {items.filter((i) => i.severity === 'warning').length}
                </span>
              )}
            </span>
          </button>
          {expanded.has(sheet) && (
            <div className="border-t border-gray-100 divide-y divide-gray-50">
              {items.map((issue, idx) => (
                <div key={idx} className="flex items-start gap-2 px-3 py-2">
                  {issue.severity === 'error' ? (
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                  )}
                  <div className="text-xs">
                    <span className="font-medium text-gray-700">
                      Row {(issue.row_index ?? 0) + 1} · {issue.field}
                    </span>
                    <span className="ml-1 text-gray-500">— {issue.message}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
