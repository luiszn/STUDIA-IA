import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'

import { cn } from '@/lib/format'

const FIELD_BASE =
  'w-full rounded-xl border border-ink-700 bg-ink-900/80 px-3.5 text-sm text-ink-100 ' +
  'placeholder:text-ink-500 transition focus:border-flame-400/70 focus:bg-ink-900 ' +
  'focus:outline-none focus:ring-2 focus:ring-flame-400/20 disabled:opacity-60'

export interface FieldProps {
  label?: string
  hint?: ReactNode
  error?: string | null
  required?: boolean
  className?: string
  children: ReactNode
}

export function Field({ label, hint, error, required, className, children }: FieldProps) {
  return (
    <label className={cn('block space-y-1.5', className)}>
      {label ? (
        <span className="flex items-center gap-1 text-xs font-medium tracking-wide text-ink-300 uppercase">
          {label}
          {required ? <span className="text-flame-400">*</span> : null}
        </span>
      ) : null}
      {children}
      {error ? (
        <span className="block text-xs text-danger">{error}</span>
      ) : hint ? (
        <span className="block text-xs text-ink-400">{hint}</span>
      ) : null}
    </label>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(FIELD_BASE, 'h-10', className)} {...props} />
  },
)

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, rows = 4, ...props }, ref) {
    return <textarea ref={ref} rows={rows} className={cn(FIELD_BASE, 'resize-y py-2.5', className)} {...props} />
  },
)

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select
        ref={ref}
        className={cn(FIELD_BASE, 'h-10 cursor-pointer appearance-none pr-9', className)}
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236f6f7d' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 0.75rem center',
        }}
        {...props}
      >
        {children}
      </select>
    )
  },
)

export function Checkbox({
  label,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }) {
  return (
    <label className={cn('flex cursor-pointer items-center gap-2.5 text-sm text-ink-200', className)}>
      <input
        type="checkbox"
        className="size-4 shrink-0 cursor-pointer rounded border-ink-600 bg-ink-900 accent-flame-400 focus:ring-2 focus:ring-flame-400/30"
        {...props}
      />
      {label}
    </label>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2.5 text-sm text-ink-200"
    >
      <span
        className={cn(
          'relative h-5 w-9 rounded-full transition',
          checked ? 'bg-flame-400' : 'bg-ink-700',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 size-4 rounded-full bg-white transition-all',
            checked ? 'left-4.5' : 'left-0.5',
          )}
        />
      </span>
      {label}
    </button>
  )
}
