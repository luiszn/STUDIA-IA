"""Prompt library for STUDIA AI.

Prompts are versioned constants (not scattered strings) so behaviour can be
audited and tuned in one place. Language: English instructions, Spanish-first
output because the target users are Spanish speaking undergraduates.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import Difficulty, QuestionType, StudyLevel, SummaryStyle
from app.utils.text import excerpt

STUDENT_CONTEXT_MARKER = "=== CONTEXTO DEL ESTUDIANTE ==="

ACADEMIC_IDENTITY = (
    "Eres STUDIA AI, un asistente académico de una plataforma universitaria. "
    "Ayudas a estudiantes a estudiar mejor: explicas conceptos, resúmenes documentos, "
    "creas preguntas y flashedcards, y planificas sesiones de estudio. "
    "Reglas innegociables:\n"
    "1) Si el usuario aporta contexto documental, baste tu respuesta EN ese material y "
    "no inventes datos que no aparezcan allí.\n"
    "2) Si el contexto es insuficiente, dilo explícitamente y pide el documento o el "
    "detalle que falta. Nunca rellenes huecos con suposiciones presentadas como hechos.\n"
    "3) Separa siempre la realidad de lo generado: cuando uses razonamiento externo o "
    "conocimiento general, márcalo como complementario.\n"
    "4) Responde en español claro y académico. Usa Markdown (títulos, listas, negritas) y "
    "bloques de código cuando corresponda.\n"
    "5) Sé breve y accionable. Si el estudiante tiene tareas o exámenes próximos, "
    "sugiere el siguiente paso concreto."
)

STRICT_JSON_RULE = (
    "Responde EXCLUSIVAMENTE con un objeto JSON válido, sin texto antes ni después, "
    "sin bloque de código y sin comentarios."
)


def academic_system_prompt() -> str:
    return ACADEMIC_IDENTITY


def build_student_context(
    *,
    courses: list[str],
    upcoming: list[str],
    average_grade: float | None,
    pending_tasks: int,
    study_minutes_week: int,
    weak_topics: list[str] | None = None,
) -> str:
    """Real application data that grounds the assistant in the user's reality."""
    lines = [
        "Datos reales del estudiante (base de datos de STUDIA AI):",
        f"- Cursos: {', '.join(courses) if courses else 'sin cursos registrados'}",
        f"- Tareas pendientes: {pending_tasks}",
        f"- Próximas actividades: {'; '.join(upcoming) if upcoming else 'ninguna'}",
        f"- Promedio actual: {f'{average_grade:.1f}/100' if average_grade is not None else 'sin notas'}",
        f"- Tiempo de estudio esta semana: {study_minutes_week} minutos",
    ]
    if weak_topics:
        lines.append(f"- Temas débiles detectados: {', '.join(weak_topics)}")
    return "\n".join(lines)


def rag_block(context: str) -> str:
    return (
        f"{STUDENT_CONTEXT_MARKER}\n"
        f"{context}\n\n"
        "Usa estos fragmentos para responder. Cita las fuentes relevantes al final "
        "con el formato: `Fuentes: <nombre de archivo> (p. N)`."
    )


SUMMARY_TEMPLATES: dict[SummaryStyle, dict[str, str]] = {
    SummaryStyle.SHORT: {
        "goal": "un resumen de 3 a 5 frases que capture la idea central",
        "shape": "3-5 frases, sin listas",
    },
    SummaryStyle.DETAILED: {
        "goal": "un resumen exhaustivo que preserves detalles, definiciones y datos",
        "shape": "secciones con títulos, listas y todos los datos relevantes",
    },
    SummaryStyle.EXAM: {
        "goal": "los puntos que con mayor probabilidad entran en un examen",
        "shape": "lista numerada de 5-8 puntos, cada uno en una frase",
    },
    SummaryStyle.KEY_POINTS: {
        "goal": "los puntos clave accionables para memorizar",
        "shape": "viñetas de 6-10 puntos, una idea por viñeta",
    },
}


