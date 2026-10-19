"""STUDIA AI — FastAPI application entrypoint.

Study smarter. Learn better.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger("app.main")

DESCRIPTION = """
**STUDIA AI** — plataforma de aprendizaje inteligente para estudiantes universitarios.

STUDIA AI no es un CRUD con un chatbot pegado: la IA está integrada en el flujo de
estudio completo. Sube documentos, y el sistema los indexa (chunking + embeddings +
vector store) para que el chat, los resúmenes, las preguntas y las flashcards se
fundamenten en **tu** material, citando las fuentes.

### Qué puedes hacer
* Organizar cursos, tareas, evaluaciones y notas.
* Subir PDF / DOCX / TXT y estudiarlos con IA (RAG).
* Generar resúmenes, preguntas con nota y flashcards.
* Crear planes de estudio basados en exámenes y notas reales.
* Recibir recomendaciones calculadas con tus datos, no inventadas.

### Autenticación
Obtén un token en `POST /api/v1/auth/login` y envíalo como
`Authorization: Bearer <access_token>`.
""".strip()

TAGS_METADATA = [
    {"name": "auth", "description": "Registro, login, perfil y recuperación de contraseña."},
    {"name": "courses", "description": "Cursos y sus estadísticas."},
    {"name": "tasks", "description": "Tareas con estado, prioridad y fecha límite."},
    {"name": "exams", "description": "Evaluaciones programadas."},
    {"name": "grades", "description": "Notas, promedios, proyección y rendimiento."},
    {"name": "documents", "description": "Carga, extracción, troceado e indexación de material."},
    {"name": "flashcards", "description": "Tarjetas y repaso espaciado (SM-2)."},
    {"name": "study sessions", "description": "Registro de tiempo de estudio."},
    {"name": "studia-ai", "description": "Chat, RAG, resúmenes, preguntas, flashcards y planes."},
    {"name": "insights", "description": "Dashboard, calendario, búsqueda y recomendaciones."},
    {"name": "system", "description": "Salud del servicio y proveedores de IA."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "%s API ready · env=%s · db=%s · ai=%s",
        settings.app_name,
        settings.app_env,
        "sqlite" if settings.is_sqlite else "postgresql",
        settings.ai_provider,
    )
    yield
    logger.info("Shutting down %s API", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title="STUDIA AI API",
        description=DESCRIPTION,
        version="0.1.0",
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "STUDIA AI"},
        license_info={"name": "MIT"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"], summary="Liveness probe")
    async def health() -> dict[str, object]:
        from sqlalchemy import text

        from app.db.session import engine

        database = "up"
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            database = "down"
        return {
            "status": "ok" if database == "up" else "degraded",
            "app": settings.app_name,
            "environment": settings.app_env,
            "database": database,
            "ai_provider": settings.ai_provider,
            "version": app.version,
        }

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "STUDIA AI",
            "tagline": "Study smarter. Learn better.",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()