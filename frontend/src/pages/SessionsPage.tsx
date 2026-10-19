import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { BookOpen, Pause, Play, RotateCcw, Timer, Trash2 } from 'lucide-react'

import { PageHeader, StatTile } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
} from '@/components/ui/Card'
import { Field, Input, Select } from '@/components/ui/Input'
import { cn, formatDateTime, formatMinutes } from '@/lib/format'
import {
  useCourses,
  useCreateSession,
  useDeleteSession,
  useSessions,
} from '@/lib/queries'

const MODES = {
  pomodoro: { label: 'Pomodoro', seconds: 25 * 60 },
  short: { label: 'Descanso corto', seconds: 5 * 60 },
  long: { label: 'Descanso largo', seconds: 15 * 60 },
} as const

type Mode = keyof typeof MODES

function formatClock(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${`${minutes}`.padStart(2, '0')}:${`${seconds}`.padStart(2, '0')}`
}

function describeError(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return error instanceof Error ? error.message : 'No se pudo completar la operación'
}

export default function SessionsPage() {
  const sessions = useSessions({ limit: 50 })
  const courses = useCourses()
  const createSession = useCreateSession()
  const deleteSession = useDeleteSession()

  const [mode, setMode] = useState<Mode>('pomodoro')
  const [remaining, setRemaining] = useState(MODES.pomodoro.seconds)
  const [running, setRunning] = useState(false)
  const [focus, setFocus] = useState('')
  const [courseId, setCourseId] = useState('')
  const startedAtRef = useRef<Date | null>(null)
  const sessionRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const items = sessions.data?.items ?? []
  const total = items.reduce((sum, item) => sum + item.duration_minutes, 0)
  const totalSeconds = MODES[mode].seconds
  const progress = 1 - remaining / totalSeconds

  const saveSession = async (durationSeconds: number) => {
    const minutes = Math.max(1, Math.round(durationSeconds / 60))
    if (minutes < 1) return
    try {
      await createSession.mutateAsync({
        focus: focus.trim() || MODES[mode].label,
        course_id: courseId || undefined,
        started_at: (startedAtRef.current ?? new Date(Date.now() - durationSeconds * 1000)).toISOString(),
        duration_minutes: minutes,
      })
      toast.success(`Sesión guardada · ${formatMinutes(minutes)}`)
    } catch (error) {
      toast.error(describeError(error))
    }
  }

  const stop = () => {
    setRunning(false)
    if (sessionRef.current) {
      clearTimeout(sessionRef.current)
      sessionRef.current = null
    }
  }

  const reset = (nextMode: Mode = mode) => {
    stop()
    setMode(nextMode)
    setRemaining(MODES[nextMode].seconds)
    startedAtRef.current = null
  }

  const toggle = () => {
    if (running) {
      stop()
      return
    }
    if (!startedAtRef.current) startedAtRef.current = new Date()
    setRunning(true)
  }

  useEffect(() => {
    if (!running) return
    sessionRef.current = setTimeout(() => {
      setRemaining((value) => {
        if (value <= 1) {
          stop()
          const duration = MODES[mode].seconds
          void saveSession(duration).then(() => {
            const next: Mode = mode === 'pomodoro' ? 'short' : 'pomodoro'
            setMode(next)
            setRemaining(MODES[next].seconds)
            startedAtRef.current = null
          })
          return 0
        }
        return value - 1
      })
    }, 1000)
    return () => {
      if (sessionRef.current) clearTimeout(sessionRef.current)
    }
  }, [running, mode])

  const saveEarly = () => {
    const elapsed = totalSeconds - remaining
    if (elapsed < 60) {
      toast.error('Mínimo 1 minuto para guardar una sesión')
      return
    }
    stop()
    void saveSession(elapsed).then(() => reset())
  }

  const radius = 96
  const circumference = 2 * Math.PI * radius

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sesiones de estudio"
        description="Temporizador Pomodoro y historial de tiempo enfocado."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile label="Sesiones" value={items.length} icon={<BookOpen className="size-5" />} />
        <StatTile
          label="Tiempo total"
          value={formatMinutes(total)}
          icon={<Timer className="size-5" />}
          tone="success"
        />
        <StatTile
          label="Promedio"
          value={items.length > 0 ? formatMinutes(Math.round(total / items.length)) : '—'}
          icon={<Play className="size-5" />}
          tone="info"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card>
          <CardHeader title="Temporizador" description="Estudia en bloques y registra tu tiempo." />
          <CardBody className="space-y-5">
            <div className="flex justify-center gap-1.5">
              {(Object.keys(MODES) as Mode[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => !running && reset(key)}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-medium transition',
                    mode === key
                      ? 'bg-flame-400 text-ink-950'
                      : 'bg-ink-850 text-ink-300 hover:bg-ink-800',
                    running && 'cursor-not-allowed opacity-50',
                  )}
                >
                  {MODES[key].label} · {MODES[key].seconds / 60}′
                </button>
              ))}
            </div>

            <div className="relative mx-auto size-56">
              <svg viewBox="0 0 220 220" className="size-full -rotate-90">
                <circle
                  cx="110"
                  cy="110"
                  r={radius}
                  fill="none"
                  stroke="#262631"
                  strokeWidth="10"
                />
                <circle
                  cx="110"
                  cy="110"
                  r={radius}
                  fill="none"
                  stroke={mode === 'pomodoro' ? '#ff7a1a' : '#43c59e'}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference * (1 - progress)}
                  className="transition-[stroke-dashoffset] duration-1000 ease-linear"
                />
              </svg>
              <div className="absolute inset-0 grid place-items-center">
                <div className="text-center">
                  <p className="font-display text-5xl font-semibold tabular-nums text-ink-50">
                    {formatClock(remaining)}
                  </p>
                  <p className="mt-1 text-xs tracking-widest text-ink-500 uppercase">
                    {running ? 'En curso' : 'En pausa'}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-2">
              <IconButton label={running ? 'Pausar' : 'Empezar'} onClick={toggle}>
                {running ? <Pause className="size-5" /> : <Play className="size-5" />}
              </IconButton>
              <IconButton label="Reiniciar" onClick={() => reset()}>
                <RotateCcw className="size-4" />
              </IconButton>
              <Button variant="outline" size="sm" onClick={saveEarly} disabled={remaining === totalSeconds}>
                Guardar ahora
              </Button>
            </div>

            <div className="space-y-3">
              <Field label="¿En qué trabajas?">
                <Input
                  value={focus}
                  onChange={(event) => setFocus(event.target.value)}
                  placeholder="Repasar derivadas"
                />
              </Field>
              <Field label="Curso (opcional)">
                <Select value={courseId} onChange={(event) => setCourseId(event.target.value)}>
                  <option value="">Sin curso</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.code} — {course.name}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Historial" description="Tus últimas sesiones registradas." />
          <CardBody className="pt-0">
            {sessions.isLoading ? (
              <div className="space-y-3 py-4">
                {Array.from({ length: 5 }, (_, index) => (
                  <Skeleton key={index} className="h-14" />
                ))}
              </div>
            ) : sessions.isError ? (
              <ErrorState onRetry={() => void sessions.refetch()} />
            ) : items.length === 0 ? (
              <EmptyState
                icon={<Timer className="size-5" />}
                title="Sin sesiones"
                description="Pulsa Empezar en el temporizador para registrar tu primera sesión."
              />
            ) : (
              <ul className="divide-y divide-ink-850">
                {items.map((session) => (
                  <li key={session.id} className="group flex items-center gap-3 py-3">
                    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-success/12 text-success">
                      <Timer className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-ink-100">{session.focus}</p>
                      <p className="text-xs text-ink-400">
                        {formatDateTime(session.started_at)}
                        {session.course ? ` · ${session.course.code}` : ''}
                      </p>
                    </div>
                    <span className="text-sm text-ink-300">
                      {formatMinutes(session.duration_minutes)}
                    </span>
                    <IconButton
                      label="Eliminar sesión"
                      className="opacity-0 transition group-hover:opacity-100"
                      onClick={() => {
                        void deleteSession.mutateAsync(session.id).then(
                          () => toast.success('Sesión eliminada'),
                          (error) => toast.error(describeError(error)),
                        )
                      }}
                    >
                      <Trash2 className="size-4" />
                    </IconButton>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
