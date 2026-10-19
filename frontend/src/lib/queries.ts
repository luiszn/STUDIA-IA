/**
 * TanStack Query hooks � one place that knows every endpoint, so pages only
 * describe what they want to show.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api'
import type {
  AIProviderStatus,
  CalendarResponse,
  ChatResponse,
  ConversationDetail,
  ConversationRead,
  CourseGradeSummary,
  CourseRead,
  CourseStats,
  DashboardResponse,
  DocumentDetail,
  DocumentRead,
  ExamRead,
  ExplainResult,
  FlashcardDeckSummary,
  FlashcardRead,
  FlashcardReviewResult,
  GenerateFlashcardsResult,
  GenerateQuestionsResult,
  GeneratedQuestion,
  GradeAnswersResult,
  GradeOverview,
  GradeRead,
  AnswerPayload,
  RecommendationRead,
  SearchResponse,
  StudyPlanRead,
  StudySessionRead,
  SummaryResult,
  TaskRead,
  UserRead,
  WeakTopic,
} from '@/lib/types'

/** Mirrors `backend/app/schemas/common.py::Page`. */
export type Page<T> = {
  items: T[]
  meta: { total: number; limit: number; offset: number; has_more: boolean }
}

export const keys = {
  me: ['auth', 'me'] as const,
  dashboard: ['dashboard'] as const,
  courses: (filters?: unknown) => ['courses', filters ?? {}] as const,
  course: (id: string) => ['courses', 'detail', id] as const,
  courseStats: (id: string) => ['courses', 'stats', id] as const,
  tasks: (filters?: unknown) => ['tasks', filters ?? {}] as const,
  exams: (filters?: unknown) => ['exams', filters ?? {}] as const,
  grades: (filters?: unknown) => ['grades', filters ?? {}] as const,
  gradeOverview: ['grades', 'overview'] as const,
  documents: (filters?: unknown) => ['documents', filters ?? {}] as const,
  document: (id: string) => ['documents', 'detail', id] as const,
  flashcards: (filters?: unknown) => ['flashcards', filters ?? {}] as const,
  decks: ['flashcards', 'decks'] as const,
  dueCards: ['flashcards', 'due'] as const,
  sessions: (filters?: unknown) => ['sessions', filters ?? {}] as const,
  plans: ['plans'] as const,
  plan: (id: string) => ['plans', 'detail', id] as const,
  recommendations: ['recommendations'] as const,
  weakTopics: ['weak-topics'] as const,
  conversations: ['ai', 'conversations'] as const,
  conversation: (id: string) => ['ai', 'conversations', id] as const,
  aiStatus: ['ai', 'status'] as const,
  calendar: (range: string) => ['calendar', range] as const,
  search: (query: string) => ['search', query] as const,
}

function useApiQuery<T>(
  queryKey: readonly unknown[],
  path: string,
  options: {
    query?: Record<string, string | number | boolean | null | undefined>
    enabled?: boolean
    refetchInterval?: number | false
  } = {},
): UseQueryResult<T, ApiError> {
  return useQuery<T, ApiError>({
    queryKey,
    queryFn: () => api.get<T>(path, options.query),
    enabled: options.enabled ?? true,
    refetchInterval: options.refetchInterval,
    staleTime: 30_000,
    retry: (failureCount, error) =>
      error instanceof ApiError && error.status < 500 ? false : failureCount < 2,
  })
}

/** Invalidate every key that starts with any of the prefixes. */
function useInvalidate() {
  const client = useQueryClient()
  return (...prefixes: readonly (readonly unknown[])[]) => {
    for (const prefix of prefixes) {
      void client.invalidateQueries({ queryKey: prefix })
    }
  }
}

/* ------------------------------------------------------------------- auth */
export function useMe() {
  return useApiQuery<UserRead>(keys.me, '/auth/me')
}

export function useUpdateProfile() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Partial<UserRead>) => api.patch<UserRead>('/auth/me', payload),
    onSuccess: () => invalidate(keys.me),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      api.post<void>('/auth/me/password', payload),
  })
}

/* --------------------------------------------------------------- dashboard */
export function useDashboard() {
  return useApiQuery<DashboardResponse>(keys.dashboard, '/dashboard')
}

export function useCalendar(start: string, end: string) {
  return useApiQuery<CalendarResponse>(keys.calendar(`${start}:${end}`), '/calendar', {
    query: { start, end },
  })
}

export function useSearch(query: string, enabled = true) {
  const trimmed = query.trim()
  return useApiQuery<SearchResponse>(keys.search(trimmed), '/search', {
    query: { q: trimmed, limit: 8 },
    enabled: enabled && trimmed.length >= 2,
  })
}

/* ----------------------------------------------------------------- courses */
/** `GET /courses` answers with a bare array, not the paginated envelope. */
export function useCourses(filters: { status?: string; search?: string } = {}) {
  return useApiQuery<CourseRead[]>(keys.courses(filters), '/courses', { query: filters })
}

