import React from 'react'
import clsx from 'clsx'

interface Props {
  value: number  // 0.0 – 1.0
  showLabel?: boolean
}

export const ConfidenceBar: React.FC<Props> = ({ value, showLabel = true }) => {
  const pct = Math.round(value * 100)
  const colour =
    pct >= 85 ? 'bg-green-500'
    : pct >= 60 ? 'bg-amber-400'
    : 'bg-red-400'

  const label =
    pct >= 85 ? 'High'
    : pct >= 60 ? 'Medium'
    : 'Low'

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative h-2 w-20 overflow-hidden rounded-full bg-gray-200">
        <span
          className={clsx('absolute left-0 top-0 h-full rounded-full transition-all', colour)}
          style={{ width: `${pct}%` }}
        />
      </span>
      {showLabel && (
        <span className={clsx(
          'text-xs font-medium',
          pct >= 85 ? 'text-green-600' : pct >= 60 ? 'text-amber-600' : 'text-red-500',
        )}>
          {label} ({pct}%)
        </span>
      )}
    </span>
  )
}
