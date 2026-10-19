/**
 * Minimal typed fetch client.
 *
 * A hand written client instead of axios: the surface we need is small, and it
 * keeps one place responsible for the auth header, the error envelope and the
 * single-flight refresh.
 */

export const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1'

const ACCESS_KEY = 'studia.access'
const REFRESH_KEY = 'studia.refresh'

export class ApiError extends Error {
  status: number
  code: string
  details: unknown

  constructor(status: number, message: string, code = 'unknown', details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  get isUnauthorized() {
    return this.status === 401
  }

  get isNotFound() {
    return this.status === 404
  }

  get isValidation() {
    return this.status === 422 || this.status === 400
  }
}

interface ErrorEnvelope {
  error?: { code?: string; message?: string; details?: unknown }
  detail?: string | { msg?: string }[]
}

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

function parseError(status: number, payload: unknown): ApiError {
  const body = payload as ErrorEnvelope | null
  const envelope = body?.error
  if (envelope?.message) {
    return new ApiError(status, envelope.message, envelope.code ?? 'unknown', envelope.details)
  }
  if (typeof body?.detail === 'string') {
    return new ApiError(status, body.detail)
  }
  if (Array.isArray(body?.detail)) {
    const first = body.detail[0]
    return new ApiError(status, first?.msg ?? 'Datos inválidos', 'validation', body.detail)
  }
  return new ApiError(status, status === 500 ? 'Error interno del servidor' : 'Petición fallida')
}

type Query = Record<string, string | number | boolean | null | undefined>

function withQuery(path: string, query?: Query) {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === '') continue
    params.set(key, String(value))
  }
  const search = params.toString()
  return search ? `${path}?${search}` : path
}

async function parseBody(response: Response) {
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

let refreshInFlight: Promise<boolean> | null = null

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokens.refresh
  if (!refresh) return false

  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (!response.ok) return false
      const data = (await response.json()) as { access_token: string; refresh_token: string }
      tokens.set(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      refreshInFlight = null
    }
  })()

  return refreshInFlight
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  query?: Query
  /** Set for auth endpoints so a 401 does not trigger a refresh loop. */
  anonymous?: boolean
  raw?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, query, anonymous, raw, headers, ...rest } = options
  const send = async (): Promise<Response> => {
    const isForm = body instanceof FormData
    return fetch(withQuery(`${API_BASE}${path}`, query), {
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(isForm ? {} : body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(anonymous ? {} : tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {}),
        ...headers,
      },
      body: isForm ? (body as FormData) : body === undefined ? undefined : JSON.stringify(body),
    })
  }

  let response = await send()

  if (response.status === 401 && !anonymous && tokens.refresh) {
    if (await refreshAccessToken()) {
      response = await send()
    } else {
      tokens.clear()
    }
  }

  const payload = await parseBody(response)

  if (!response.ok) {
    throw parseError(response.status, payload)
  }

  return payload as T
}

export const api = {
  get: <T>(path: string, query?: Query, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET', query }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: 'POST', body: form, raw: true }),
}

/** Paginated envelope used by the list endpoints. */
export interface Paginated<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
