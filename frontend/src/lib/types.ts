/** Types mirroring the FastAPI schemas. Keep in sync with `backend/app/schemas`. */

export type UUID = string
export type ISODate = string
export type ISODateTime = string

export type CourseStatus = 'active' | 'archived' | 'completed'
export type EnrollmentRole = 'owner' | 'student' | 'assistant'
export type Priority = 'low' | 'medium' | 'high' | 'urgent'
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type ExamType = 'quiz' | 'partial' | 'final' | 'project' | 'other'
export type ExamStatus = 'scheduled' | 'done' | 'cancelled'
export type GradeCategory = 'exam' | 'quiz' | 'homework' | 'project' | 'participation' | 'other'
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'
export type SummaryStyle = 'short' | 'detailed' | 'key_points'
export type StudyLevel = 'beginner' | 'intermediate' | 'advanced'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type QuestionType = 'multiple_choice' | 'true_false' | 'short_answer'
export type FlashcardOrigin = 'manual' | 'ai'
export type FlashcardDifficulty = 'easy' | 'medium' | 'hard'
export type FlashcardStatus = 'new' | 'review' | 'mastered'
export type StudyPlanStatus = 'draft' | 'active' | 'completed'
export type RecommendationKind =
  | 'weak_topic'
  | 'due_review'
  | 'upcoming_exam'
  | 'overdue_task'
  | 'streak'
  | 'inactive_course'

export interface CourseSummary {
  id: UUID
  code: string
  name: string
  professor: string | null
  color: string
  credits: number
  semester: string | null
  status: CourseStatus
}

export interface CourseRead extends CourseSummary {
  role: EnrollmentRole
  description: string | null
  academic_year: string | null
  created_at: ISODateTime
  updated_at: ISODateTime
  task_count: number
  pending_task_count: number
  document_count: number
  flashcard_count: number
  exam_count: number
  average_grade: number | null
}

export interface CourseStats {
  total_tasks: number
  completed_tasks: number
  overdue_tasks: number
  upcoming_exams: number
  average_grade: number | null
  highest_grade: number | null
  documents: number
  flashcards: number
  study_minutes: number
}

export interface TaskRead {
  id: UUID
  title: string
  description: string | null
  course_id: UUID | null
  course: CourseSummary | null
  status: TaskStatus
  priority: Priority
  due_at: ISODateTime | null
  completed_at: ISODateTime | null
  estimated_minutes: number | null
  is_overdue: boolean
  created_at: ISODateTime
  updated_at: ISODateTime
}

export interface ExamRead {
  id: UUID
  title: string
  course_id: UUID | null
  course: CourseSummary | null
  exam_type: ExamType
  status: ExamStatus
  scheduled_at: ISODateTime
  duration_minutes: number | null
  location: string | null
  notes: string | null
  weight: number | null
  topics: string[] | null
  days_until: number | null
  grade_id: UUID | null
  created_at: ISODateTime
}

export interface GradeRead {
  id: UUID
  title: string
  course_id: UUID | null
  course: CourseSummary | null
  exam_id: UUID | null
  category: GradeCategory
  score: number
  max_score: number
  percentage: number
  weight: number | null
  graded_at: ISODateTime | null
  graded_on_date: ISODate | null
  notes: string | null
  created_at: ISODateTime
}

export interface CourseGradeSummary {
  course_id: UUID
  course_name: string
  course_code: string
  color: string
  average: number
  highest: number
  lowest: number
  count: number
  projected: number | null
  required_to_pass: number | null
  trend: { date: ISODate; percentage: number }[]
}

export interface GradeDistribution {
  range: string
  min: number
  max: number
  count: number
}

export interface CategoryBreakdown {
  category: GradeCategory
  average: number
  count: number
}

export interface GradeOverview {
  overall_average: number | null
  courses: CourseGradeSummary[]
  distribution: GradeDistribution[]
  category_breakdown: CategoryBreakdown[]
  recent: GradeRead[]
}

