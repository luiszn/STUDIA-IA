import { CalendarDays, ChevronLeft, ChevronRight, ClipboardList, NotebookPen, Timer } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Badge, Card, EmptyState, ErrorState, Skeleton } from '@/components/ui/Card'
import { cn, formatDate } from '@/lib/format'
import { useCalendar } from '@/lib/queries'
import type { CalendarEvent } from '@/lib/types'

const KIND_META: Record<CalendarEvent['kind'], { label: string; className: string; dot: string; icon: typeof Timer }> = {
  task: { label: 'Tarea', className: 'border-info/40 text-info', dot: 'bg-info', icon: ClipboardList },
  exam: { label: 'Examen', className: 'border-warning/40 text-warning', dot: 'bg-warning', icon: NotebookPen },
  session: { label: 'Sesión', className: 'border-success/40 text-success', dot: 'bg-success', icon: Timer },
}

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function toISO(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function addMonths(date: Date, delta: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + delta, 1)
}

export default function CalendarPage() {
  const navigate = useNavigate()
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()))
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const start = toISO(cursor)
  const end = toISO(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0))

  const calendar = useCalendar(start, end)
  const events = calendar.data?.events ?? []

  const weeks = useMemo(() => {
    const first = startOfMonth(cursor)
    const weekdayIndex = (first.getDay() + 6) % 7 // lunes = 0
    const gridStart = new Date(first)
    gridStart.setDate(first.getDate() - weekdayIndex)

    const days: Date[] = []
    for (let index = 0; index < 42; index += 1) {
      const day = new Date(gridStart)
      day.setDate(gridStart.getDate() + index)
      days.push(day)
    }

    const result: Date[][] = []
    for (let index = 0; index < 6; index += 1) {
      result.push(days.slice(index * 7, index * 7 + 7))
    }
    return result
  }, [cursor])

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>()
    for (const event of events) {
      const list = map.get(event.date) ?? []
      list.push(event)
      map.set(event.date, list)
    }
    for (const list of map.values()) {
      list.sort((a, b) => (a.time ?? '99:99').localeCompare(b.time ?? '99:99'))
    }
    return map
  }, [events])

  const dayEvents = selectedDay ? (eventsByDay.get(selectedDay) ?? []) : []
  const monthLabel = cursor.toLocaleDateString('es', { month: 'long', year: 'numeric' })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Calendario"
        description="Tareas, exámenes y sesiones en una sola vista."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setSelectedDay(toISO(new Date()))}>
              Hoy
            </Button>
            <div className="flex items-center gap-1">
              <Button
                variant="secondary"
                size="icon"
                aria-label="Mes anterior"
                onClick={() => setCursor(addMonths(cursor, -1))}
              >
                <ChevronLeft className="size-4" />
              </Button>
              <Button
                variant="secondary"
                size="icon"
                aria-label="Mes siguiente"
                onClick={() => setCursor(addMonths(cursor, 1))}
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3 text-xs text-ink-400">
        {(Object.keys(KIND_META) as CalendarEvent['kind'][]).map((kind) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className={cn('size-2 rounded-full', KIND_META[kind].dot)} />
            {KIND_META[kind].label}
          </span>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-ink-800 px-4 py-3">
            <h2 className="font-display text-lg font-semibold capitalize text-ink-100">{monthLabel}</h2>
            <span className="text-xs text-ink-400">
              {events.length} {events.length === 1 ? 'evento' : 'eventos'}
            </span>
          </div>

          {calendar.isLoading ? (
            <div className="grid grid-cols-7 gap-px bg-ink-800">
              {Array.from({ length: 35 }, (_, index) => (
                <Skeleton key={index} className="h-24 rounded-none" />
              ))}
            </div>
          ) : calendar.isError ? (
            <ErrorState onRetry={() => void calendar.refetch()} />
          ) : (
            <div className="grid grid-cols-7">
              {WEEKDAYS.map((weekday) => (
                <div
                  key={weekday}
                  className="border-b border-ink-800 px-2 py-2 text-center text-[0.7rem] font-semibold tracking-wider text-ink-500 uppercase"
                >
                  {weekday}
                </div>
              ))}
              {weeks.flat().map((day) => {
                const iso = toISO(day)
                const inMonth = day.getMonth() === cursor.getMonth()
                const isToday = iso === toISO(new Date())
                const dayEventsList = eventsByDay.get(iso) ?? []
                const isSelected = selectedDay === iso
                return (
                  <button
                    key={iso}
                    type="button"
                    onClick={() => setSelectedDay(iso)}
                    className={cn(
                      'min-h-24 border-r border-b border-ink-800 p-1.5 text-left align-top transition',
                      inMonth ? 'bg-ink-900/40' : 'bg-ink-950/60',
                      isSelected ? 'ring-1 ring-flame-400/60 ring-inset' : 'hover:bg-ink-850',
                    )}
                  >
                    <span
                      className={cn(
                        'inline-grid size-6 place-items-center rounded-full text-xs',
                        isToday
                          ? 'bg-flame-400 font-semibold text-ink-950'
                          : inMonth
                            ? 'text-ink-200'
                            : 'text-ink-600',
                      )}
                    >
                      {day.getDate()}
                    </span>
                    <span className="mt-1 block space-y-1">
                      {dayEventsList.slice(0, 3).map((event) => {
                        const meta = KIND_META[event.kind] ?? KIND_META.task
                        return (
                          <span
                            key={event.id}
                            className="flex items-center gap-1 truncate rounded-md px-1 py-0.5 text-[0.65rem] text-ink-200"
                            style={{
                              backgroundColor: event.color ? `${event.color}26` : undefined,
                            }}
                          >
                            <span
                              className={cn(
                                'size-1.5 shrink-0 rounded-full',
                                event.color ? '' : meta.dot,
                              )}
                              style={event.color ? { backgroundColor: event.color } : undefined}
                            />
                            <span className="truncate">
                              {event.time ? `${event.time} ` : ''}
                              {event.title}
                            </span>
                          </span>
                        )
                      })}
                      {dayEventsList.length > 3 ? (
                        <span className="block px-1 text-[0.65rem] text-ink-500">
                          +{dayEventsList.length - 3} más
                        </span>
                      ) : null}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
        </Card>

        <Card className="h-fit">
          <div className="border-b border-ink-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-ink-100">
              {selectedDay ? formatDate(`${selectedDay}T12:00:00`) : 'Selecciona un día'}
            </h2>
          </div>
          {!selectedDay ? (
            <EmptyState
              icon={<CalendarDays className="size-5" />}
              title="Elige un día"
              description="Verás aquí las tareas, exámenes y sesiones programadas."
            />
          ) : dayEvents.length === 0 ? (
            <EmptyState
              icon={<CalendarDays className="size-5" />}
              title="Día libre"
              description="No hay nada programado para esta fecha."
            />
          ) : (
            <ul className="divide-y divide-ink-850">
              {dayEvents.map((event) => {
                const meta = KIND_META[event.kind] ?? KIND_META.task
                const Icon = meta.icon
                return (
                  <li key={event.id}>
                    <button
                      type="button"
                      onClick={() => navigate(event.path)}
                      className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-ink-850"
                    >
                      <span
                        className={cn('mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border', meta.className)}
                      >
                        <Icon className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-ink-100">{event.title}</span>
                        <span className="mt-0.5 block text-xs text-ink-400">
                          {event.time ?? 'Todo el día'}
                          {event.course_name ? ` · ${event.course_name}` : ''}
                        </span>
                      </span>
                      <Badge className={meta.className}>{meta.label}</Badge>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
