"""Triage orchestration: intake → safety → questions → recommendation.

Safety runs BEFORE every LLM call and can never be overridden by it.
Max questions comes from configuration. The service owns the workflow;
the API layer owns the transaction commit.
"""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID, uuid4

from app.application.llm_port import LLMMessage, LLMProviderPort
from app.application.ports import (
    IAIRecommendationRepository,
    IAuditLogRepository,
    IConversationMessageRepository,
    ISafetyFlagRepository,
    IServiceRequestRepository,
    ITriageAnswerRepository,
    IUserSessionRepository,
)
from app.domain.entities import (
    AIRecommendation,
    AuditLog,
    ConversationMessage,
    SafetyFlag,
    ServiceRequest,
    TriageAnswer,
    UserSession,
)
from app.domain.enums import (
    Language,
    RecommendedService,
    RequestClassification,
    RequestStatus,
    UrgencyLevel,
)
from app.domain.exceptions import (
    RequestStateConflictException,
    ResourceNotFoundException,
)
from app.safety.engine import SafetyEngine

EMERGENCY_MESSAGE = {
    "en": "Your symptoms may indicate an emergency. Please call 997 or go to the nearest emergency department immediately.",
    "ar": "قد تشير أعراضك إلى حالة طارئة. يرجى الاتصال بالرقم 997 أو التوجه فوراً إلى أقرب قسم طوارئ.",
}

WORKFLOW_VERSION = "hackathon-a-1"
MODEL_NAME_MOCK = "mock-deterministic"


@dataclass
class Repos:
    sessions: IUserSessionRepository
    requests: IServiceRequestRepository
    messages: IConversationMessageRepository
    answers: ITriageAnswerRepository
    flags: ISafetyFlagRepository
    recommendations: IAIRecommendationRepository
    audits: IAuditLogRepository


