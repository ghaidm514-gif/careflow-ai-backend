"""LLM provider implementations.

MockLLMProvider: deterministic, no network, drives the three demo scenarios.
ClaudeLLMProvider can be added later behind the same interface without
touching domain or application code.
"""

from dataclasses import dataclass
from typing import Any

from app.application.llm_port import LLMMessage

_ = LLMMessage  # re-exported for provider implementations and tests


def _has_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


ADMIN_TERMS = [
    "sick leave",
    "sick note",
    "reschedule",
    "appointment",
    "certificate",
    "اجازة مرضية",
    "إجازة مرضية",
    "اجازه",
    "موعد",
    "تقرير طبي",
    "شهادة",
]
CHEST_TERMS = ["chest", "صدر"]
THROAT_TERMS = ["sore throat", "throat", "حلق", "التهاب الحلق", "بلعوم"]
HEALTH_TERMS = [
    "pain",
    "fever",
    "cough",
    "sick",
    "hurt",
    "symptom",
    "الم",
    "ألم",
    "حرارة",
    "سخونة",
    "سعال",
    "مريض",
    "تعب",
    "اعراض",
    "أعراض",
]


@dataclass(frozen=True)
class _Question:
    question_id: str
    text_en: str
    text_ar: str
    question_type: str

    def text(self, language: str) -> str:
        return self.text_ar if language == "ar" else self.text_en


CHEST_FLOW = [
    _Question(
        "q_breathing",
        "Do you also have difficulty breathing?",
        "هل تعاني أيضاً من صعوبة في التنفس؟",
        "symptom",
    ),
    _Question("q_duration", "When did the chest pain start?", "متى بدأ ألم الصدر؟", "duration"),
    _Question(
        "q_severity",
        "How severe is the pain from 1 to 10?",
        "ما شدة الألم من 1 إلى 10؟",
        "severity",
    ),
]

THROAT_FLOW = [
    _Question(
        "q_duration",
        "How long have you had the sore throat?",
        "منذ متى تعاني من التهاب الحلق؟",
        "duration",
    ),
    _Question("q_fever", "Do you have a fever?", "هل لديك حرارة؟", "symptom"),
    _Question(
        "q_swallow",
        "Can you swallow liquids normally?",
        "هل تستطيع بلع السوائل بشكل طبيعي؟",
        "severity",
    ),
]

GENERIC_FLOW = [
    _Question("q_main", "What is your main symptom?", "ما هو العرض الرئيسي لديك؟", "symptom"),
    _Question(
        "q_duration", "How long has this been going on?", "منذ متى وهذه الحالة مستمرة؟", "duration"
    ),
    _Question("q_severity", "How severe is it from 1 to 10?", "ما شدتها من 1 إلى 10؟", "severity"),
]


def _flow_for(description: str) -> list[_Question]:
    if _has_any(description, CHEST_TERMS):
        return CHEST_FLOW
    if _has_any(description, THROAT_TERMS):
        return THROAT_FLOW
    return GENERIC_FLOW


class MockLLMProvider:
    """Deterministic scenario-driven mock. Makes no network calls."""

    def __init__(self) -> None:
        self.call_count = 0

    async def classify_intake(self, user_input: str, language: str) -> dict[str, Any]:
        self.call_count += 1
        if _has_any(user_input, ADMIN_TERMS):
            return {
                "classification": "administrative",
                "extracted_info": {"type": "admin"},
                "confidence": 0.95,
            }
        if _has_any(user_input, CHEST_TERMS + THROAT_TERMS + HEALTH_TERMS):
            return {
                "classification": "healthcare",
                "extracted_info": {"has_symptoms": True},
                "confidence": 0.92,
            }
        return {"classification": "unclear", "extracted_info": {}, "confidence": 0.40}

    async def generate_triage_question(
        self,
        request_id: str,
        conversation_history: list[LLMMessage],
        language: str,
        collected_answers: dict[str, str],
    ) -> dict[str, Any]:
        self.call_count += 1
        description = conversation_history[0].content if conversation_history else ""
        flow = _flow_for(description)
        for question in flow:
            if question.question_id not in collected_answers:
                return {
                    "status": "ask_question",
                    "question": {
                        "question_id": question.question_id,
                        "text": question.text(language),
                        "question_type": question.question_type,
                    },
                    "confidence": 0.9,
                }
        return {"status": "complete", "question": None, "confidence": 0.9}

    async def generate_recommendation(
        self,
        request_id: str,
        classification: str,
        conversation_history: list[LLMMessage],
        triage_answers: dict[str, str],
        urgency_estimate: str,
        language: str,
    ) -> dict[str, Any]:
        self.call_count += 1
        description = conversation_history[0].content if conversation_history else ""

        if classification == "administrative":
            return {
                "recommended_service": "administrative_service",
                "urgency_level": "low",
                "rationale": "Administrative request; no clinical assessment required.",
                "confidence_score": 0.95,
                "confidence_reason": "Clear administrative intent.",
                "staff_summary": "Patient requests an administrative service (e.g. sick leave note).",
            }

        if classification == "healthcare":
            if _has_any(description, THROAT_TERMS):
                return {
                    "recommended_service": "primary_care",
                    "urgency_level": "low",
                    "rationale": "Sore throat without red flags; primary care within 48 hours.",
                    "confidence_score": 0.85,
                    "confidence_reason": "Common presentation, no emergency indicators.",
                    "staff_summary": "Sore throat, no red flags. Recommend primary care appointment.",
                }
            return {
                "recommended_service": "primary_care",
                "urgency_level": "medium",
                "rationale": "Symptoms warrant clinical evaluation in primary care.",
                "confidence_score": 0.75,
                "confidence_reason": "No emergency indicators detected.",
                "staff_summary": "Non-emergency symptoms. Recommend primary care.",
            }

        return {
            "recommended_service": "human_review",
            "urgency_level": "low",
            "rationale": "Request unclear; staff review required.",
            "confidence_score": 0.40,
            "confidence_reason": "Could not classify the request.",
            "staff_summary": "Unclear request — needs human review.",
        }


Provider = MockLLMProvider  # future: select ClaudeLLMProvider via config


def build_llm_provider(provider_name: str) -> MockLLMProvider:
    """Factory: only the mock exists today; claude/openai arrive later."""
    return MockLLMProvider()
