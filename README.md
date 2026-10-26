<div align="center">

# STUDIA AI

**Plataforma de aprendizaje inteligente para estudiantes universitarios**

*Study smarter. Learn better.*

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)

</div>

---

## ¿Qué es STUDIA AI?

STUDIA AI no es un CRUD con un chatbot pegado. La IA está integrada en el flujo de estudio completo: sube tus documentos, el sistema los indexa mediante **chunking + embeddings + vector store**, y desde ese momento el chat, los resúmenes, las preguntas y las flashcards se fundamentan en **tu** material real, citando las fuentes.

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| **API** | FastAPI · Uvicorn · Pydantic v2 |
| **ORM / Migraciones** | SQLAlchemy 2.0 · Alembic |
| **Base de datos** | SQLite (dev) · PostgreSQL (prod) |
| **Auth** | JWT (PyJWT · bcrypt) |
| **IA / RAG** | Ollama · OpenAI-compatible · provider `local` (offline) |
| **Parsing** | PyPDF · python-docx |
| **Frontend** | React 19 · TypeScript 6 · Vite 8 · TailwindCSS 4 |
| **Data fetching** | TanStack Query v5 |
| **Routing** | React Router v7 |
| **Linting** | Ruff (backend) · OXLint (frontend) |
| **Testing** | Pytest · Vitest |

---

## Estructura del repositorio

```
STUDIA-IA/
├── backend/          # FastAPI app (app/, alembic/, tests/)
├── frontend/         # Vite + React SPA
├── docs/             # Documentación adicional
├── .env.example      # Plantilla de variables de entorno
└── README.md
```

---

## Setup

### Prerequisitos

- Python >= 3.11
- Node.js >= 20
- *(Opcional)* PostgreSQL >= 15 · Ollama para LLM local

### 1 · Variables de entorno

```bash
cp .env.example .env
# Edita .env con tus valores (SECRET_KEY, DATABASE_URL, AI_PROVIDER, etc.)
```

### 2 · Backend

```bash
cd backend

# Crear entorno virtual e instalar dependencias
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Aplicar migraciones
alembic upgrade head

# Levantar servidor (http://localhost:8000)
uvicorn app.main:app --reload
```

> API Docs disponibles en `http://localhost:8000/docs`

### 3 · Frontend

```bash
cd frontend

npm install

# Asegurate de que VITE_API_URL en .env apunte al backend
npm run dev   # http://localhost:5173
```

---

## Proveedores de IA

Configura `AI_PROVIDER` en `.env`:

| Valor | Descripción |
|---|---|
| `local` | Offline, determinista. Sin configuración extra. Ideal para demos. |
| `ollama` | LLM local vía Ollama runtime. Requiere `OLLAMA_BASE_URL` y modelo descargado. |
| `openai` | Cualquier endpoint compatible (OpenAI, Groq, OpenRouter). Requiere `OPENAI_API_KEY`. |

---

## Scripts útiles

```bash
# Backend
pytest                          # Correr tests
ruff check . && ruff format .   # Lint + format

# Frontend
npm run lint                    # OXLint
npm run build                   # Build de producción (dist/)
```

---

## Licencia

MIT © STUDIA AI
