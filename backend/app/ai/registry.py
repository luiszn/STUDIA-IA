"""Provider registry with graceful degradation.

`AI_PROVIDER` selects the primary runtime. If that runtime is unreachable we do
**not** return a 502 to the student: the `LocalProvider` takes over and every
response is flagged as fallback content so the UI can disclose it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.ai.base import AIProvider, ProviderHealth
from app.ai.providers.local import LocalProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.ai.registry")

_HEALTH_TTL_SECONDS = 60.0


@dataclass
class ResolvedProvider:
    provider: AIProvider
    health: ProviderHealth
    used_fallback: bool


_provider: AIProvider | None = None
_health_cache: tuple[float, ProviderHealth] | None = None


def build_provider(name: str | None = None) -> AIProvider:
    """Instantiate the provider described by configuration."""
    provider_name = (name or settings.ai_provider).lower()
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "local":
        return LocalProvider()
    raise ValueError(f"Unknown AI provider: {provider_name}")


def get_ai_provider() -> AIProvider:
    """Cached primary provider instance."""
    global _provider
    if _provider is None:
        _provider = build_provider()
        logger.info("AI provider initialised: %s", _provider.name)
    return _provider


async def get_health(force: bool = False) -> ProviderHealth:
    global _health_cache
    now = time.monotonic()
    if not force and _health_cache and now - _health_cache[0] < _HEALTH_TTL_SECONDS:
        return _health_cache[1]

    health = await get_ai_provider().health()
    _health_cache = (now, health)
    return health


async def resolve_provider() -> ResolvedProvider:
    """Return a usable provider, degrading to the offline one when needed."""
    primary = get_ai_provider()
    if primary.name == "local":
        return ResolvedProvider(primary, await get_health(), used_fallback=False)

    health = await get_health()
    if health.available:
        return ResolvedProvider(primary, health, used_fallback=False)

    logger.warning("AI provider %s unavailable (%s) - using offline fallback", primary.name, health.message)
    fallback = LocalProvider()
    return ResolvedProvider(fallback, health, used_fallback=True)


async def reset_registry() -> None:
    """Test helper: drop cached provider and health."""
    global _provider, _health_cache
    if _provider is not None and hasattr(_provider, "aclose"):
        await _provider.aclose()  # type: ignore[attr-defined]
    _provider = None
    _health_cache = None