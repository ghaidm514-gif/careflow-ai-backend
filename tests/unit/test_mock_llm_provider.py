"""Tests for MockLLMProvider — determinism, single-question invariant, no network."""

import pytest

from app.infrastructure.llm import MockLLMProvider


@pytest.mark.asyncio
async def test_classification_is_deterministic():
    """Same input always produces the same classification."""
    provider = MockLLMProvider()
    result1 = await provider.classify_intake("I want to reschedule my appointment", "en")
    result2 = await provider.classify_intake("I want to reschedule my appointment", "en")
    assert result1 == result2


@pytest.mark.asyncio
async def test_classifies_administrative_request():
    """Appointment rescheduling is classified as administrative."""
    provider = MockLLMProvider()
    result = await provider.classify_intake("I need to reschedule my appointment", "en")
    assert result["classification"] == "administrative"
    assert result["confidence"] > 0.9


@pytest.mark.asyncio
async def test_classifies_healthcare_request():
    """Symptom descriptions are classified as healthcare."""
    provider = MockLLMProvider()
    result = await provider.classify_intake("I have a fever and chest pain", "en")
    assert result["classification"] == "healthcare"


@pytest.mark.asyncio
async def test_classifies_unclear_request():
    """Ambiguous input is classified as unclear with low confidence."""
    provider = MockLLMProvider()
    result = await provider.classify_intake("hello", "en")
    assert result["classification"] == "unclear"
    assert result["confidence"] <= 0.6


@pytest.mark.asyncio
async def test_returns_exactly_one_question():
    """Triage output contains exactly one question per call."""
    provider = MockLLMProvider()
    result = await provider.generate_triage_question(
        request_id="req1",
        conversation_history=[],
        language="en",
        collected_answers={},
    )
    assert result["status"] == "ask_question"
    assert result["question"] is not None
    assert isinstance(result["question"]["text"], str)


@pytest.mark.asyncio
async def test_terminal_status_after_enough_answers():
    """After 3+ answers the provider returns complete with no question."""
    provider = MockLLMProvider()
    result = await provider.generate_triage_question(
        request_id="req1",
        conversation_history=[],
        language="en",
        collected_answers={"q_main": "a", "q_duration": "b", "q_severity": "c"},
    )
    assert result["status"] == "complete"
    assert result["question"] is None


@pytest.mark.asyncio
async def test_recommendation_for_administrative():
    """Administrative requests route to administrative_service."""
    provider = MockLLMProvider()
    result = await provider.generate_recommendation(
        request_id="req1",
        classification="administrative",
        conversation_history=[],
        triage_answers={},
        urgency_estimate="low",
        language="en",
    )
    assert result["recommended_service"] == "administrative_service"
    assert result["urgency_level"] == "low"


@pytest.mark.asyncio
async def test_recommendation_contains_confidence():
    """Recommendations carry a confidence score in [0, 1]."""
    provider = MockLLMProvider()
    result = await provider.generate_recommendation(
        request_id="req1",
        classification="healthcare",
        conversation_history=[],
        triage_answers={"q1": "Three days"},
        urgency_estimate="medium",
        language="en",
    )
    assert 0.0 <= result["confidence_score"] <= 1.0


@pytest.mark.asyncio
async def test_call_count_tracks_invocations():
    """The mock records how many times it was invoked."""
    provider = MockLLMProvider()
    await provider.classify_intake("test", "en")
    await provider.classify_intake("test", "en")
    assert provider.call_count == 2
