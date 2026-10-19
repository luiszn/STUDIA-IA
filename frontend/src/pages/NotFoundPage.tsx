import { AlertTriangle, Home, Search } from 'lucide-react'

import { LinkButton } from '@/components/ui/Button'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink-950 px-6 text-center">
      <div className="panel max-w-md space-y-6 p-8">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-danger/12 text-danger">
          <AlertTriangle className="size-6" />
        </span>
        <div className="space-y-2">
          <h1 className="font-display text-3xl font-semibold text-ink-100">404 — Página no encontrada</h1>
          <p className="text-sm text-ink-400">
            La ruta a la que intentaste acceder no existe. Puede que hayas escrito mal la dirección o que el recurso haya
            sido eliminado.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <LinkButton to="/app" leftIcon={<Home className="size-4" />}>
            Ir al Dashboard
          </LinkButton>
          <LinkButton to="/" variant="outline" leftIcon={<Search className="size-4" />}>
            Volver al inicio
          </LinkButton>
        </div>
      </div>
    </div>
  )
}
