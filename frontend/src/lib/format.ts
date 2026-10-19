import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const DAY_MS = 86_400_000

/** Local-time ISO string, needed by `datetime-local` inputs. */
export function toLocalInput(value: string | Date | null | undefined): string {
  if (!value) return ''
  const date = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function fromLocalInput(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}

export function formatDate(value: string | null | undefined, options?: Intl.DateTimeFormatOptions) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('es', options ?? { day: '2-digit', month: 'short', year: 'numeric' }).format(date)
}

export function formatDateTime(value: string | null | undefined) {
  return formatDate(value, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function formatTime(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('es', { hour: '2-digit', minute: '2-digit' }).format(date)
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const diff = Date.now() - date.getTime()
  const minutes = Math.round(diff / 60_000)
  if (Math.abs(minutes) < 1) return 'ahora mismo'
  if (Math.abs(minutes) < 60) return relative(minutes, 'minute')
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return relative(hours, 'hour')
  const days = Math.round(hours / 24)
  if (Math.abs(days) < 30) return relative(days, 'day')
  return formatDate(value)
}

function relative(value: number, unit: Intl.RelativeTimeFormatUnit) {
  const formatter = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })
  return formatter.format(-value, unit)
}

/** "en 3 días" / "hace 2 h" for deadlines. */
export function formatDueLabel(value: string | null | undefined) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  const days = Math.ceil((date.getTime() - Date.now()) / DAY_MS)
  if (days < 0) return `hace ${Math.abs(days)} d`
  if (days === 0) return 'hoy'
  if (days === 1) return 'mañana'
  if (days <= 30) return `en ${days} días`
  return formatDate(value)
}

export function formatMinutes(minutes: number | null | undefined): string {
  const value = minutes ?? 0
  if (value < 60) return `${value} min`
  const hours = Math.floor(value / 60)
  const rest = value % 60
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

export function formatBytes(bytes: number | null | undefined): string {
  const value = bytes ?? 0
  if (value < 1024) return `${value} B`
  const units = ['KB', 'MB', 'GB']
  let size = value / 1024
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unit]}`
}

export function initialsOf(name: string): string {
  return (
    name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('') || 'ST'
  )
}

export function pluralize(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

export function addDays(date: Date, days: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

export function startOfWeek(date = new Date()): Date {
  const start = new Date(date)
  const weekday = (start.getDay() + 6) % 7
  start.setDate(start.getDate() - weekday)
  start.setHours(0, 0, 0, 0)
  return start
}

export function sameDay(a: Date | string, b: Date | string) {
  const first = typeof a === 'string' ? new Date(a) : a
  const second = typeof b === 'string' ? new Date(b) : b
  return (
    first.getFullYear() === second.getFullYear() &&
    first.getMonth() === second.getMonth() &&
    first.getDate() === second.getDate()
  )
}

export function isToday(value: string | null | undefined) {
  return value ? sameDay(value, new Date()) : false
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

export function percentage(part: number, total: number) {
  if (!total) return 0
  return clamp(Math.round((part / total) * 100), 0, 100)
}

export function groupBy<T, K extends string>(items: T[], key: (item: T) => K) {
  return items.reduce<Record<K, T[]>>((accumulator, item) => {
    const bucket = key(item)
    accumulator[bucket] = [...(accumulator[bucket] ?? []), item]
    return accumulator
  }, {} as Record<K, T[]>)
}

export const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente',
}

export const EXAM_TYPE_LABELS: Record<string, string> = {
  quiz: 'Quiz',
  partial: 'Parcial',
  final: 'Final',
  project: 'Proyecto',
  other: 'Otro',
}

export const EXAM_STATUS_LABELS: Record<string, string> = {
  scheduled: 'Programado',
  done: 'Realizado',
  cancelled: 'Cancelado',
}

export const CATEGORY_LABELS: Record<string, string> = {
  exam: 'Examen',
  quiz: 'Quiz',
  homework: 'Tarea',
  project: 'Proyecto',
  participation: 'Participación',
  other: 'Otro',
}

export const LEVEL_LABELS: Record<string, string> = {
  beginner: 'Principiante',
  intermediate: 'Intermedio',
  advanced: 'Avanzado',
}

export const DIFFICULTY_LABELS: Record<string, string> = {
  easy: 'Fácil',
  medium: 'Media',
  hard: 'Difícil',
}

export const STATUS_LABELS: Record<string, string> = {
  todo: 'Pendiente',
  in_progress: 'En curso',
  done: 'Completada',
  new: 'Nueva',
  review: 'Repaso',
  mastered: 'Dominada',
  scheduled: 'Programado',
  cancelled: 'Cancelado',
  pending: 'Pendiente',
  processing: 'Procesando',
  ready: 'Listo',
  failed: 'Fallido',
  draft: 'Borrador',
  active: 'Activo',
  completed: 'Completado',
}
