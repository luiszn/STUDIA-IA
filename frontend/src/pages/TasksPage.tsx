import { CheckCircle2, Circle, Filter, ListChecks, Plus, Trash2 } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import { Badge, Card, EmptyState, ErrorState, Modal, Skeleton, Tabs } from '@/components/ui/Card'
import { Field, Input, Select, Textarea } from '@/components/ui/Input'
import { cn, formatDueLabel, fromLocalInput, PRIORITY_LABELS } from '@/lib/format'
import {
  useCourses,
  useCreateTask,
  useDeleteTask,
  useTasks,
  useToggleTask,
} from '@/lib/queries'
import type { Priority, TaskRead } from '@/lib/types'

type Filter = 'all' | 'todo' | 'done' | 'overdue'

const PRIORITY_TONE = {
  urgent: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'neutral',
} as const

function TaskRow({
  task,
  onToggle,
  onDelete,
  isToggling,
}: {
  task: TaskRead
  onToggle: () => void
  onDelete: () => void
  isToggling: boolean
}) {
  const done = task.status === 'done'
  return (
    <li className="group flex items-start gap-3 px-4 py-3 transition hover:bg-ink-850/40">
      <button
        onClick={onToggle}
        disabled={isToggling}
        aria-label={done ? 'Marcar como pendiente' : 'Marcar como completada'}
        className="mt-0.5 shrink-0 transition"
      >
        {done ? (
          <CheckCircle2 className="size-5 text-success" />
        ) : (
          <Circle className="size-5 text-ink-600 hover:text-flame-400" />
        )}
      </button>

      <div className="min-w-0 flex-1">
        <p className={cn('text-sm', done ? 'text-ink-500 line-through' : 'text-ink-100')}>
          {task.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-400">
          {task.course ? (
            <span className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full" style={{ backgroundColor: task.course.color }} />
              {task.course.code}
            </span>
          ) : null}
          {task.due_at ? (
            <span className={cn(!done && task.is_overdue && 'text-danger')}>
              {formatDueLabel(task.due_at)} · {new Date(task.due_at).toLocaleDateString('es')}
            </span>
          ) : null}
          {task.estimated_minutes ? <span>{task.estimated_minutes} min</span> : null}
          {task.status === 'in_progress' ? <Badge tone="info">en curso</Badge> : null}
        </div>
        {task.description ? (
          <p className="mt-1.5 line-clamp-2 text-xs text-ink-500">{task.description}</p>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <Badge tone={PRIORITY_TONE[task.priority]}>
          {PRIORITY_LABELS[task.priority] ?? task.priority}
        </Badge>
        <IconButton
          label="Eliminar tarea"
          className="opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
          onClick={onDelete}
        >
          <Trash2 className="size-4" />
        </IconButton>
      </div>
    </li>
  )
}

export default function TasksPage() {
  const [filter, setFilter] = useState<Filter>('all')
  const [courseId, setCourseId] = useState('')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    title: '',
    description: '',
    course_id: '',
    priority: 'medium' as Priority,
    due_at: '',
    estimated_minutes: 60,
  })

  const { data: courses } = useCourses()
  const query = useMemo(
    () => ({
      status: filter === 'done' ? 'done' : filter === 'todo' ? 'todo' : undefined,
      course_id: courseId || undefined,
      limit: 100,
    }),
    [filter, courseId],
  )
  const { data, isPending, error, refetch } = useTasks(query)
  const createTask = useCreateTask()
  const toggleTask = useToggleTask()
  const deleteTask = useDeleteTask()

  const all = data?.items ?? []
  const visible = useMemo(() => {
    if (filter === 'overdue') return all.filter((task) => task.is_overdue && task.status !== 'done')
    return all
  }, [all, filter])

  const counts = {
    all: all.length,
    todo: all.filter((task) => task.status !== 'done').length,
    done: all.filter((task) => task.status === 'done').length,
    overdue: all.filter((task) => task.is_overdue && task.status !== 'done').length,
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    try {
      await createTask.mutateAsync({
        title: form.title.trim(),
        description: form.description.trim() || null,
        course_id: form.course_id || null,
        priority: form.priority,
        due_at: fromLocalInput(form.due_at),
        estimated_minutes: Number(form.estimated_minutes) || null,
      })
      toast.success('Tarea creada')
      setForm({ title: '', description: '', course_id: '', priority: 'medium', due_at: '', estimated_minutes: 60 })
      setOpen(false)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : 'No pudimos crear la tarea')
    }
  }

  return (
    <div>
      <PageHeader
        title="Tareas"
        description={`${counts.todo} pendientes · ${counts.overdue} vencidas`}
        actions={
          <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
            Nueva tarea
          </Button>
        }
      />

      <Tabs
        className="mb-5"
        value={filter}
        onChange={setFilter}
        tabs={[
          { value: 'all', label: 'Todas', count: counts.all },
          { value: 'todo', label: 'Pendientes', count: counts.todo },
          { value: 'overdue', label: 'Vencidas', count: counts.overdue },
          { value: 'done', label: 'Completadas', count: counts.done },
        ]}
      />

      <div className="mb-5 flex items-center gap-3">
        <Filter className="size-4 text-ink-500" />
        <Select
          value={courseId}
          onChange={(event) => setCourseId(event.target.value)}
          className="max-w-xs"
          aria-label="Filtrar por curso"
        >
          <option value="">Todos los cursos</option>
          {(courses ?? []).map((course) => (
            <option key={course.id} value={course.id}>
              {course.code} — {course.name}
            </option>
          ))}
        </Select>
      </div>

      <Card>
        {isPending ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} className="h-14" />
            ))}
          </div>
        ) : error ? (
          <ErrorState message={error.message} onRetry={() => void refetch()} />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={<ListChecks className="size-6" />}
            title={filter === 'done' ? 'Nada completado todavía' : 'Sin tareas en esta vista'}
            description="Crea una tarea y aparece aquí con su fecha y prioridad."
            action={
              <Button onClick={() => setOpen(true)} leftIcon={<Plus className="size-4" />}>
                Nueva tarea
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-ink-850">
            {visible.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                isToggling={toggleTask.isPending && toggleTask.variables === task.id}
                onToggle={() =>
                  toggleTask.mutate(task.id, {
                    onError: () => toast.error('No pudimos actualizar la tarea'),
                  })
                }
                onDelete={() =>
                  deleteTask.mutate(task.id, {
                    onSuccess: () => toast.success('Tarea eliminada'),
                    onError: () => toast.error('No pudimos eliminar'),
                  })
                }
              />
            ))}
          </ul>
        )}
      </Card>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Nueva tarea"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button form="new-task" type="submit" isLoading={createTask.isPending}>
              Crear tarea
            </Button>
          </>
        }
      >
        <form id="new-task" onSubmit={onSubmit} className="space-y-4">
          <Field label="Título" required>
            <Input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Leer caps. 4 y 5"
              required
            />
          </Field>

          <Field label="Descripción">
            <Textarea
              rows={3}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Detalles, enlaces, entregables…"
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Curso">
              <Select
                value={form.course_id}
                onChange={(event) => setForm({ ...form, course_id: event.target.value })}
              >
                <option value="">Sin curso</option>
                {(courses ?? []).map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Prioridad">
              <Select
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value as Priority })}
              >
                {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Entrega">
              <Input
                type="datetime-local"
                value={form.due_at}
                onChange={(event) => setForm({ ...form, due_at: event.target.value })}
              />
            </Field>
            <Field label="Tiempo estimado (min)">
              <Input
                type="number"
                min={0}
                value={form.estimated_minutes}
                onChange={(event) =>
                  setForm({ ...form, estimated_minutes: Number(event.target.value) })
                }
              />
            </Field>
          </div>

        </form>
      </Modal>
    </div>
  )
}
