import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  ArrowRight,
  BrainCircuit,
  Check,
  MessageSquare,
  Sparkles,
  TrendingDown,
  X,
  Zap,
} from 'lucide-react'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
} from '@/components/ui/Card'
import { useRecommendations, useUpdateRecommendation, useWeakTopics } from '@/lib/queries'

export default function WeakTopicsPage() {
  const topics = useWeakTopics()
  const recs = useRecommendations()
  const updateRec = useUpdateRecommendation()
  const navigate = useNavigate()
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const items = topics.data ?? []
  const recommendations = (recs.data ?? []).filter(
    (rec) => !rec.is_dismissed && !dismissed.has(rec.id),
  )

  const askAi = (topicName: string, courseName: string | null) => {
    const question = `Explícame con detalle "${topicName}"${
      courseName ? ` de ${courseName}` : ''
    }. Dame ejemplos y cómo practicarlo.`
    navigate(`/ai?q=${encodeURIComponent(question)}`)
  }

  const resolveRec = async (id: string, action: 'read' | 'dismiss') => {
    try {
      await updateRec.mutateAsync(
        action === 'read' ? { id, is_read: true } : { id, is_dismissed: true },
      )
      if (action === 'dismiss') {
        setDismissed((prev) => new Set(prev).add(id))
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo actualizar')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Temas débiles"
        description="Detectados automáticamente a partir de tus notas y actividad."
      />

      <Card>
        <CardHeader
          title="Análisis de debilidades"
          description="Confianza del modelo y evidencia encontrada."
          action={
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<Sparkles className="size-4" />}
              onClick={() => void topics.refetch()}
            >
              Reanalizar
            </Button>
          }
        />
        <CardBody className="pt-0">
          {topics.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-20" />
              ))}
            </div>
          ) : topics.isError ? (
            <ErrorState onRetry={() => void topics.refetch()} />
          ) : items.length === 0 ? (
            <EmptyState
              icon={<Zap className="size-5" />}
              title="Todo sólido por ahora"
              description="Sigue estudiando y aquí aparecerán tus debilidades."
            />
          ) : (
            <ul className="space-y-4">
              {items.map((topic, index) => {
                const confidence = Math.round((topic.confidence ?? 0) * 100)
                const tone =
                  confidence >= 75 ? 'danger' : confidence >= 50 ? 'warning' : 'info'
                return (
                  <li
                    key={`${topic.topic}-${index}`}
                    className="rounded-2xl border border-ink-800 bg-ink-850/40 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-ink-100">{topic.topic}</p>
                        <p className="mt-0.5 text-xs text-ink-400">
                          {topic.course_name ?? 'Sin curso asignado'}
                        </p>
                      </div>
                      <Badge tone={tone}>
                        <TrendingDown className="mr-1 inline size-3" />
                        {confidence}% confianza
                      </Badge>
                    </div>

                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-800">
                      <div
                        className={
                          tone === 'danger'
                            ? 'h-full rounded-full bg-danger'
                            : tone === 'warning'
                              ? 'h-full rounded-full bg-warning'
                              : 'h-full rounded-full bg-info'
                        }
                        style={{ width: `${confidence}%` }}
                      />
                    </div>

                    {topic.evidence.length > 0 ? (
                      <ul className="mt-3 flex flex-wrap gap-1.5">
                        {topic.evidence.map((fact) => (
                          <li
                            key={fact}
                            className="rounded-lg bg-ink-900 px-2 py-1 text-[0.7rem] text-ink-300"
                          >
                            {fact}
                          </li>
                        ))}
                      </ul>
                    ) : null}

                    {topic.suggested_action ? (
                      <p className="mt-3 text-xs text-ink-400">
                        <span className="font-medium text-ink-300">Sugerencia: </span>
                        {topic.suggested_action}
                      </p>
                    ) : null}

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        leftIcon={<MessageSquare className="size-3.5" />}
                        onClick={() => askAi(topic.topic, topic.course_name)}
                      >
                        Preguntar a la IA
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        leftIcon={<Sparkles className="size-3.5" />}
                        onClick={() => navigate('/flashcards')}
                      >
                        Practicar flashcards
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate('/planner')}
                      >
                        Generar plan
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Recomendaciones rápidas"
          description="Acciones sugeridas según tu actividad reciente."
        />
        <CardBody className="pt-0">
          {recs.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 2 }, (_, index) => (
                <Skeleton key={index} className="h-16" />
              ))}
            </div>
          ) : recommendations.length === 0 ? (
            <EmptyState
              icon={<BrainCircuit className="size-5" />}
              title="Sin recomendaciones activas"
              description="Cuando detectemos algo urgente aparecerá aquí."
            />
          ) : (
            <ul className="divide-y divide-ink-850">
              {recommendations.map((rec) => (
                <li key={rec.id} className="flex flex-wrap items-start gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-ink-100">{rec.title}</p>
                      <Badge
                        tone={
                          rec.priority === 'high' || rec.priority === 'urgent'
                            ? 'danger'
                            : rec.priority === 'medium'
                              ? 'warning'
                              : 'info'
                        }
                      >
                        {rec.priority}
                      </Badge>
                      {rec.is_read ? <Check className="size-3.5 text-success" /> : null}
                    </div>
                    <p className="mt-0.5 text-xs text-ink-400">{rec.message}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {rec.cta_path ? (
                      <Link
                        to={rec.cta_path}
                        className="inline-flex items-center gap-1 rounded-lg bg-flame-400 px-3 py-1.5 text-xs font-medium text-ink-950 transition hover:bg-flame-300"
                      >
                        {rec.cta_label ?? 'Ver'}
                        <ArrowRight className="size-3" />
                      </Link>
                    ) : null}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void resolveRec(rec.id, 'read')}
                    >
                      <Check className="size-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void resolveRec(rec.id, 'dismiss')}
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
