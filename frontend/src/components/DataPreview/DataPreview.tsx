/**
 * DataPreview.tsx - Tabbed data grid for reviewing and editing extracted LIMS data.
 *
 * Each tab corresponds to one Excel sheet.
 * Low-confidence cells are highlighted in amber.
 * Validation error cells are highlighted in red.
 * Inline editing is supported via AG Grid.
 */

import React, { useCallback, useMemo, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { CellValueChangedEvent, ColDef } from 'ag-grid-community'
import { themeQuartz } from 'ag-grid-community'
import clsx from 'clsx'
import {
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  Save, RotateCcw,
} from 'lucide-react'
import type { ExtractionResult } from '@/types/lims'
import { SHEET_DEFS } from './sheetDefs'
import { updateJobData } from '@/services/api'
import { ConfidenceBar } from './ConfidenceBar'
import { ValidationPanel } from './ValidationPanel'
import { DocumentViewer } from './DocumentViewer'
import { RefinePanel } from './RefinePanel'
import { AuditPanel } from './AuditPanel'

const themeParams: any = {
  fontFamily: "'Inter', system-ui, sans-serif",
  fontSize: 12.5,
  accentColor: '#3B82F6',
  backgroundColor: '#FFFFFF',
  headerBackgroundColor: '#F8FAFC',
  headerTextColor: '#475569',
  oddRowBackgroundColor: '#FFFFFF',
  rowHoverColor: '#F8FAFC',
  selectedRowBackgroundColor: '#EFF6FF',
  borderColor: '#E2E8F0',
  rowBorder: { style: 'solid', color: '#F1F5F9' },
  columnBorder: { style: 'solid', color: '#F1F5F9' },
  headerColumnBorderColor: '#E2E8F0',
  cellTextColor: '#334155',
  inputFocusBorderColor: '#3B82F6',
  rangeSelectionBorderColor: '#3B82F6',
}

const gridTheme = themeQuartz.withParams(themeParams)

interface Props {
  jobId: string
  result: ExtractionResult
  onResultChange: (updated: ExtractionResult) => void
}

export const DataPreview: React.FC<Props> = ({ jobId, result, onResultChange }) => {
  const [activeSheet, setActiveSheet] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  const [showValidation, setShowValidation] = useState(false)

  const availableSheets = SHEET_DEFS.filter(
    (def) => (result[def.dataKey] as unknown[])?.length > 0,
  )

  const currentSheet = availableSheets[activeSheet] ?? availableSheets[0]

  const rowData = useMemo(() => {
    if (!currentSheet) return []
    return (result[currentSheet.dataKey] as Record<string, unknown>[]) ?? []
  }, [result, currentSheet])

  const columnDefs: ColDef[] = useMemo(() => {
    if (!currentSheet) return []
    const issueSet = new Set(
      result.validation_errors
        .filter((e) => e.sheet === currentSheet.name)
        .map((e) => `${e.row_index}:${e.field}`),
    )

    return currentSheet.columns.map((col) => ({
      field: col.field,
      headerName: col.headerName,
      width: col.width ?? 150,
      editable: true,
      resizable: true,
      sortable: true,
      filter: true,
      cellStyle: (params: { rowIndex: number; value: unknown; data: Record<string, unknown> }) => {
        const key = `${params.rowIndex}:${col.field}`
        if (issueSet.has(key)) return { backgroundColor: '#FEE2E2' }
        const conf = params.data?.confidence as number
        if (conf !== undefined && conf < 0.6) return { backgroundColor: '#FEF9C3' }
        return null
      },
      valueFormatter:
        col.type === 'number'
          ? (p: { value: unknown }) => (p.value != null ? String(p.value) : '')
          : undefined,
    }))
  }, [currentSheet, result.validation_errors])

  const handleCellChange = useCallback(
    (event: CellValueChangedEvent) => {
      if (!currentSheet) return
      const key = currentSheet.dataKey
      const rows = result[key] as Record<string, unknown>[]
      const rowIdx = rows.indexOf(event.data)
      if (rowIdx === -1) return
      const newRows = [...rows]
      newRows[rowIdx] = { ...rows[rowIdx], [event.colDef.field!]: event.newValue }
      onResultChange({ ...result, [key]: newRows })
      setSaveStatus('idle')
    },
    [currentSheet, result, onResultChange],
  )

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      await updateJobData(jobId, result)
      setSaveStatus('saved')
      onResultChange({
        ...result,
        // Backend re-validates; if it returned updated errors, use them
      })
    } catch {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }, [jobId, result, onResultChange])

  const errorCount = result.validation_errors.filter((e) => e.severity === 'error').length
  const warnCount = result.validation_errors.filter((e) => e.severity === 'warning').length

  if (availableSheets.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 py-16 text-center">
        <p className="text-sm text-gray-500">No data extracted from this document.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-bold text-gray-800">{result.document_name}</h2>
          <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
            <span className="font-medium">Type: {result.document_type}</span>
            <ConfidenceBar value={result.overall_confidence} />
          </div>
        </div>

        {/* Validation summary + Save */}
        <div className="flex items-center gap-2">
          {(errorCount > 0 || warnCount > 0) && (
            <button
              onClick={() => setShowValidation((v) => !v)}
              className="flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              {errorCount} error{errorCount !== 1 ? 's' : ''}, {warnCount} warning{warnCount !== 1 ? 's' : ''}
              {showValidation ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
          {errorCount === 0 && warnCount === 0 && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="h-4 w-4" /> No issues
            </span>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className={clsx(
              'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors',
              saveStatus === 'saved'
                ? 'bg-green-100 text-green-700'
                : saveStatus === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-primary-600 text-white hover:bg-primary-700',
            )}
          >
            {saving ? (
              <RotateCcw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {saving ? 'Saving…' : saveStatus === 'saved' ? 'Saved' : 'Save edits'}
          </button>
        </div>
      </div>

      {/* Validation panel */}
      {showValidation && (
        <ValidationPanel issues={result.validation_errors} />
      )}

      {/* Sheet tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-gray-200 pb-0">
        {availableSheets.map((sheet, idx) => {
          const rowCount = (result[sheet.dataKey] as unknown[])?.length ?? 0
          const hasErrors = result.validation_errors.some((e) => e.sheet === sheet.name)
          return (
            <button
              key={sheet.name}
              onClick={() => setActiveSheet(idx)}
              className={clsx(
                'relative flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px',
                idx === activeSheet
                  ? 'border-primary-600 text-primary-700 bg-white'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50',
              )}
            >
              {sheet.name}
              <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                {rowCount}
              </span>
              {hasErrors && (
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              )}
            </button>
          )
        })}
      </div>

      {/* AG Grid */}
      {currentSheet && (
        <div className="rounded-lg overflow-hidden border border-gray-200" style={{ height: 500 }}>
          <AgGridReact
            theme={gridTheme}
            rowData={rowData}
            columnDefs={columnDefs}
            onCellValueChanged={handleCellChange}
            defaultColDef={{
              editable: true,
              resizable: true,
              sortable: true,
              filter: true,
            }}
            headerHeight={36}
            rowHeight={34}
            animateRows
            rowSelection="multiple"
            suppressRowClickSelection
            pagination
            paginationPageSize={50}
          />
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-6 rounded bg-yellow-100 border border-yellow-200" />
          Low confidence (&lt;60%)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-6 rounded bg-red-100 border border-red-200" />
          Validation error
        </span>
        <span className="text-gray-400">Click any cell to edit · Changes saved manually</span>
      </div>

      {/* AI natural-language refinement */}
      <RefinePanel jobId={jobId} onResultChange={onResultChange} />

      {/* Field-level edit history / audit trail */}
      <AuditPanel jobId={jobId} />

      {/* Document viewer + AI annotation comments */}
      <DocumentViewer
        jobId={jobId}
        result={result}
        activeSheetName={currentSheet?.name}
      />
    </div>
  )
}
