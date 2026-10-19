"""Offline provider: real study tooling with no LLM attached.

Why it exists: STUDIA AI must stay demonstrable (and testable) on a machine with
no Ollama and no API key. This provider performs **extractive** NLP over the
user's own documents — keyword-ranked sentence selection, cloze-based question
generation, definitional flashcard mining, hashed lexical embeddings — and
honestly labels every answer as fallback content (`is_fallback=True`) so the UI
can disclose that no LLM generated it.
"""

from __future__ import annotations

import hashlib
import math
import random
import re
from typing import Any

from app.ai.base import AICompletion, AIProvider, ChatMessage, ProviderHealth
from app.ai.rag.parsing import ensure_list, extract_json
from app.core.config import settings
from app.utils.text import (
    STOPWORDS,
    content_words,
    estimate_tokens,
    excerpt,
    keyword_scores,
    split_sentences,
    tokenize,
)

_DEFINITION = re.compile(
    r"^(?P<term>[A-ZÁÉÍÓÚÑ][\w\s\-]{2,48}?)\s*(?:es|son|se define como|significa|"
    r"se denomina|consiste en|se compone de)\s+(?P<definition>.{15,})$",
    re.IGNORECASE,
)
_COLON_DEFINITION = re.compile(r"^(?P<term>[\w\s\-]{2,48}):\s+(?P<definition>.{15,})$")
_BULLET = re.compile(r"^\s*[-*•]\s+")


