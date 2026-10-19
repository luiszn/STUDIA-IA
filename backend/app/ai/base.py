"""Provider-agnostic AI contracts.

Nothing in the application imports `ollama` or `openai` directly: every feature
depends on `AIProvider` only. Swapping providers is a configuration change
(`AI_PROVIDER`), not a code change.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.errors import AIProviderError

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> ChatMessage:
        return cls(role="assistant", content=content)


class AICompletion(BaseModel):
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    #: True when the content was produced without a real LLM (offline mode).
    is_fallback: bool = False
    raw: dict[str, Any] | None = Field(default=None, exclude=True)


class ProviderHealth(BaseModel):
    provider: str
    available: bool
    model: str | None = None
    embedding_model: str | None = None
    message: str
    latency_ms: int | None = None


class AIProvider(ABC):
    """Interface implemented by every provider."""

    name: str = "base"
    supports_streaming: bool = False

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> AICompletion:
        """Return a single completion for a chat-style conversation."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Cheap readiness probe used by `/ai/status` and the dashboard."""

    @property
    def model_name(self) -> str:
        return self.name

    @property
    def embedding_model_name(self) -> str:
        return f"{self.name}-embed"

    async def complete_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> AICompletion:
        """Convenience wrapper for one-shot prompts."""
        started = time.perf_counter()
        result = await self.complete(
            [ChatMessage.user(prompt)],
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )
        result.latency_ms = result.latency_ms or int((time.perf_counter() - started) * 1000)
        return result

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        if not vectors:
            raise AIProviderError("The embedding provider returned no vectors.")
        return vectors[0]

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars/token) used when a provider omits usage."""
        return max(1, len(text) // 4)