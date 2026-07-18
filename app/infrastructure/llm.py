"""LLM provider implementations."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class MockLLMProvider:
    """Deterministic mock LLM for testing."""

    def __init__(self):
        self.call_count = 0

    async def classify_intake(
        self,
        user_input: str,
        language: str,
    ) -> dict[str, Any]:
        """Mock intake classification."""
        self.call_count += 1
        lower_input = user_input.lower()

        if any(word in lower_input for word in ["reschedule", "appointment", "administrative"]):
            return {
                "classification": "administrative",
                "extracted_info": {"request_type": "appointment"},
                "confidence": 0.95,
            }

        if any(word in lower_input for word in ["pain", "symptom", "fever", "chest", "health"]):
            return {
                "classification": "healthcare",
                "extracted_info": {"has_symptoms": True},
                "confidence": 0.92,
            }

        return {
            "classification": "unclear",
            "extracted_info": {},
            "confidence": 0.50,
        }

    async def generate_triage_question(
        self,
        request_id: str,
        conversation_history: list[LLMMessage],
        language: str,
        collected_answers: dict[str, str],
    ) -> dict[str, Any]:
        """Mock triage question generation."""
        self.call_count += 1
        num_answers = len(collected_answers)

        if num_answers == 0:
            return {
                "status": "ask_question",
                "question": {
                    "question_id": "q1",
                    "text": "When did your symptoms start?",
                    "question_type": "symptom",
                },
                "confidence": 0.88,
            }

        if num_answers >= 3:
            return {
                "status": "complete",
                "question": None,
                "confidence": 0.90,
            }

        return {
            "status": "ask_question",
            "question": {
                "question_id": f"q{num_answers + 1}",
                "text": "Tell me more about your symptoms.",
                "question_type": "symptom",
            },
            "confidence": 0.85,
        }

    async def generate_recommendation(
        self,
        request_id: str,
        classification: str,
        conversation_history: list[LLMMessage],
        triage_answers: dict[str, str],
        urgency_estimate: str,
        language: str,
    ) -> dict[str, Any]:
        """Mock recommendation generation."""
        self.call_count += 1

        if classification == "administrative":
            return {
                "recommended_service": "administrative_service",
                "urgency_level": "low",
                "rationale": "Administrative request",
                "confidence_score": 0.95,
            }

        return {
            "recommended_service": "primary_care",
            "urgency_level": "medium",
            "rationale": "Healthcare query",
            "confidence_score": 0.82,
        }