export function useCourse(id: string | undefined) {
  if (!id) throw new Error('useCourse needs an id')
  return useApiQuery<CourseRead>(keys.course(id), `/courses/${id}`)
}

export function useCourseStats(id: string | undefined) {
  return useApiQuery<CourseStats>(keys.courseStats(id ?? ''), `/courses/${id}/stats`)
}

export function useCreateCourse() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Partial<CourseRead>) => api.post<CourseRead>('/courses', payload),
    onSuccess: () => invalidate(keys.courses(), keys.dashboard),
  })
}

export function useUpdateCourse(id: string) {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Partial<CourseRead>) => api.patch<CourseRead>(`/courses/${id}`, payload),
    onSuccess: () => invalidate(keys.courses(), keys.course(id), keys.dashboard),
  })
}

export function useDeleteCourse() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/courses/${id}`),
    onSuccess: () => invalidate(keys.courses(), keys.dashboard),
  })
}

/* ------------------------------------------------------------------- tasks */
export function useTasks(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<Page<TaskRead>>(keys.tasks(filters), '/tasks', { query: filters })
}

export function useCreateTask() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<TaskRead>('/tasks', payload),
    onSuccess: () => invalidate(keys.tasks(), keys.dashboard),
  })
}

export function useUpdateTask(id: string) {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.patch<TaskRead>(`/tasks/${id}`, payload),
    onSuccess: () => invalidate(keys.tasks(), keys.dashboard),
  })
}

export function useToggleTask() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.post<TaskRead>(`/tasks/${id}/toggle`),
    onSuccess: () => invalidate(keys.tasks(), keys.dashboard),
  })
}

export function useDeleteTask() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/tasks/${id}`),
    onSuccess: () => invalidate(keys.tasks(), keys.dashboard),
  })
}

/* ------------------------------------------------------------------- exams */
export function useExams(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<Page<ExamRead>>(keys.exams(filters), '/exams', { query: filters })
}

export function useCreateExam() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<ExamRead>('/exams', payload),
    onSuccess: () => invalidate(keys.exams(), keys.dashboard),
  })
}

export function useUpdateExam(id: string) {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.patch<ExamRead>(`/exams/${id}`, payload),
    onSuccess: () => invalidate(keys.exams(), keys.dashboard),
  })
}

export function useDeleteExam() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/exams/${id}`),
    onSuccess: () => invalidate(keys.exams(), keys.dashboard),
  })
}

/* ------------------------------------------------------------------ grades */
export function useGrades(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<Page<GradeRead>>(keys.grades(filters), '/grades', { query: filters })
}

export function useGradeOverview() {
  return useApiQuery<GradeOverview>(keys.gradeOverview, '/grades/overview')
}

export function useCreateGrade() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<GradeRead>('/grades', payload),
    onSuccess: () => invalidate(keys.grades(), keys.gradeOverview, keys.dashboard),
  })
}

export function useDeleteGrade() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/grades/${id}`),
    onSuccess: () => invalidate(keys.grades(), keys.gradeOverview, keys.dashboard),
  })
}

export type GradeCourseSummary = CourseGradeSummary

/* --------------------------------------------------------------- documents */
export function useDocuments(
  filters: Record<string, string | number | boolean | undefined> = {},
  options: { refetchInterval?: number | false } = {},
) {
  return useApiQuery<DocumentRead[]>(keys.documents(filters), '/documents', {
    query: filters,
    refetchInterval: options.refetchInterval,
  })
}

export function useDocument(id: string | undefined) {
  return useApiQuery<DocumentDetail>(keys.document(id ?? ''), `/documents/${id ?? ''}`, {
    enabled: Boolean(id),
  })
}

export function useUploadDocument() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (form: FormData) => api.upload<DocumentRead>('/documents/upload', form),
    onSuccess: () => invalidate(keys.documents(), keys.dashboard),
  })
}

export function useDeleteDocument() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/documents/${id}`),
    onSuccess: () => invalidate(keys.documents(), keys.dashboard),
  })
}

export function useSummarizeDocument() {
  return useMutation({
    mutationFn: (payload: {
      document_ids: string[]
      style?: string
      focus?: string
      course_id?: string | null
    }) => api.post<SummaryResult>('/ai/summarize', payload),
  })
}

/* -------------------------------------------------------------- flashcards */
export function useFlashcards(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<Page<FlashcardRead>>(keys.flashcards(filters), '/flashcards', { query: filters })
}

export function useDecks() {
  return useApiQuery<FlashcardDeckSummary[]>(keys.decks, '/flashcards/decks')
}

export function useDueCards() {
  return useApiQuery<FlashcardRead[]>(keys.dueCards, '/flashcards/due')
}

export function useCreateFlashcard() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<FlashcardRead>('/flashcards', payload),
    onSuccess: () => invalidate(keys.flashcards(), keys.decks, keys.dueCards, keys.dashboard),
  })
}

export function useReviewFlashcard() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: { card_id: string; quality: number; response_seconds?: number }) =>
      api.post<FlashcardReviewResult>('/flashcards/review', payload),
    onSuccess: () => invalidate(keys.flashcards(), keys.decks, keys.dueCards, keys.dashboard),
  })
}

export function useDeleteFlashcard() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/flashcards/${id}`),
    onSuccess: () => invalidate(keys.flashcards(), keys.decks, keys.dueCards),
  })
}