export interface DocumentRead {
  id: UUID
  title: string
  filename: string
  content_type: string
  extension: string
  size_bytes: number
  page_count: number | null
  word_count: number
  char_count: number
  chunk_count: number
  status: DocumentStatus
  error_message: string | null
  detected_language: string | null
  summary: string | null
  topics: string[]
  course_id: UUID | null
  course: CourseSummary | null
  created_at: ISODateTime
  updated_at: ISODateTime
}

export interface DocumentChunkRead {
  id: UUID
  document_id: UUID
  chunk_index: number
  content: string
  page_number: number | null
  heading: string | null
  token_estimate: number
}

export interface DocumentDetail extends DocumentRead {
  chunks: DocumentChunkRead[]
  preview: string
}

export interface SourceCitation {
  document_id: UUID
  title: string
  filename: string
  chunk_index: number | null
  page_number: number | null
  score?: number | null
  excerpt: string | null
}

export interface SummaryResult {
  summary: string
  style: SummaryStyle
  sources: SourceCitation[]
  provider: string
  model: string
  tokens: number | null
}

export interface FlashcardRead {
  id: UUID
  front: string
  back: string
  explanation: string | null
  deck: string
  course_id: UUID | null
  course: CourseSummary | null
  origin: FlashcardOrigin
  difficulty: FlashcardDifficulty
  status: FlashcardStatus
  tags: string[]
  source_document_id: UUID | null
  repetitions: number
  lapses: number
  ease_factor: number
  interval_days: number
  next_review_at: ISODateTime | null
  last_reviewed_at: ISODateTime | null
  created_at: ISODateTime
}

export interface FlashcardDeckSummary {
  name: string
  course_id: UUID | null
  course_name: string | null
  color: string | null
  total: number
  new: number
  due_today: number
  mastered: number
  average_difficulty: number
}

export interface StudySessionRead {
  id: UUID
  focus: string
  course_id: UUID | null
  course: CourseSummary | null
  study_plan_id: UUID | null
  started_at: ISODateTime
  ended_at: ISODateTime | null
  duration_minutes: number
  notes: string | null
}

export interface StudyPlanDay {
  day: number
  date: ISODate | null
  title: string
  focus: string
  theory_minutes: number
  practice_minutes: number
  review_minutes: number
  objectives: string[]
  resources: string[]
}

export interface StudyPlanRead {
  id: UUID
  title: string
  course_id: UUID | null
  course: CourseSummary | null
  exam_id: UUID | null
  exam_date: ISODateTime | null
  level: StudyLevel
  daily_minutes: number
  total_days: number
  total_minutes: number
  status: StudyPlanStatus
  days: StudyPlanDay[]
  weak_topics: string[]
  rationale: string | null
  provider: string | null
  model: string | null
  created_at: ISODateTime
}

export interface RecommendationRead {
  id: UUID
  kind: RecommendationKind
  title: string
  message: string
  priority: Priority
  score: number
  cta_label: string | null
  cta_path: string | null
  evidence: Record<string, unknown>
  course_id: UUID | null
  course: CourseSummary | null
  is_read: boolean
  is_dismissed: boolean
  created_at: ISODateTime
  expires_at: ISODateTime | null
}

export interface WeakTopic {
  topic: string
  course_id: UUID | null
  course_name: string | null
  confidence: number
  evidence: string[]
  suggested_action: string | null
}

export interface UserRead {
  id: UUID
  email: string
  full_name: string
  avatar_url: string | null
  university: string | null
  career: string | null
  academic_year: string | null
  timezone: string
  daily_study_goal_minutes: number
  locale: string
  is_active: boolean
  is_verified: boolean
  last_login_at: ISODateTime | null
  created_at: ISODateTime
  initials: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserRead
}

export interface DashboardStats {
  active_courses: number
  total_courses: number
  pending_tasks: number
  overdue_tasks: number
  completed_tasks: number
  upcoming_exams: number
  next_exam_in_days: number | null
  average_grade: number | null
  study_minutes_week: number
  study_minutes_total: number
  documents: number
  flashcards: number
  flashcards_due: number
  study_streak_days: number
  daily_goal_minutes: number
}

export type ActivityKind = 'task' | 'exam' | 'session'

