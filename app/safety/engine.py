"""Deterministic, LLM-free safety rule engine.

Runs on the initial description and after every answer, BEFORE any LLM call.
The LLM can never override a triggered rule. Bilingual (Arabic + English)
keyword matching over normalized text.
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.domain.enums import SafetyFlagSeverity

_ARABIC_DIACRITICS = re.compile(r"[ً-ْ]")

CHEST_PAIN_TERMS = [
    "chest pain",
    "chest pressure",
    "chest tightness",
    "الم الصدر",
    "الم في الصدر",
    "ألم الصدر",
    "ضغط في الصدر",
    "الم صدر",
]
BREATHING_TERMS = [
    "difficulty breathing",
    "shortness of breath",
    "can't breathe",
    "cannot breathe",
    "trouble breathing",
    "صعوبة التنفس",
    "ضيق التنفس",
    "ضيق في التنفس",
    "لا استطيع التنفس",
]
BLEEDING_TERMS = [
    "severe bleeding",
    "bleeding heavily",
    "bleeding a lot",
    "heavy bleeding",
    "uncontrolled bleeding",
    "نزيف حاد",
    "نزيف شديد",
    "نزيف غزير",
]
CONSCIOUSNESS_TERMS = [
    "loss of consciousness",
    "lost consciousness",
    "unconscious",
    "passed out",
    "fainted",
    "فقدان الوعي",
    "فقد الوعي",
    "اغمي عليه",
    "أغمي علي",
    "اغمي علي",
]
AFFIRMATIVE_TERMS = ["yes", "yeah", "yep", "نعم", "اي", "أجل", "ايوه", "ايوا"]

# question_ids whose affirmative answer implies breathing difficulty
BREATHING_QUESTION_IDS = {"q_breathing"}


_ARABIC_FOLDS = str.maketrans(
    {"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"}
)


def normalize(text: str) -> str:
    lowered = text.lower()
    lowered = _ARABIC_DIACRITICS.sub("", lowered)
    lowered = lowered.translate(_ARABIC_FOLDS)  # fold hamza/teh-marbuta variants
    lowered = re.sub(r"[^\w\s؀-ۿ]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(normalize(term) in text for term in terms)


@dataclass(frozen=True)
class SafetyEvaluation:
    """Result of a deterministic safety pass."""

    triggered: bool
    rule_code: Optional[str] = None
    severity: Optional[SafetyFlagSeverity] = None
    description: str = ""
    action_taken: str = ""


class SafetyEngine:
    """Evaluates the three frozen MVP red-flag rules. Pure and synchronous."""

    def evaluate(
        self,
        initial_description: str,
        answers: list[tuple[str, str]],  # (question_id, answer_text)
    ) -> SafetyEvaluation:
        full_text = normalize(" ".join([initial_description] + [answer for _, answer in answers]))

        breathing_affirmed = any(
            question_id in BREATHING_QUESTION_IDS
            and _contains_any(normalize(answer), AFFIRMATIVE_TERMS)
            for question_id, answer in answers
        )

        if _contains_any(full_text, CHEST_PAIN_TERMS) and (
            _contains_any(full_text, BREATHING_TERMS) or breathing_affirmed
        ):
            return SafetyEvaluation(
                triggered=True,
                rule_code="CHEST_PAIN_AND_DIFFICULTY_BREATHING",
                severity=SafetyFlagSeverity.CRITICAL,
                description="Chest pain with difficulty breathing detected",
                action_taken="EMERGENCY_ESCALATION",
            )

        if _contains_any(full_text, BLEEDING_TERMS):
            return SafetyEvaluation(
                triggered=True,
                rule_code="SEVERE_BLEEDING",
                severity=SafetyFlagSeverity.CRITICAL,
                description="Severe active bleeding detected",
                action_taken="EMERGENCY_ESCALATION",
            )

        if _contains_any(full_text, CONSCIOUSNESS_TERMS):
            return SafetyEvaluation(
                triggered=True,
                rule_code="LOSS_OF_CONSCIOUSNESS",
                severity=SafetyFlagSeverity.CRITICAL,
                description="Loss of consciousness detected",
                action_taken="EMERGENCY_ESCALATION",
            )

        return SafetyEvaluation(triggered=False)
