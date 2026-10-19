import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '@/auth/AuthProvider'
import AppShell from '@/components/layout/AppShell'
import { SplashScreen } from '@/components/layout/SplashScreen'
import AIChatPage from '@/pages/AIChatPage'
import CalendarPage from '@/pages/CalendarPage'
import CourseDetailPage from '@/pages/CourseDetailPage'
import CoursesPage from '@/pages/CoursesPage'
import DashboardPage from '@/pages/DashboardPage'
import DocumentsPage from '@/pages/DocumentsPage'
import ExamsPage from '@/pages/ExamsPage'
import FlashcardsPage from '@/pages/FlashcardsPage'
import GradesPage from '@/pages/GradesPage'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import NotFoundPage from '@/pages/NotFoundPage'
import PlannerPage from '@/pages/PlannerPage'
import RegisterPage from '@/pages/RegisterPage'
import SessionsPage from '@/pages/SessionsPage'
import SettingsPage from '@/pages/SettingsPage'
import TasksPage from '@/pages/TasksPage'
import WeakTopicsPage from '@/pages/WeakTopicsPage'

function Protected({ children }: { children: ReactNode }) {
  const { isAuthenticated, isReady } = useAuth()
  const location = useLocation()

  if (!isReady) return <SplashScreen />
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  return <>{children}</>
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { isAuthenticated, isReady } = useAuth()
  if (!isReady) return <SplashScreen />
  if (isAuthenticated) return <Navigate to="/app" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnly>
            <RegisterPage />
          </PublicOnly>
        }
      />

      <Route
        path="/app"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="courses/:courseId" element={<CourseDetailPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="exams" element={<ExamsPage />} />
        <Route path="grades" element={<GradesPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="flashcards" element={<FlashcardsPage />} />
        <Route path="planner" element={<PlannerPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="ai" element={<AIChatPage />} />
        <Route path="weak-topics" element={<WeakTopicsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
