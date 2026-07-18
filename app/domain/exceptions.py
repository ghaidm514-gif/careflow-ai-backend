"""Domain exceptions — Application-level error handling."""

from typing import Any, Dict, Optional


class CareFlowException(Exception):
    """Base exception for all CareFlow domain errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
    ):
        self.message = message or self.message
        self.details = details or {}
        if code:
            self.code = code
        super().__init__(self.message)


class IdempotencyConflictException(CareFlowException):
    """409: Same idempotency key with different payload."""
    code = "IDEMPOTENCY_CONFLICT"
    http_status = 409
    message = "The same idempotency key was used with a different request payload."


class RequestStateConflictException(CareFlowException):
    """409: Invalid workflow state transition."""
    code = "REQUEST_STATE_CONFLICT"
    http_status = 409
    message = "This request is not in a state that accepts this operation."


class DuplicateActiveRequestException(CareFlowException):
    """409: Session already has an active request."""
    code = "DUPLICATE_ACTIVE_REQUEST"
    http_status = 409
    message = "This session already has an active request."


class QuestionAlreadyAnsweredException(CareFlowException):
    """409: Question has already been answered."""
    code = "QUESTION_ALREADY_ANSWERED"
    http_status = 409
    message = "This question has already been answered."


class LLMUnavailableException(CareFlowException):
    """502: LLM provider failure."""
    code = "LLM_UNAVAILABLE"
    http_status = 502
    message = "The recommendation system is temporarily unavailable."


class LLMTimeoutException(CareFlowException):
    """504: LLM provider timeout."""
    code = "LLM_TIMEOUT"
    http_status = 504
    message = "The system timed out while processing your request."
