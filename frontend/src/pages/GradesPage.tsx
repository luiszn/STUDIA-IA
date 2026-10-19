import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useState } from 'react'
import { toast } from 'sonner'
import { LineChart as LineChartIcon, Plus, Trash2 } from 'lucide-react'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorState,
  Modal,
  Skeleton,
} from '@/components/ui/Card'
import { Field, Input, Select } from '@/components/ui/Input'
import { CATEGORY_LABELS, formatDate } from '@/lib/format'
import {
  useCourses,
  useCreateGrade,
  useDeleteGrade,
  useGradeOverview,
  useGrades,
} from '@/lib/queries'

const TOOLTIP_STYLE = {
  background: '#121218',
  border: '1px solid #262631',
  borderRadius: 12,
  fontSize: 12,
} as const

interface DistributionBucket {
  range: string
  count: number
}

interface CategoryRow {
  category: string
  average: number
  count: number
}

export default function GradesPage() {
  const overview = useGradeOverview()
  const grades = useGrades({ limit: 30 })
  const courses = useCourses()
  const createGrade = useCreateGrade()
  const deleteGrade = useDeleteGrade()

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    course_id: '',
    title: '',
    category: 'exam',
    score: '',
    max_score: '100',
    weight: '',
    graded_on_date: '',
  })

  const data = overview.data
  const items = grades.data?.items ?? []

  const distribution = (data?.distribution ?? []) as unknown as DistributionBucket[]
  const categories = (data?.category_breakdown ?? []) as unknown as CategoryRow[]

  const courseChartData = (data?.courses ?? []).map((course) => ({
    name: course.course_code,
    average: course.average,
    color: course.color,
  }))

  const handleSubmit = async () => {
    if (!form.course_id) return toast.error('Selecciona un curso')
    if (!form.title.trim()) return toast.error('Escribe un título para la nota')
    const score = Number(form.score)
    const maxScore = Number(form.max_score) || 100
    if (!Number.isFinite(score) || score < 0) return toast.error('Puntuación no válida')
    if (maxScore <= 0) return toast.error('La puntuación máxima debe ser mayor que 0')

    try {
      await createGrade.mutateAsync({
        course_id: form.course_id,
        title: form.title.trim(),
        category: form.category,
        score,
        max_score: maxScore,
        weight: form.weight ? Number(form.weight) : undefined,
        graded_on_date: form.graded_on_date || undefined,
      })
      toast.success('Nota registrada')
      setOpen(false)
      setForm({ course_id: '', title: '', category: 'exam', score: '', max_score: '100', weight: '', graded_on_date: '' })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo guardar la nota')
    }
  }

  if (overview.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Notas" description="Promedios, distribución y registros recientes." />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-72" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (overview.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title="Notas" description="Promedios, distribución y registros recientes." />
        <ErrorState onRetry={() => void overview.refetch()} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notas"
        description="Promedios, distribución y registros recientes."
        actions={
          <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
            Añadir nota
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs tracking-widest text-ink-500 uppercase">Promedio general</p>
          <p className="mt-1 font-display text-3xl font-semibold text-flame-300">
            {data?.overall_average != null ? `${data.overall_average.toFixed(1)}%` : '—'}
          </p>
          <p className="mt-1 text-xs text-ink-400">
            {(data?.courses ?? []).length} cursos con notas
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-xs tracking-widest text-ink-500 uppercase">Notas registradas</p>
          <p className="mt-1 font-display text-3xl font-semibold text-ink-100">
            {grades.data?.meta.total ?? items.length}
          </p>
          <p className="mt-1 text-xs text-ink-400">en tus cursos</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs tracking-widest text-ink-500 uppercase">Mejor curso</p>
          <p className="mt-1 font-display text-3xl font-semibold text-success">
            {data && data.courses.length > 0
              ? `${Math.max(...data.courses.map((course) => course.average)).toFixed(1)}%`
              : '—'}
          </p>
          <p className="mt-1 text-xs text-ink-400">promedio más alto</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Promedio por curso" description="Comparativa entre cursos del semestre." />
          <CardBody>
            {courseChartData.length === 0 ? (
              <EmptyState
                icon={<LineChartIcon className="size-5" />}
                title="Sin datos todavía"
                description="Registra notas para ver tu promedio por curso."
              />
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={courseChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262631" vertical={false} />
                    <XAxis dataKey="name" tick={{ fill: '#9a9aa8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#9a9aa8', fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#9a9aa8' }} formatter={(value) => [`${Number(value ?? 0).toFixed(1)}%`, 'Promedio']} cursor={{ fill: '#17171f66' }} />
                    <Bar dataKey="average" radius={[6, 6, 0, 0]} maxBarSize={48}>
                      {courseChartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color || '#ff7a1a'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Distribución" description="Cuántas notas caen en cada rango." />
          <CardBody>
            {distribution.length === 0 ? (
              <EmptyState icon={<LineChartIcon className="size-5" />} title="Sin distribución" />
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={distribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262631" vertical={false} />
                    <XAxis dataKey="range" tick={{ fill: '#9a9aa8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: '#9a9aa8', fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#9a9aa8' }} formatter={(value) => [String(value ?? 0), 'Notas']} cursor={{ fill: '#17171f66' }} />
                    <Bar dataKey="count" fill="#ff7a1a" radius={[6, 6, 0, 0]} maxBarSize={48} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {(data?.courses ?? []).length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data?.courses.map((course) => (
            <Card key={course.course_id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-display text-sm font-semibold text-ink-100">
                    {course.course_code} — {course.course_name}
                  </p>
                  <p className="mt-0.5 text-xs text-ink-400">{course.count} notas</p>
                </div>
                <span className="font-display text-2xl font-semibold" style={{ color: course.color }}>
                  {course.average.toFixed(1)}
                </span>
              </div>

              {course.trend.length > 1 ? (
                <div className="mt-3 h-16">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={course.trend.map((value, index) => ({ index, value }))}>
                      <Line type="monotone" dataKey="value" stroke={course.color || '#ff7a1a'} strokeWidth={2} dot={false} />
                      <Tooltip
                        contentStyle={TOOLTIP_STYLE}
                        labelStyle={{ color: '#9a9aa8' }}
                        labelFormatter={() => 'Nota'}
                        formatter={(value) => [`${Number(value ?? 0).toFixed(1)}%`, 'Nota']}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : null}

              <div className="mt-3 flex flex-wrap gap-1.5">
                <Badge tone="success">Máx {course.highest.toFixed(0)}%</Badge>
                <Badge tone="danger">Mín {course.lowest.toFixed(0)}%</Badge>
                {course.projected != null ? <Badge tone="info">Proyectado {course.projected.toFixed(1)}%</Badge> : null}
                {course.required_to_pass != null ? (
                  <Badge tone="warning">Necesitas {course.required_to_pass.toFixed(1)}%</Badge>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader title="Notas recientes" description="Tus últimas calificaciones registradas." />
          <CardBody className="pt-0">
            {grades.isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }, (_, index) => (
                  <Skeleton key={index} className="h-12" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <EmptyState
                icon={<LineChartIcon className="size-5" />}
                title="Sin notas"
                description="Registra tu primera calificación para empezar a ver tendencias."
                action={
                  <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
                    Añadir nota
                  </Button>
                }
              />
            ) : (
              <ul className="divide-y divide-ink-850">
                {items.map((grade) => (
                  <li key={grade.id} className="group flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-ink-100">{grade.title}</p>
                      <p className="text-xs text-ink-400">
                        {grade.course?.code}
                        {grade.graded_on_date ? ` · ${formatDate(grade.graded_on_date)}` : ''}
                        {grade.weight != null ? ` · peso ${grade.weight}%` : ''}
                        {' · '}
                        {CATEGORY_LABELS[grade.category] ?? grade.category}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge
                        tone={
                          grade.percentage >= 90
                            ? 'success'
                            : grade.percentage >= 70
                              ? 'info'
                              : grade.percentage >= 60
                                ? 'warning'
                                : 'danger'
                        }
                      >
                        {grade.percentage.toFixed(1)}%
                      </Badge>
                      <span className="text-xs text-ink-500">
                        {grade.score}/{grade.max_score}
                      </span>
                      <IconButton
                        label="Eliminar nota"
                        className="opacity-0 transition group-hover:opacity-100"
                        onClick={() => {
                          void deleteGrade.mutateAsync(grade.id).then(
                            () => toast.success('Nota eliminada'),
                            () => toast.error('No se pudo eliminar'),
                          )
                        }}
                      >
                        <Trash2 className="size-4" />
                      </IconButton>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card className="h-fit">
          <CardHeader title="Por categoría" description="Promedio según el tipo de evaluación." />
          <CardBody className="pt-0">
            {categories.length === 0 ? (
              <p className="py-4 text-sm text-ink-400">Sin datos por categoría todavía.</p>
            ) : (
              <ul className="space-y-3">
                {categories.map((row) => (
                  <li key={row.category}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-ink-300">
                        {CATEGORY_LABELS[row.category] ?? row.category}
                      </span>
                      <span className="text-ink-400">{row.count} notas</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-800">
                        <div
                          className="h-full rounded-full bg-flame-400"
                          style={{ width: `${Math.min(row.average, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-ink-200">{row.average.toFixed(1)}%</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Añadir nota"
        description="Registra una calificación con su peso para el promedio."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button isLoading={createGrade.isPending} onClick={() => void handleSubmit()}>
              Guardar nota
            </Button>
          </>
        }
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            void handleSubmit()
          }}
        >
          <Field label="Curso" required>
            <Select
              value={form.course_id}
              onChange={(event) => setForm({ ...form, course_id: event.target.value })}
            >
              <option value="">Selecciona un curso…</option>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code} — {course.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Título" required>
            <Input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Parcial 1"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Categoría">
              <Select
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
              >
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fecha">
              <Input
                type="date"
                value={form.graded_on_date}
                onChange={(event) => setForm({ ...form, graded_on_date: event.target.value })}
              />
            </Field>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Nota" required>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.score}
                onChange={(event) => setForm({ ...form, score: event.target.value })}
                placeholder="85"
              />
            </Field>
            <Field label="Máximo">
              <Input
                type="number"
                min={1}
                step="0.01"
                value={form.max_score}
                onChange={(event) => setForm({ ...form, max_score: event.target.value })}
              />
            </Field>
            <Field label="Peso %" hint="opcional">
              <Input
                type="number"
                min={0}
                max={100}
                value={form.weight}
                onChange={(event) => setForm({ ...form, weight: event.target.value })}
                placeholder="30"
              />
            </Field>
          </div>
          <button type="submit" className="hidden" />
        </form>
      </Modal>
    </div>
  )
}
