import React from 'react'
import clsx from 'clsx'

interface Props {
  value: number   // 0.0 – 1.0
  showLabel?: boolean
}

export const ConfidenceBar: React.FC<Props> = ({ value, showLabel = true }) => {
  const pct = Math.round(value * 100)
  const colour = pct >= 85 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-400' : 'bg-red-400'
  const textCls = pct >= 85 ? 'text-emerald-600' : pct >= 60 ? 'text-amber-600' : 'text-red-500'
  const label = pct >= 85 ? 'High' : pct >= 60 ? 'Medium' : 'Low'

  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative h-1.5 w-24 overflow-hidden rounded-full bg-slate-200">
        <span
          className={clsx('absolute left-0 top-0 h-full rounded-full transition-all duration-500', colour)}
          style={{ width: `${pct}%` }}
        />
      </span>
      {showLabel && (
        <span className={clsx('text-xs font-medium tabular-nums', textCls)}>
          {label} · {pct}%
        </span>
      )}
    </span>
  )
}
