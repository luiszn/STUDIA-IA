"""OpenAI-compatible provider (OpenAI, OpenRouter, Groq, local gateways...)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.ai.base import AICompletion, AIProvider, ChatMessage, ProviderHealth
from app.core.config import settings
from app.core.errors import AIProviderError
from app.core.logging import get_logger

logger = get_logger("app.ai.openai")


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        chat_model: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.chat_model = chat_model or settings.openai_chat_model
        self.embedding_model = embedding_model or settings.openai_embedding_model
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            if not self.api_key:
                raise AIProviderError("OPENAI_API_KEY is not configured.")
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(settings.ai_timeout_seconds, connect=10.0),
                headers={"Authorization": f"Bearer {self.api_key}"},
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
            "messages": (
                ([{"role": "system", "content": system}] if system else [])
                + [{"role": m.role, "content": m.content} for m in messages]
            ),
            "temperature": temperature if temperature is not None else settings.ai_temperature,
            "max_tokens": max_tokens or settings.ai_max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await self._http().post("/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Could not reach {self.base_url}: {exc.__class__.__name__}") from exc

        if response.status_code >= 400:
            logger.error("OpenAI error %s: %s", response.status_code, response.text[:300])
            raise AIProviderError(f"The AI provider rejected the request ({response.status_code}).")

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise AIProviderError("The AI provider returned no choices.")

        content = (choices[0].get("message") or {}).get("content") or ""
        content = self._strip_code_fence(content) if json_mode else content.strip()
        usage = data.get("usage") or {}

        return AICompletion(
            content=content,
            provider=self.name,
            model=data.get("model", self.chat_model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._http().post("/embeddings", json={"model": self.embedding_model, "input": texts})
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Could not reach {self.base_url}: {exc.__class__.__name__}") from exc

        if response.status_code >= 400:
            raise AIProviderError(f"Embedding request failed ({response.status_code}).")

        data = response.json()
        ordered = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        return [[float(value) for value in item["embedding"]] for item in ordered]

    async def health(self) -> ProviderHealth:
        if not self.api_key:
            return ProviderHealth(
                provider=self.name,
                available=False,
                model=self.chat_model,
                message="OPENAI_API_KEY is not configured.",
            )
        try:
            response = await self._http().get("/models")
        except httpx.HTTPError as exc:
            return ProviderHealth(
                provider=self.name,
                available=False,
                model=self.chat_model,
                message=f"Could not reach {self.base_url} ({exc.__class__.__name__}).",
            )
        available = response.status_code < 400
        return ProviderHealth(
            provider=self.name,
            available=available,
            model=self.chat_model,
            embedding_model=self.embedding_model,
            message="Provider is ready." if available else f"Status {response.status_code}.",
        )

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()


def parse_json_block(text: str) -> Any:
    """Best-effort JSON extraction for models that ignore `json_mode`."""
    from app.ai.rag.parsing import extract_json

    return extract_json(text)