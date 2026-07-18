"""Tests for domain enums."""

from app.domain.enums import Language, RequestStatus, UrgencyLevel


def test_language_enum_values():
    """Language enum has expected values."""
    assert Language.ENGLISH.value == "en"
    assert Language.ARABIC.value == "ar"


def test_request_status_has_lifecycle():
    """RequestStatus covers full lifecycle."""
    statuses = [s.value for s in RequestStatus]
    assert "pending" in statuses
    assert "closed" in statuses


def test_urgency_level_values():
    """UrgencyLevel has all severity levels."""
    levels = [u.value for u in UrgencyLevel]
    assert "low" in levels
    assert "emergency" in levels
