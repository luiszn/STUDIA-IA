import { Loader2 } from 'lucide-react'
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { cn } from '@/lib/format'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'sm' | 'md' | 'lg' | 'icon'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-flame-400 text-ink-950 font-semibold hover:bg-flame-300 active:bg-flame-500 shadow-[0_8px_24px_-10px_rgb(255_122_26/0.7)]',
  secondary: 'bg-ink-800 text-ink-100 hover:bg-ink-750 border border-ink-700',
  ghost: 'text-ink-300 hover:bg-ink-800 hover:text-ink-100',
  danger: 'bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25',
  outline: 'border border-ink-600 text-ink-200 hover:border-flame-400 hover:text-flame-200',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-12 px-6 text-sm gap-2.5 rounded-xl',
  icon: 'h-9 w-9 rounded-lg',
}

const BASE =
  'inline-flex items-center justify-center whitespace-nowrap font-medium transition duration-150 ' +
  'disabled:pointer-events-none disabled:opacity-50 select-none'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  isLoading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    isLoading = false,
    leftIcon,
    rightIcon,
    className,
    children,
    disabled,
    ...props
  },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(BASE, VARIANTS[variant], SIZES[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : leftIcon}
      {children}
      {rightIcon}
    </button>
  )
})

export interface LinkButtonProps {
  to: string
  variant?: Variant
  size?: Size
  className?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  children?: ReactNode
}

export function LinkButton({
  to,
  variant = 'primary',
  size = 'md',
  className,
  leftIcon,
  rightIcon,
  children,
}: LinkButtonProps) {
  return (
    <Link to={to} className={cn(BASE, VARIANTS[variant], SIZES[size], className)}>
      {leftIcon}
      {children}
      {rightIcon}
    </Link>
  )
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  variant?: Variant
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, variant = 'ghost', className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      aria-label={label}
      title={label}
      className={cn(BASE, VARIANTS[variant], SIZES.icon, className)}
      {...props}
    >
      {children}
    </button>
  )
})
