import { useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft,
  Layers,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Badge,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  Modal,
  ProgressBar,
  Skeleton,
  Tabs,
} from '@/components/ui/Card'
import { Field, Input, Select, Textarea } from '@/components/ui/Input'
import { cn, pluralize } from '@/lib/format'
import {
  useCreateFlashcard,
  useDecks,
  useDeleteFlashcard,
  useDocuments,
  useDueCards,
  useFlashcards,
  useGenerateFlashcards,
  useReviewFlashcard,
} from '@/lib/queries'
import type { FlashcardRead } from '@/lib/types'

type AnswerKey = 'again' | 'hard' | 'good' | 'easy'

const ANSWERS: { key: AnswerKey; label: string; quality: number; className: string }[] = [
  { key: 'again', label: 'Otra vez', quality: 1, className: 'border-danger/40 text-danger hover:bg-danger/15' },
  { key: 'hard', label: 'Difícil', quality: 3, className: 'border-warning/40 text-warning hover:bg-warning/15' },
  { key: 'good', label: 'Bien', quality: 4, className: 'border-info/40 text-info hover:bg-info/15' },
  { key: 'easy', label: 'Fácil', quality: 5, className: 'border-success/40 text-success hover:bg-success/15' },
]

interface Session {
  queue: FlashcardRead[]
  total: number
  reviewed: number
  flipped: boolean
  stats: Record<AnswerKey, number>
  lastMessage: string | null
}

function ReviewSession({
  session,
  onFlip,
  onAnswer,
  onExit,
  isPending,
}: {
  session: Session
  onFlip: () => void
  onAnswer: (answer: (typeof ANSWERS)[number]) => void
  onExit: () => void
  isPending: boolean
}) {
  const card = session.queue[0]
  const progress = Math.round((session.reviewed / Math.max(session.total, 1)) * 100)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return
      if (event.key === ' ') {
        event.preventDefault()
        onFlip()
        return
      }
      if (session.flipped && ['1', '2', '3', '4'].includes(event.key)) {
        onAnswer(ANSWERS[Number(event.key) - 1])
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [session.flipped, onFlip, onAnswer])

  if (!card) {
    const total = Object.values(session.stats).reduce((sum, value) => sum + value, 0)
    return (
      <div className="mx-auto max-w-xl py-10 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-success/12 text-success">
          <Layers className="size-7" />
        </span>
        <h2 className="mt-5 font-display text-2xl font-semibold">¡Repaso completado!</h2>
        <p className="mt-1 text-sm text-ink-400">
          {pluralize(total, 'tarjeta revisada', 'tarjetas revisadas')} en esta sesión.
        </p>
        <div className="mt-6 grid grid-cols-4 gap-3">
          {ANSWERS.map((answer) => (
            <div key={answer.key} className="rounded-xl border border-ink-750 bg-ink-900/70 p-3">
              <p className="font-display text-xl font-semibold">{session.stats[answer.key]}</p>
              <p className="mt-0.5 text-xs text-ink-400">{answer.label}</p>
            </div>
          ))}
        </div>
        <Button className="mt-6" onClick={onExit}>
          Volver a flashcards
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <IconButton label="Salir del repaso" onClick={onExit}>
          <ChevronLeft className="size-4.5" />
        </IconButton>
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex items-center justify-between text-xs text-ink-400">
            <span>
              {session.reviewed} de {session.total} {session.reviewed === 1 ? 'revisada' : 'revisadas'}
            </span>
            <span>{progress}%</span>
          </div>
          <ProgressBar value={progress} />
        </div>
      </div>

      <div className="flip-scene">
        <button
          type="button"
          onClick={onFlip}
          aria-label={session.flipped ? 'Ver pregunta' : 'Ver respuesta'}
          className={cn('flip-card block h-72 w-full text-left sm:h-80', session.flipped && 'is-flipped')}
        >
          <div className="flip-face panel flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
            <Badge tone="flame">{card.deck}</Badge>
            <p className="font-display text-xl leading-snug font-semibold text-ink-100 sm:text-2xl">
              {card.front}
            </p>
            <span className="text-xs text-ink-500">Toca la tarjeta para ver la respuesta</span>
          </div>
          <div className="flip-face flip-back panel flex h-full flex-col items-center justify-center gap-4 border-flame-400/40 p-8 text-center">
            <span className="text-[0.7rem] tracking-widest text-ink-500 uppercase">Respuesta</span>
            <p className="text-lg leading-relaxed text-ink-100 sm:text-xl">{card.back}</p>
            {card.explanation ? (
              <p className="max-w-md text-sm text-ink-400">{card.explanation}</p>
            ) : null}
          </div>
        </button>
      </div>

      {session.lastMessage ? (
        <p className="text-center text-xs text-flame-300">{session.lastMessage}</p>
      ) : null}

      {session.flipped ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {ANSWERS.map((answer) => (
            <button
              key={answer.key}
              type="button"
              disabled={isPending}
              onClick={() => onAnswer(answer)}
              className={cn(
                'rounded-xl border px-3 py-3 text-sm font-medium transition disabled:opacity-50',
                answer.className,
              )}
            >
              {answer.label}
            </button>
          ))}
        </div>
      ) : (
        <Button variant="secondary" className="w-full" onClick={onFlip}>
          Mostrar respuesta
        </Button>
      )}

      <p className="text-center text-[0.7rem] text-ink-500">
        Espacio para girar · 1-4 para calificar
      </p>
    </div>
  )
}

