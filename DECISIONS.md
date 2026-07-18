# Frozen Design Decisions

## D-001 — Answer correction is out of scope for the MVP (Phase 3)

- `TriageAnswer` is immutable (frozen dataclass, append-only table, PostgreSQL
  trigger, `UNIQUE(request_id, question_id)`).
- Re-submitting the same transport operation is absorbed by the Idempotency-Key
  mechanism and returns the original response.
- Submitting a *different* answer to an already answered question returns
  `409 QUESTION_ALREADY_ANSWERED`. The earlier draft API contract's
  `correction_endpoint` hint is removed from MVP scope.
- No revision/supersedes columns exist; they will be added only if answer
  correction enters scope in a later phase.

## D-002 — Deletion policy

- `ServiceRequest` is never physically deleted. Closing is a status
  transition (`status = closed`).
- Every business-history child FK (`conversation_messages`, `triage_answers`,
  `safety_flags`, `ai_recommendations`, `staff_decisions`, `audit_logs`,
  and `service_requests.session_id`) uses `ondelete=RESTRICT`.
- `AuditLog` can never be cascade-deleted.
- `user_sessions.staff_user_id` uses `SET NULL` (nullable actor reference).
- No CASCADE remains on any audit or healthcare history relationship.

## D-003 — AIRecommendation regeneration

- Append-only: each regeneration inserts a new row with the next
  `sequence_number`; `UNIQUE(request_id, sequence_number)`.
- The current recommendation is the row with the highest sequence_number
  (deterministic `ORDER BY sequence_number DESC LIMIT 1`).
- Repository contract: `add`, `get`, `list_for_request`,
  `get_latest_for_request` — no update, no delete.