class TriageService:
    def __init__(
        self,
        repos: Repos,
        llm: LLMProviderPort,
        safety: SafetyEngine,
        max_questions: int,
    ):
        self.repos = repos
        self.llm = llm
        self.safety = safety
        self.max_questions = max_questions

    # ── session ────────────────────────────────────────────────────────────
    async def create_session(self, language: Language) -> UserSession:
        return await self.repos.sessions.create(UserSession(session_id=uuid4(), language=language))

    # ── intake ─────────────────────────────────────────────────────────────
    async def create_request(self, session_id: UUID, description: str) -> dict[str, Any]:
        session = await self.repos.sessions.get_by_id(session_id)
        if session is None:
            raise ResourceNotFoundException(details={"resource": "session"})

        request = await self.repos.requests.create(
            ServiceRequest(
                request_id=uuid4(),
                session_id=session_id,
                initial_description=description,
                language=session.language,
                status=RequestStatus.PENDING,
            )
        )
        await self._add_message(request.request_id, "user", description, "user_response")

        # SAFETY FIRST: deterministic check on the raw description, before LLM
        evaluation = self.safety.evaluate(description, [])
        if evaluation.triggered:
            return await self._escalate_emergency(request, evaluation)

        intake = await self.llm.classify_intake(description, session.language.value)
        classification = RequestClassification(intake["classification"])
        request.classification = classification
        await self._audit(
            request.request_id,
            "INTAKE_CLASSIFIED",
            {"classification": classification.value, "confidence": intake["confidence"]},
        )

        if classification is RequestClassification.ADMINISTRATIVE:
            request.status = RequestStatus.RECOMMENDATION_READY
            await self.repos.requests.update(request)
            rec = await self._store_recommendation(request, await self._llm_recommendation(request))
            return {
                "request": request,
                "recommendation": rec,
                "next_question": None,
                "escalated": False,
            }

        if classification is RequestClassification.UNCLEAR:
            request.status = RequestStatus.RECOMMENDATION_READY
            await self.repos.requests.update(request)
            rec = await self._store_recommendation(request, await self._llm_recommendation(request))
            return {
                "request": request,
                "recommendation": rec,
                "next_question": None,
                "escalated": False,
            }

        # healthcare → first question
        request.status = RequestStatus.IN_TRIAGE
        await self.repos.requests.update(request)
        question = await self._next_question(request)
        return {
            "request": request,
            "recommendation": None,
            "next_question": question,
            "escalated": False,
        }

    # ── answers ────────────────────────────────────────────────────────────
    async def submit_answer(
        self, request_id: UUID, question_id: str, answer_text: str
    ) -> dict[str, Any]:
        request = await self.repos.requests.get_by_id(request_id)
        if request is None:
            raise ResourceNotFoundException(details={"resource": "request"})
        if request.status is not RequestStatus.IN_TRIAGE:
            raise RequestStateConflictException(
                details={"expected_status": "in_triage", "actual_status": request.status.value}
            )

        prior = await self.repos.answers.list_by_request(request_id)
        question_text = await self._last_question_text(request_id)
        await self.repos.answers.create(
            TriageAnswer(
                answer_id=uuid4(),
                request_id=request_id,
                question_id=question_id,
                question_text=question_text,
                user_answer=answer_text,
            )
        )
        await self._add_message(request_id, "user", answer_text, "user_response")

        # SAFETY AFTER EVERY ANSWER, BEFORE ANY NEW LLM CALL
        answered = [(a.question_id, a.user_answer) for a in prior] + [(question_id, answer_text)]
        evaluation = self.safety.evaluate(request.initial_description, answered)
        if evaluation.triggered:
            return await self._escalate_emergency(request, evaluation)

        if len(answered) >= self.max_questions:
            return await self._complete_triage(request)

        question = await self._next_question(request)
        if question is None:
            return await self._complete_triage(request)
        return {
            "request": request,
            "recommendation": None,
            "next_question": question,
            "escalated": False,
        }

    # ── read model ─────────────────────────────────────────────────────────
    async def get_request(self, request_id: UUID) -> dict[str, Any]:
        request = await self.repos.requests.get_by_id(request_id)
        if request is None:
            raise ResourceNotFoundException(details={"resource": "request"})
        return {
            "request": request,
            "messages": await self.repos.messages.list_by_request(request_id),
            "answers": await self.repos.answers.list_by_request(request_id),
            "flags": await self.repos.flags.list_by_request(request_id),
            "recommendation": await self.repos.recommendations.get_latest_for_request(request_id),
        }

    # ── internals ──────────────────────────────────────────────────────────
    async def _next_question(self, request: ServiceRequest) -> Optional[dict[str, str]]:
        answers = await self.repos.answers.list_by_request(request.request_id)
        output = await self.llm.generate_triage_question(
            request_id=str(request.request_id),
            conversation_history=[LLMMessage(role="user", content=request.initial_description)],
            language=request.language.value,
            collected_answers={a.question_id: a.user_answer for a in answers},
        )
        if output["status"] != "ask_question" or output["question"] is None:
            return None
        question: dict[str, str] = output["question"]
        await self._add_message(
            request.request_id, "assistant", question["text"], "triage_question"
        )
        return question

    async def _complete_triage(self, request: ServiceRequest) -> dict[str, Any]:
        request.status = RequestStatus.RECOMMENDATION_READY
        await self.repos.requests.update(request)
        rec = await self._store_recommendation(request, await self._llm_recommendation(request))
        return {
            "request": request,
            "recommendation": rec,
            "next_question": None,
            "escalated": False,
        }

    async def _llm_recommendation(self, request: ServiceRequest) -> dict[str, Any]:
        answers = await self.repos.answers.list_by_request(request.request_id)
        classification = request.classification.value if request.classification else "unclear"
        return await self.llm.generate_recommendation(
            request_id=str(request.request_id),
            classification=classification,
            conversation_history=[LLMMessage(role="user", content=request.initial_description)],
            triage_answers={a.question_id: a.user_answer for a in answers},
            urgency_estimate="medium",
            language=request.language.value,
        )

    async def _store_recommendation(
        self, request: ServiceRequest, output: dict[str, Any], rule_triggered: Optional[str] = None
    ) -> AIRecommendation:
        existing = await self.repos.recommendations.list_for_request(request.request_id)
        service = RecommendedService(output["recommended_service"])
        urgency = UrgencyLevel(output["urgency_level"])
        rec = await self.repos.recommendations.add(
            AIRecommendation(
                recommendation_id=uuid4(),
                request_id=request.request_id,
                recommended_service=service,
                urgency_level=urgency,
                rationale=output["rationale"],
                confidence=output["confidence_score"],
                confidence_reason=output["confidence_reason"],
                rule_triggered=rule_triggered,
                sequence_number=len(existing) + 1,
                model_provider="mock",
                model_name=MODEL_NAME_MOCK,
                workflow_version=WORKFLOW_VERSION,
            )
        )
        request.recommended_service = service
        request.urgency_level = urgency
        await self.repos.requests.update(request)
        await self._audit(
            request.request_id,
            "RECOMMENDATION_GENERATED",
            {"service": service.value, "urgency": urgency.value, "sequence": rec.sequence_number},
        )
        return rec

    async def _escalate_emergency(self, request: ServiceRequest, evaluation: Any) -> dict[str, Any]:
        assert evaluation.rule_code is not None and evaluation.severity is not None
        await self.repos.flags.create(
            SafetyFlag(
                flag_id=uuid4(),
                request_id=request.request_id,
                rule_code=evaluation.rule_code,
                severity=evaluation.severity,
                description=evaluation.description,
                action_taken=evaluation.action_taken,
            )
        )
        request.status = RequestStatus.SAFETY_ALERT
        request.classification = request.classification or RequestClassification.HEALTHCARE
        await self.repos.requests.update(request)
        await self._audit(
            request.request_id, "SAFETY_RULE_TRIGGERED", {"rule_code": evaluation.rule_code}
        )

        rec = await self._store_recommendation(
            request,
            {
                "recommended_service": RecommendedService.EMERGENCY_DEPARTMENT.value,
                "urgency_level": UrgencyLevel.EMERGENCY.value,
                "rationale": f"Deterministic safety rule {evaluation.rule_code} triggered.",
                "confidence_score": 1.0,
                "confidence_reason": "Deterministic rule; not an AI judgment.",
            },
            rule_triggered=evaluation.rule_code,
        )
        message = EMERGENCY_MESSAGE.get(request.language.value, EMERGENCY_MESSAGE["en"])
        await self._add_message(request.request_id, "assistant", message, "system_message")
        return {
            "request": request,
            "recommendation": rec,
            "next_question": None,
            "escalated": True,
            "emergency_message": message,
        }

    async def _add_message(
        self, request_id: UUID, role: str, content: str, message_type: str
    ) -> None:
        await self.repos.messages.create(
            ConversationMessage(
                message_id=uuid4(),
                request_id=request_id,
                role=role,
                content=content,
                message_type=message_type,
            )
        )

    async def _last_question_text(self, request_id: UUID) -> str:
        messages = await self.repos.messages.list_by_request(request_id)
        for message in reversed(messages):
            if message.message_type == "triage_question":
                return message.content
        return ""

    async def _audit(self, request_id: UUID, action: str, details: dict[str, Any]) -> None:
        await self.repos.audits.create(
            AuditLog(
                log_id=uuid4(),
                request_id=request_id,
                actor="ai_system",
                action=action,
                details=details,
                model_provider="mock",
                model_name=MODEL_NAME_MOCK,
                workflow_version=WORKFLOW_VERSION,
            )
        )