export function useGenerateFlashcards() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<GenerateFlashcardsResult>('/ai/flashcards', payload),
    onSuccess: () => invalidate(keys.flashcards(), keys.decks, keys.documents()),
  })
}

/* ---------------------------------------------------------------- sessions */
export function useSessions(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<Page<StudySessionRead>>(keys.sessions(filters), '/sessions', { query: filters })
}

export function useCreateSession() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<StudySessionRead>('/sessions', payload),
    onSuccess: () => invalidate(keys.sessions(), keys.dashboard),
  })
}

export function useDeleteSession() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/sessions/${id}`),
    onSuccess: () => invalidate(keys.sessions(), keys.dashboard),
  })
}

/* ------------------------------------------------------------ study plans */
export function useStudyPlans() {
  return useApiQuery<StudyPlanRead[]>(keys.plans, '/ai/study-plans')
}

export function useStudyPlan(id: string | undefined) {
  return useApiQuery<StudyPlanRead>(keys.plan(id ?? ''), `/ai/study-plans/${id ?? ''}`, {
    enabled: Boolean(id),
  })
}

export function useCreateStudyPlan() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<StudyPlanRead>('/ai/study-plans', payload),
    onSuccess: () => invalidate(keys.plans, keys.dashboard),
  })
}

export function useConvertStudyPlan() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: { id: string; create_tasks?: boolean; create_sessions?: boolean }) =>
      api.post<{ tasks_created: number; sessions_created: number }>(
        `/ai/study-plans/${id}/convert`,
        payload,
      ),
    onSuccess: () => invalidate(keys.plans, keys.tasks(), keys.sessions(), keys.dashboard),
  })
}
export function useDeleteStudyPlan() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/ai/study-plans/${id}`),
    onSuccess: () => invalidate(keys.plans),
  })
}

/* ------------------------------------------------------- recommendations */
export function useRecommendations(filters: Record<string, string | number | boolean | undefined> = {}) {
  return useApiQuery<RecommendationRead[]>(keys.recommendations, '/recommendations', {
    query: filters,
  })
}

export function useUpdateRecommendation() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload: { id: string; is_read?: boolean; is_dismissed?: boolean }) =>
      api.patch<RecommendationRead>(`/recommendations/${payload.id}`, {
        is_read: payload.is_read,
        is_dismissed: payload.is_dismissed,
      }),
    onSuccess: () => invalidate(keys.recommendations, keys.dashboard),
  })
}

export function useRegenerateRecommendations() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: () => api.post<RecommendationRead[]>('/recommendations/regenerate'),
    onSuccess: () => invalidate(keys.recommendations, keys.dashboard),
  })
}

export function useWeakTopics() {
  return useApiQuery<WeakTopic[]>(keys.weakTopics, '/ai/weak-topics')
}

/* ---------------------------------------------------------------------- ai */
export function useAiStatus() {
  return useApiQuery<AIProviderStatus>(keys.aiStatus, '/ai/status')
}

export function useConversations() {
  return useApiQuery<ConversationRead[]>(keys.conversations, '/ai/conversations')
}

export function useConversation(id: string | undefined) {
  return useApiQuery<ConversationDetail>(keys.conversation(id ?? ''), `/ai/conversations/${id ?? ''}`, {
    enabled: Boolean(id),
  })
}

export function useSendMessage(): UseMutationResult<
  ChatResponse,
  ApiError,
  { message: string; conversation_id?: string; course_id?: string | null; document_ids?: string[]; use_rag?: boolean }
> {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (payload) => api.post<ChatResponse>('/ai/chat', payload),
    onSuccess: () => invalidate(keys.conversations, keys.dashboard),
  })
}

export function useDeleteConversation() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/ai/conversations/${id}`),
    onSuccess: () => invalidate(keys.conversations),
  })
}

export function useGenerateQuestions() {
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<GenerateQuestionsResult>('/ai/questions', payload),
  })
}

export function useGradeAnswers() {
  return useMutation({
    mutationFn: (payload: {
      questions: GeneratedQuestion[]
      answers: AnswerPayload[]
    }) => api.post<GradeAnswersResult>('/ai/questions/grade', payload),
  })
}

export function useExplainTopic() {
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post<ExplainResult>('/ai/explain', payload),
  })
}
