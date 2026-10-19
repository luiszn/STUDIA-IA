import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { Button } from '@/components/ui/Button'
import { Field, Input } from '@/components/ui/Input'
import { AuthLayout, FormError } from '@/pages/auth/authLayout'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const destination = (location.state as { from?: string } | null)?.from ?? '/app'

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsLoading(true)
    try {
      await login(email.trim(), password)
      navigate(destination, { replace: true })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No pudimos iniciar sesión.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Bienvenido de vuelta"
      subtitle="Entra para continuar donde lo dejaste."
      footer={
        <>
          ¿Aún no tienes cuenta?{' '}
          <Link to="/register" className="text-flame-300 hover:text-flame-200">
            Crear una gratis
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <FormError message={error} />

        <Field label="Email" required>
          <Input
            type="email"
            autoComplete="email"
            placeholder="tu@university.edu"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </Field>

        <Field label="Contraseña" required>
          <Input
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </Field>

        <Button type="submit" className="w-full" isLoading={isLoading}>
          Entrar
        </Button>
      </form>
    </AuthLayout>
  )
}
