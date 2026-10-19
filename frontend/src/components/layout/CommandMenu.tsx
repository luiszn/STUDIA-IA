import { useState } from 'react'
import { Command } from 'cmdk'
import { useNavigate } from 'react-router-dom'
import {
  BrainCircuit,
  CalendarDays,
  ClipboardList,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Layers,
  LineChart,
  MessageSquareText,
  NotebookPen,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react'

import { useSearch } from '@/lib/queries'

interface CommandOption {
  id: string
  label: string
  hint?: string
  icon: typeof Search
  path?: string
}

const NAV_OPTIONS: CommandOption[] = [
  { id: 'nav-dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/app' },
  { id: 'nav-courses', label: 'Cursos', icon: GraduationCap, path: '/app/courses' },
  { id: 'nav-tasks', label: 'Tareas', icon: ClipboardList, path: '/app/tasks' },
  { id: 'nav-exams', label: 'Exámenes', icon: NotebookPen, path: '/app/exams' },
  { id: 'nav-grades', label: 'Notas', icon: LineChart, path: '/app/grades' },
  { id: 'nav-documents', label: 'Documentos', icon: FileText, path: '/app/documents' },
  { id: 'nav-flashcards', label: 'Flashcards', icon: Layers, path: '/app/flashcards' },
  { id: 'nav-planner', label: 'Planificador', icon: Sparkles, path: '/app/planner' },
  { id: 'nav-calendar', label: 'Calendario', icon: CalendarDays, path: '/app/calendar' },
  { id: 'nav-ai', label: 'Asistente IA', icon: MessageSquareText, path: '/app/ai' },
  { id: 'nav-weak-topics', label: 'Temas débiles', icon: BrainCircuit, path: '/app/weak-topics' },
  { id: 'nav-settings', label: 'Ajustes', icon: Settings, path: '/app/settings' },
]

const ACTIONS: CommandOption[] = [
  { id: 'act-task', label: 'Nueva tarea', hint: 'Tareas', icon: ClipboardList, path: '/app/tasks' },
  { id: 'act-exam', label: 'Nuevo examen', hint: 'Exámenes', icon: NotebookPen, path: '/app/exams' },
  { id: 'act-grade', label: 'Añadir nota', hint: 'Notas', icon: LineChart, path: '/app/grades' },
  { id: 'act-doc', label: 'Subir documento', hint: 'Documentos', icon: FileText, path: '/app/documents' },
  { id: 'act-flashcards', label: 'Repasar flashcards', hint: 'Flashcards', icon: Layers, path: '/app/flashcards' },
  { id: 'act-chat', label: 'Preguntar a la IA', hint: 'Asistente', icon: MessageSquareText, path: '/app/ai' },
]

function CommandOptionRow({ option }: { option: CommandOption }) {
  const Icon = option.icon
  return (
    <div className="flex items-center gap-3">
      <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-ink-800 text-ink-300">
        <Icon className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm text-ink-100">{option.label}</span>
        {option.hint ? <span className="block truncate text-xs text-ink-500">{option.hint}</span> : null}
      </span>
    </div>
  )
}

interface CommandMenuProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CommandMenu({ open, onOpenChange }: CommandMenuProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const { data: searchResult } = useSearch(query, open && query.trim().length >= 2)
  const results = searchResult?.results ?? []

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]">
      <button
        type="button"
        aria-label="Cerrar paleta"
        className="absolute inset-0 bg-ink-950/75 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <Command
        autoFocus
        onKeyDown={(event) => {
          if (event.key === 'Escape') onOpenChange(false)
        }}
        shouldFilter
        className="relative max-h-[60vh] w-[92vw] max-w-xl overflow-hidden rounded-2xl border border-ink-700 bg-ink-900 shadow-panel"
      >
        <div className="flex items-center gap-2 border-b border-ink-800 px-4">
          <Search className="size-4 text-ink-500" />
          <Command.Input
            value={query}
            onValueChange={setQuery}
            placeholder="Buscar cursos, tareas, documentos…"
            className="h-12 w-full bg-transparent text-sm text-ink-100 outline-none placeholder:text-ink-500"
          />
          <kbd className="rounded-md border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-[0.65rem] text-ink-400">
            esc
          </kbd>
        </div>

        <Command.List className="max-h-[52vh] overflow-y-auto p-2">
          <Command.Empty className="px-4 py-8 text-center text-sm text-ink-400">
            Sin resultados para “{query}”.
          </Command.Empty>

          {query.trim() === '' ? (
            <>
              <Command.Group heading="Navegar">
                {NAV_OPTIONS.map((option) => (
                  <Command.Item
                    key={option.id}
                    value={`nav ${option.label} ${option.hint ?? ''}`}
                    onSelect={() => {
                      onOpenChange(false)
                      navigate(option.path ?? '/app')
                    }}
                    className="cursor-pointer rounded-xl px-2.5 py-2 data-[selected=true]:bg-ink-800"
                  >
                    <CommandOptionRow option={option} />
                  </Command.Item>
                ))}
              </Command.Group>
              <Command.Group heading="Acciones">
                {ACTIONS.map((option) => (
                  <Command.Item
                    key={option.id}
                    value={`action ${option.label} ${option.hint ?? ''}`}
                    onSelect={() => {
                      onOpenChange(false)
                      navigate(option.path ?? '/app')
                    }}
                    className="cursor-pointer rounded-xl px-2.5 py-2 data-[selected=true]:bg-ink-800"
                  >
                    <CommandOptionRow option={option} />
                  </Command.Item>
                ))}
              </Command.Group>
            </>
          ) : null}

          {query.trim() !== '' ? (
            <Command.Group heading="Resultados">
              {results.map((result) => (
                <Command.Item
                  key={`${result.type}-${result.id}-${result.path}`}
                  value={`result ${result.title} ${result.subtitle ?? ''}`}
                  onSelect={() => {
                    onOpenChange(false)
                    setQuery('')
                    navigate(result.path)
                  }}
                  className="cursor-pointer rounded-xl px-2.5 py-2 data-[selected=true]:bg-ink-800"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-ink-100">{result.title}</span>
                      {result.subtitle ? (
                        <span className="block truncate text-xs text-ink-500">{result.subtitle}</span>
                      ) : null}
                    </span>
                    <span className="shrink-0 rounded-md bg-ink-800 px-1.5 py-0.5 text-[0.65rem] tracking-wide text-ink-400 uppercase">
                      {result.type}
                    </span>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          ) : null}
        </Command.List>
      </Command>
    </div>
  )
}