"""LLM provider port — the application depends on this Protocol, never on a
concrete provider. Mock/Claude/OpenAI implementations live in infrastructure
and satisfy it structurally."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMProviderPort(Protocol):
    async def classify_intake(self, user_input: str, language: str) -> dict[str, Any]: ...

    async def generate_triage_question(
        self,
        request_id: str,
        conversation_history: list[LLMMessage],
        language: str,
        collected_answers: dict[str, str],
    ) -> dict[str, Any]: ...

    async def generate_recommendation(
        self,
        request_id: str,
        classification: str,
        conversation_history: list[LLMMessage],
        triage_answers: dict[str, str],
        urgency_estimate: str,
        language: str,
    ) -> dict[str, Any]: ...
