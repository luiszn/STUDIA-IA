"""Pytest fixtures: isolated SQLite database per test, ASGI transport client."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.models import User


@pytest.fixture(scope="session")
def engine() -> Generator:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    """A session on a database that only contains this test's data.

    ``StaticPool`` hands out the same connection to every ``connect()``, so an
    outer transaction cannot be used to isolate tests. Recreating the schema is
    fast on in-memory SQLite and impossible to leak.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def client(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "estudiante@studia.ai",
            "password": "Secret1234",
            "full_name": "Ana Restrepo",
            "university": "Universidad Nacional",
            "career": "Ingeniería de Sistemas",
        },
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


@pytest.fixture
def other_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="otro@studia.ai",
        hashed_password=hash_password("Secret1234"),
        full_name="Carlos Pérez",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def other_user_token(other_user: User) -> str:
    return create_access_token(other_user.id)


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    """A realistic academic text used by the RAG tests."""
    path = tmp_path / "redes.txt"
    path.write_text(
        "Redes de computadores — clase 03\n\n"
        "Subnetting es la técnica que permite dividir una red IP en subredes más pequeñas. "
        "El mask se aplica bit a bit: los bits del prefijo se conservan en 1 y el resto "
        "se completan con 0.\n\n"
        "Máscara de subred: una dirección IPv4 tiene 32 bits. Si el prefijo es /24, la máscara "
        "es 255.255.255.0, lo que equivale a 256 direcciones, de las cuales 254 son asignables "
        "porque dos quedan reservadas: la dirección de red y la de difusión.\n\n"
        "Protocolos de transporte: TCP es orientado a conexión, fiable y ordenado; ofrece "
        "control de flujo y de congestión. UDP es sin conexión, rápido y de tamaño fijo, y se "
        "usa en streaming, VoIP y juegos donde la latencia importa más que la fiabilidad.\n\n"
        "El protocolo ARP traduce direcciones IP a direcciones MAC dentro de la red local, "
        "y resuelve la tabla ARP con entradas estáticas y dinámicas.\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
async def course_payload() -> dict:
    return {
        "code": "REDES-101",
        "name": "Redes de Computadores",
        "professor": "Dra. Martha Ríos",
        "credits": 4,
        "semester": "2026-1",
        "description": "Fundamentos de redes, TCP/IP y subnetting.",
        "color": "#FF6B00",
    }