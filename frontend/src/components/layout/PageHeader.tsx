import type { ReactNode } from 'react'

import { cn } from '@/lib/format'

export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('mb-6 flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-semibold tracking-tight sm:text-[1.75rem]">{title}</h1>
        {description ? <p className="mt-1 text-sm text-ink-400">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function SectionTitle({
  children,
  action,
  className,
}: {
  children: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('mb-3 flex items-center justify-between gap-3', className)}>
      <h2 className="font-display text-sm font-semibold tracking-wide text-ink-300 uppercase">
        {children}
      </h2>
      {action}
    </div>
  )
}

export function StatTile({
  label,
  value,
  hint,
  icon,
  tone = 'flame',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
  tone?: 'flame' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
}) {
  const tones = {
    flame: 'text-flame-300 bg-flame-400/12',
    success: 'text-success bg-success/12',
    warning: 'text-warning bg-warning/12',
    danger: 'text-danger bg-danger/12',
    info: 'text-info bg-info/12',
    neutral: 'text-ink-300 bg-ink-800',
  }
  return (
    <div className="panel panel-hover flex items-start gap-3.5 p-4">
      {icon ? (
        <span className={cn('grid size-10 shrink-0 place-items-center rounded-xl', tones[tone])}>
          {icon}
        </span>
      ) : null}
      <div className="min-w-0">
        <p className="text-xs tracking-wide text-ink-400 uppercase">{label}</p>
        <p className="mt-1 font-display text-2xl leading-none font-semibold text-ink-100">{value}</p>
        {hint ? <p className="mt-1.5 text-xs text-ink-400">{hint}</p> : null}
      </div>
    </div>
  )
}
