"""Phase A triage endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_triage_service
from app.application.triage_service import TriageService
from app.schemas.triage import (
    CreateSessionRequest,
    CreateTriageRequest,
    RequestDetailResponse,
    SessionResponse,
    SubmitAnswerRequest,
    TriageStateResponse,
    detail_from_result,
    state_from_result,
)

router = APIRouter(prefix="/api/v1", tags=["triage"])


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> SessionResponse:
    session = await service.create_session(body.language)
    return SessionResponse(
        session_id=session.session_id,
        language=session.language,
        created_at=session.created_at,
    )


@router.post(
    "/triage/requests", response_model=TriageStateResponse, status_code=status.HTTP_201_CREATED
)
async def create_triage_request(
    body: CreateTriageRequest,
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> TriageStateResponse:
    result = await service.create_request(body.session_id, body.description)
    return state_from_result(result)


@router.post("/triage/requests/{request_id}/answers", response_model=TriageStateResponse)
async def submit_answer(
    request_id: UUID,
    body: SubmitAnswerRequest,
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> TriageStateResponse:
    result = await service.submit_answer(request_id, body.question_id, body.answer)
    return state_from_result(result)


@router.get("/triage/requests/{request_id}", response_model=RequestDetailResponse)
async def get_triage_request(
    request_id: UUID,
    service: Annotated[TriageService, Depends(get_triage_service)],
) -> RequestDetailResponse:
    result = await service.get_request(request_id)
    return detail_from_result(result)
