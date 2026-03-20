/**
 * LimsSelector.tsx — Enterprise onboarding screen for LIMS system selection.
 */

import React, { useState } from 'react'
import { Database, ArrowRight, Check } from 'lucide-react'
import clsx from 'clsx'
import { updateConfig } from '@/services/api'

const SYSTEMS = [
  {
    id: 'LabWare',
    name: 'LabWare LIMS',
    version: 'v8 / LIMS Basic',
    description: 'Highly configurable, widely adopted in pharmaceutical QC labs.',
    features: ['Analysis Types & Components', 'Product / Grade specifications', 'Process Schedules'],
    accent: 'border-blue-600',
    iconBg: 'bg-blue-600',
  },
  {
    id: 'LabVantage',
    name: 'LabVantage LIMS',
    version: 'LIMS 8.x / SDM',
    description: 'Cloud-native enterprise platform with real-time analytics.',
    features: ['Test & Result Definitions', 'Sample Login Groups', 'Workflow Definitions'],
    accent: 'border-violet-600',
    iconBg: 'bg-violet-600',
  },
  {
    id: 'Veeva',
    name: 'Veeva Vault LIMS',
    version: 'Vault QMS',
    description: 'GxP-validated quality management with lifecycle control.',
    features: ['Document Number tracking', 'Lifecycle state management', 'Change Control links'],
    accent: 'border-emerald-600',
    iconBg: 'bg-emerald-600',
  },
] as const

type LimsId = 'LabWare' | 'LabVantage' | 'Veeva'

export const LimsSelector: React.FC<{ onSelect: (s: LimsId) => void }> = ({ onSelect }) => {
  const [selected, setSelected] = useState<LimsId | null>(null)
  const [loading,  setLoading]  = useState(false)

  const confirm = async () => {
    if (!selected) return
    setLoading(true)
    try {
      await updateConfig({ lims_system: selected })
      localStorage.setItem('lims_system', selected)
      onSelect(selected)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-6 py-12">
      <div className="w-full max-w-3xl">

        {/* Header */}
        <div className="mb-10 text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-primary-600 shadow-lg">
            <Database className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            LIMS OCR Document Processor
          </h1>
          <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto">
            Select your Laboratory Information Management System. This configures field
            mappings, extraction agents, and export templates.
          </p>
        </div>

        {/* System cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {SYSTEMS.map((sys) => {
            const active = selected === sys.id
            return (
              <button
                key={sys.id}
                onClick={() => setSelected(sys.id as LimsId)}
                className={clsx(
                  'relative rounded-lg border-2 bg-white p-5 text-left transition-all duration-150 shadow-card hover:shadow-panel',
                  active ? clsx(sys.accent, 'ring-1 ring-inset', sys.accent.replace('border-', 'ring-')) : 'border-slate-200',
                )}
              >
                {/* Selected mark */}
                {active && (
                  <span className={clsx(
                    'absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full',
                    sys.iconBg,
                  )}>
                    <Check className="h-3 w-3 text-white" strokeWidth={3} />
                  </span>
                )}

                {/* Icon */}
                <div className={clsx(
                  'mb-4 flex h-9 w-9 items-center justify-center rounded-lg',
                  active ? sys.iconBg : 'bg-slate-100',
                )}>
                  <Database className={clsx('h-4.5 w-4.5', active ? 'text-white' : 'text-slate-500')} style={{ width: 18, height: 18 }} />
                </div>

                <p className="text-sm font-bold text-slate-900">{sys.name}</p>
                <p className="mt-0.5 text-2xs font-medium text-slate-400 uppercase tracking-wide">{sys.version}</p>
                <p className="mt-2 text-xs text-slate-500 leading-relaxed">{sys.description}</p>

                <ul className="mt-3 space-y-1">
                  {sys.features.map(f => (
                    <li key={f} className="flex items-start gap-1.5 text-xs text-slate-600">
                      <span className={clsx('mt-1.5 h-1 w-1 shrink-0 rounded-full', active ? sys.iconBg : 'bg-slate-300')} />
                      {f}
                    </li>
                  ))}
                </ul>
              </button>
            )
          })}
        </div>

        {/* CTA */}
        <div className="text-center">
          <button
            onClick={confirm}
            disabled={!selected || loading}
            className={clsx(
              'inline-flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold shadow-sm transition-all',
              selected && !loading
                ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-md hover:shadow-lg'
                : 'cursor-not-allowed bg-slate-200 text-slate-400',
            )}
          >
            {loading ? 'Configuring…' : 'Continue'}
            {!loading && <ArrowRight className="h-4 w-4" />}
          </button>
          <p className="mt-3 text-xs text-slate-400">You can change this later in Configure.</p>
        </div>
      </div>
    </div>
  )
}