def summarize_prompt(
    *, context: str, style: SummaryStyle, student_data: str, focus: str | None = None
) -> str:
    template = SUMMARY_TEMPLATES[style]
    focus_line = f"\nEnfócate específicamente en: {focus}." if focus else ""
    return (
        f"{student_data}\n\n{STUDENT_CONTEXT_MARKER}\n{context}\n\n"
        f"Tarea: genera {template['goal']}. Formato: {template['shape']}.{focus_line}\n"
        "Responde solo con el resumen, sin preámbulo."
    )


QUESTIONS_SCHEMA_HINT = """{
  "questions": [
    {
      "id": "q1",
      "type": "multiple_choice|true_false|short_answer|essay",
      "prompt": "enunciado",
      "options": [{"id": "A", "text": "..."}],
      "correct_answer": "A (id) o el texto de la respuesta",
      "correct_option_id": "A",
      "explanation": "por qué es correcta, citando el material",
      "difficulty": "easy|medium|hard",
      "topic": "tema"
    }
  ]
}"""


def questions_prompt(
    *,
    context: str,
    count: int,
    types: list[QuestionType],
    difficulty: Difficulty,
    topics: list[str],
    student_data: str,
) -> str:
    return (
        f"{student_data}\n\n{STUDENT_CONTEXT_MARKER}\n{context}\n\n"
        f"Tarea: crea exactamente {count} preguntas de evaluación sobre el material anterior.\n"
        f"- Tipos permitidos: {', '.join(item.value for item in types)}\n"
        f"- Dificultad: {difficulty.value}\n"
        f"- Temas: {', '.join(topics) if topics else 'los dominantes del material'}\n"
        "- Para multiple_choice y true_false incluye las opciones con identificadores "
        "A, B, C, D y marca la correcta.\n"
        "- La explicación debe citar el fragmento del material del que sale la respuesta.\n"
        f"- No inventes información ausente del material.\n\n"
        f"{QUESTIONS_SCHEMA_HINT}\n{STRICT_JSON_RULE}"
    )


FLASHCARDS_SCHEMA_HINT = """{
  "flashcards": [
    {
      "front": "pregunta corta (máx. 25 palabras)",
      "back": "respuesta directa (máx. 60 palabras)",
      "explanation": "contexto adicional opcional",
      "topic": "tema",
      "difficulty": "easy|medium|hard"
    }
  ]
}"""


def flashcards_prompt(
    *, context: str, count: int, difficulty: Difficulty, focus: str | None, student_data: str
) -> str:
    focus_line = f"- Céntrate en: {focus}\n" if focus else ""
    return (
        f"{student_data}\n\n{STUDENT_CONTEXT_MARKER}\n{context}\n\n"
        f"Tarea: crea exactamente {count} flashcards para repasar este material.\n"
        "- Una idea por tarjeta; la cara trasera responde de forma autosuficiente.\n"
        "- Evita tarjetas triviales tipo definiciones de palabras.\n"
        f"{focus_line}- Dificultad objetivo: {difficulty.value}\n"
        "- Prioriza los conceptos con más peso en el material.\n\n"
        f"{FLASHCARDS_SCHEMA_HINT}\n{STRICT_JSON_RULE}"
    )


STUDY_PLAN_SCHEMA_HINT = """{
  "title": "nombre del plan",
  "rationale": "por qué este plan funciona, citando datos del estudiante",
  "weak_topics": ["tema1", "tema2"],
  "days": [
    {
      "day": 1,
      "title": "título del día",
      "focus": "tema central",
      "theory_minutes": 60,
      "practice_minutes": 30,
      "review_minutes": 30,
      "objectives": ["objetivo1", "objetivo2"],
      "resources": ["recurso del estudiante", "flashcards"]
    }
  ]
}"""


