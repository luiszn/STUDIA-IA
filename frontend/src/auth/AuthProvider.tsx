import { useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { ApiError, api, tokens } from '@/lib/api'
import type { TokenResponse, UserRead } from '@/lib/types'

interface AuthContextValue {
  user: UserRead | null
  isAuthenticated: boolean
  isReady: boolean
  login: (email: string, password: string) => Promise<UserRead>
  register: (payload: RegisterPayload) => Promise<UserRead>
  logout: () => Promise<void>
  setUser: (user: UserRead) => void
}

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  university?: string
  career?: string
  academic_year?: string
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUserState] = useState<UserRead | null>(null)
  const [isReady, setIsReady] = useState(false)

  const hydrate = useCallback(async () => {
    if (!tokens.access) {
      setIsReady(true)
      return
    }
    try {
      setUserState(await api.get<UserRead>('/auth/me'))
    } catch (error) {
      // An expired or revoked token must not keep a ghost session around.
      if (error instanceof ApiError && error.isUnauthorized) tokens.clear()
      setUserState(null)
    } finally {
      setIsReady(true)
    }
  }, [])

  useEffect(() => {
    void hydrate()
  }, [hydrate])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isReady,
      async login(email, password) {
        const response = await api.post<TokenResponse>(
          '/auth/login',
          { email, password },
          { anonymous: true },
        )
        tokens.set(response.access_token, response.refresh_token)
        setUserState(response.user)
        void queryClient.invalidateQueries()
        return response.user
      },
      async register(payload) {
        const response = await api.post<TokenResponse>('/auth/register', payload, {
          anonymous: true,
        })
        tokens.set(response.access_token, response.refresh_token)
        setUserState(response.user)
        void queryClient.invalidateQueries()
        return response.user
      },
      async logout() {
        try {
          await api.post<void>('/auth/logout')
        } catch {
          // Logging out locally must succeed even if the call fails.
        }
        tokens.clear()
        setUserState(null)
        queryClient.clear()
      },
      setUser: setUserState,
    }),
    [user, isReady, queryClient],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
