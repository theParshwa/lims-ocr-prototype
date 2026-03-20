/**
 * ConfigurePage.tsx - Application configuration panel.
 *
 * Users can:
 * - Change the active LIMS system
 * - Enable / disable LIMS output sheets
 * - Tune AI extraction settings
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  Settings, FlaskConical, Layers, SlidersHorizontal, FileSpreadsheet,
  CheckCircle2, AlertCircle, Loader2, RotateCcw, Info,
} from 'lucide-react'
import clsx from 'clsx'
import { getConfig, updateConfig, resetConfig, type AppConfig } from '@/services/api'

const LIMS_SYSTEMS = ['LabWare', 'LabVantage', 'Veeva'] as const

const ALL_SHEETS = [
  { key: 'analysis_types',      label: 'Analysis Types' },
  { key: 'common_names',        label: 'Common Names' },
  { key: 'analysis',            label: 'Analysis' },
  { key: 'components',          label: 'Components' },
  { key: 'units',               label: 'Units' },
  { key: 'products',            label: 'Products' },
  { key: 'product_specs',       label: 'Product Specs' },
  { key: 'customers',           label: 'Customers' },
  { key: 'instruments',         label: 'Instruments' },
  { key: 'lims_users',          label: 'LIMS Users' },
  { key: 'vendors',             label: 'Vendors' },
  { key: 'suppliers',           label: 'Suppliers' },
  { key: 'process_schedules',   label: 'Process Schedules' },
  { key: 'lists',               label: 'Lists' },
  { key: 'list_entries',        label: 'List Entries' },
  { key: 'sampling_points',     label: 'Sampling Points' },
  { key: 'product_grades',      label: 'Product Grades' },
  { key: 'tph_grades',          label: 'TPH Grades' },
  { key: 'sites',               label: 'Sites' },
  { key: 'plants',              label: 'Plants' },
  { key: 'suites',              label: 'Suites' },
  { key: 'process_units',       label: 'Process Units' },
  { key: 'versions',            label: 'Versions' },
]

type TabId = 'system' | 'sheets' | 'ai' | 'template'

export const ConfigurePage: React.FC = () => {
  const [tab, setTab] = useState<TabId>('system')
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')

  const refresh = useCallback(async () => {
    try {
      const data = await getConfig()
      setConfig(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const save = async (patch: Partial<AppConfig>) => {
    setSaveStatus('saving')
    try {
      const updated = await updateConfig(patch)
      setConfig(updated)
      // Update localStorage if lims_system changed
      if (patch.lims_system) {
        localStorage.setItem('lims_system', patch.lims_system)
      }
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    }
  }

  const handleReset = async () => {
    setSaveStatus('saving')
    try {
      const data = await resetConfig()
      setConfig(data)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    }
  }

  if (loading || !config) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-400 p-8">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading configuration…
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100">
            <Settings className="h-5 w-5 text-slate-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-800">Application Configuration</p>
            <p className="text-xs text-gray-400">Changes take effect on the next document upload.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus === 'saved' && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="h-3.5 w-3.5" /> Saved
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="flex items-center gap-1 text-xs text-red-500">
              <AlertCircle className="h-3.5 w-3.5" /> Error saving
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={saveStatus === 'saving'}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <RotateCcw className={clsx('h-3.5 w-3.5', saveStatus === 'saving' && 'animate-spin')} />
            Reset all
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl border border-gray-200 bg-gray-50 p-1">
        {[
          { id: 'system' as TabId,   label: 'LIMS System',      Icon: FlaskConical },
          { id: 'template' as TabId, label: 'Load Sheet',        Icon: FileSpreadsheet },
          { id: 'sheets' as TabId,   label: 'Output Sheets',     Icon: Layers },
          { id: 'ai' as TabId,       label: 'AI Settings',       Icon: SlidersHorizontal },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-colors',
              tab === id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700',
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'system' && (
        <SystemTab config={config} onSave={save} />
      )}
      {tab === 'template' && (
        <TemplateTab config={config} onSave={save} />
      )}
      {tab === 'sheets' && (
        <SheetsTab config={config} onSave={save} />
      )}
      {tab === 'ai' && (
        <AITab config={config} onSave={save} />
      )}
    </div>
  )
}

// ── SystemTab ──────────────────────────────────────────────────────────────────

const SystemTab: React.FC<{ config: AppConfig; onSave: (patch: Partial<AppConfig>) => void }> = ({
  config, onSave,
}) => (
  <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
    <h2 className="text-sm font-semibold text-gray-700">LIMS Platform</h2>
    <p className="text-sm text-gray-500">
      The selected platform determines field mappings, sheet templates, and export format.
    </p>
    <div className="grid grid-cols-3 gap-3">
      {LIMS_SYSTEMS.map((system) => (
        <button
          key={system}
          onClick={() => onSave({ lims_system: system })}
          className={clsx(
            'rounded-xl border-2 p-4 text-left transition-all',
            config.lims_system === system
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm',
          )}
        >
          <div className="mb-2 text-2xl">
            {system === 'LabWare' ? '🧪' : system === 'LabVantage' ? '⚗️' : '🔬'}
          </div>
          <p className="text-sm font-semibold text-gray-800">{system}</p>
          {config.lims_system === system && (
            <p className="mt-1 flex items-center gap-1 text-xs font-medium text-blue-600">
              <CheckCircle2 className="h-3 w-3" /> Active
            </p>
          )}
        </button>
      ))}
    </div>
  </div>
)

// ── SheetsTab ──────────────────────────────────────────────────────────────────

const SheetsTab: React.FC<{ config: AppConfig; onSave: (patch: Partial<AppConfig>) => void }> = ({
  config, onSave,
}) => {
  const enabled = new Set(config.enabled_sheets ?? [])

  const toggle = (key: string) => {
    const next = new Set(enabled)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    onSave({ enabled_sheets: Array.from(next) })
  }

  const toggleAll = () => {
    if (enabled.size === ALL_SHEETS.length) {
      onSave({ enabled_sheets: [] })
    } else {
      onSave({ enabled_sheets: ALL_SHEETS.map((s) => s.key) })
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Output Sheets</h2>
        <button
          onClick={toggleAll}
          className="text-xs text-blue-600 hover:underline font-medium"
        >
          {enabled.size === ALL_SHEETS.length ? 'Deselect all' : 'Select all'}
        </button>
      </div>
      <p className="text-sm text-gray-500">
        Choose which LIMS sheets will be extracted and included in the exported Load Sheet.
      </p>
      <div className="grid grid-cols-2 gap-2">
        {ALL_SHEETS.map(({ key, label }) => (
          <label
            key={key}
            className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-gray-100 px-3 py-2.5 hover:bg-gray-50 transition-colors"
          >
            <input
              type="checkbox"
              checked={enabled.has(key)}
              onChange={() => toggle(key)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{label}</span>
          </label>
        ))}
      </div>
      <p className="text-xs text-gray-400">{enabled.size} of {ALL_SHEETS.length} sheets enabled</p>
    </div>
  )
}

// ── AITab ──────────────────────────────────────────────────────────────────────

const AITab: React.FC<{ config: AppConfig; onSave: (patch: Partial<AppConfig>) => void }> = ({
  config, onSave,
}) => {
  const ai = config.ai ?? {}
  const [temp, setTemp] = useState(String(ai.temperature ?? 0.1))
  const [maxTokens, setMaxTokens] = useState(String(ai.max_tokens ?? 4096))
  const [chunkSize, setChunkSize] = useState(String(ai.chunk_size ?? 4000))
  const [chunkOverlap, setChunkOverlap] = useState(String(ai.chunk_overlap ?? 400))
  const [threshold, setThreshold] = useState(String(config.confidence_threshold ?? 0.6))

  const handleSave = () => {
    onSave({
      confidence_threshold: parseFloat(threshold),
      ai: {
        temperature: parseFloat(temp),
        max_tokens: parseInt(maxTokens),
        chunk_size: parseInt(chunkSize),
        chunk_overlap: parseInt(chunkOverlap),
      },
    })
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
      <h2 className="text-sm font-semibold text-gray-700">AI Extraction Settings</h2>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Temperature" hint="Lower = more deterministic (0.0–1.0)">
          <input
            type="number" step="0.05" min="0" max="1"
            value={temp}
            onChange={(e) => setTemp(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </Field>

        <Field label="Max Tokens" hint="Maximum LLM response tokens">
          <input
            type="number" step="256" min="512" max="16000"
            value={maxTokens}
            onChange={(e) => setMaxTokens(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </Field>

        <Field label="Chunk Size" hint="Characters per extraction chunk">
          <input
            type="number" step="500" min="1000" max="16000"
            value={chunkSize}
            onChange={(e) => setChunkSize(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </Field>

        <Field label="Chunk Overlap" hint="Overlap characters between chunks">
          <input
            type="number" step="50" min="0" max="2000"
            value={chunkOverlap}
            onChange={(e) => setChunkOverlap(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </Field>

        <Field label="Confidence Threshold" hint="Below this value cells are highlighted yellow">
          <input
            type="number" step="0.05" min="0" max="1"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </Field>
      </div>

      <button
        onClick={handleSave}
        className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
      >
        Save AI Settings
      </button>
    </div>
  )
}

const Field: React.FC<{ label: string; hint: string; children: React.ReactNode }> = ({
  label, hint, children,
}) => (
  <div>
    <label className="mb-1 block text-xs font-medium text-gray-700">{label}</label>
    <p className="mb-1.5 text-xs text-gray-400">{hint}</p>
    {children}
  </div>
)

// ── TemplateTab ────────────────────────────────────────────────────────────────

const LIMS_TEMPLATE_HINTS: Record<string, { example: string; description: string }> = {
  LabWare: {
    description:
      'Paste your LabWare Load Sheet column headers and sheet names. ' +
      'The Extraction Agent uses this to know exactly which fields to look for and how they are named in your organisation.',
    example: `ANALYSIS_TYPES sheet columns: ANALYSIS_TYPE_CODE, DESCRIPTION
ANALYSIS sheet columns: NAME, VERSION, ANALYSIS_TYPE, GROUP, ACTIVE, REPORTED_NAME
COMPONENT sheet columns: ANALYSIS_NAME, COMPONENT_NAME, UNITS, LOWER_SPEC_LIMIT, UPPER_SPEC_LIMIT, NUM_REPLICATES, REPORTED
PRODUCT sheet columns: PRODUCT, GRADE, SAMPLING_POINT, TEST_LIST
PRODUCT_SPEC sheet columns: PRODUCT, GRADE, COMPONENT_NAME, LOWER_SPEC_LIMIT, UPPER_SPEC_LIMIT, SPEC_TYPE
INSTRUMENT sheet columns: INSTRUMENT_NAME, INSTRUMENT_GROUP, VENDOR, SERIAL_NUMBER, NEXT_CALIBRATION_DATE`,
  },
  LabVantage: {
    description:
      'Paste your LabVantage SDM export format — TestDefinition fields, ResultDefinition fields, SampleLoginGroup fields, etc.',
    example: `TestDefinition: test_id, test_name, test_version, method_reference, sample_type, turnaround_time, required_volume
ResultDefinition: result_name, data_type (Numeric/Text/Date), uom, lower_limit, upper_limit, decimal_places, reported
SampleLoginGroup: group_name, sample_type, default_test_list, container_type, storage_condition
InstrumentDefinition: instrument_id, instrument_name, instrument_type, location, calibration_due_date`,
  },
  Veeva: {
    description:
      'Paste your Veeva Vault object field names and document types. ' +
      'Include Document Number formats, lifecycle states, and any custom fields.',
    example: `TestMethod fields: document_number (format: QC-TM-NNN), title, version, lifecycle_state (Draft/Approved/Effective/Retired/Obsolete), effective_date, method_type (Compendial/Validated/In-House)
Specification fields: spec_number (format: QC-SP-NNN), product_name, spec_type (Release/Stability/In-Process), parameters[]
Parameter fields: parameter_name, uom, lower_limit, upper_limit, test_method_reference, compendial_reference (USP/EP/BP)`,
  },
}

const TemplateTab: React.FC<{ config: AppConfig; onSave: (patch: Partial<AppConfig>) => void }> = ({
  config, onSave,
}) => {
  const lims = config.lims_system ?? 'LabWare'
  const [activeSystem, setActiveSystem] = useState<string>(lims)
  const templates = config.load_sheet_templates ?? { LabWare: '', LabVantage: '', Veeva: '' }
  const [values, setValues] = useState<Record<string, string>>({ ...templates })
  const [saved, setSaved] = useState(false)

  const hint = LIMS_TEMPLATE_HINTS[activeSystem]

  const handleSave = () => {
    onSave({ load_sheet_templates: { LabWare: values.LabWare, LabVantage: values.LabVantage, Veeva: values.Veeva } })
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const handleLoadExample = () => {
    setValues((prev) => ({ ...prev, [activeSystem]: hint.example }))
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
      <div>
        <h2 className="text-sm font-semibold text-gray-700">Load Sheet Template</h2>
        <p className="mt-1 text-sm text-gray-500">
          Define the exact column headers and sheet structure for each LIMS system.
          The <strong>Extraction Agent</strong> uses this to target the right fields in your documents.
        </p>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 rounded-lg border border-amber-100 bg-amber-50 p-4">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <p className="text-xs text-amber-800">
          {hint?.description}
          {' '}Changes apply on the next document upload — no restart required.
        </p>
      </div>

      {/* System switcher */}
      <div className="flex gap-2">
        {(['LabWare', 'LabVantage', 'Veeva'] as const).map((sys) => (
          <button
            key={sys}
            onClick={() => setActiveSystem(sys)}
            className={clsx(
              'rounded-lg border px-4 py-1.5 text-xs font-medium transition-colors',
              activeSystem === sys
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-500 hover:bg-gray-50',
            )}
          >
            {sys === 'LabWare' ? '🧪' : sys === 'LabVantage' ? '⚗️' : '🔬'} {sys}
            {values[sys] && (
              <span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-green-500" title="Template defined" />
            )}
          </button>
        ))}
      </div>

      {/* Template editor */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            {activeSystem} Template
          </label>
          <button
            onClick={handleLoadExample}
            className="text-xs text-blue-600 hover:underline font-medium"
          >
            Load example
          </button>
        </div>
        <textarea
          rows={12}
          value={values[activeSystem] ?? ''}
          onChange={(e) => setValues((prev) => ({ ...prev, [activeSystem]: e.target.value }))}
          placeholder={`Paste your ${activeSystem} load sheet column headers and sheet names here…\n\nExample:\n${hint?.example ?? ''}`}
          className="w-full rounded-lg border border-gray-300 px-3 py-2.5 font-mono text-xs leading-relaxed text-gray-700 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
        />
        <p className="mt-1 text-xs text-gray-400">
          {(values[activeSystem] ?? '').length} characters · tip: copy headers directly from your Load Sheet Excel file
        </p>
      </div>

      <button
        onClick={handleSave}
        className={clsx(
          'rounded-lg px-5 py-2 text-sm font-semibold transition-colors',
          saved
            ? 'bg-green-500 text-white'
            : 'bg-blue-600 text-white hover:bg-blue-700',
        )}
      >
        {saved ? '✓ Saved' : 'Save Templates'}
      </button>
    </div>
  )
}
