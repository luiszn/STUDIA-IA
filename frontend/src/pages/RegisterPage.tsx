import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { Button } from '@/components/ui/Button'
import { Field, Input } from '@/components/ui/Input'
import { AuthLayout, FormError } from '@/pages/auth/authLayout'

const MIN_PASSWORD = 8

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    university: '',
    career: '',
    academic_year: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const update = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }))

  const passwordTooShort = form.password.length > 0 && form.password.length < MIN_PASSWORD

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (form.password.length < MIN_PASSWORD) {
      setError(`La contraseña necesita al menos ${MIN_PASSWORD} caracteres.`)
      return
    }
    setIsLoading(true)
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        university: form.university.trim() || undefined,
        career: form.career.trim() || undefined,
        academic_year: form.academic_year.trim() || undefined,
      })
      navigate('/app', { replace: true })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'No pudimos crear la cuenta.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Crea tu cuenta"
      subtitle="Empieza con tu semestre real: cursos, fechas y material."
      footer={
        <>
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-flame-300 hover:text-flame-200">
            Iniciar sesión
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <FormError message={error} />

        <Field label="Nombre completo" required>
          <Input
            autoComplete="name"
            placeholder="Ana Martínez"
            value={form.full_name}
            onChange={update('full_name')}
            required
          />
        </Field>

        <Field label="Email" required>
          <Input
            type="email"
            autoComplete="email"
            placeholder="tu@university.edu"
            value={form.email}
            onChange={update('email')}
            required
          />
        </Field>

        <Field
          label="Contraseña"
          required
          error={passwordTooShort ? `Mínimo ${MIN_PASSWORD} caracteres` : null}
        >
          <Input
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={form.password}
            onChange={update('password')}
            required
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Universidad" hint="Opcional">
            <Input
              placeholder="Universidad de Chile"
              value={form.university}
              onChange={update('university')}
            />
          </Field>
          <Field label="Carrera" hint="Opcional">
            <Input placeholder="Ingeniería" value={form.career} onChange={update('career')} />
          </Field>
        </div>

        <Field label="Año académico" hint="Opcional, ej. 2026-1">
          <Input
            placeholder="2026-1"
            value={form.academic_year}
            onChange={update('academic_year')}
          />
        </Field>

        <Button type="submit" className="w-full" isLoading={isLoading}>
          Crear cuenta
        </Button>

        <p className="text-center text-xs text-ink-500">
          Al registrarte aceptas usar tus datos únicamente dentro de tu cuenta.
        </p>
      </form>
    </AuthLayout>
  )
}
