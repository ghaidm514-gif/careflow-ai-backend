"""Request/response schemas for the Phase A triage API."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import Language


class CreateSessionRequest(BaseModel):
    language: Language


class SessionResponse(BaseModel):
    session_id: UUID
    language: Language
    created_at: datetime


class CreateTriageRequest(BaseModel):
    session_id: UUID
    description: str = Field(min_length=1, max_length=2000)


class QuestionPayload(BaseModel):
    question_id: str
    text: str
    question_type: str


class RecommendationPayload(BaseModel):
    recommendation_id: UUID
    recommended_service: str
    urgency_level: str
    rationale: str
    confidence: float
    confidence_reason: str
    rule_triggered: Optional[str]
    sequence_number: int


class TriageStateResponse(BaseModel):
    request_id: UUID
    status: str
    classification: Optional[str]
    language: str
    escalated: bool
    emergency_message: Optional[str] = None
    next_question: Optional[QuestionPayload] = None
    recommendation: Optional[RecommendationPayload] = None


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=2000)


class MessagePayload(BaseModel):
    role: str
    content: str
    message_type: str
    created_at: datetime


class AnswerPayload(BaseModel):
    question_id: str
    question_text: str
    user_answer: str


class SafetyFlagPayload(BaseModel):
    rule_code: str
    severity: str
    description: str
    action_taken: str


class RequestDetailResponse(BaseModel):
    request_id: UUID
    session_id: UUID
    status: str
    classification: Optional[str]
    language: str
    initial_description: str
    urgency_level: Optional[str]
    recommended_service: Optional[str]
    created_at: datetime
    messages: list[MessagePayload]
    answers: list[AnswerPayload]
    safety_flags: list[SafetyFlagPayload]
    recommendation: Optional[RecommendationPayload]


def state_from_result(result: dict[str, Any]) -> TriageStateResponse:
    request = result["request"]
    rec = result.get("recommendation")
    question = result.get("next_question")
    return TriageStateResponse(
        request_id=request.request_id,
        status=request.status.value,
        classification=request.classification.value if request.classification else None,
        language=request.language.value,
        escalated=bool(result.get("escalated")),
        emergency_message=result.get("emergency_message"),
        next_question=QuestionPayload(**question) if question else None,
        recommendation=_rec_payload(rec) if rec else None,
    )


def _rec_payload(rec: Any) -> RecommendationPayload:
    return RecommendationPayload(
        recommendation_id=rec.recommendation_id,
        recommended_service=rec.recommended_service.value,
        urgency_level=rec.urgency_level.value,
        rationale=rec.rationale,
        confidence=rec.confidence,
        confidence_reason=rec.confidence_reason,
        rule_triggered=rec.rule_triggered,
        sequence_number=rec.sequence_number,
    )


def detail_from_result(result: dict[str, Any]) -> RequestDetailResponse:
    request = result["request"]
    rec = result.get("recommendation")
    return RequestDetailResponse(
        request_id=request.request_id,
        session_id=request.session_id,
        status=request.status.value,
        classification=request.classification.value if request.classification else None,
        language=request.language.value,
        initial_description=request.initial_description,
        urgency_level=request.urgency_level.value if request.urgency_level else None,
        recommended_service=request.recommended_service.value
        if request.recommended_service
        else None,
        created_at=request.created_at,
        messages=[
            MessagePayload(
                role=m.role, content=m.content, message_type=m.message_type, created_at=m.created_at
            )
            for m in result["messages"]
        ],
        answers=[
            AnswerPayload(
                question_id=a.question_id, question_text=a.question_text, user_answer=a.user_answer
            )
            for a in result["answers"]
        ],
        safety_flags=[
            SafetyFlagPayload(
                rule_code=f.rule_code,
                severity=f.severity.value,
                description=f.description,
                action_taken=f.action_taken,
            )
            for f in result["flags"]
        ],
        recommendation=_rec_payload(rec) if rec else None,
    )
