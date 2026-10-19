import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  BrainCircuit,
  Check,
  Copy,
  FileText,
  Loader2,
  MessageSquareText,
  Plus,
  SendHorizonal,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge, Skeleton } from '@/components/ui/Card'
import { IconButton } from '@/components/ui/Button'
import { api } from '@/lib/api'
import { cn } from '@/lib/format'
import { keys, useAiStatus, useConversation, useConversations, useSendMessage } from '@/lib/queries'
import type { SourceCitation } from '@/lib/types'

const SUGGESTIONS = [
  'Explícame el tema más difícil de esta semana',
  'Resume mis documentos de la carrera',
  '¿Qué debo repasar antes del próximo examen?',
  'Genera preguntas de examen sobre mis apuntes',
]

function SourcesList({ sources }: { sources: SourceCitation[] | null | undefined }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex items-center gap-1.5 text-xs text-ink-400 transition hover:text-flame-300"
      >
        <FileText className="size-3.5" />
        {sources.length} {sources.length === 1 ? 'fuente' : 'fuentes'}
        <span className="text-ink-500">{open ? '· ocultar' : '· ver'}</span>
      </button>
      {open ? (
        <ul className="mt-2 space-y-1.5">
          {sources.map((source, index) => (
            <li
              key={`${source.document_id}-${index}`}
              className="rounded-lg border border-ink-800 bg-ink-900/70 px-3 py-2"
            >
              <p className="flex items-center gap-2 text-xs text-ink-200">
                <span className="truncate font-medium">{source.title || source.filename}</span>
                {source.page_number ? (
                  <span className="shrink-0 text-ink-500">p. {source.page_number}</span>
                ) : null}
                {typeof source.score === 'number' ? (
                  <span className="shrink-0 text-ink-500">{Math.round(source.score * 100)}%</span>
                ) : null}
              </p>
              {source.excerpt ? (
                <p className="mt-1 line-clamp-3 text-xs text-ink-400">{source.excerpt}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <IconButton
      label="Copiar respuesta"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        })
      }}
      className="size-7"
    >
      {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
    </IconButton>
  )
}

export default function AIChatPage() {
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()

  const activeId = params.get('conversation')
  const [input, setInput] = useState('')
  const [useRag, setUseRag] = useState(true)

  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: conversations = [], isLoading: loadingConversations } = useConversations()
  const { data: status } = useAiStatus()
  const { data: conversation, isLoading: loadingMessages } = useConversation(activeId ?? undefined)
  const sendMessage = useSendMessage()

  const messages = useMemo(
    () => (conversation?.messages ?? []).filter((message) => message.role !== 'system'),
    [conversation],
  )

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages.length, sendMessage.isPending])

  useEffect(() => {
    const preset = params.get('q')
    if (!preset) return
    setInput(preset)
    const next = new URLSearchParams(params)
    next.delete('q')
    setParams(next, { replace: true })
    textareaRef.current?.focus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = '0px'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }, [input])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || sendMessage.isPending) return
    setInput('')
    try {
      const response = await sendMessage.mutateAsync({ message, conversation_id: activeId ?? undefined, use_rag: useRag })
      await queryClient.invalidateQueries({ queryKey: keys.conversation(response.conversation_id) })
      setParams({ conversation: response.conversation_id }, { replace: !activeId })
    } catch (error) {
      setInput(message)
      toast.error(error instanceof Error ? error.message : 'No se pudo enviar el mensaje')
    }
  }

  const handleNewChat = () => {
    setParams({})
    setInput('')
    textareaRef.current?.focus()
  }

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/ai/conversations/${id}`)
      await queryClient.invalidateQueries({ queryKey: keys.conversations })
      if (activeId === id) setParams({})
      toast.success('Conversación eliminada')
    } catch {
      toast.error('No se pudo eliminar la conversación')
    }
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-3">
        <span className="text-xs font-semibold tracking-widest text-ink-500 uppercase">
          Conversaciones
        </span>
        <IconButton label="Nueva conversación" onClick={handleNewChat}>
          <Plus className="size-4" />
        </IconButton>
      </div>
      <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
        {loadingConversations ? (
          <div className="space-y-2 px-1">
            {Array.from({ length: 5 }, (_, index) => (
              <Skeleton key={index} className="h-11 w-full" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-ink-500">
            Aún no hay conversaciones. Haz tu primera pregunta.
          </p>
        ) : (
          conversations.map((item) => (
            <div
              key={item.id}
              className={cn(
                'group flex items-center gap-1 rounded-xl px-2 transition',
                activeId === item.id ? 'bg-flame-400/12' : 'hover:bg-ink-800/70',
              )}
            >
              <button
                type="button"
                onClick={() => setParams({ conversation: item.id })}
                className={cn(
                  'min-w-0 flex-1 truncate px-2 py-2.5 text-left text-sm transition',
                  activeId === item.id ? 'text-flame-200' : 'text-ink-300 hover:text-ink-100',
                )}
              >
                {item.title}
              </button>
              <button
                type="button"
                aria-label="Eliminar conversación"
                title="Eliminar conversación"
                onClick={() => void handleDelete(item.id)}
                className="hidden size-7 shrink-0 place-items-center rounded-lg text-ink-500 transition hover:bg-ink-750 hover:text-danger group-hover:grid"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))
        )}
      </nav>
      <div className="border-t border-ink-800 px-4 py-3">
        <p className="flex items-center gap-1.5 text-[0.7rem] text-ink-500">
          <Sparkles className="size-3" />
          {status?.available
            ? `${status.provider}${status.model ? ` · ${status.model}` : ''}`
            : 'Proveedor de IA no disponible'}
        </p>
      </div>
    </div>
  )

  const chatEmpty = (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-flame-400/12 text-flame-300">
        <BrainCircuit className="size-7" />
      </span>
      <div className="space-y-1.5">
        <h2 className="font-display text-xl font-semibold">¿En qué te ayudo hoy?</h2>
        <p className="max-w-md text-sm text-ink-400">
          Pregúntame sobre tus cursos, documentos o exámenes. Si el RAG está activo, responderé
          citando tus propios materiales.
        </p>
      </div>
      <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => {
              setInput(suggestion)
              textareaRef.current?.focus()
            }}
            className="rounded-xl border border-ink-700 bg-ink-900/60 px-3.5 py-2.5 text-left text-xs text-ink-300 transition hover:border-flame-400/50 hover:text-ink-100"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <div className="-m-4 flex h-[calc(100vh-7rem)] sm:-m-6 lg:-m-8">
      <aside
        className={cn(
          'hidden w-72 shrink-0 border-r border-ink-800 bg-ink-900/60 md:block',
        )}
      >
        {sidebar}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-13 shrink-0 items-center gap-2 border-b border-ink-800 px-3 sm:px-4">
          {activeId ? (
            <div className="md:hidden">
              <IconButton label="Volver" onClick={handleNewChat}>
                <ArrowLeft className="size-4.5" />
              </IconButton>
            </div>
          ) : null}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink-100">
              {activeId ? (conversation?.title ?? 'Conversación') : 'Nueva conversación'}
            </p>
            {activeId && conversation ? (
              <p className="truncate text-xs text-ink-500">
                {conversation.message_count} mensajes
                {conversation.course_name ? ` · ${conversation.course_name}` : ''}
                {conversation.used_rag ? ' · RAG activo' : ''}
              </p>
            ) : null}
          </div>
          {status?.available ? <Badge tone="success">{status.provider}</Badge> : <Badge tone="neutral">IA off</Badge>}
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          {!activeId ? (
            chatEmpty
          ) : loadingMessages ? (
            <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="ml-auto h-10 w-1/2" />
              <Skeleton className="h-24 w-3/4" />
            </div>
          ) : messages.length === 0 ? (
            chatEmpty
          ) : (
            <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn('flex flex-col gap-1.5', message.role === 'user' ? 'items-end' : 'items-start')}
                >
                  <div
                    className={cn(
                      'max-w-[92%] rounded-2xl px-4 py-2.5 text-sm',
                      message.role === 'user'
                        ? 'rounded-br-md bg-flame-400 font-medium text-ink-950'
                        : 'rounded-bl-md border border-ink-800 bg-ink-850 text-ink-100',
                    )}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    ) : (
                      <div className="markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                  {message.role === 'assistant' ? (
                    <div className="flex items-center gap-2 px-1">
                      <span className="text-[0.7rem] text-ink-500">
                        {message.provider}
                        {message.latency_ms ? ` · ${(message.latency_ms / 1000).toFixed(1)}s` : ''}
                      </span>
                      <CopyButton text={message.content} />
                    </div>
                  ) : null}
                  {message.role === 'assistant' ? (
                    <SourcesList sources={message.sources as SourceCitation[] | null} />
                  ) : null}
                </div>
              ))}
              {sendMessage.isPending ? (
                <div className="flex items-center gap-2 text-sm text-ink-400">
                  <Loader2 className="size-4 animate-spin text-flame-400" />
                  Pensando…
                </div>
              ) : null}
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-ink-800 bg-ink-950/90 px-3 py-3 sm:px-4">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setUseRag((value) => !value)}
                aria-pressed={useRag}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition',
                  useRag
                    ? 'border-flame-400/40 bg-flame-400/12 text-flame-200'
                    : 'border-ink-700 bg-ink-800 text-ink-400 hover:text-ink-200',
                )}
                title={useRag ? 'Responder con tus documentos' : 'Responder solo con el modelo'}
              >
                <MessageSquareText className="size-3.5" />
                RAG {useRag ? 'activado' : 'desactivado'}
              </button>
              <span className="hidden text-[0.7rem] text-ink-500 sm:block">
                Intro para enviar · Mayús+Intro para nueva línea
              </span>
            </div>
            <div className="flex items-end gap-2 rounded-2xl border border-ink-700 bg-ink-900 p-2 focus-within:border-flame-400/60">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void handleSend()
                  }
                }}
                rows={1}
                placeholder="Escribe tu pregunta…"
                className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => void handleSend()}
                disabled={!input.trim() || sendMessage.isPending}
                aria-label="Enviar mensaje"
                className="grid size-9 shrink-0 place-items-center rounded-xl bg-flame-400 text-ink-950 transition hover:bg-flame-300 disabled:opacity-40"
              >
                {sendMessage.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <SendHorizonal className="size-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
