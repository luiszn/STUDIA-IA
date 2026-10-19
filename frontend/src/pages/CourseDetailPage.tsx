import {
  ArrowLeft,
  BookOpen,
  CalendarClock,
  FileText,
  Layers,
  NotebookPen,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader, StatTile } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, Modal, ProgressBar, Skeleton } from '@/components/ui/Card'
import { Field, Input, Select } from '@/components/ui/Input'
import { EXAM_TYPE_LABELS, formatDate, formatMinutes, toLocalInput, fromLocalInput } from '@/lib/format'
import {
  useCourse,
  useCourseStats,
  useCreateExam,
  useCreateTask,
  useDeleteCourse,
  useDocuments,
  useExams,
  useGenerateFlashcards,
  useTasks,
} from '@/lib/queries'

export default function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: course, isPending, error, refetch } = useCourse(courseId)
  const { data: stats } = useCourseStats(courseId)
  const { data: tasks } = useTasks({ course_id: courseId, limit: 8 })
  const { data: exams } = useExams({ course_id: courseId, upcoming_only: true, limit: 5 })
  const { data: documents } = useDocuments({ course_id: courseId })
  const deleteCourse = useDeleteCourse()
  const createTask = useCreateTask()
  const createExam = useCreateExam()
  const generateFlashcards = useGenerateFlashcards()

  const [taskOpen, setTaskOpen] = useState(false)
  const [examOpen, setExamOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [aiCount, setAiCount] = useState(12)
  const [taskForm, setTaskForm] = useState({ title: '', due_at: '', priority: 'medium', estimated_minutes: 60 })
  const [examForm, setExamForm] = useState({
    title: '',
    exam_type: 'partial',
    scheduled_at: '',
    location: '',
  })

  if (isPending)
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-10 w-3/4" />
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
  if (error || !course) {
    return <ErrorState message={error?.message} onRetry={() => void refetch()} />
  }

  async function onCreateTask(event: FormEvent) {
    event.preventDefault()
    try {
      await createTask.mutateAsync({
        title: taskForm.title.trim(),
        course_id: courseId,
        priority: taskForm.priority,
        due_at: fromLocalInput(taskForm.due_at),
        estimated_minutes: Number(taskForm.estimated_minutes) || null,
      })
      toast.success('Tarea creada')
      setTaskForm({ title: '', due_at: '', priority: 'medium', estimated_minutes: 60 })
      setTaskOpen(false)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : 'No pudimos crear la tarea')
    }
  }

  async function onCreateExam(event: FormEvent) {
    event.preventDefault()
    try {
      await createExam.mutateAsync({
        title: examForm.title.trim(),
        course_id: courseId,
        exam_type: examForm.exam_type,
        scheduled_at: fromLocalInput(examForm.scheduled_at),
        location: examForm.location.trim() || null,
      })
      toast.success('Examen agendado')
      setExamForm({ title: '', exam_type: 'partial', scheduled_at: '', location: '' })
      setExamOpen(false)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : 'No pudimos crear el examen')
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to="/app/courses"
        className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-200"
      >
        <ArrowLeft className="size-4" /> Cursos
      </Link>

      <PageHeader
        title={course.name}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs" style={{ color: course.color }}>
              {course.code}
            </span>
            {course.professor ? <span>· {course.professor}</span> : null}
            <span>· {course.credits} créditos</span>
            {course.semester ? <span>· {course.semester}</span> : null}
            <Badge tone={course.status === 'active' ? 'success' : 'neutral'}>
              {course.status === 'active' ? 'Activo' : course.status}
            </Badge>
          </span>
        }
        actions={
          <>
            <Button variant="secondary" leftIcon={<NotebookPen className="size-4" />} onClick={() => setTaskOpen(true)}>
              Tarea
            </Button>
            <Button leftIcon={<CalendarClock className="size-4" />} onClick={() => setExamOpen(true)}>
              Examen
            </Button>
            <IconButton label="Eliminar curso" variant="danger" onClick={() => setConfirmDelete(true)}>
              <Trash2 className="size-4" />
            </IconButton>
          </>
        }
      />

      {course.description ? (
        <Card>
          <CardBody className="py-4 text-sm leading-relaxed text-ink-300">{course.description}</CardBody>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Tareas" value={`${stats?.completed_tasks ?? 0}/${stats?.total_tasks ?? 0}`} hint={`${course.pending_task_count} pendientes`} icon={<NotebookPen className="size-5" />} tone="info" />
        <StatTile label="Exámenes" value={stats?.upcoming_exams ?? 0} hint="programados" icon={<CalendarClock className="size-5" />} tone="warning" />
        <StatTile label="Material" value={stats?.documents ?? 0} hint="documentos" icon={<FileText className="size-5" />} tone="neutral" />
        <StatTile label="Estudio" value={formatMinutes(stats?.study_minutes ?? 0)} hint={`${stats?.flashcards ?? 0} tarjetas`} icon={<BookOpen className="size-5" />} tone="flame" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Tareas del curso"
            icon={<NotebookPen className="size-4" />}
            action={
              <Link to="/app/tasks" className="text-xs text-flame-300 hover:text-flame-200">
                Ver todas
              </Link>
            }
          />
          <CardBody className="pt-0">
            {(tasks?.items ?? []).length === 0 ? (
              <EmptyState title="Sin tareas" description="Crea la primera tarea de este curso." className="py-8" />
            ) : (
              <ul className="divide-y divide-ink-850">
                {tasks?.items.map((task) => (
                  <li key={task.id} className="flex items-center gap-3 py-2.5">
                    <span
                      className={
                        task.status === 'done'
                          ? 'size-2 rounded-full bg-success'
                          : task.is_overdue
                            ? 'size-2 rounded-full bg-danger'
                            : 'size-2 rounded-full bg-ink-600'
                      }
                    />
                    <div className="min-w-0 flex-1">
                      <p
                        className={
                          task.status === 'done' ? 'truncate text-sm text-ink-500 line-through' : 'truncate text-sm text-ink-100'
                        }
                      >
                        {task.title}
                      </p>
                      <p className="text-xs text-ink-400">
                        {task.due_at ? formatDate(task.due_at) : 'sin fecha'}
                        {task.estimated_minutes ? ` · ${task.estimated_minutes} min` : ''}
                      </p>
                    </div>
                    <Badge
                      tone={
                        task.priority === 'urgent'
                          ? 'danger'
                          : task.priority === 'high'
                            ? 'warning'
                            : task.priority === 'low'
                              ? 'neutral'
                              : 'info'
                      }
                    >
                      {task.priority}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Asistente IA" icon={<Sparkles className="size-4" />} />
            <CardBody className="space-y-3 pt-0">
              <p className="text-xs text-ink-400">
                Genera material de estudio desde las clases y documentos de este curso.
              </p>
              <Button
                className="w-full"
                leftIcon={<Wand2 className="size-4" />}
                onClick={() => setAiOpen(true)}
              >
                Generar flashcards con IA
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => navigate('/app/planner')}
              >
                Crear plan de estudio
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate('/app/ai?q=' + encodeURIComponent(`Ayúdame a simplificar ${course.code}`))}
              >
                Preguntar a la IA
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Próximos exámenes" icon={<CalendarClock className="size-4" />} />
            <CardBody className="space-y-3 pt-0">
              {(exams?.items ?? []).length === 0 ? (
                <p className="py-4 text-sm text-ink-400">Sin exámenes programados.</p>
              ) : (
                exams?.items.map((exam) => (
                  <div key={exam.id} className="rounded-xl border border-ink-800 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm text-ink-100">{exam.title}</p>
                      <Badge tone={exam.days_until !== null && exam.days_until <= 3 ? 'danger' : 'info'}>
                        {exam.days_until !== null ? `${exam.days_until} d` : '—'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-ink-400">
                      {formatDate(exam.scheduled_at)} · {EXAM_TYPE_LABELS[exam.exam_type]}
                      {exam.location ? ` · ${exam.location}` : ''}
                    </p>
                  </div>
                ))
              )}
            </CardBody>
          </Card>

          {stats?.average_grade !== null && stats?.average_grade !== undefined ? (
            <Card>
              <CardHeader title="Rendimiento" />
              <CardBody className="pt-0">
                <div className="mb-2 flex items-baseline justify-between">
                  <span className="font-display text-2xl font-semibold">
                    {stats.average_grade.toFixed(1)}%
                  </span>
                  {stats.highest_grade !== null ? (
                    <span className="text-xs text-ink-400">máx {stats.highest_grade.toFixed(1)}%</span>
                  ) : null}
                </div>
                <ProgressBar
                  value={stats.average_grade}
                  tone={stats.average_grade >= 70 ? 'success' : stats.average_grade >= 50 ? 'warning' : 'danger'}
                />
              </CardBody>
            </Card>
          ) : null}

          <Card>
            <CardHeader title="Material" icon={<Layers className="size-4" />} />
            <CardBody className="space-y-2 pt-0 text-sm">
              <Link
                to="/app/documents"
                className="flex items-center justify-between rounded-xl border border-ink-800 px-3 py-2.5 hover:border-flame-400/40"
              >
                <span className="text-ink-200">Documentos</span>
                <span className="text-ink-400">{course.document_count}</span>
              </Link>
              <Link
                to="/app/flashcards"
                className="flex items-center justify-between rounded-xl border border-ink-800 px-3 py-2.5 hover:border-flame-400/40"
              >
                <span className="text-ink-200">Flashcards</span>
                <span className="text-ink-400">{course.flashcard_count}</span>
              </Link>
            </CardBody>
          </Card>
        </div>
      </div>

      <Modal
        open={taskOpen}
        onClose={() => setTaskOpen(false)}
        title="Nueva tarea"
        footer={
          <>
            <Button variant="ghost" onClick={() => setTaskOpen(false)}>
              Cancelar
            </Button>
            <Button form="task-form" type="submit" isLoading={createTask.isPending}>
              Crear
            </Button>
          </>
        }
      >
        <form id="task-form" onSubmit={onCreateTask} className="space-y-4">
          <Field label="Título" required>
            <Input
              value={taskForm.title}
              onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })}
              placeholder="Taller 3 — subnetting"
              required
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Prioridad">
              <Select
                value={taskForm.priority}
                onChange={(event) => setTaskForm({ ...taskForm, priority: event.target.value })}
              >
                <option value="low">Baja</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </Select>
            </Field>
            <Field label="Entrega">
              <Input
                type="datetime-local"
                value={taskForm.due_at || toLocalInput(new Date().toISOString())}
                onChange={(event) => setTaskForm({ ...taskForm, due_at: event.target.value })}
              />
            </Field>
            <Field label="Minutos">
              <Input
                type="number"
                min={0}
                value={taskForm.estimated_minutes}
                onChange={(event) =>
                  setTaskForm({ ...taskForm, estimated_minutes: Number(event.target.value) })
                }
              />
            </Field>
          </div>
        </form>
      </Modal>

      <Modal
        open={examOpen}
        onClose={() => setExamOpen(false)}
        title="Nuevo examen"
        footer={
          <>
            <Button variant="ghost" onClick={() => setExamOpen(false)}>
              Cancelar
            </Button>
            <Button form="exam-form" type="submit" isLoading={createExam.isPending}>
              Agendar
            </Button>
          </>
        }
      >
        <form id="exam-form" onSubmit={onCreateExam} className="space-y-4">
          <Field label="Título" required>
            <Input
              value={examForm.title}
              onChange={(event) => setExamForm({ ...examForm, title: event.target.value })}
              placeholder="Parcial 1"
              required
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tipo">
              <Select
                value={examForm.exam_type}
                onChange={(event) => setExamForm({ ...examForm, exam_type: event.target.value })}
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
                value={examForm.scheduled_at}
                onChange={(event) => setExamForm({ ...examForm, scheduled_at: event.target.value })}
                required
              />
            </Field>
          </div>
          <Field label="Sala">
            <Input
              value={examForm.location}
              onChange={(event) => setExamForm({ ...examForm, location: event.target.value })}
              placeholder="Aula 204"
            />
          </Field>
        </form>
      </Modal>

      <Modal
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        title="Generar flashcards con IA"
        description="Se crearán tarjetas a partir de los documentos indexados del curso."
        footer={
          <>
            <Button variant="ghost" onClick={() => setAiOpen(false)}>
              Cancelar
            </Button>
            <Button
              form="ai-form"
              type="submit"
              isLoading={generateFlashcards.isPending}
            >
              Generar
            </Button>
          </>
        }
      >
        <form
          id="ai-form"
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            const ready = (documents ?? []).filter((doc) => doc.status === 'ready')
            if (ready.length === 0) {
              toast.error('Sube y procesa documentos de este curso primero')
              return
            }
            void generateFlashcards
              .mutateAsync({
                document_ids: ready.slice(0, 10).map((doc) => doc.id),
                count: aiCount,
                deck: course.name,
                course_id: courseId,
                difficulty: 'medium',
                focus: undefined,
              })
              .then(
                () => {
                  toast.success('Flashcards generadas')
                  setAiOpen(false)
                  void queryClient.invalidateQueries({ queryKey: ['flashcards'] })
                  navigate('/app/flashcards')
                },
                (cause: unknown) =>
                  toast.error(cause instanceof Error ? cause.message : 'No pudimos generar las tarjetas'),
              )
          }}
        >
          <Field label="Cantidad" hint="entre 1 y 60">
            <Input
              type="number"
              min={1}
              max={60}
              value={aiCount}
              onChange={(event) => setAiCount(Number(event.target.value))}
            />
          </Field>
          <p className="text-xs text-ink-400">
            {((documents ?? []).filter((doc) => doc.status === 'ready').length)} documento(s)
            listo(s) para usar.
          </p>
        </form>
      </Modal>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Eliminar curso"
        size="sm"
        description="Se borrarán también sus tareas, exámenes, notas y flashcards asociadas."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              isLoading={deleteCourse.isPending}
              onClick={async () => {
                try {
                  await deleteCourse.mutateAsync(courseId ?? '')
                  toast.success('Curso eliminado')
                  navigate('/app/courses')
                } catch (cause) {
                  toast.error(cause instanceof Error ? cause.message : 'No pudimos eliminar')
                }
              }}
            >
              Eliminar
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-300">
          ¿Seguro que quieres eliminar <span className="text-ink-100">{course.code}</span>?
        </p>
      </Modal>
    </div>
  )
}
