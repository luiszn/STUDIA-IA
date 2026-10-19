import { BookOpen, FileText, GraduationCap, Layers, NotebookPen, Plus } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import { Badge, Card, EmptyState, ErrorState, Modal, ProgressBar, Skeleton } from '@/components/ui/Card'
import { Field, Input, Select, Textarea } from '@/components/ui/Input'
import { cn, pluralize } from '@/lib/format'
import { useCourses, useCreateCourse } from '@/lib/queries'
import type { CourseRead } from '@/lib/types'

const PALETTE = ['#ff7a1a', '#f5a524', '#2fbf71', '#4b9bff', '#a855f7', '#ef4a5b', '#14b8a6', '#eab308']

const EMPTY_FORM = {
  code: '',
  name: '',
  professor: '',
  credits: 4,
  semester: '',
  color: PALETTE[0],
  description: '',
}

function CourseCard({ course }: { course: CourseRead }) {
  const graded = course.average_grade !== null
  return (
    <Link
      to={`/app/courses/${course.id}`}
      className="panel panel-hover group relative overflow-hidden p-5"
    >
      <span
        className="absolute inset-y-0 left-0 w-1 transition-all group-hover:w-1.5"
        style={{ backgroundColor: course.color }}
      />
      <div className="flex items-start justify-between gap-3 pl-2">
        <div className="min-w-0">
          <p className="font-mono text-xs text-ink-400">{course.code}</p>
          <h3 className="mt-0.5 truncate font-display text-base font-semibold text-ink-100">
            {course.name}
          </h3>
          {course.professor ? (
            <p className="mt-0.5 truncate text-xs text-ink-400">{course.professor}</p>
          ) : null}
        </div>
        <Badge tone={course.status === 'active' ? 'success' : 'neutral'}>
          {course.status === 'active' ? 'Activo' : course.status}
        </Badge>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 pl-2 text-xs text-ink-400 sm:grid-cols-4">
        <span className="flex items-center gap-1.5">
          <NotebookPen className="size-3.5" /> {course.pending_task_count}/{course.task_count}
        </span>
        <span className="flex items-center gap-1.5">
          <FileText className="size-3.5" /> {course.document_count}
        </span>
        <span className="flex items-center gap-1.5">
          <Layers className="size-3.5" /> {course.flashcard_count}
        </span>
        <span className="flex items-center gap-1.5">
          <BookOpen className="size-3.5" /> {course.exam_count}
        </span>
      </div>

      {graded ? (
        <div className="mt-4 pl-2">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="text-ink-400">Promedio</span>
            <span className="font-medium text-ink-100">{course.average_grade?.toFixed(1)}%</span>
          </div>
          <ProgressBar
            value={course.average_grade ?? 0}
            tone={
              (course.average_grade ?? 0) >= 70 ? 'success' : (course.average_grade ?? 0) >= 50 ? 'warning' : 'danger'
            }
          />
        </div>
      ) : null}
    </Link>
  )
}

export default function CoursesPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('active')
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const { data, isPending, error, refetch } = useCourses({ status, search: search || undefined })
  const createCourse = useCreateCourse()

  const courses = useMemo(() => data ?? [], [data])

  const totals = useMemo(
    () => ({
      credits: courses.reduce((sum, course) => sum + course.credits, 0),
      documents: courses.reduce((sum, course) => sum + course.document_count, 0),
      flashcards: courses.reduce((sum, course) => sum + course.flashcard_count, 0),
    }),
    [courses],
  )

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    try {
      await createCourse.mutateAsync({
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        professor: form.professor.trim() || null,
        credits: Number(form.credits) || 0,
        semester: form.semester.trim() || null,
        color: form.color,
        description: form.description.trim() || null,
      })
      toast.success(`Curso ${form.code.toUpperCase()} creado`)
      setForm(EMPTY_FORM)
      setOpen(false)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : 'No pudimos crear el curso')
    }
  }

  return (
    <div>
      <PageHeader
        title="Cursos"
        description={
          courses.length
            ? `${pluralize(courses.length, 'curso')} · ${totals.credits} créditos · ${totals.documents} documentos · ${totals.flashcards} tarjetas`
            : 'Tu semestre, ordenado.'
        }
        actions={
          <Button leftIcon={<Plus className="size-4" />} onClick={() => setOpen(true)}>
            Nuevo curso
          </Button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar por nombre o código…"
          className="max-w-xs"
        />
        <Select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="w-auto"
          aria-label="Estado"
        >
          <option value="active">Activos</option>
          <option value="archived">Archivados</option>
          <option value="completed">Completados</option>
          <option value="">Todos</option>
        </Select>
      </div>

      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-44" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error.message} onRetry={() => void refetch()} />
      ) : courses.length === 0 ? (
        <Card>
          <EmptyState
            icon={<GraduationCap className="size-6" />}
            title="Todavía no tienes cursos"
            description="Crea tu primer curso para empezar a organizar tareas, exámenes, notas y material."
            action={
              <Button onClick={() => setOpen(true)} leftIcon={<Plus className="size-4" />}>
                Crear curso
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {courses.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Nuevo curso"
        description="Código, nombre y lo que necesites recordar."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button form="course-form" type="submit" isLoading={createCourse.isPending}>
              Crear curso
            </Button>
          </>
        }
      >
        <form id="course-form" onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
            <Field label="Código" required>
              <Input
                value={form.code}
                onChange={(event) => setForm({ ...form, code: event.target.value })}
                placeholder="REDES-101"
                required
              />
            </Field>
            <Field label="Nombre" required>
              <Input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="Redes de Computadores"
                required
              />
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Profesor">
              <Input
                value={form.professor}
                onChange={(event) => setForm({ ...form, professor: event.target.value })}
                placeholder="Opcional"
              />
            </Field>
            <Field label="Créditos">
              <Input
                type="number"
                min={0}
                max={30}
                value={form.credits}
                onChange={(event) => setForm({ ...form, credits: Number(event.target.value) })}
              />
            </Field>
            <Field label="Semestre">
              <Input
                value={form.semester}
                onChange={(event) => setForm({ ...form, semester: event.target.value })}
                placeholder="2026-1"
              />
            </Field>
          </div>

          <Field label="Color" hint="Se usa en gráficos y etiquetas del calendario.">
            <div className="flex flex-wrap gap-2">
              {PALETTE.map((color) => (
                <button
                  key={color}
                  type="button"
                  aria-label={`Color ${color}`}
                  onClick={() => setForm({ ...form, color })}
                  className={cn(
                    'size-7 rounded-lg transition',
                    form.color === color && 'ring-2 ring-ink-100 ring-offset-2 ring-offset-ink-900',
                  )}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </Field>

          <Field label="Descripción" hint="Opcional">
            <Textarea
              rows={3}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Programa, temario, objetivos…"
            />
          </Field>

          <p className="text-xs text-ink-500">
            Después podrás asociar documentos, tareas y flashcards a este curso.
          </p>
        </form>
      </Modal>
    </div>
  )
}
