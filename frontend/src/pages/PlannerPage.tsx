import { CalendarRange, CheckCheck, ChevronDown, ChevronUp, Loader2, Sparkles, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Modal,
  ProgressBar,
  Skeleton,
} from '@/components/ui/Card'
import { Checkbox, Field, Input, Select } from '@/components/ui/Input'
import { formatDate, formatMinutes, LEVEL_LABELS } from '@/lib/format'
import {
  useConvertStudyPlan,
  useCreateStudyPlan,
  useCourses,
  useDeleteStudyPlan,
  useExams,
  useStudyPlans,
} from '@/lib/queries'
import type { StudyPlanRead } from '@/lib/types'

function PlanDetail({ plan }: { plan: StudyPlanRead }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="flame">{plan.total_days} días</Badge>
        <Badge>{formatMinutes(plan.daily_minutes)}/día</Badge>
        <Badge>{formatMinutes(plan.total_minutes)} en total</Badge>
        <Badge tone={plan.status === 'active' ? 'success' : plan.status === 'completed' ? 'info' : 'neutral'}>
          {plan.status}
        </Badge>
        <Badge>{LEVEL_LABELS[plan.level] ?? plan.level}</Badge>
        {plan.exam_date ? <Badge tone="warning">Examen {formatDate(plan.exam_date)}</Badge> : null}
      </div>

      {plan.rationale ? <p className="text-sm text-ink-400">{plan.rationale}</p> : null}

      {plan.weak_topics.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-ink-500">Temas débiles detectados:</span>
          {plan.weak_topics.map((topic) => (
            <Badge key={topic} tone="danger">
              {topic}
            </Badge>
          ))}
        </div>
      ) : null}

      <ol className="space-y-3">
        {plan.days.map((day) => (
          <li key={day.day} className="rounded-xl border border-ink-750 bg-ink-900/60 p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-ink-100">
                  Día {day.day}
                  {day.date ? ` · ${formatDate(day.date)}` : ''} — {day.title}
                </p>
                <p className="mt-0.5 text-xs text-ink-400">{day.focus}</p>
              </div>
              <div className="flex shrink-0 gap-1.5 text-[0.7rem]">
                <Badge tone="info">Teoría {day.theory_minutes}m</Badge>
                <Badge tone="flame">Práctica {day.practice_minutes}m</Badge>
                <Badge tone="success">Repaso {day.review_minutes}m</Badge>
              </div>
            </div>
            {day.objectives.length > 0 ? (
              <ul className="mt-2.5 space-y-1">
                {day.objectives.map((objective) => (
                  <li key={objective} className="flex items-start gap-2 text-xs text-ink-300">
                    <span className="mt-1 size-1 shrink-0 rounded-full bg-flame-400" />
                    {objective}
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function PlannerPage() {
  const plans = useStudyPlans()
  const courses = useCourses()
  const exams = useExams({ upcoming_only: true, limit: 30 })

  const createPlan = useCreateStudyPlan()
  const convertPlan = useConvertStudyPlan()
  const deletePlan = useDeleteStudyPlan()

  const [wizardOpen, setWizardOpen] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [form, setForm] = useState({
    course_id: '',
    exam_id: '',
    title: '',
    level: 'intermediate',
    daily_minutes: 120,
    total_days: 7,
    focus_topics: '',
    use_weak_topics: true,
  })

  const openWizard = () => {
    setStep(1)
    setForm({
      course_id: '',
      exam_id: '',
      title: '',
      level: 'intermediate',
      daily_minutes: 120,
      total_days: 7,
      focus_topics: '',
      use_weak_topics: true,
    })
    setWizardOpen(true)
  }

  const handleCreate = async () => {
    try {
      const plan = await createPlan.mutateAsync({
        course_id: form.course_id || undefined,
        exam_id: form.exam_id || undefined,
        title: form.title.trim() || undefined,
        level: form.level,
        daily_minutes: Number(form.daily_minutes),
        total_days: Number(form.total_days),
        focus_topics: form.focus_topics
          .split(',')
          .map((topic) => topic.trim())
          .filter(Boolean),
        use_weak_topics: form.use_weak_topics,
      })
      toast.success('Plan de estudio generado')
      setWizardOpen(false)
      setExpanded(plan.id)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo generar el plan')
    }
  }

  const handleConvert = async (plan: StudyPlanRead) => {
    try {
      const result = await convertPlan.mutateAsync({
        id: plan.id,
        create_tasks: true,
        create_sessions: true,
      })
      toast.success(
        `Plan convertido: ${result.tasks_created} tareas y ${result.sessions_created} sesiones creadas`,
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo convertir el plan')
    }
  }

  const selectedExam = (exams.data?.items ?? []).find((exam) => exam.id === form.exam_id)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Planificador"
        description="Planes de estudio generados por IA, día a día."
        actions={
          <Button leftIcon={<Sparkles className="size-4" />} onClick={openWizard}>
            Nuevo plan
          </Button>
        }
      />

      {plans.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }, (_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
      ) : plans.isError ? (
        <ErrorState onRetry={() => void plans.refetch()} />
      ) : (plans.data ?? []).length === 0 ? (
        <EmptyState
          icon={<CalendarRange className="size-5" />}
          title="Sin planes de estudio"
          description="Elige un examen y la IA construirá un plan diario con teoría, práctica y repaso."
          action={
            <Button leftIcon={<Sparkles className="size-4" />} onClick={openWizard}>
              Crear mi primer plan
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {(plans.data ?? []).map((plan) => {
            const isOpen = expanded === plan.id
            return (
              <Card key={plan.id}>
                <div className="flex items-center gap-3 px-5 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate font-display text-base font-semibold text-ink-100">
                        {plan.title}
                      </p>
                      <Badge tone={plan.status === 'active' ? 'success' : 'neutral'}>{plan.status}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-ink-400">
                      {plan.course?.name ?? 'Sin curso'} · {plan.total_days} días ·{' '}
                      {formatMinutes(plan.total_minutes)} totales ·{' '}
                      {plan.days.length} sesiones planificadas
                    </p>
                    <ProgressBar
                      value={
                        plan.status === 'completed' ? 100 : plan.status === 'active' ? 45 : 0
                      }
                      className="mt-2.5 max-w-xs"
                    />
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      leftIcon={<CheckCheck className="size-3.5" />}
                      onClick={() => void handleConvert(plan)}
                      disabled={convertPlan.isPending}
                    >
                      Convertir
                    </Button>
                    <IconButton
                      label={isOpen ? 'Ocultar detalle' : 'Ver detalle'}
                      onClick={() => setExpanded(isOpen ? null : plan.id)}
                    >
                      {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                    </IconButton>
                    <IconButton
                      label="Eliminar plan"
                      onClick={() => {
                        void deletePlan.mutateAsync(plan.id).then(
                          () => toast.success('Plan eliminado'),
                          () => toast.error('No se pudo eliminar'),
                        )
                      }}
                    >
                      <Trash2 className="size-4" />
                    </IconButton>
                  </div>
                </div>
                {isOpen ? (
                  <div className="border-t border-ink-800 px-5 py-4">
                    <PlanDetail plan={plan} />
                  </div>
                ) : null}
              </Card>
            )
          })}
        </div>
      )}

      <Modal
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        title={step === 1 ? 'Paso 1 · ¿qué vas a estudiar?' : 'Paso 2 · Ajustes del plan'}
        description={
          step === 1
            ? 'Elige un examen (recomendado) o un curso, y la IA calculará las fechas.'
            : 'Define el ritmo diario y los temas a priorizar.'
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => (step === 1 ? setWizardOpen(false) : setStep(1))}>
              {step === 1 ? 'Cancelar' : 'Atrás'}
            </Button>
            {step === 1 ? (
              <Button onClick={() => setStep(2)}>Continuar</Button>
            ) : (
              <Button
                isLoading={createPlan.isPending}
                leftIcon={<Sparkles className="size-4" />}
                onClick={() => void handleCreate()}
              >
                Generar plan
              </Button>
            )}
          </>
        }
      >
        {step === 1 ? (
          <div className="space-y-4">
            <Field label="Examen (opcional)">
              <Select
                value={form.exam_id}
                onChange={(event) => {
                  const exam = (exams.data?.items ?? []).find((item) => item.id === event.target.value)
                  setForm({
                    ...form,
                    exam_id: event.target.value,
                    course_id: exam?.course_id ?? form.course_id,
                  })
                }}
              >
                <option value="">Sin examen concreto</option>
                {(exams.data?.items ?? []).map((exam) => (
                  <option key={exam.id} value={exam.id}>
                    {exam.title} · {formatDate(exam.scheduled_at)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Curso (opcional)">
              <Select
                value={form.course_id}
                onChange={(event) => setForm({ ...form, course_id: event.target.value })}
              >
                <option value="">Sin curso específico</option>
                {(courses.data ?? []).map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Título del plan" hint={selectedExam ? `Se enfocará en: ${selectedExam.title}` : undefined}>
              <Input
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                placeholder="p. ej. Preparación parcial de Redes"
              />
            </Field>
            {selectedExam ? (
              <p className="rounded-xl border border-flame-400/30 bg-flame-400/10 px-3 py-2 text-xs text-flame-200">
                Fecha objetivo: {formatDate(selectedExam.scheduled_at)} ({selectedExam.exam_type})
              </p>
            ) : null}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Nivel">
                <Select
                  value={form.level}
                  onChange={(event) => setForm({ ...form, level: event.target.value })}
                >
                  <option value="beginner">Inicial</option>
                  <option value="intermediate">Intermedio</option>
                  <option value="advanced">Avanzado</option>
                </Select>
              </Field>
              <Field label="Días hasta el examen">
                <Input
                  type="number"
                  min={1}
                  max={90}
                  value={form.total_days}
                  onChange={(event) => setForm({ ...form, total_days: Number(event.target.value) })}
                />
              </Field>
            </div>
            <Field label="Minutos de estudio al día">
              <Input
                type="number"
                min={15}
                max={720}
                step={15}
                value={form.daily_minutes}
                onChange={(event) => setForm({ ...form, daily_minutes: Number(event.target.value) })}
              />
            </Field>
            <Field label="Temas a priorizar" hint="Separados por comas">
              <Input
                value={form.focus_topics}
                onChange={(event) => setForm({ ...form, focus_topics: event.target.value })}
                placeholder="modelos OSI, transporte, seguridad"
              />
            </Field>
            <Checkbox
              checked={form.use_weak_topics}
              onChange={(event) => setForm({ ...form, use_weak_topics: event.target.checked })}
              label="Incluir mis temas débiles detectados por IA"
            />
            {createPlan.isPending ? (
              <p className="flex items-center gap-2 text-xs text-ink-400">
                <Loader2 className="size-3.5 animate-spin" /> Construyendo tu plan día a día…
              </p>
            ) : null}
          </div>
        )}
      </Modal>
    </div>
  )
}
