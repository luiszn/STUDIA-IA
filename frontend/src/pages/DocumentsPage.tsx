import { useEffect, useRef, useState, type DragEvent } from 'react'
import { toast } from 'sonner'

import {
  AlertTriangle,
  FilePlus2,
  FileText,
  Loader2,
  Sparkles,
  Trash2,
  UploadCloud,
} from 'lucide-react'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button, IconButton } from '@/components/ui/Button'
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  Modal,
  Skeleton,
} from '@/components/ui/Card'
import { Select } from '@/components/ui/Input'
import { cn, formatBytes, formatDate } from '@/lib/format'
import { useCourses, useDeleteDocument, useDocuments, useSummarizeDocument, useUploadDocument } from '@/lib/queries'
import type { DocumentRead, SummaryResult } from '@/lib/types'

const STATUS_STYLE: Record<string, { tone: 'neutral' | 'success' | 'warning' | 'danger' | 'info'; label: string }> = {
  uploaded: { tone: 'neutral', label: 'Subido' },
  processing: { tone: 'info', label: 'Indexando…' },
  ready: { tone: 'success', label: 'Listo' },
  failed: { tone: 'danger', label: 'Error' },
}

const ACCEPTED = '.pdf,.docx,.txt'

export default function DocumentsPage() {
  const [courseId, setCourseId] = useState('')
  const [dragging, setDragging] = useState(false)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DocumentRead | null>(null)
  const [summary, setSummary] = useState<SummaryResult | null>(null)

  const inputRef = useRef<HTMLInputElement>(null)

  const filters = courseId ? { course_id: courseId } : {}
  const [poll, setPoll] = useState<number | false>(false)
  const documents = useDocuments(filters, { refetchInterval: poll })
  const courses = useCourses()
  const upload = useUploadDocument()
  const remove = useDeleteDocument()
  const summarize = useSummarizeDocument()

  const docs = documents.data ?? []
  const hasProcessing = docs.some((doc) => doc.status === 'processing')

  useEffect(() => {
    setPoll(hasProcessing ? 3000 : false)
  }, [hasProcessing])

  const doUpload = async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    if (courseId) form.append('course_id', courseId)
    try {
      const created = await upload.mutateAsync(form)
      toast.success(`“${created.title}” subido — indexando contenido…`)
      setPendingFile(null)
      void documents.refetch()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo subir el archivo')
    }
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (!file) return
    if (!ACCEPTED.split(',').some((ext) => file.name.toLowerCase().endsWith(ext))) {
      toast.error('Formato no soportado. Usa PDF, DOCX o TXT.')
      return
    }
    setPendingFile(file)
  }

  const runSummary = async (doc: DocumentRead) => {
    setSummary(null)
    try {
      const result = await summarize.mutateAsync({ document_ids: [doc.id], style: 'exam' })
      setSummary(result)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'No se pudo generar el resumen')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documentos"
        description="Sube tu material y la IA lo indexa para el asistente y las flashcards."
        actions={
          <div className="w-48">
            <Select value={courseId} onChange={(event) => setCourseId(event.target.value)} aria-label="Filtrar por curso">
              <option value="">Todos los cursos</option>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code} — {course.name}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click()
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition',
          dragging
            ? 'border-flame-400 bg-flame-400/8 scale-[1.01]'
            : 'border-ink-700 bg-ink-900/50 hover:border-flame-400/60 hover:bg-ink-900',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) void doUpload(file)
            event.target.value = ''
          }}
        />
        {upload.isPending ? (
          <Loader2 className="size-8 animate-spin text-flame-400" />
        ) : (
          <UploadCloud className={cn('size-8', dragging ? 'text-flame-400' : 'text-ink-400')} />
        )}
        <div>
          <p className="text-sm font-medium text-ink-100">
            {upload.isPending ? 'Subiendo e indexando…' : 'Arrastra un PDF, DOCX o TXT aquí'}
          </p>
          <p className="mt-1 text-xs text-ink-400">
            o haz clic para elegirlo · máx. 20 MB · el índice RAG se genera automáticamente
          </p>
        </div>
      </div>

      {pendingFile ? (
        <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <FilePlus2 className="size-5 shrink-0 text-flame-300" />
            <div className="min-w-0">
              <p className="truncate text-sm text-ink-100">{pendingFile.name}</p>
              <p className="text-xs text-ink-400">{formatBytes(pendingFile.size)}</p>
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="ghost" size="sm" onClick={() => setPendingFile(null)}>
              Cancelar
            </Button>
            <Button size="sm" isLoading={upload.isPending} onClick={() => void doUpload(pendingFile)}>
              Subir e indexar
            </Button>
          </div>
        </Card>
      ) : null}

      {documents.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-20" />
          ))}
        </div>
      ) : documents.isError ? (
        <ErrorState onRetry={() => void documents.refetch()} />
      ) : docs.length === 0 ? (
        <EmptyState
          icon={<FileText className="size-5" />}
          title="Sin documentos"
          description="Sube apuntes, guías o lecturas en PDF, DOCX o TXT para desbloquear el RAG."
        />
      ) : (
        <ul className="space-y-3">
          {docs.map((doc) => {
            const status = STATUS_STYLE[doc.status] ?? STATUS_STYLE.uploaded
            return (
              <li key={doc.id}>
                <Card className="group flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
                  <span
                    className={cn(
                      'grid size-11 shrink-0 place-items-center rounded-xl',
                      doc.status === 'ready'
                        ? 'bg-success/12 text-success'
                        : doc.status === 'failed'
                          ? 'bg-danger/12 text-danger'
                          : 'bg-ink-800 text-ink-300',
                    )}
                  >
                    <FileText className="size-5" />
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium text-ink-100">{doc.title}</p>
                      <Badge tone={status.tone}>
                        {doc.status === 'processing' ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : null}
                        {status.label}
                      </Badge>
                      {doc.course ? <Badge>{doc.course.code}</Badge> : null}
                    </div>
                    <p className="mt-1 truncate text-xs text-ink-400">
                      {doc.filename} · {formatBytes(doc.size_bytes)}
                      {doc.page_count ? ` · ${doc.page_count} pág.` : ''}
                      {doc.chunk_count ? ` · ${doc.chunk_count} fragmentos indexados` : ''} ·{' '}
                      {formatDate(doc.created_at)}
                    </p>
                    {doc.status === 'failed' && doc.error_message ? (
                      <p className="mt-1.5 flex items-start gap-1.5 text-xs text-danger">
                        <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                        {doc.error_message}
                      </p>
                    ) : null}
                    {doc.summary ? (
                      <p className="mt-1.5 line-clamp-2 text-xs text-ink-400">{doc.summary}</p>
                    ) : null}
                  </div>

                  <div className="flex shrink-0 items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      leftIcon={<Sparkles className="size-3.5" />}
                      disabled={doc.status !== 'ready' || summarize.isPending}
                      onClick={() => void runSummary(doc)}
                    >
                      Resumir
                    </Button>
                    <IconButton
                      label="Eliminar documento"
                      className="opacity-0 transition group-hover:opacity-100"
                      onClick={() => setDeleteTarget(doc)}
                    >
                      <Trash2 className="size-4" />
                    </IconButton>
                  </div>
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar documento"
        description="Se borrará del índice RAG y el asistente dejará de citarlo."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              isLoading={remove.isPending}
              onClick={() => {
                if (!deleteTarget) return
                void remove.mutateAsync(deleteTarget.id).then(
                  () => {
                    toast.success('Documento eliminado')
                    setDeleteTarget(null)
                  },
                  () => toast.error('No se pudo eliminar'),
                )
              }}
            >
              Eliminar
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-300">
          ¿Seguro que quieres eliminar <strong className="text-ink-100">{deleteTarget?.title}</strong>?
        </p>
      </Modal>

      <Modal
        open={Boolean(summary)}
        onClose={() => setSummary(null)}
        title="Resumen generado por IA"
        description="Puedes copiarlo o usarlo como base para tus apuntes."
        size="lg"
        footer={
          <Button
            variant="outline"
            onClick={() => {
              if (summary) void navigator.clipboard.writeText(summary.summary)
              toast.success('Resumen copiado')
            }}
          >
            Copiar resumen
          </Button>
        }
      >
        {summarize.isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : summary ? (
          <div className="markdown max-h-[60vh] overflow-y-auto">
            {summary.summary.split('\n').map((line, index) =>
              line.trim() ? <p key={index} className="mb-2 text-sm text-ink-200">{line}</p> : null,
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
