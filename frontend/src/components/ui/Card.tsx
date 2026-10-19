import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { cn } from '@/lib/format'
import { IconButton } from './Button'

/* ------------------------------------------------------------------- card */
export function Card({
  className,
  children,
  as: Tag = 'section',
}: {
  className?: string
  children: ReactNode
  as?: 'section' | 'div' | 'article' | 'aside'
}) {
  return <Tag className={cn('panel', className)}>{children}</Tag>
}

export function CardHeader({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex items-start justify-between gap-4 px-5 pt-5 pb-4', className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-flame-400/12 text-flame-300">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-ink-100">{title}</h2>
          {description ? <p className="mt-0.5 text-sm text-ink-400">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  )
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('px-5 pb-5', className)}>{children}</div>
}

export function CardFooter({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <footer className={cn('flex items-center justify-end gap-2 border-t border-ink-800 px-5 py-3.5', className)}>
      {children}
    </footer>
  )
}

/* ------------------------------------------------------------------ badge */
type Tone = 'neutral' | 'flame' | 'success' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-ink-800 text-ink-300 border-ink-700',
  flame: 'bg-flame-400/12 text-flame-300 border-flame-400/25',
  success: 'bg-success/12 text-success border-success/25',
  warning: 'bg-warning/12 text-warning border-warning/25',
  danger: 'bg-danger/12 text-danger border-danger/25',
  info: 'bg-info/12 text-info border-info/25',
}

export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: Tone
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.7rem] font-medium whitespace-nowrap',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ misc */
export function ProgressBar({
  value,
  className,
  tone = 'flame',
}: {
  value: number
  className?: string
  tone?: Tone
}) {
  const fills: Record<Tone, string> = {
    neutral: 'bg-ink-500',
    flame: 'bg-flame-400',
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger',
    info: 'bg-info',
  }
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-ink-800', className)}>
      <div
        className={cn('h-full rounded-full transition-[width] duration-500', fills[tone])}
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="panel space-y-3 p-5">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-3 w-full" />
      ))}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 px-6 py-14 text-center', className)}>
      {icon ? (
        <span className="grid size-12 place-items-center rounded-2xl bg-ink-800 text-ink-400">{icon}</span>
      ) : null}
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-ink-100">{title}</h3>
        {description ? <p className="mx-auto max-w-sm text-sm text-ink-400">{description}</p> : null}
      </div>
      {action}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
  className,
}: {
  message?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center gap-3 px-6 py-12 text-center', className)}>
      <span className="grid size-12 place-items-center rounded-2xl bg-danger/12 text-danger">
        <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
        </svg>
      </span>
      <div>
        <h3 className="text-base font-semibold text-ink-100">No pudimos cargar los datos</h3>
        <p className="mt-1 text-sm text-ink-400">{message ?? 'Revisa tu conexión e inténtalo de nuevo.'}</p>
      </div>
      {onRetry ? (
        <button
          onClick={onRetry}
          className="rounded-lg border border-ink-600 px-3 py-1.5 text-xs text-ink-200 hover:border-flame-400 hover:text-flame-200"
        >
          Reintentar
        </button>
      ) : null}
    </div>
  )
}

/* ------------------------------------------------------------------ modal */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-3xl' } as const

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      <div
        className="absolute inset-0 bg-ink-950/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          'panel relative z-10 max-h-[92vh] w-full overflow-y-auto rounded-b-none sm:rounded-2xl',
          widths[size],
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-ink-800 px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-ink-100">{title}</h2>
            {description ? <p className="mt-0.5 text-sm text-ink-400">{description}</p> : null}
          </div>
          <IconButton label="Cerrar" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer ? (
          <div className="flex justify-end gap-2 border-t border-ink-800 px-5 py-3.5">{footer}</div>
        ) : null}
      </div>
    </div>,
    document.body,
  )
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: { value: T; label: string; count?: number }[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div className={cn('flex gap-1 overflow-x-auto border-b border-ink-800', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={cn(
            '-mb-px flex items-center gap-2 border-b-2 px-3.5 py-2.5 text-sm transition',
            value === tab.value
              ? 'border-flame-400 text-ink-100'
              : 'border-transparent text-ink-400 hover:text-ink-200',
          )}
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className="rounded-full bg-ink-800 px-1.5 py-0.5 text-[0.65rem] text-ink-300">
              {tab.count}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  )
}