export interface ActivityItem {
  id: string
  kind: ActivityKind
  title: string
  course_name: string | null
  course_code: string | null
  color: string | null
  /** ISO datetime, not a plain date. */
  date: string | null
  time_label: string | null
  priority: Priority | null
  status: string | null
  path: string
  is_overdue: boolean
}

export interface PerformancePoint {
  label: string
  value: number
}

export interface CoursePerformance {
  course_id: UUID
  code: string
  name: string
  color: string
  average: number
}

export interface PerformanceSeries {
  study_minutes: PerformancePoint[]
  grades: PerformancePoint[]
  by_course: CoursePerformance[]
}

export interface DashboardResponse {
  greeting: string
  generated_at: ISODateTime
  stats: DashboardStats
  upcoming: ActivityItem[]
  recommendation: RecommendationRead | null
  performance: PerformanceSeries
  focus_course: Record<string, unknown> | null
  quick_actions: { label: string; path: string; icon?: string }[]
}

export interface CalendarEvent {
  id: string
  kind: ActivityKind
  title: string
  course_name: string | null
  color: string | null
  /** ISO date (no time). */
  date: ISODate
  time: string | null
  path: string
  priority: Priority | null
  status: string | null
  meta: Record<string, unknown>
}

export interface CalendarResponse {
  start: ISODate
  end: ISODate
  events: CalendarEvent[]
}

export interface SearchResultItem {
  id: UUID
  type: string
  title: string
  subtitle: string | null
  path: string
  meta?: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  total: number
  results: SearchResultItem[]
  groups: Record<string, number>
}

export interface AIProviderStatus {
  provider: string
  available: boolean
  model: string | null
  embedding_model: string | null
  message: string
  latency_ms: number | null
}

export interface MessageRead {
  id: UUID
  conversation_id: UUID
  role: 'user' | 'assistant' | 'system'
  content: string
  sources: SourceCitation[]
  provider: string | null
  model: string | null
  latency_ms: number | null
  created_at: ISODateTime
}

export interface ConversationRead {
  id: UUID
  title: string
  course_id: UUID | null
  course_name: string | null
  provider: string | null
  model: string | null
  message_count: number
  used_rag: boolean
  created_at: ISODateTime
  updated_at: ISODateTime
  last_message_at: ISODateTime | null
}

export interface ConversationDetail extends ConversationRead {
  messages: MessageRead[]
}

export interface ChatResponse {
  conversation_id: UUID
  title: string
  message: string
  sources: SourceCitation[]
  used_rag: boolean
  provider: string
  model: string
  latency_ms: number
  created_at: ISODateTime
}

export interface QuestionOption {
  id: string
  text: string
}

export interface GeneratedQuestion {
  id: string
  type: QuestionType
  prompt: string
  options: QuestionOption[]
  correct_answer: string
  correct_option_id: string | null
  explanation: string
  difficulty: Difficulty
  topic: string | null
  source_document_id: UUID | null
}

export interface GenerateQuestionsResult {
  questions: GeneratedQuestion[]
  provider: string
  model: string
  sources: SourceCitation[]
  count: number
}

export interface GradedAnswer {
  question_id: string
  is_correct: boolean
  expected_answer: string
  explanation: string
  awarded_points: number
  max_points: number
}

export interface GradeAnswersResult {
  score: number
  correct_count: number
  total: number
  answers: GradedAnswer[]
  feedback: string
}

export interface GradeQuestionsRequest {
  questions: GeneratedQuestion[]
  answers: AnswerPayload[]
}

export interface GradeAnswersRequest {
  questions: AnswerPayload[]
}

export interface AnswerPayload {
  question_id: string
  answer: string
}

export interface ExplainResult {
  topic: string
  level: StudyLevel
  answer: string
  sources: SourceCitation[]
  used_rag: boolean
  provider: string
  model: string
}

export interface GenerateFlashcardsResult {
  flashcards: FlashcardRead[]
  created: number
  provider: string
  model: string
  sources: SourceCitation[]
}

export interface FlashcardReviewResult {
  card_id: UUID
  status: FlashcardStatus
  repetitions: number
  interval_days: number
  next_review_at: ISODateTime | null
  message: string
}
