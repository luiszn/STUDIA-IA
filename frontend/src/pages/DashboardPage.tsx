import {
  ArrowUpRight,
  BrainCircuit,
  CalendarClock,
  FileText,
  Flame,
  GraduationCap,
  Layers,
  ListChecks,
  Sparkles,
  Timer,
  TrendingUp,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { PageHeader, StatTile } from '@/components/layout/PageHeader'
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, ProgressBar, Skeleton } from '@/components/ui/Card'
import { LinkButton } from '@/components/ui/Button'
import { useAuth } from '@/auth/AuthProvider'
import {
  formatDueLabel,
  formatMinutes,
  formatTime,
  percentage,
} from '@/lib/format'
import { useDashboard, useUpdateRecommendation } from '@/lib/queries'

const KIND_TONE = {
  task: 'info',
  exam: 'danger',
  session: 'success',
} as const

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-9 w-64" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-24" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-80 lg:col-span-2" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { data, isPending, error, refetch } = useDashboard()
  const markRead = useUpdateRecommendation()

  if (isPending) return <DashboardSkeleton />

  if (error || !data) {
    return <ErrorState message={error?.message} onRetry={() => void refetch()} />
  }

  const { stats, upcoming, recommendation, performance, quick_actions: quickActions } = data
  const weeklyGoal = percentage(stats.study_minutes_week, stats.daily_goal_minutes * 7)
  const studySeries = performance.study_minutes
  const courseSeries = performance.by_course.map((course) => ({
    name: course.code,
    average: course.average,
  }))
  const firstName = user?.full_name.split(' ')[0] ?? ''

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${data.greeting}, ${firstName}`}
        description={<>Tu semana en un vistazo · objetivo diario {stats.daily_goal_minutes} min</>}
        actions={
          <>
            <LinkButton to="/app/ai" variant="secondary" leftIcon={<Sparkles className="size-4" />}>
              Ask AI
            </LinkButton>
            <LinkButton to="/app/planner" leftIcon={<BrainCircuit className="size-4" />}>
              Crear plan
            </LinkButton>
          </>
        }
      />

      {/* stats */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Cursos activos"
          value={stats.active_courses}
          hint={`${stats.total_courses} en total`}
          icon={<GraduationCap className="size-5" />}
        />
        <StatTile
          label="Tareas pendientes"
          value={stats.pending_tasks}
          hint={
            stats.overdue_tasks > 0 ? (
              <span className="text-danger">{stats.overdue_tasks} vencidas</span>
            ) : (
              `${stats.completed_tasks} completadas`
            )
          }
          icon={<ListChecks className="size-5" />}
          tone={stats.overdue_tasks > 0 ? 'danger' : 'info'}
        />
        <StatTile
          label="Próximo examen"
          value={
            stats.next_exam_in_days === null
              ? '—'
              : stats.next_exam_in_days === 0
                ? 'hoy'
                : `${stats.next_exam_in_days} d`
          }
          hint={`${stats.upcoming_exams} próximas`}
          icon={<CalendarClock className="size-5" />}
          tone="warning"
        />
        <StatTile
          label="Racha de estudio"
          value={`${stats.study_streak_days} d`}
          hint={`${formatMinutes(stats.study_minutes_week)} esta semana`}
          icon={<Flame className="size-5" />}
          tone="flame"
        />
      </div>

      {/* recommendation */}
      {recommendation ? (
        <Card className="border-flame-400/25 bg-gradient-to-br from-flame-400/8 to-transparent">
          <CardBody className="flex flex-wrap items-start gap-4 p-5">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-flame-400/15 text-flame-300">
              <Sparkles className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold text-ink-100">{recommendation.title}</h3>
                <Badge tone="flame">Prioridad {recommendation.priority}</Badge>
              </div>
              <p className="mt-1 text-sm text-ink-300">{recommendation.message}</p>
            </div>
            <div className="flex items-center gap-2">
              {recommendation.cta_path ? (
                <LinkButton to={recommendation.cta_path} size="sm">
                  {recommendation.cta_label ?? 'Ir'}
                  <ArrowUpRight className="size-3.5" />
                </LinkButton>
              ) : null}
              {!recommendation.is_read ? (
                <button
                  onClick={() =>
                    markRead.mutate({ id: recommendation.id, is_read: true })
                  }
                  className="text-xs text-ink-400 hover:text-ink-200"
                >
                  Marcar leída
                </button>
              ) : null}
            </div>
          </CardBody>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* chart */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Minutos de estudio"
            description="Últimos 7 días"
            icon={<Timer className="size-4" />}
            action={
              <div className="text-right">
                <p className="font-display text-lg font-semibold text-ink-100">
                  {formatMinutes(stats.study_minutes_week)}
                </p>
                <p className="text-xs text-ink-400">{weeklyGoal}% del objetivo semanal</p>
              </div>
            }
          />
          <CardBody>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={studySeries} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
                  <defs>
                    <linearGradient id="minutesFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ff7a1a" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#ff7a1a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1e1e27" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#6f6f7d', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                    <YAxis
                      tick={{ fill: '#6f6f7d', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#121218',
                        border: '1px solid #262631',
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: '#9a9aa8' }}
                      formatter={(value) => [`${value ?? 0} min`, 'Estudio']}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#ff7a1a"
                      strokeWidth={2}
                      fill="url(#minutesFill)"
                    />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-ink-800 bg-ink-950/50 p-3">
                <p className="text-xs text-ink-400">Promedio general</p>
                <p className="font-display text-xl font-semibold text-ink-100">
                  {stats.average_grade !== null ? `${stats.average_grade.toFixed(1)}%` : '—'}
                </p>
              </div>
              <div className="rounded-xl border border-ink-800 bg-ink-950/50 p-3">
                <p className="text-xs text-ink-400">Flashcards</p>
                <p className="font-display text-xl font-semibold text-ink-100">
                  {stats.flashcards}
                  <span className="ml-1 text-xs font-normal text-ink-400">
                    ({stats.flashcards_due} por repasar)
                  </span>
                </p>
              </div>
              <div className="rounded-xl border border-ink-800 bg-ink-950/50 p-3">
                <p className="text-xs text-ink-400">Documentos</p>
                <p className="font-display text-xl font-semibold text-ink-100">{stats.documents}</p>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* upcoming */}
        <Card>
          <CardHeader
            title="Próximos"
            icon={<CalendarClock className="size-4" />}
            action={
              <Link to="/app/calendar" className="text-xs text-flame-300 hover:text-flame-200">
                Ver calendario
              </Link>
            }
          />
          <CardBody className="pt-0">
            {upcoming.length === 0 ? (
              <EmptyState
                title="Nada programado"
                description="Cuando agregues exámenes o tareas aparecerán aquí ordenados por fecha."
                action={
                  <LinkButton to="/app/exams" size="sm" variant="secondary">
                    Agregar examen
                  </LinkButton>
                }
                className="py-8"
              />
            ) : (
              <ul className="space-y-1.5">
                {upcoming.slice(0, 6).map((item) => {
                  const due = formatDueLabel(item.date)
                  return (
                    <li key={`${item.kind}-${item.id}`}>
                      <Link
                        to={item.path}
                        className="flex items-center gap-3 rounded-xl px-2.5 py-2 transition hover:bg-ink-800/70"
                      >
                        <span
                          className="size-2 shrink-0 rounded-full"
                          style={{ backgroundColor: item.color ?? '#ff7a1a' }}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-ink-100">{item.title}</p>
                          <p className="truncate text-xs text-ink-400">
                            {item.course_name ?? 'Sin curso'}
                            {item.time_label ? ` · ${item.time_label}` : ''}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <Badge tone={KIND_TONE[item.kind] ?? 'neutral'}>
                            {item.kind === 'task' ? 'tarea' : item.kind === 'exam' ? 'examen' : 'sesión'}
                          </Badge>
                          {item.is_overdue ? (
                            <span className="text-[0.65rem] text-danger">vencida</span>
                          ) : due ? (
                            <span className="text-[0.65rem] text-ink-500">{due}</span>
                          ) : null}
                        </div>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* course performance */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Rendimiento por curso"
            description="Promedio ponderado de tus notas"
            icon={<TrendingUp className="size-4" />}
            action={
              <Link to="/app/grades" className="text-xs text-flame-300 hover:text-flame-200">
                Ver notas
              </Link>
            }
          />
          <CardBody>
            {courseSeries.length === 0 ? (
              <EmptyState
                title="Sin notas todavía"
                description="Registra tus notas para ver el rendimiento por materia."
                className="py-8"
              />
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={courseSeries} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
                    <CartesianGrid stroke="#1e1e27" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: '#6f6f7d', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#6f6f7d', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                    />
                    <Tooltip
                      cursor={{ fill: '#1e1e2720' }}
                      contentStyle={{
                        background: '#121218',
                        border: '1px solid #262631',
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                      formatter={(value) => [`${Number(value ?? 0).toFixed(1)}%`, 'Promedio']}
                    />
                    <Bar dataKey="average" fill="#ff7a1a" radius={[6, 6, 0, 0]} maxBarSize={54} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardBody>
        </Card>

        {/* quick actions */}
        <Card>
          <CardHeader title="Acciones rápidas" icon={<Sparkles className="size-4" />} />
          <CardBody className="space-y-2 pt-0">
            {quickActions.map((action) => (
              <Link
                key={action.path + action.label}
                to={action.path}
                className="panel-hover flex items-center justify-between gap-3 rounded-xl border border-ink-800 px-3.5 py-3"
              >
                <span className="text-sm text-ink-200">{action.label}</span>
                <ArrowUpRight className="size-4 shrink-0 text-ink-500" />
              </Link>
            ))}
            <div className="space-y-3 pt-2">
              <div>
                <div className="mb-1.5 flex items-center justify-between text-xs text-ink-400">
                  <span className="flex items-center gap-1.5">
                    <Layers className="size-3.5" /> Repaso de hoy
                  </span>
                  <span>
                    {stats.flashcards_due} de {stats.flashcards}
                  </span>
                </div>
                <ProgressBar
                  value={percentage(
                    stats.flashcards - stats.flashcards_due,
                    stats.flashcards || 1,
                  )}
                  tone="success"
                />
              </div>
              <div>
                <div className="mb-1.5 flex items-center justify-between text-xs text-ink-400">
                  <span className="flex items-center gap-1.5">
                    <FileText className="size-3.5" /> Material indexado
                  </span>
                  <span>{stats.documents} documentos</span>
                </div>
                <ProgressBar
                  value={percentage(stats.documents, Math.max(stats.documents, 1))}
                  tone="info"
                />
              </div>
            </div>
            <p className="pt-1 text-xs text-ink-500">
              Última actualización {formatTime(data.generated_at)}
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
