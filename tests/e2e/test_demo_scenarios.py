"""End-to-end demo scenarios through the real API (mock LLM, SQLite)."""


def _create_session(client, language="en"):
    response = client.post("/api/v1/sessions", json={"language": language})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def _create_request(client, session_id, description):
    response = client.post(
        "/api/v1/triage/requests",
        json={"session_id": session_id, "description": description},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_scenario_a_chest_pain_breathing_emergency(client):
    """Chest pain → breathing question → 'yes' → deterministic Emergency."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "I have chest pain")

    assert state["status"] == "in_triage"
    assert state["classification"] == "healthcare"
    assert state["next_question"]["question_id"] == "q_breathing"
    assert state["escalated"] is False

    response = client.post(
        f"/api/v1/triage/requests/{state['request_id']}/answers",
        json={"question_id": "q_breathing", "answer": "yes"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["escalated"] is True
    assert result["status"] == "safety_alert"
    assert result["recommendation"]["recommended_service"] == "emergency_department"
    assert result["recommendation"]["urgency_level"] == "emergency"
    assert result["recommendation"]["rule_triggered"] == "CHEST_PAIN_AND_DIFFICULTY_BREATHING"
    assert result["emergency_message"]

    detail = client.get(f"/api/v1/triage/requests/{state['request_id']}").json()
    assert detail["safety_flags"][0]["rule_code"] == "CHEST_PAIN_AND_DIFFICULTY_BREATHING"
    assert detail["safety_flags"][0]["severity"] == "critical"


def test_scenario_b_sick_leave_administrative(client):
    """Sick leave → administrative route, no clinical questions."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "I need a sick leave note for work")

    assert state["classification"] == "administrative"
    assert state["status"] == "recommendation_ready"
    assert state["next_question"] is None
    assert state["recommendation"]["recommended_service"] == "administrative_service"
    assert state["recommendation"]["urgency_level"] == "low"

    detail = client.get(f"/api/v1/triage/requests/{state['request_id']}").json()
    assert detail["answers"] == []  # no triage questions were asked
    assert detail["safety_flags"] == []


def test_scenario_c_sore_throat_primary_care(client):
    """Sore throat → sequential questions → Primary Care."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "I have a sore throat")

    assert state["status"] == "in_triage"
    answers = {"q_duration": "two days", "q_fever": "no", "q_swallow": "yes"}
    result = state
    asked = []
    while result["next_question"] is not None:
        question_id = result["next_question"]["question_id"]
        asked.append(question_id)
        response = client.post(
            f"/api/v1/triage/requests/{state['request_id']}/answers",
            json={"question_id": question_id, "answer": answers[question_id]},
        )
        assert response.status_code == 200, response.text
        result = response.json()

    assert asked == ["q_duration", "q_fever", "q_swallow"]  # one question at a time
    assert len(asked) <= 5
    assert result["status"] == "recommendation_ready"
    assert result["escalated"] is False
    assert result["recommendation"]["recommended_service"] == "primary_care"


def test_scenario_a_arabic(client):
    """Scenario A works fully in Arabic."""
    session_id = _create_session(client, language="ar")
    state = _create_request(client, session_id, "عندي ألم في الصدر")

    assert state["classification"] == "healthcare"
    question = state["next_question"]
    assert question["question_id"] == "q_breathing"
    assert "التنفس" in question["text"]  # Arabic question text

    response = client.post(
        f"/api/v1/triage/requests/{state['request_id']}/answers",
        json={"question_id": "q_breathing", "answer": "نعم"},
    )
    result = response.json()
    assert result["escalated"] is True
    assert result["recommendation"]["recommended_service"] == "emergency_department"
    assert "997" in result["emergency_message"]


def test_immediate_emergency_on_description(client):
    """Severe bleeding in the initial description escalates before any LLM."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "My father has severe bleeding from his arm")
    assert state["escalated"] is True
    assert state["status"] == "safety_alert"
    assert state["recommendation"]["rule_triggered"] == "SEVERE_BLEEDING"


def test_loss_of_consciousness_rule(client):
    """Loss of consciousness triggers immediate emergency."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "My colleague fainted and passed out")
    assert state["escalated"] is True
    assert state["recommendation"]["rule_triggered"] == "LOSS_OF_CONSCIOUSNESS"


def test_answer_after_escalation_rejected(client):
    """No answers accepted after the workflow is stopped by safety."""
    session_id = _create_session(client)
    state = _create_request(client, session_id, "severe bleeding everywhere")
    response = client.post(
        f"/api/v1/triage/requests/{state['request_id']}/answers",
        json={"question_id": "q_x", "answer": "hello"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REQUEST_STATE_CONFLICT"


def test_unknown_request_returns_404(client):
    response = client.get("/api/v1/triage/requests/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
