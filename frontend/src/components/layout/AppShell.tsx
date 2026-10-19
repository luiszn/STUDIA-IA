import { LogOut, Menu, Search, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { IconButton, LinkButton } from '@/components/ui/Button'
import { useAiStatus, useSearch } from '@/lib/queries'
import { cn } from '@/lib/format'

import CommandMenu from './CommandMenu'

import { NavLink } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { LayoutDashboard, Settings, GraduationCap, ClipboardList, NotebookPen, LineChart, FileText, Layers, CalendarDays, BookOpen, MessageSquareText, BrainCircuit } from 'lucide-react'

export interface NavItem { to: string; label: string; icon: LucideIcon; end?: boolean; badge?: number }

export const PRIMARY_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/courses', label: 'Cursos', icon: GraduationCap },
  { to: '/app/tasks', label: 'Tareas', icon: ClipboardList },
  { to: '/app/exams', label: 'Exámenes', icon: NotebookPen },
  { to: '/app/grades', label: 'Notas', icon: LineChart },
  { to: '/app/documents', label: 'Documentos', icon: FileText },
]

export const STUDY_NAV: NavItem[] = [
  { to: '/app/flashcards', label: 'Flashcards', icon: Layers },
  { to: '/app/planner', label: 'Planificador', icon: Sparkles },
  { to: '/app/calendar', label: 'Calendario', icon: CalendarDays },
  { to: '/app/sessions', label: 'Sesiones', icon: BookOpen },
]

export const AI_NAV: NavItem[] = [
  { to: '/app/ai', label: 'Asistente', icon: MessageSquareText },
  { to: '/app/weak-topics', label: 'Temas débiles', icon: BrainCircuit },
]

export const NAV_GROUPS = [
  { title: 'Académico', items: PRIMARY_NAV },
  { title: 'Estudio', items: STUDY_NAV },
  { title: 'IA', items: AI_NAV },
]

export function NavItemLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = item.icon
  return (
    <NavLink to={item.to} end={item.end} onClick={onNavigate} className={({ isActive }) => cn('group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition', isActive ? 'bg-flame-400/12 text-flame-200' : 'text-ink-300 hover:bg-ink-800/70 hover:text-ink-100')}>
      {({ isActive }) => (
        <>
          <span className={cn('absolute inset-y-2 left-0 w-0.5 rounded-full bg-flame-400 transition-opacity', isActive ? 'opacity-100' : 'opacity-0')} />
          <Icon className={cn('size-4.5', isActive ? 'text-flame-300' : 'text-ink-400')} />
          <span className='flex-1 truncate'>{item.label}</span>
          {item.badge ? <span className='rounded-full bg-flame-400 px-1.5 py-0.5 text-[0.65rem] font-semibold text-ink-950'>{item.badge}</span> : null}
        </>
      )}
    </NavLink>
  )
}

