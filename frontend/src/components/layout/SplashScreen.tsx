export function SplashScreen() {
  return (
    <div className="grid min-h-screen place-items-center">
      <div className="flex flex-col items-center gap-4">
        <span className="grid size-12 animate-pulse place-items-center rounded-2xl bg-flame-400 font-display text-2xl font-bold text-ink-950">
          S
        </span>
        <p className="text-sm text-ink-400">Cargando tu espacio…</p>
      </div>
    </div>
  )
}

export default SplashScreen
