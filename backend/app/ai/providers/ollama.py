"""Ollama provider — local, privacy-friendly models (default AI runtime)."""

from __future__ import annotations

from typing import Any

import httpx

from app.ai.base import AICompletion, AIProvider, ChatMessage, ProviderHealth
from app.core.config import settings
from app.core.errors import AIProviderError
from app.core.logging import get_logger

logger = get_logger("app.ai.ollama")


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        chat_model: str | None = None,
        embedding_model: str | None = None,
        keep_alive: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.chat_model = chat_model or settings.ollama_chat_model
        self.embedding_model = embedding_model or settings.ollama_embedding_model
        self.keep_alive = keep_alive or settings.ollama_keep_alive
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ infra
    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(settings.ai_timeout_seconds, connect=5.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    @property
    def model_name(self) -> str:
        return self.chat_model

    @property
    def embedding_model_name(self) -> str:
        return self.embedding_model

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http().post(path, json=payload)
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Could not reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from exc

        if response.status_code >= 400:
            detail = response.text[:300]
            logger.error("Ollama error %s on %s: %s", response.status_code, path, detail)
            raise AIProviderError(f"Ollama rejected the request ({response.status_code}).")

        return response.json()

    # ------------------------------------------------------------------ chat
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> AICompletion:
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in ([ChatMessage.system(system)] if system else []) + messages
            ],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature if temperature is not None else settings.ai_temperature,
                "num_predict": max_tokens or settings.ai_max_tokens,
                **({"num_ctx": 8192} if json_mode else {}),
            },
        }
        data = await self._post("/api/chat", payload)
        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise AIProviderError("Ollama returned an empty completion.")
        return AICompletion(
            content=content,
            provider=self.name,
            model=data.get("model", self.chat_model),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            latency_ms=int(data.get("total_duration", 0) / 1_000_000),
        )

    # ------------------------------------------------------------ embeddings
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = await self._post(
            "/api/embed", {"model": self.embedding_model, "input": texts, "keep_alive": self.keep_alive}
        )
        vectors = data.get("embeddings") or []
        if len(vectors) != len(texts):
            raise AIProviderError("Ollama returned an unexpected number of embeddings.")
        return [[float(value) for value in vector] for vector in vectors]

    # ---------------------------------------------------------------- health
    async def health(self) -> ProviderHealth:
        try:
            response = await self._http().get("/api/tags")
        except httpx.HTTPError as exc:
            return ProviderHealth(
                provider=self.name,
                available=False,
                model=self.chat_model,
                embedding_model=self.embedding_model,
                message=f"Ollama is not reachable at {self.base_url} ({exc.__class__.__name__}).",
            )

        if response.status_code >= 400:
            return ProviderHealth(
                provider=self.name,
                available=False,
                model=self.chat_model,
                message=f"Ollama responded with status {response.status_code}.",
            )

        installed = {m.get("name", "") for m in response.json().get("models", [])}
        base_chat = self.chat_model.split(":")[0]
        has_chat = any(name == self.chat_model or name.split(":")[0] == base_chat for name in installed)
        has_embed = any(name.split(":")[0] == self.embedding_model.split(":")[0] for name in installed)

        if not has_chat:
            return ProviderHealth(
                provider=self.name,
                available=False,
                model=self.chat_model,
                embedding_model=self.embedding_model,
                message=f"Model `{self.chat_model}` is not installed. Run: ollama pull {self.chat_model}",
            )
        if not has_embed:
            return ProviderHealth(
                provider=self.name,
                available=True,
                model=self.chat_model,
                embedding_model=self.embedding_model,
                message=(
                    f"Chat model ready, but `{self.embedding_model}` is missing, so document "
                    f"retrieval is degraded. Run: ollama pull {self.embedding_model}"
                ),
            )
        return ProviderHealth(
            provider=self.name,
            available=True,
            model=self.chat_model,
            embedding_model=self.embedding_model,
            message="Ollama is ready.",
        )