export function SidebarFooter({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <NavLink to='/app/settings' onClick={onNavigate} className={({ isActive }) => cn('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition', isActive ? 'bg-ink-800 text-ink-100' : 'text-ink-400 hover:bg-ink-800/70 hover:text-ink-100')}>
      <Settings className='size-4.5' />
      Ajustes
    </NavLink>
  )
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to='/app' className='flex items-center gap-2.5'>
      <span className='grid size-9 place-items-center rounded-xl bg-flame-400 font-display text-lg font-bold text-ink-950 shadow-[0_8px_24px_-8px_rgb(255_122_26/0.8)]'>S</span>
      {!compact ? (<span className='font-display text-lg font-semibold tracking-tight'>STUDIA <span className='text-flame-400'>AI</span></span>) : null}
    </Link>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className='flex h-full flex-col gap-6 p-4'>
      <div className='px-1.5'>
        <Brand />
      </div>
      <nav className='min-h-0 flex-1 space-y-5 overflow-y-auto'>
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <p className='mb-1.5 px-3 text-[0.7rem] font-semibold tracking-widest text-ink-500 uppercase'>
              {group.title}
            </p>
            <div className='space-y-0.5'>
              {group.items.map((item) => (
                <NavItemLink key={item.to} item={item} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className='border-t border-ink-800 pt-3'>
        <SidebarFooter onNavigate={onNavigate} />
      </div>
    </div>
  )
}

export default function AppShell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)

  const searchWrapRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const { data: aiStatus } = useAiStatus()
  const trimmed = query.trim()
  const { data: searchResults, isFetching } = useSearch(trimmed, searchOpen)

  useEffect(() => {
    setDrawerOpen(false)
    setSearchOpen(false)
    setCommandOpen(false)
    setQuery('')
  }, [location.pathname])

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!searchWrapRef.current?.contains(event.target as Node)) setSearchOpen(false)
    }
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen((open) => !open)
      }
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setCommandOpen(false)
      }
    }
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const results = searchResults?.results ?? []

  return (
    <div className='flex min-h-screen bg-ink-950 text-ink-100'>
      <aside className='hidden w-64 shrink-0 border-r border-ink-800 bg-ink-900 lg:block'>
        <div className='sticky top-0 h-screen'>
          <SidebarContent />
        </div>
      </aside>

      {drawerOpen ? (
        <div className='fixed inset-0 z-50 lg:hidden'>
          <button
            type='button'
            aria-label='Cerrar menú'
            className='absolute inset-0 bg-ink-950/75 backdrop-blur-sm'
            onClick={() => setDrawerOpen(false)}
          />
          <aside className='absolute inset-y-0 left-0 w-72 border-r border-ink-800 bg-ink-900'>
            <div className='absolute top-3 right-3 z-10'>
              <IconButton label='Cerrar menú' onClick={() => setDrawerOpen(false)}>
                <X className='size-4.5' />
              </IconButton>
            </div>
            <SidebarContent onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className='flex min-w-0 flex-1 flex-col'>
        <header className='sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-ink-800 bg-ink-950/85 px-3 backdrop-blur sm:gap-3 sm:px-5'>
          <div className='lg:hidden'>
            <IconButton label='Abrir menú' onClick={() => setDrawerOpen(true)}>
              <Menu className='size-4.5' />
            </IconButton>
          </div>

          <div className='relative min-w-0 flex-1 max-w-md' ref={searchWrapRef}>
            <Search className='pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-500' />
            <input
              ref={searchInputRef}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setSearchOpen(true)
              }}
              onFocus={() => setSearchOpen(true)}
              placeholder='Buscar cursos, tareas, documentos…'
              aria-label='Buscar'
              className='h-10 w-full rounded-xl border border-ink-700 bg-ink-900/80 pr-14 pl-9 text-sm text-ink-100 placeholder:text-ink-500 transition focus:border-flame-400/70 focus:outline-none focus:ring-2 focus:ring-flame-400/20'
            />
            <kbd
              onClick={() => setCommandOpen(true)}
              className='pointer-events-auto absolute top-1/2 right-2.5 hidden -translate-y-1/2 cursor-pointer rounded-md border border-ink-700 bg-ink-800 px-1.5 py-0.5 text-[0.65rem] text-ink-400 sm:block'
            >
              Ctrl K
            </kbd>

            {searchOpen && trimmed.length >= 2 ? (
              <div className='absolute top-full right-0 left-0 z-40 mt-2 overflow-hidden rounded-xl border border-ink-700 bg-ink-850 shadow-panel'>
                {isFetching && results.length === 0 ? (
                  <p className='px-4 py-3 text-sm text-ink-400'>Buscando…</p>
                ) : results.length === 0 ? (
                  <p className='px-4 py-3 text-sm text-ink-400'>Sin resultados para “{trimmed}”.</p>
                ) : (
                  <ul className='max-h-80 overflow-y-auto py-1'>
                    {results.map((result) => (
                      <li key={`${result.type}-${result.id}`}>
                        <Link
                          to={result.path}
                          className='flex items-center gap-3 px-4 py-2.5 text-sm transition hover:bg-ink-800'
                        >
                          <span className='min-w-0 flex-1'>
                            <span className='block truncate text-ink-100'>{result.title}</span>
                            {result.subtitle ? (
                              <span className='block truncate text-xs text-ink-400'>{result.subtitle}</span>
                            ) : null}
                          </span>
                          <span className='shrink-0 rounded-md bg-ink-800 px-1.5 py-0.5 text-[0.65rem] tracking-wide text-ink-400 uppercase'>
                            {result.type}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}
          </div>

          <span
            title={aiStatus?.message}
            className={cn(
              'hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs sm:inline-flex',
              aiStatus?.available
                ? 'border-success/30 bg-success/10 text-success'
                : 'border-ink-700 bg-ink-800 text-ink-400',
            )}
          >
            <Sparkles className='size-3.5' />
            {aiStatus?.available ? aiStatus.provider : 'IA off'}
          </span>

          <LinkButton to='/app/planner' variant='outline' size='sm' className='hidden md:inline-flex'>
            Planificar
          </LinkButton>

          <div className='hidden items-center gap-2 sm:flex'>
            <span className='grid size-8 shrink-0 place-items-center rounded-full bg-ink-800 font-display text-xs font-semibold text-flame-300'>
              {(user?.full_name || user?.email || 'U').slice(0, 1).toUpperCase()}
            </span>
            <span className='max-w-32 truncate text-sm text-ink-300'>
              {user?.full_name || user?.email}
            </span>
          </div>

          <IconButton
            label='Cerrar sesión'
            onClick={() => {
              void logout().then(() => navigate('/'))
            }}
          >
            <LogOut className='size-4.5' />
          </IconButton>
        </header>

        <main className='min-w-0 flex-1 p-4 sm:p-6 lg:p-8'>
          <Outlet />
        </main>
      </div>

      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  )
}
