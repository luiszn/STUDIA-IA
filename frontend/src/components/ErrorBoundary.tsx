import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('ErrorBoundary capturó un error:', error, info)
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="grid min-h-screen place-items-center bg-ink-950 p-6 text-ink-100">
          <div className="w-full max-w-md rounded-2xl border border-ink-700 bg-ink-900 p-8 text-center">
            <p className="font-display text-2xl font-semibold">Algo salió mal</p>
            <p className="mt-2 text-sm text-ink-400">
              Ocurrió un error inesperado al mostrar esta pantalla.
            </p>
            <p className="mt-4 rounded-xl bg-ink-850 px-3 py-2 text-left text-xs text-danger">
              {this.state.error.message}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 rounded-xl bg-flame-400 px-4 py-2 text-sm font-medium text-ink-950 transition hover:bg-flame-300"
            >
              Recargar página
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}