LEVEL_GUIDANCE: dict[StudyLevel, str] = {
    StudyLevel.BEGINNER: "conceptos desde cero, analogías y definiciones",
    StudyLevel.INTERMEDIATE: "aplicación práctica, casos y ejercicios",
    StudyLevel.ADVANCED: "profundidad, excepciones, casos límite y análisis",
}


def study_plan_prompt(
    *,
    course_name: str,
    exam_date: str | None,
    total_days: int,
    daily_minutes: int,
    level: StudyLevel,
    focus_topics: list[str],
    weak_topics: list[str],
    context: str,
    student_data: str,
    exam_topics: str | None = None,
) -> str:
    topics = focus_topics or weak_topics or []
    return (
        f"{student_data}\n\n"
        f"Curso: {course_name}\n"
        f"Examen: {exam_date or 'sin fecha definida'}\n"
        f"Días disponibles: {total_days}\n"
        f"Minutos por día: {daily_minutes}\n"
        f"Nivel: {level.value} ({LEVEL_GUIDANCE[level]})\n"
        f"Temas prioritarios: {', '.join(topics) if topics else 'los dominantes del material'}\n"
        f"Temas anunciados por el profesor: {exam_topics or 'no informados'}\n\n"
        f"{STUDENT_CONTEXT_MARKER}\n{context or '(sin material indexado)'}\n\n"
        f"Tarea: diseña un plan de estudio de {total_days} días, {daily_minutes} minutos por día, "
        f"para {course_name}. La suma de theory_minutes + practice_minutes + review_minutes debe "
        f"ser exactamente {daily_minutes} en cada día. Distribuye la dificultad de forma "
        f"progresiva y deja los temas más débiles al principio. Incluye objetivos concretos.\n"
        f"{'Si no hay material indexado, usa los temas prioritarios y tu conocimiento general, y decláralo en rationale.' if not context.strip() else ''}\n\n"
        f"{STUDY_PLAN_SCHEMA_HINT}\n{STRICT_JSON_RULE}"
    )


def explain_topic_prompt(
    *, topic: str, level: StudyLevel, context: str, student_data: str
) -> str:
    return (
        f"{student_data}\n\n"
        f"{STUDENT_CONTEXT_MARKER}\n{context or '(sin material indexado para este tema)'}\n\n"
        f"Tarea: explica «{topic}» al nivel {level.value}. "
        f"{LEVEL_GUIDANCE[level]}.\n"
        "- Si el material indexado cubre el tema, basate en él.\n"
        "- Si no lo cubre, dilo claramente y explica con conocimiento general marcándolo "
        "como complementario.\n"
        "- Cierra con 3 puntos clave y una sugerencia de práctica.\n"
        "Formato Markdown."
    )


WEAK_TOPICS_SCHEMA_HINT = """{"topics": [{"topic": "tema", "confidence": 0.0, "evidence": ["..."]}]}"""


def weak_topics_prompt(*, context: str, student_data: str) -> str:
    return (
        f"{student_data}\n\n{STUDENT_CONTEXT_MARKER}\n{context}\n\n"
        "Tarea: identifica los temas donde el estudiante tiene más riesgo de fallar, "
        "usando sus grades, tareas pendientes y el material indexado. "
        "Devuelve solo los más relevantes, con confianza entre 0 y 1 y la evidencia concreta "
        f"que lo sustenta (notas bajas, tareas sin entregar,Material complejo).\n\n"
        f"{WEAK_TOPICS_SCHEMA_HINT}\n{STRICT_JSON_RULE}"
    )


def conversation_title_prompt(first_message: str) -> str:
    return (
        "Genera un título de máximo 6 palabras para esta conversación. "
        "Devuelve solo el título, sin comillas ni punto final.\n\n"
        f"Mensaje: {excerpt(first_message, 300)}"
    )


def build_messages(*, instruction: str, student_data: str) -> dict[str, Any]:
    """Small helper so services build prompts consistently."""
    return {"system": academic_system_prompt(), "user": f"{student_data}\n\n{instruction}"}