export default function FlashcardsPage() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'decks' | 'all'>('decks')
  const [session, setSession] = useState<Session | null>(null)

  const [newCardOpen, setNewCardOpen] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)

  const decks = useDecks()
  const due = useDueCards()
  const all = useFlashcards({ limit: 100 })
  const documents = useDocuments()

  const createCard = useCreateFlashcard()
  const reviewCard = useReviewFlashcard()
  const deleteCard = useDeleteFlashcard()
  const generateCards = useGenerateFlashcards()

  const [cardForm, setCardForm] = useState({
    front: '',
    back: '',
    explanation: '',
    deck: 'General',
    difficulty: 'medium',
  })
  const [genForm, setGenForm] = useState({ document_id: '', deck: 'General', count: 12, focus: '' })

  const dueCards = due.data ?? []
  const dueByDeck = useMemo(() => {
    const map = new Map<string, FlashcardRead[]>()
    for (const card of dueCards) {
      const list = map.get(card.deck) ?? []
      list.push(card)
      map.set(card.deck, list)
    }
    return map
  }, [dueCards])

  const startSession = (cards: FlashcardRead[]) => {
    if (cards.length === 0) {
      toast.info('No hay tarjetas pendientes en este mazo')
      return
    }
    setSession({
      queue: cards,
      total: cards.length,
      reviewed: 0,
      flipped: false,
      stats: { again: 0, hard: 0, good: 0, easy: 0 },
      lastMessage: null,
    })
  }

  const handleAnswer = async (answer: (typeof ANSWERS)[number]) => {
    if (!session || !session.flipped || reviewCard.isPending) return
    const card = session.queue[0]
    try {
      const result = await reviewCard.mutateAsync({ card_id: card.id, quality: answer.quality })
      setSession((current) => {
        if (!current) return current
        const rest = current.queue.slice(1)
        const queue = answer.quality < 3 ? [...rest, card] : rest
        return {
          ...current,
          queue,
          total: Math.max(current.total, current.reviewed + queue.length),
          reviewed: current.reviewed + 1,
          flipped: false,
          stats: { ...current.stats, [answer.key]: current.stats[answer.key] + 1 },
          lastMessage: result.message,
        }
      })
      if (answer.quality < 3) {
        toast.warning('La tarjeta volverá al final de la cola')
      }
      void queryClient.invalidateQueries({ queryKey: ['search'] })
    } catch {
      toast.error('No se pudo registrar la revisión')
    }
  }

  const handleSubmitNewCard = async () => {
    if (!cardForm.front.trim() || !cardForm.back.trim()) {
      toast.error('Completa el anverso y el reverso')
      return
    }
    try {
      await createCard.mutateAsync({
        front: cardForm.front.trim(),
        back: cardForm.back.trim(),
        explanation: cardForm.explanation.trim() || null,
        deck: cardForm.deck.trim() || 'General',
        difficulty: cardForm.difficulty,
      })
      toast.success('Tarjeta creada')
      setNewCardOpen(false)
      setCardForm({ front: '', back: '', explanation: '', deck: 'General', difficulty: 'medium' })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo crear la tarjeta')
    }
  }

  const handleGenerate = async () => {
    if (!genForm.document_id) {
      toast.error('Selecciona un documento')
      return
    }
    try {
      const result = await generateCards.mutateAsync({
        document_ids: [genForm.document_id],
        count: Number(genForm.count),
        deck: genForm.deck.trim() || 'General',
        focus: genForm.focus.trim() || undefined,
        save: true,
      })
      toast.success(`${result.created} flashcards generadas`)
      setGenerateOpen(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudieron generar las flashcards')
    }
  }

  if (session) {
    return (
      <div className="space-y-6">
        <ReviewSession
          session={session}
          isPending={reviewCard.isPending}
          onFlip={() => setSession((current) => (current ? { ...current, flipped: !current.flipped } : current))}
          onAnswer={(answer) => void handleAnswer(answer)}
          onExit={() => setSession(null)}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Flashcards"
        description="Repaso activo con algoritmo SM-2."
        actions={
          <>
            <Button variant="outline" leftIcon={<Wand2 className="size-4" />} onClick={() => setGenerateOpen(true)}>
              Generar con IA
            </Button>
            <Button leftIcon={<Plus className="size-4" />} onClick={() => setNewCardOpen(true)}>
              Nueva tarjeta
            </Button>
          </>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs tracking-widest text-ink-500 uppercase">Pendientes hoy</p>
            <p className="mt-1 font-display text-3xl font-semibold text-flame-300">
              {due.isLoading ? '…' : dueCards.length}
            </p>
            <p className="mt-1 text-sm text-ink-400">
              {dueCards.length === 0
                ? 'Estás al día. ¡Buen trabajo!'
                : `Listas para repasar · ${pluralize(Object.keys(dueByDeck).length, 'mazo', 'mazos')} con pendientes`}
            </p>
          </div>
          <Button
            size="lg"
            disabled={dueCards.length === 0 || due.isLoading}
            leftIcon={<Layers className="size-4.5" />}
            onClick={() => startSession(dueCards)}
          >
            Repasar ahora
          </Button>
        </div>
      </Card>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: 'decks', label: 'Mazos', count: decks.data?.length },
          { value: 'all', label: 'Todas', count: all.data?.meta.total },
        ]}
      />

      {tab === 'decks' ? (
        decks.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }, (_, index) => (
              <Skeleton key={index} className="h-36" />
            ))}
          </div>
        ) : decks.isError ? (
          <ErrorState onRetry={() => void decks.refetch()} />
        ) : (decks.data ?? []).length === 0 ? (
          <EmptyState
            icon={<Layers className="size-5" />}
            title="Aún no tienes mazos"
            description="Crea tarjetas manualmente o genera un mazo desde tus documentos con IA."
            action={
              <Button leftIcon={<Plus className="size-4" />} onClick={() => setNewCardOpen(true)}>
                Crear primera tarjeta
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {(decks.data ?? []).map((deck) => {
              const pending = dueByDeck.get(deck.name) ?? []
              return (
                <Card key={`${deck.name}-${deck.course_id ?? 'x'}`} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-display text-base font-semibold text-ink-100">
                        {deck.name}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-ink-400">
                        {deck.course_name ?? 'Sin curso'}
                      </p>
                    </div>
                    {pending.length > 0 ? <Badge tone="flame">{pending.length} hoy</Badge> : null}
                  </div>
                  <dl className="mt-4 grid grid-cols-4 gap-2 text-center">
                    {[
                      { label: 'Total', value: deck.total },
                      { label: 'Nuevas', value: deck.new },
                      { label: 'Hoy', value: deck.due_today },
                      { label: 'Dominadas', value: deck.mastered },
                    ].map((item) => (
                      <div key={item.label} className="rounded-lg bg-ink-850 py-2">
                        <dd className="text-sm font-semibold text-ink-100">{item.value}</dd>
                        <dt className="text-[0.65rem] text-ink-500">{item.label}</dt>
                      </div>
                    ))}
                  </dl>
                  <Button
                    variant={pending.length > 0 ? 'primary' : 'secondary'}
                    size="sm"
                    className="mt-4 w-full"
                    disabled={pending.length === 0}
                    onClick={() => startSession(pending)}
                  >
                    {pending.length > 0 ? `Repasar ${pending.length}` : 'Sin pendientes'}
                  </Button>
                </Card>
              )
            })}
          </div>
        )
      ) : all.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} className="h-16" />
          ))}
        </div>
      ) : all.isError ? (
        <ErrorState onRetry={() => void all.refetch()} />
      ) : (all.data?.items ?? []).length === 0 ? (
        <EmptyState
          icon={<Layers className="size-5" />}
          title="Sin tarjetas"
          description="Genera flashcards con IA o crea manualmente."
        />
      ) : (
        <Card>
          <CardBody className="pt-5">
            <ul className="divide-y divide-ink-850">
              {(all.data?.items ?? []).map((card) => (
                <li key={card.id} className="group flex items-start gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-ink-100">{card.front}</p>
                    <p className="mt-0.5 line-clamp-1 text-xs text-ink-400">{card.back}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <Badge>{card.deck}</Badge>
                      <Badge tone={card.status === 'mastered' ? 'success' : card.status === 'new' ? 'info' : 'neutral'}>
                        {card.status}
                      </Badge>
                      {card.next_review_at ? (
                        <span className="text-[0.7rem] text-ink-500">
                          próxima: {new Date(card.next_review_at).toLocaleDateString('es')}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <IconButton
                    label="Eliminar tarjeta"
                    className="opacity-0 transition group-hover:opacity-100"
                    onClick={() => {
                      void deleteCard.mutateAsync(card.id).then(
                        () => toast.success('Tarjeta eliminada'),
                        () => toast.error('No se pudo eliminar'),
                      )
                    }}
                  >
                    <Trash2 className="size-4" />
                  </IconButton>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <Modal
        open={newCardOpen}
        onClose={() => setNewCardOpen(false)}
        title="Nueva tarjeta"
        description="Escribe el anverso (pregunta) y el reverso (respuesta)."
        footer={
          <>
            <Button variant="ghost" onClick={() => setNewCardOpen(false)}>
              Cancelar
            </Button>
            <Button isLoading={createCard.isPending} onClick={() => void handleSubmitNewCard()}>
              Crear tarjeta
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Anverso" required>
            <Textarea
              rows={3}
              value={cardForm.front}
              onChange={(event) => setCardForm({ ...cardForm, front: event.target.value })}
              placeholder="¿Qué es el protocolo TCP?"
            />
          </Field>
          <Field label="Reverso" required>
            <Textarea
              rows={3}
              value={cardForm.back}
              onChange={(event) => setCardForm({ ...cardForm, back: event.target.value })}
              placeholder="Un protocolo de transporte confiable…"
            />
          </Field>
          <Field label="Explicación (opcional)">
            <Input
              value={cardForm.explanation}
              onChange={(event) => setCardForm({ ...cardForm, explanation: event.target.value })}
              placeholder="Detalle extra para recordar"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Mazo">
              <Input
                list="deck-list"
                value={cardForm.deck}
                onChange={(event) => setCardForm({ ...cardForm, deck: event.target.value })}
              />
              <datalist id="deck-list">
                {(decks.data ?? []).map((deck) => (
                  <option key={deck.name} value={deck.name} />
                ))}
              </datalist>
            </Field>
            <Field label="Dificultad">
              <Select
                value={cardForm.difficulty}
                onChange={(event) => setCardForm({ ...cardForm, difficulty: event.target.value })}
              >
                <option value="easy">Fácil</option>
                <option value="medium">Media</option>
                <option value="hard">Difícil</option>
              </Select>
            </Field>
          </div>
        </div>
      </Modal>

      <Modal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        title="Generar flashcards con IA"
        description="La IA leerá el documento y creará el mazo por ti."
        footer={
          <>
            <Button variant="ghost" onClick={() => setGenerateOpen(false)}>
              Cancelar
            </Button>
            <Button
              isLoading={generateCards.isPending}
              leftIcon={<Sparkles className="size-4" />}
              onClick={() => void handleGenerate()}
            >
              Generar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Documento" required>
            <Select
              value={genForm.document_id}
              onChange={(event) => setGenForm({ ...genForm, document_id: event.target.value })}
            >
              <option value="">Selecciona un documento…</option>
              {(documents.data ?? [])
                .filter((doc) => doc.status === 'ready')
                .map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title}
                  </option>
                ))}
            </Select>
          </Field>
          {(documents.data ?? []).filter((doc) => doc.status === 'ready').length === 0 &&
          !documents.isLoading ? (
            <p className="rounded-xl border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
              Necesitas al menos un documento indexado (estado “listo”). Súbelo desde Documentos.
            </p>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Mazo">
              <Input
                value={genForm.deck}
                onChange={(event) => setGenForm({ ...genForm, deck: event.target.value })}
              />
            </Field>
            <Field label="Cantidad">
              <Input
                type="number"
                min={1}
                max={60}
                value={genForm.count}
                onChange={(event) => setGenForm({ ...genForm, count: Number(event.target.value) })}
              />
            </Field>
          </div>
          <Field label="Enfoque (opcional)">
            <Input
              value={genForm.focus}
              onChange={(event) => setGenForm({ ...genForm, focus: event.target.value })}
              placeholder="p. ej. capítulos 3 y 4"
            />
          </Field>
          {generateCards.isPending ? (
            <p className="flex items-center gap-2 text-xs text-ink-400">
              <Loader2 className="size-3.5 animate-spin" /> Generando tarjetas, esto puede tardar…
            </p>
          ) : null}
        </div>
      </Modal>
    </div>
  )
}
