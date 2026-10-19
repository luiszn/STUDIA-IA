import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { CalendarClock, MapPin, NotebookPen, Plus, Trash2 } from 'lucide-react'

import { PageHeader, StatTile } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Badge,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  Modal,
  Skeleton,
} from '@/components/ui/Card'
import { Field, Input, Select, Textarea } from '@/components/ui/Input'
import { EXAM_STATUS_LABELS, EXAM_TYPE_LABELS, formatDateTime } from '@/lib/format'
import { useCourses, useCreateExam, useDeleteExam, useExams } from '@/lib/queries'

function daysUntil(iso: string): number {
  const target = new Date(iso).getTime()
  const now = Date.now()
  return Math.ceil((target - now) / 86_400_000)
}

export default function ExamsPage() {
  const exams = useExams({ limit: 50 })
  const courses = useCourses()
  const createExam = useCreateExam()
  const deleteExam = useDeleteExam()
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    course_id: '',
    title: '',
    exam_type: 'partial',
    scheduled_at: '',
    duration_minutes: '',
    location: '',
    weight: '',
    topics: '',
  })

  const items = exams.data?.items ?? []

  const { upcoming, past } = useMemo(() => {
    const now = Date.now()
    const sorted = [...items].sort(
      (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
    )
    return {
      upcoming: sorted.filter((exam) => new Date(exam.scheduled_at).getTime() >= now),
      past: sorted.filter((exam) => new Date(exam.scheduled_at).getTime() < now).reverse(),
    }
  }, [items])

  const nextExam = upcoming[0]
  const nearestDays = nextExam ? daysUntil(nextExam.scheduled_at) : null
  const graded = past.filter((exam) => exam.grade_id).length

  const handleSubmit = async () => {
    if (!form.course_id) return toast.error('Selecciona un curso')
    if (form.title.trim().length < 2) return toast.error('Escribe un título')
    if (!form.scheduled_at) return toast.error('Indica fecha y hora del examen')

    try {
      await createExam.mutateAsync({
        course_id: form.course_id,
        title: form.title.trim(),
        exam_type: form.exam_type,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : undefined,
        location: form.location.trim() || undefined,
        weight: form.weight ? Number(form.weight) : undefined,
        topics: form.topics.trim() || undefined,
      })
      toast.success('Examen agendado')
      setOpen(false)
      setForm({
        course_id: '',
        title: '',
        exam_type: 'partial',
        scheduled_at: '',
        duration_minutes: '',
        location: '',
        weight: '',
        topics: '',
      })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo crear el examen')
    }
  }

  if (exams.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Exámenes" description="Próximos y pasados." />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (exams.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title="Exámenes" description="Próximos y pasados." />
        <ErrorState onRetry={() => void exams.refetch()} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exámenes"
        description="Próximos y pasados."
        actions={
          <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
            Nuevo examen
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          label="Próximo examen"
          value={nearestDays != null ? (nearestDays === 0 ? 'Hoy' : `${nearestDays} d`) : '—'}
          icon={<CalendarClock className="size-5" />}
          tone={nearestDays != null && nearestDays <= 3 ? 'danger' : 'flame'}
        />
        <StatTile
          label="Programados"
          value={upcoming.length}
          icon={<NotebookPen className="size-5" />}
          tone="info"
        />
        <StatTile
          label="Anotados"
          value={`${graded}/${past.length}`}
          icon={<NotebookPen className="size-5" />}
          tone="success"
        />
      </div>

      <Card>
        <CardBody>
          {upcoming.length === 0 ? (
            <EmptyState
              icon={<CalendarClock className="size-5" />}
              title="Sin exámenes programados"
              description="Agenda uno para recibir recordatorios en el calendario."
              action={
                <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
                  Nuevo examen
                </Button>
              }
            />
          ) : (
            <ul className="space-y-3">
              {upcoming.map((exam) => {
                const remaining = daysUntil(exam.scheduled_at)
                const urgent = remaining <= 3
                return (
                  <li
                    key={exam.id}
                    className="group flex flex-wrap items-center gap-4 rounded-2xl border border-ink-800 bg-ink-850/40 p-4 transition hover:border-ink-700"
                  >
                    <div
                      className={
                        urgent
                          ? 'grid size-16 shrink-0 place-items-center rounded-2xl bg-danger/12 text-center'
                          : 'grid size-16 shrink-0 place-items-center rounded-2xl bg-flame-400/12 text-center'
                      }
                    >
                      <div>
                        <p
                          className={
                            urgent
                              ? 'font-display text-2xl font-semibold leading-none text-danger'
                              : 'font-display text-2xl font-semibold leading-none text-flame-300'
                          }
                        >
                          {remaining}
                        </p>
                        <p className="text-[0.6rem] tracking-wider text-ink-500 uppercase">
                          {remaining === 1 ? 'día' : 'días'}
                        </p>
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-medium text-ink-100">{exam.title}</p>
                        <Badge tone={urgent ? 'danger' : 'neutral'}>
                          {EXAM_TYPE_LABELS[exam.exam_type] ?? exam.exam_type}
                        </Badge>
                        <Badge tone="success">{EXAM_STATUS_LABELS[exam.status] ?? exam.status}</Badge>
                      </div>
                      <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-400">
                        <span>{formatDateTime(exam.scheduled_at)}</span>
                        {exam.duration_minutes ? <span>{exam.duration_minutes} min</span> : null}
                        {exam.location ? (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="size-3" /> {exam.location}
                          </span>
                        ) : null}
                        {exam.course ? <span>{exam.course.code}</span> : null}
                        {exam.weight != null ? <span>peso {exam.weight}%</span> : null}
                      </p>
                      {exam.topics && exam.topics.length > 0 ? (
                        <p className="mt-1.5 truncate text-xs text-ink-500">
                          {Array.isArray(exam.topics) ? exam.topics.join(' · ') : exam.topics}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex shrink-0 items-center gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => navigate('/planner')}
                      >
                        Preparar
                      </Button>
                      {!exam.grade_id ? (
                        <Button size="sm" variant="outline" onClick={() => navigate('/grades')}>
                          Calificar
                        </Button>
                      ) : null}
                      <IconButton
                        label="Eliminar examen"
                        className="opacity-0 transition group-hover:opacity-100"
                        onClick={() => {
                          void deleteExam.mutateAsync(exam.id).then(
                            () => toast.success('Examen eliminado'),
                            () => toast.error('No se pudo eliminar'),
                          )
                        }}
                      >
                        <Trash2 className="size-4" />
                      </IconButton>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </CardBody>
      </Card>

      {past.length > 0 ? (
        <Card>
          <CardBody>
            <h2 className="mb-3 text-sm font-semibold text-ink-200">Pasados</h2>
            <ul className="divide-y divide-ink-850">
              {past.map((exam) => (
                <li key={exam.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-ink-200">{exam.title}</p>
                    <p className="text-xs text-ink-500">
                      {formatDateTime(exam.scheduled_at)}
                      {exam.course ? ` · ${exam.course.code}` : ''}
                    </p>
                  </div>
                  <Badge tone={exam.grade_id ? 'success' : 'warning'}>
                    {exam.grade_id ? 'Anotado' : 'Sin nota'}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ) : null}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Nuevo examen"
        description="Aparecerá en tu calendario con cuenta atrás."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button isLoading={createExam.isPending} onClick={() => void handleSubmit()}>
              Agendar
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
              placeholder="Parcial 2"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tipo">
              <Select
                value={form.exam_type}
                onChange={(event) => setForm({ ...form, exam_type: event.target.value })}
              >
                {Object.entries(EXAM_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fecha y hora" required>
              <Input
                type="datetime-local"
                value={form.scheduled_at}
                onChange={(event) => setForm({ ...form, scheduled_at: event.target.value })}
              />
            </Field>
            <Field label="Duración (min)">
              <Input
                type="number"
                min={1}
                max={1440}
                value={form.duration_minutes}
                onChange={(event) => setForm({ ...form, duration_minutes: event.target.value })}
                placeholder="90"
              />
            </Field>
            <Field label="Lugar">
              <Input
                value={form.location}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
                placeholder="Aula 301"
              />
            </Field>
            <Field label="Peso %" hint="0–100">
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
          <Field label="Temas" hint="separados por comas">
            <Textarea
              rows={3}
              value={form.topics}
              onChange={(event) => setForm({ ...form, topics: event.target.value })}
              placeholder="Derivadas, integrales, límites"
            />
          </Field>
          <button type="submit" className="hidden" />
        </form>
      </Modal>
    </div>
  )
}
