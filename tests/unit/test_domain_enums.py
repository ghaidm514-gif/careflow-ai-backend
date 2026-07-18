"""Tests for domain enums."""

import json

from app.domain.enums import (
    Language,
    Permission,
    RecommendedService,
    RequestClassification,
    RequestStatus,
    SafetyFlagSeverity,
    SafetyRuleCategory,
    StaffRole,
    UrgencyLevel,
)


def test_language_enum_values():
    """Language enum has exactly English and Arabic."""
    assert Language.ENGLISH.value == "en"
    assert Language.ARABIC.value == "ar"
    assert len(Language) == 2


def test_language_round_trip():
    """Language values deserialize back to the same member."""
    assert Language(Language.ENGLISH.value) is Language.ENGLISH


def test_request_status_lifecycle():
    """RequestStatus covers the full workflow lifecycle."""
    statuses = {s.value for s in RequestStatus}
    expected = {
        "pending",
        "intake_complete",
        "in_triage",
        "triage_complete",
        "safety_alert",
        "awaiting_recommendation",
        "recommendation_ready",
        "staff_review",
        "closed",
    }
    assert expected == statuses


def test_request_classification_values():
    """RequestClassification has all three outcomes."""
    values = {c.value for c in RequestClassification}
    assert values == {"administrative", "healthcare", "unclear"}


def test_urgency_level_values():
    """UrgencyLevel covers low through emergency."""
    values = {u.value for u in UrgencyLevel}
    assert values == {"low", "medium", "high", "emergency"}


def test_recommended_service_values():
    """RecommendedService includes all six routing destinations."""
    values = {s.value for s in RecommendedService}
    assert values == {
        "administrative_service",
        "virtual_consultation",
        "primary_care",
        "urgent_care",
        "emergency_department",
        "human_review",
    }


def test_safety_flag_severity_values():
    """SafetyFlagSeverity has info, warning, critical."""
    values = {s.value for s in SafetyFlagSeverity}
    assert values == {"info", "warning", "critical"}


def test_safety_rule_category_values():
    """SafetyRuleCategory has all management categories."""
    values = {c.value for c in SafetyRuleCategory}
    assert values == {"emergency", "urgent", "quality", "system"}


def test_staff_role_values():
    """StaffRole defines the three staff roles."""
    values = {r.value for r in StaffRole}
    assert values == {"triage_nurse", "administrator", "supervisor"}


def test_permission_values():
    """Permission covers all required operations."""
    values = {p.value for p in Permission}
    assert "view_request" in values
    assert "close_request" in values
    assert "manage_staff" in values
    assert "view_audit_log" in values


def test_enums_are_json_serializable():
    """String enums serialize directly to JSON."""
    payload = json.dumps({"language": Language.ENGLISH.value, "status": RequestStatus.CLOSED.value})
    assert payload == '{"language": "en", "status": "closed"}'
