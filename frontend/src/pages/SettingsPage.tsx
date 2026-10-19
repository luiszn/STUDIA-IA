import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Bot, KeyRound, LogOut, RefreshCw, Save, ShieldCheck, User } from 'lucide-react'

import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/Button'
import {
  Badge,
  Card,
  CardBody,
  CardHeader,
  Skeleton,
} from '@/components/ui/Card'
import { Field, Input } from '@/components/ui/Input'
import { formatDate } from '@/lib/format'
import {
  useAiStatus,
  useChangePassword,
  useMe,
  useUpdateProfile,
} from '@/lib/queries'
import { useAuth } from '@/auth/AuthProvider'

function describeError(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return error instanceof Error ? error.message : 'No se pudo completar la operación'
}

export default function SettingsPage() {
  const { data: user, isLoading } = useMe()
  const update = useUpdateProfile()
  const changePassword = useChangePassword()
  const aiStatus = useAiStatus()
  const { logout } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState({
    full_name: '',
    university: '',
    career: '',
    academic_year: '',
    avatar_url: '',
    daily_study_goal_minutes: '120',
  })
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm: '',
  })
  const [refreshingAi, setRefreshingAi] = useState(false)

  useEffect(() => {
    if (!user) return
    setProfile({
      full_name: user.full_name ?? '',
      university: user.university ?? '',
      career: user.career ?? '',
      academic_year: user.academic_year ?? '',
      avatar_url: user.avatar_url ?? '',
      daily_study_goal_minutes: `${user.daily_study_goal_minutes ?? 120}`,
    })
  }, [user])

  const saveProfile = async () => {
    if (profile.full_name.trim().length < 2) return toast.error('Escribe tu nombre completo')
    const goal = Number(profile.daily_study_goal_minutes)
    if (!Number.isFinite(goal) || goal < 15 || goal > 960) {
      return toast.error('La meta diaria debe estar entre 15 y 960 minutos')
    }
    try {
      await update.mutateAsync({
        full_name: profile.full_name.trim(),
        university: profile.university.trim() || null,
        career: profile.career.trim() || null,
        academic_year: profile.academic_year.trim() || null,
        avatar_url: profile.avatar_url.trim() || null,
        daily_study_goal_minutes: goal,
      })
      toast.success('Perfil actualizado')
    } catch (error) {
      toast.error(describeError(error))
    }
  }

  const savePassword = async () => {
    if (passwords.new_password.length < 8) {
      return toast.error('La nueva contraseña debe tener al menos 8 caracteres')
    }
    if (passwords.new_password !== passwords.confirm) {
      return toast.error('Las contraseñas no coinciden')
    }
    try {
      await changePassword.mutateAsync({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      })
      toast.success('Contraseña cambiada')
      setPasswords({ current_password: '', new_password: '', confirm: '' })
    } catch (error) {
      toast.error(describeError(error))
    }
  }

  const refreshAi = async () => {
    setRefreshingAi(true)
    try {
      await aiStatus.refetch()
      toast.success('Estado de IA actualizado')
    } finally {
      setRefreshingAi(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes"
        description="Tu perfil, seguridad y estado del sistema."
        actions={
          <Button
            variant="outline"
            leftIcon={<LogOut className="size-4" />}
            onClick={() => {
              void logout().then(() => navigate('/login'))
            }}
          >
            Cerrar sesión
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Perfil" description="Cómo te ven tus cursos y planes." />
          <CardBody className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="grid size-12 place-items-center rounded-2xl bg-flame-400/12 text-flame-300">
                <User className="size-5" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm text-ink-100">{user?.full_name}</p>
                <p className="truncate text-xs text-ink-400">
                  {user?.email}
                  {user?.created_at ? ` · desde ${formatDate(user.created_at)}` : ''}
                </p>
              </div>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-10" />
                <Skeleton className="h-10" />
              </div>
            ) : (
              <>
                <Field label="Nombre completo" required>
                  <Input
                    value={profile.full_name}
                    onChange={(event) => setProfile({ ...profile, full_name: event.target.value })}
                  />
                </Field>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Universidad">
                    <Input
                      value={profile.university}
                      onChange={(event) => setProfile({ ...profile, university: event.target.value })}
                      placeholder="TU Universidad"
                    />
                  </Field>
                  <Field label="Carrera">
                    <Input
                      value={profile.career}
                      onChange={(event) => setProfile({ ...profile, career: event.target.value })}
                      placeholder="Ingeniería..."
                    />
                  </Field>
                  <Field label="Año académico">
                    <Input
                      value={profile.academic_year}
                      onChange={(event) => setProfile({ ...profile, academic_year: event.target.value })}
                      placeholder="3º"
                    />
                  </Field>
                  <Field label="Meta diaria (min)" hint="15–960">
                    <Input
                      type="number"
                      min={15}
                      max={960}
                      value={profile.daily_study_goal_minutes}
                      onChange={(event) =>
                        setProfile({ ...profile, daily_study_goal_minutes: event.target.value })
                      }
                    />
                  </Field>
                </div>
                <Button
                  leftIcon={<Save className="size-4" />}
                  isLoading={update.isPending}
                  onClick={() => void saveProfile()}
                >
                  Guardar perfil
                </Button>
              </>
            )}
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Seguridad" description="Cambia tu contraseña de acceso." />
            <CardBody className="space-y-4">
              <Field label="Contraseña actual" required>
                <Input
                  type="password"
                  autoComplete="current-password"
                  value={passwords.current_password}
                  onChange={(event) =>
                    setPasswords({ ...passwords, current_password: event.target.value })
                  }
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Nueva contraseña" required hint="mín. 8 caracteres">
                  <Input
                    type="password"
                    autoComplete="new-password"
                    value={passwords.new_password}
                    onChange={(event) =>
                      setPasswords({ ...passwords, new_password: event.target.value })
                    }
                  />
                </Field>
                <Field label="Repetir contraseña" required>
                  <Input
                    type="password"
                    autoComplete="new-password"
                    value={passwords.confirm}
                    onChange={(event) => setPasswords({ ...passwords, confirm: event.target.value })}
                  />
                </Field>
              </div>
              <Button
                variant="secondary"
                leftIcon={<KeyRound className="size-4" />}
                isLoading={changePassword.isPending}
                onClick={() => void savePassword()}
              >
                Cambiar contraseña
              </Button>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Estado de la IA"
              description="Proveedor activo y latencia del modelo."
              action={
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<RefreshCw className={refreshingAi ? 'size-4 animate-spin' : 'size-4'} />}
                  onClick={() => void refreshAi()}
                >
                  Actualizar
                </Button>
              }
            />
            <CardBody className="pt-0">
              {aiStatus.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                </div>
              ) : aiStatus.isError || !aiStatus.data ? (
                <p className="text-sm text-ink-400">No se pudo consultar el estado de la IA.</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 text-sm text-ink-200">
                      <Bot className="size-4 text-flame-300" />
                      {aiStatus.data.provider}
                    </span>
                    <Badge tone={aiStatus.data.available ? 'success' : 'danger'}>
                      {aiStatus.data.available ? 'Disponible' : 'No disponible'}
                    </Badge>
                  </div>
                  <dl className="space-y-2 text-xs">
                    <div className="flex justify-between gap-3">
                      <dt className="text-ink-500">Modelo</dt>
                      <dd className="truncate text-ink-200">{aiStatus.data.model ?? '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-ink-500">Embeddings</dt>
                      <dd className="truncate text-ink-200">
                        {aiStatus.data.embedding_model ?? '—'}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-ink-500">Latencia</dt>
                      <dd className="text-ink-200">
                        {aiStatus.data.latency_ms != null ? `${aiStatus.data.latency_ms} ms` : '—'}
                      </dd>
                    </div>
                  </dl>
                  <p className="rounded-xl bg-ink-850 px-3 py-2 text-xs text-ink-400">
                    {aiStatus.data.message}
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Cuenta" description="Estado y verificación." />
            <CardBody className="pt-0">
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between">
                  <span className="text-ink-400">Correo</span>
                  <span className="truncate pl-3 text-ink-200">{user?.email}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-ink-400">Verificación</span>
                  <Badge tone={user?.is_verified ? 'success' : 'warning'}>
                    <ShieldCheck className="mr-1 inline size-3" />
                    {user?.is_verified ? 'Verificada' : 'Pendiente'}
                  </Badge>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-ink-400">Último acceso</span>
                  <span className="text-ink-200">
                    {user?.last_login_at ? formatDate(user.last_login_at) : '—'}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-ink-400">Zona horaria</span>
                  <span className="text-ink-200">{user?.timezone ?? '—'}</span>
                </li>
              </ul>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
