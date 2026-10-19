import {
  ArrowRight,
  BrainCircuit,
  CalendarCheck,
  FileSearch,
  GraduationCap,
  Layers,
  MessageSquareText,
  Sparkles,
  TrendingUp,
} from 'lucide-react'

import { LinkButton } from '@/components/ui/Button'

const FEATURES = [
  {
    icon: GraduationCap,
    title: 'Cursos y progreso real',
    body: 'Materias, créditos, tareas y notas en un solo lugar. Cada curso muestra su avance, pendientes y promedio.',
  },
  {
    icon: Layers,
    title: 'Flashcards con repetición espaciada',
    body: 'El algoritmo SM-2 decide cuándo repites cada tarjeta. Sin obsesionarte con las statistics.',
  },
  {
    icon: FileSearch,
    title: 'Tus documentos, entendidos',
    body: 'Sube PDF, DOCX o TXT. STUDIA extrae el texto, lo indexa y responde citando el fragmento exacto.',
  },
  {
    icon: MessageSquareText,
    title: 'Asistente con contexto',
    body: 'Pregunta sobre tu material y recibe respuestas con citas verificables, no invenciones.',
  },
  {
    icon: Sparkles,
    title: 'Generadores con IA',
    body: 'Resúmenes, preguntas tipo examen, tarjetas y planes de estudio alineados a tu próxima evaluación.',
  },
  {
    icon: TrendingUp,
    title: 'Rendimiento y temas débiles',
    body: 'Detecta dónde estás flojo con evidencia y te propone la acción concreta para recuperarlo.',
  },
]

const WORKFLOW = [
  {
    step: '01',
    title: 'Carga tu semestre',
    body: 'Crea tus cursos, pega el programa y registra tareas, exámenes y notas.',
  },
  {
    step: '02',
    title: 'Sube el material',
    body: 'Apuntes, textos guía, slides en PDF. El motor los procesa y los hace buscables.',
  },
  {
    step: '03',
    title: ' Estudia con foco',
    body: 'Un plan diario que se adapta a tus fechas reales y a tu disponibilidad de tiempo.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-ink-850/80 bg-ink-950/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <span className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-flame-400 font-display text-lg font-bold text-ink-950">
              S
            </span>
            <span className="font-display text-lg font-semibold tracking-tight">
              STUDIA <span className="text-flame-400">AI</span>
            </span>
          </span>
          <nav className="flex items-center gap-2">
            <LinkButton to="/login" variant="ghost" size="sm">
              Entrar
            </LinkButton>
            <LinkButton to="/register" size="sm">
              Crear cuenta
            </LinkButton>
          </nav>
        </div>
      </header>

      {/* hero */}
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              'radial-gradient(50rem 30rem at 50% -10%, rgb(255 122 26 / 0.18), transparent 70%)',
          }}
          aria-hidden
        />
        <div className="relative mx-auto max-w-6xl px-6 pt-24 pb-20 text-center sm:pt-32">
          <span className="inline-flex items-center gap-2 rounded-full border border-flame-400/25 bg-flame-400/10 px-3 py-1 text-xs text-flame-200">
            <Sparkles className="size-3.5" />
            assistants que conocen tu material
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl font-display text-4xl leading-[1.05] font-bold tracking-tight sm:text-6xl">
            Estudia menos por obligación.
            <span className="block text-flame-400">Entiende más por método.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base text-ink-300 sm:text-lg">
            STUDIA AI convierte tus apuntes, syllabus y evaluaciones en un plan de estudio que se
            adapta a tu tiempo real — y te explica el porqué de cada recomendación.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <LinkButton to="/register" size="lg" rightIcon={<ArrowRight className="size-4" />}>
              Empezar gratis
            </LinkButton>
            <LinkButton to="/login" size="lg" variant="outline">
              Ya tengo cuenta
            </LinkButton>
          </div>
          <p className="mt-4 text-xs text-ink-500">
            Sin tarjeta. Tus datos y documentos quedan privados por diseño.
          </p>
        </div>
      </section>

      {/* workflow */}
      <section className="mx-auto max-w-6xl px-6 pb-8">
        <div className="grid gap-4 md:grid-cols-3">
          {WORKFLOW.map((item) => (
            <div key={item.step} className="panel panel-hover p-6">
              <span className="font-display text-sm font-semibold text-flame-400">{item.step}</span>
              <h3 className="mt-3 text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-400">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* features */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
          Todo lo que necesitas para un semestre aprobado
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="panel panel-hover group p-6">
              <span className="grid size-11 place-items-center rounded-xl bg-flame-400/12 text-flame-300 transition group-hover:bg-flame-400/20">
                <feature.icon className="size-5" />
              </span>
              <h3 className="mt-4 text-base font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-400">{feature.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ai callout */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <div className="panel relative overflow-hidden p-8 sm:p-12">
          <div
            className="pointer-events-none absolute inset-0 opacity-60"
            style={{
              backgroundImage:
                'radial-gradient(30rem 20rem at 80% 0%, rgb(255 122 26 / 0.16), transparent 70%)',
            }}
            aria-hidden
          />
          <div className="relative grid gap-8 lg:grid-cols-2 lg:items-center">
            <div>
              <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
                Pregunta en lenguaje natural y recibe <span className="text-flame-400">citas</span>
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-300">
                Cada respuesta grounded en tus documentos incluye el fragmento del que salió. Si la
                fuente no está en tu material, te lo decimos en vez de inventar.
              </p>
              <div className="mt-6 flex flex-wrap gap-2 text-xs text-ink-400">
                <span className="rounded-lg border border-ink-700 px-3 py-1.5">PDF · DOCX · TXT</span>
                <span className="rounded-lg border border-ink-700 px-3 py-1.5">
                  Búsqueda semántica
                </span>
                <span className="rounded-lg border border-ink-700 px-3 py-1.5">
                  Motor local sin conexion
                </span>
              </div>
            </div>
            <div className="rounded-2xl border border-ink-750 bg-ink-950/70 p-4 font-mono text-[0.8rem] leading-relaxed">
              <p className="text-ink-500">// pregunta</p>
              <p className="mt-1 text-ink-200">¿Diferencia entre máscara de subred y mascara?</p>
              <p className="mt-4 text-ink-500">// respuesta</p>
              <p className="mt-1 text-ink-300">
                La mascara limita el alcance de una red…
                <span className="mt-3 block border-l-2 border-flame-400/60 pl-3 text-xs text-ink-400">
                  📄 Redes clase 03 · fragmento 2 — «una direccion IPv4 tiene 32 bits…»
                </span>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* closing */}
      <section className="mx-auto max-w-6xl px-6 pb-24 text-center">
        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-ink-400">
          <span className="flex items-center gap-2">
            <BrainCircuit className="size-4 text-flame-400" /> IA explicable
          </span>
          <span className="flex items-center gap-2">
            <CalendarCheck className="size-4 text-flame-400" /> Planes con fechas reales
          </span>
          <span className="flex items-center gap-2">
            <Layers className="size-4 text-flame-400" /> Repetición espaciada
          </span>
        </div>
        <div className="mt-8">
          <LinkButton to="/register" size="lg" rightIcon={<ArrowRight className="size-4" />}>
            Crear mi cuenta
          </LinkButton>
        </div>
      </section>

      <footer className="border-t border-ink-850 px-6 py-8 text-center text-xs text-ink-500">
        STUDIA AI — study smarter, learn better.
      </footer>
    </div>
  )
}