class LocalProvider(AIProvider):
    name = "local"

    def __init__(self, dimensions: int | None = None, seed: int = 20260101) -> None:
        self.dimensions = dimensions or settings.embedding_dimensions
        self._random = random.Random(seed)

    # ------------------------------------------------------------------ meta
    @property
    def model_name(self) -> str:
        return "studia-offline-extractive"

    @property
    def embedding_model_name(self) -> str:
        return "studia-hashed-lexical"

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            available=True,
            model=self.model_name,
            embedding_model=self.embedding_model_name,
            message=(
                "Offline mode: no LLM connected. STUDIA AI answers extractively from your own "
                "documents. Set AI_PROVIDER=ollama (or openai) to enable generative answers."
            ),
        )

    # -------------------------------------------------------------- embeddings
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_sync(text) for text in texts]

    def _embed_sync(self, text: str) -> list[float]:
        """Hashed lexical embedding: word unigrams + bigrams + char 4-grams.

        Deterministic, dependency free and good enough for retrieval over a
        single user's own corpus.
        """
        vector = [0.0] * self.dimensions
        normalized = text.lower()
        words = tokenize(normalized)

        for word in words:
            self._add(vector, f"w:{word}", 1.0 + math.log1p(len(word) / 4))
        for first, second in zip(words, words[1:], strict=False):
            self._add(vector, f"b:{first}_{second}", 0.9)
        for index in range(0, max(0, len(normalized) - 3)):
            if not normalized[index].isalnum() and not normalized[index + 1].isalnum():
                continue
            self._add(vector, f"c:{normalized[index:index + 4]}", 0.35)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _add(vector: list[float], feature: str, weight: float) -> None:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % len(vector)
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * weight

    # ------------------------------------------------------------- completion
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> AICompletion:
        prompt = "\n\n".join(message.content for message in messages if message.role != "system")
        task = self._detect_task(system or "", prompt)
        content = self._render(task, prompt, system or "")

        prompt_tokens = self.estimate_tokens(prompt)
        completion_tokens = estimate_tokens(content)
        return AICompletion(
            content=content,
            provider=self.name,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            is_fallback=True,
        )

    # ------------------------------------------------------------------ tasks
    @staticmethod
    def _detect_task(system: str, prompt: str) -> str:
        haystack = f"{system}\n{prompt}".lower()
        if "json" in haystack and ("flashcard" in haystack or "tarjeta" in haystack):
            return "flashcards"
        if "json" in haystack and ("question" in haystack or "pregunta" in haystack):
            return "questions"
        if "json" in haystack and ("plan" in haystack or "plan de estudio" in haystack):
            return "study_plan"
        if "resum" in haystack:
            return "summary"
        if "weak topic" in haystack or "temas débiles" in haystack:
            return "weak_topics"
        return "chat"

    def _render(self, task: str, prompt: str, system: str) -> str:
        context = self._extract_context(prompt)
        handler = {
            "flashcards": self._render_flashcards,
            "questions": self._render_questions,
            "study_plan": self._render_study_plan,
            "summary": self._render_summary,
            "weak_topics": self._render_weak_topics,
            "chat": self._render_chat,
        }[task]
        return handler(prompt, context, system)

    @staticmethod
    def _extract_context(prompt: str) -> list[str]:
        """Pull the reference blocks the services append after a marker."""
        blocks: list[str] = []
        marker = "=== CONTEXTO DEL ESTUDIANTE ==="
        if marker in prompt:
            tail = prompt.split(marker, 1)[1]
            blocks = [
                block.strip()
                for block in re.split(r"\n---+\n", tail)
                if len(block.strip()) > 40
            ]
        if not blocks:
            body = re.sub(r"^.*?(?:\n\n)", "", prompt, count=1, flags=re.DOTALL)
            blocks = [block.strip() for block in re.split(r"\n---+\n", body) if len(block.strip()) > 40]
        return blocks

    # ------------------------------------------------------------- renderers
    def _render_chat(self, prompt: str, context: list[str], system: str) -> str:
        question = self._extract_question(prompt)
        if not context:
            return (
                "I'm running in **offline mode**, so I can only work with text that is already in "
                "this conversation.\n\n"
                "To give you a real answer, either:\n"
                "- upload your course material under **Documents** (then I'll ground my answer in it), or\n"
                "- set `AI_PROVIDER=ollama` and run `ollama pull llama3.2:3b` to enable generative answers.\n\n"
                f"You asked: _{excerpt(question, 200) or '…'}_"
            )

        keywords = set(content_words(question))
        scored: list[tuple[float, str]] = []
        for block in context:
            words = content_words(block)
            if not words:
                continue
            overlap = sum(1 for word in words if word in keywords)
            position_bonus = 1.0 - (context.index(block) / max(1, len(context) * 2))
            scored.append((overlap * position_bonus, block))

        scored.sort(key=lambda item: -item[0])
        best = [block for score, block in scored[:3] if score > 0] or context[:2]

        lines = [
            "**Offline answer** — extracted from your own material, no LLM was used.",
            "",
            f"On *{excerpt(question, 160) or 'your question'}*, your material says:",
            "",
        ]
        for block in best:
            sentences = split_sentences(block)
            # Lead with the sentences that actually answer the question; the
            # first two sentences of a chunk are not always the relevant ones.
            ranked = sorted(
                enumerate(sentences[:6]),
                key=lambda pair: (
                    -sum(1 for word in content_words(pair[1]) if word in keywords),
                    pair[0],
                ),
            )
            for _, sentence in ranked[:2]:
                lines.append(f"- {sentence.strip()}")
            lines.append("")
        lines.append(
            "> Want a full pedagogical explanation? Connect Ollama or an OpenAI-compatible model — "
            "the same endpoint will answer generatively with these same sources."
        )
        return "\n".join(lines).strip()

    @staticmethod
    def _extract_question(prompt: str) -> str:
        for line in reversed(prompt.strip().splitlines()):
            cleaned = line.strip().lstrip("#").strip()
            if cleaned and not cleaned.endswith(":") and "===" not in cleaned:
                return cleaned
        return prompt.strip()

    def _render_summary(self, prompt: str, context: list[str], system: str) -> str:
        style = self._detect_style(system, prompt)
        joined = " ".join(context)
        sentences = self._rank_sentences(joined)[: 5 if style == "short" else 9]
        if not sentences:
            return "There is not enough readable text in the selected documents to summarise yet."

        if style == "key_points":
            body = "\n".join(f"- {sentence}" for sentence in sentences[:8])
            return f"### Key points\n\n{body}"
        if style == "exam":
            body = "\n".join(f"{index}. {sentence}" for index, sentence in enumerate(sentences[:6], 1))
            return (
                "### Exam-ready summary\n\n"
                f"{body}\n\n"
                "_Revise these points first, then attempt past papers from your Documents tab._"
            )
        if style == "detailed":
            body = "\n\n".join(sentences)
            return f"### Detailed summary\n\n{body}"
        return f"### Summary\n\n{' '.join(sentences[:3])}"

    @staticmethod
    def _detect_style(system: str, prompt: str) -> str:
        haystack = f"{system}\n{prompt}".lower()
        for marker, style in (
            ("key_points", "key_points"),
            ("exam", "exam"),
            ("detailed", "detailed"),
            ("short", "short"),
        ):
            if marker in haystack:
                return style
        return "short"

    def _render_questions(self, prompt: str, context: list[str], system: str) -> str:
        joined = " ".join(context)
        sentences = self._rank_sentences(joined, min_words=6)[:6]
        if not sentences:
            return '{"questions": []}'

        difficulty = "medium"
        haystack = f"{system}\n{prompt}".lower()
        for level in ("easy", "medium", "hard"):
            if f"difficulty: {level}" in haystack or f"difficulty={level}" in haystack:
                difficulty = level

        asked = {"easy": 4, "medium": 6, "hard": 8}.get(difficulty, 6)
        questions: list[dict[str, Any]] = []
        for index, sentence in enumerate(sentences[:asked], start=1):
            key_term = self._pick_key_term(sentence)
            if not key_term:
                continue
            if index % 3 == 0:
                questions.append(
                    {
                        "id": f"q{index}",
                        "type": "true_false",
                        "prompt": f"Verdadero o falso: {sentence}",
                        "options": [
                            {"id": "A", "text": "Verdadero"},
                            {"id": "B", "text": "Falso"},
                        ],
                        "correct_answer": "A",
                        "correct_option_id": "A",
                        "explanation": f"Extraído literalmente del material: “{excerpt(sentence)}”.",
                        "difficulty": difficulty,
                    }
                )
            else:
                distractors = self._distractors(key_term, joined)
                options = [{"id": "A", "text": key_term}, *[
                    {"id": chr(66 + i), "text": term} for i, term in enumerate(distractors)
                ]]
                self._random.shuffle(options)
                correct_id = next(option["id"] for option in options if option["text"] == key_term)
                questions.append(
                    {
                        "id": f"q{index}",
                        "type": "multiple_choice",
                        "prompt": sentence.replace(key_term, "____", 1),
                        "options": options,
                        "correct_answer": correct_id,
                        "correct_option_id": correct_id,
                        "explanation": f"La respuesta correcta es «{key_term}».",
                        "difficulty": difficulty,
                    }
                )

        import json

        return json.dumps({"questions": questions}, ensure_ascii=False)

    def _render_flashcards(self, prompt: str, context: list[str], system: str) -> str:
        joined = " ".join(context)
        pairs = self._mined_pairs(joined)
        if not pairs:
            return '{"flashcards": []}'
        import json

        return json.dumps({"flashcards": pairs}, ensure_ascii=False)

    def _render_study_plan(self, prompt: str, context: list[str], system: str) -> str:
        joined = " ".join(context)
        topics = [term for term, _ in keyword_scores(joined, top_k=10)] or ["Repaso general"]
        days = int(re.search(r"total_days[:=]\s*(\d+)", f"{system}\n{prompt}").group(1)) if re.search(
            r"total_days[:=]\s*(\d+)", f"{system}\n{prompt}"
        ) else 7
        minutes = int(re.search(r"daily_minutes[:=]\s*(\d+)", f"{system}\n{prompt}").group(1)) if re.search(
            r"daily_minutes[:=]\s*(\d+)", f"{system}\n{prompt}"
        ) else 120
        course = re.search(r"course:\s*(.+)", f"{system}\n{prompt}", re.IGNORECASE)

        plan_days = []
        for day in range(1, days + 1):
            focus = topics[(day - 1) % len(topics)]
            plan_days.append(
                {
                    "day": day,
                    "title": f"{focus}",
                    "focus": focus,
                    "theory_minutes": max(20, int(minutes * 0.5)),
                    "practice_minutes": max(10, int(minutes * 0.3)),
                    "review_minutes": max(10, int(minutes * 0.2)),
                    "objectives": [
                        f"Understand {focus}",
                        "Practise {focus} with your own examples",
                        f"Review yesterday's {topics[(day - 2) % len(topics)]}",
                    ],
                    "resources": ["Your uploaded documents", "Flashcards deck"],
                }
            )
        import json

        return json.dumps(
            {
                "title": f"Plan de estudio — {course.group(1).strip() if course else 'Curso'}",
                "rationale": (
                    f"Plan generated offline from the {len(topics)} most relevant terms in your material, "
                    f"spread over {days} days at {minutes} minutes per day."
                ),
                "weak_topics": topics[:5],
                "days": plan_days,
            },
            ensure_ascii=False,
        )

    def _render_weak_topics(self, prompt: str, context: list[str], system: str) -> str:
        import json

        return json.dumps({"topics": [term for term, _ in keyword_scores(" ".join(context), top_k=8)]})

    # ---------------------------------------------------------------- helpers
    def _rank_sentences(self, text: str, min_words: int = 5) -> list[str]:
        sentences = [sentence.strip() for sentence in split_sentences(text)]
        sentences = [sentence for sentence in sentences if len(tokenize(sentence)) >= min_words]
        if not sentences:
            return []
        weights = dict(keyword_scores(text, top_k=40))
        scored = []
        for position, sentence in enumerate(sentences):
            words = content_words(sentence)
            if not words:
                continue
            score = sum(weights.get(word, 0.0) for word in words) / math.sqrt(len(words))
            score *= 1.0 + position / (len(sentences) * 3)  # mild lead bias
            scored.append((score, position, sentence))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [sentence for _, _, sentence in scored]

    def _pick_key_term(self, sentence: str) -> str | None:
        words = [word for word in tokenize(sentence) if word not in STOPWORDS and len(word) > 3]
        if not words:
            return None
        frequency = {word: sentence.lower().count(word) for word in set(words)}
        return max(frequency, key=lambda word: (frequency[word], len(word)))

    def _distractors(self, term: str, corpus: str) -> list[str]:
        pool = [
            word
            for word, _ in keyword_scores(corpus, top_k=40)
            if word != term.lower() and abs(len(word) - len(term)) <= 6
        ]
        return pool[:3] or ["No aplica", "Ninguna de las anteriores", "Ver material"]

    def _mined_pairs(self, text: str) -> list[dict[str, str]]:
        pairs: list[dict[str, str]] = []
        seen: set[str] = set()

        for block in text.splitlines():
            line = block.strip()
            if not line:
                continue
            match = _DEFINITION.match(line) or _COLON_DEFINITION.match(line)
            if not match:
                continue
            term = match.group("term").strip().rstrip(":")
            definition = match.group("definition").strip()
            key = term.lower()
            if key in seen or len(term) > 48 or len(definition) < 20:
                continue
            seen.add(key)
            pairs.append({"front": f"¿Qué es {term}?", "back": definition, "topic": term})

        if len(pairs) < 4:
            for sentence in self._rank_sentences(text):
                term = self._pick_key_term(sentence)
                if not term or term.lower() in seen:
                    continue
                statement = sentence.replace(term, "____", 1)
                if statement == sentence:
                    continue
                seen.add(term.lower())
                pairs.append(
                    {
                        "front": f"Completa: {statement}",
                        "back": term,
                        "topic": term,
                    }
                )
                if len(pairs) >= 14:
                    break
        return pairs[:14]


def _as_json(text: str) -> Any:
    try:
        return extract_json(text)
    except ValueError:
        return ensure_list(text)