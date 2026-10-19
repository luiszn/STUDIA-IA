import { Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function AuthLayout({
  title,
  subtitle,
  footer,
  children,
}: {
  title: string
  subtitle: string
  footer?: ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center bg-radial px-6">
      <div className="absolute inset-0 -z-10 bg-grid" />
      <div className="w-full max-w-md space-y-8">
        <Link to="/" className="mx-auto flex w-fit items-center gap-2.5 rounded-2xl border border-ink-700 bg-ink-900/70 px-3.5 py-1.5 text-sm text-ink-300 backdrop-blur-lg transition hover:text-ink-100">
          <Sparkles className="size-4 text-flame-400" />
          Volver a STUDIA
        </Link>
        <div className="panel px-6 py-8 sm:px-8">
          <div className="mb-6 space-y-2">
            <h1 className="font-display text-2xl font-semibold text-ink-100 sm:text-3xl">{title}</h1>
            <p className="text-sm text-ink-400">{subtitle}</p>
          </div>
          {children}
          {footer ? (
            <p className="mt-6 border-t border-ink-800 pt-5 text-center text-sm text-ink-400">
              {footer}
            </p>
          ) : null}
        </div>
        <p className="text-center text-xs text-ink-500">Construido con IA local para estudiar sin distracciones.</p>
      </div>
    </div>
  )
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return <p className="rounded-xl border border-danger/30 bg-danger/12 px-3 py-2 text-sm text-danger">{message}</p>
}
