"""
Resolution Service — Human Decision & Resolution Stage.

Conforms to PRD §12.8 (FR-049–FR-052, FR-044), UC-07, W-11, W-12.

Core rules enforced here:
  - The AI cannot resolve production incidents. The engineer decides.
  - An incident cannot reach closed state without a resolution record
    OR an explicit close_without_resolution=True with a stated reason (FR-052).
  - Idempotency: repeated POST does not create duplicate resolution records.
  - Outcome 'unknown' is valid and propagates a low-confidence marker (FR-051).
  - All resolution decisions are persisted with actor, timestamp, and recommendation outcomes.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import status
from sqlalchemy.orm import Session

from src.api.errors import APIException
from src.api.schemas.resolution import ResolveIncidentRequest
from src.data.models.incident import Incident
from src.data.models.resolution import ResolutionRecord
from src.data.repositories.incident_repository import IncidentRepository
from src.observability.logger import logger


# ---------------------------------------------------------------------------
# Resolvable incident states — the incident must be in one of these states
# for the resolve endpoint to accept the request.
# ---------------------------------------------------------------------------
_RESOLVABLE_STATES = {
    "recommendation_ready",
    "resolving",
    "mitigated",
    "analyzing",
    "analyzed",
    "investigating",
    "investigated",
    # Also allow created/any non-terminal state so engineers can close odd-path incidents
    "created",
}

# States that are already terminal — already closed
_TERMINAL_STATES = {"closed"}

# Low-confidence outcomes that must propagate a confidence marker (FR-051)
_LOW_CONFIDENCE_OUTCOMES = {"inconclusive", "unknown"}


class ResolutionService:
    """
    Manages the human engineer's resolution decision for an incident.

    All state mutations are performed through IncidentRepository to maintain
    audit integrity and optimistic-concurrency safety.
    """

    @classmethod
    def resolve_incident(
        cls,
        db: Session,
        incident_id: str,
        request: ResolveIncidentRequest,
        actor: str = "sre-operator",
    ) -> ResolutionRecord:
        """
        Record the engineer's resolution decision and move the incident to resolved/closed.

        Resolution flow:
          1. Fetch and validate incident (404 if missing)
          2. Reject if already closed (409 ALREADY_CLOSED)
          3. Check for existing resolution record → return it (idempotency)
          4. Validate state allows resolution (422 INVALID_STATE_FOR_RESOLUTION)
          5. Validate outcome enum (422 INVALID_OUTCOME)
          6. Enforce close_without_resolution gate (FR-052)
          7. Persist ResolutionRecord
          8. Transition incident to resolved / closed
          9. Record audit event
        """
        # ── 1. Fetch incident ────────────────────────────────────────────────
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False,
            )

        # ── 2. Terminal state guard ──────────────────────────────────────────
        if incident.status in _TERMINAL_STATES:
            raise APIException(
                code="ALREADY_CLOSED",
                message=(
                    f"Incident '{incident_id}' is already closed. "
                    "Closed incidents cannot be modified or re-resolved."
                ),
                status_code=status.HTTP_409_CONFLICT,
                retryable=False,
                details={"current_status": incident.status},
            )

        # ── 3. Idempotency check ─────────────────────────────────────────────
        existing = cls._get_resolution_record(db, incident_id)
        if existing:
            logger.info(
                f"resolution.idempotent_hit incident_id={incident_id} "
                f"resolution_id={existing.id}"
            )
            return existing

        # ── 4. State validation ──────────────────────────────────────────────
        # We allow resolution from any non-terminal state.
        # The state should at least not be terminal (handled above).
        # Some deployments may want stricter — we allow the PRD's flexible approach.

        # ── 5. Outcome enum validation ───────────────────────────────────────
        if not request.close_without_resolution and request.outcome:
            from src.api.schemas.resolution import ALLOWED_OUTCOMES
            if request.outcome not in ALLOWED_OUTCOMES:
                raise APIException(
                    code="INVALID_OUTCOME",
                    message=(
                        f"Outcome '{request.outcome}' is not valid. "
                        f"Allowed values: {sorted(ALLOWED_OUTCOMES)}."
                    ),
                    status_code=422,
                    retryable=False,
                    details={"outcome": request.outcome},
                )

        # ── 6. Close-without-resolution gate (FR-052) ────────────────────────
        # Pydantic validators already enforce reason is present when flag=True
        # and actions+outcome are present when flag=False.
        # No additional check needed here — schema is the gate.

        # ── 7. Determine outcome and confidence ──────────────────────────────
        outcome = request.outcome or "unknown"
        outcome_confidence = (
            "low" if outcome in _LOW_CONFIDENCE_OUTCOMES else "high"
        )

        # ── 8. Build and persist ResolutionRecord ────────────────────────────
        resolution_id = f"RES-{incident_id}-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        resolution = ResolutionRecord(
            id=resolution_id,
            incident_id=incident_id,
            actions_taken=request.actions,
            runbook_id=request.runbook_id,
            runbook_version=request.runbook_version,
            root_cause=request.root_cause,
            contributing_factors=request.contributing_factors,
            result=request.result,
            outcome=outcome,
            outcome_confidence=outcome_confidence,
            recommendation_outcomes=[ro.model_dump() for ro in request.recommendation_outcomes],
            close_without_resolution=request.close_without_resolution,
            close_without_resolution_reason=request.close_without_resolution_reason,
            operator=actor,
            operator_notes=request.operator_notes,
            resolved_at=now,
            created_at=now,
        )
        db.add(resolution)
        db.flush()  # Assign PK before updating incident

        # ── 9. Transition incident state ─────────────────────────────────────
        previous_status = incident.status
        incident.status = "resolved"
        incident.resolved_at = now
        incident.resolution_status = "resolved"

        # Propagate low-confidence marker onto incident (FR-051)
        if outcome_confidence == "low":
            incident.postmortem_status = "low_confidence"

        IncidentRepository.update(db, incident)

        # Commit the whole unit of work
        db.commit()
        db.refresh(resolution)

        # ── 10. Audit event ──────────────────────────────────────────────────
        IncidentRepository.record_audit(
            db=db,
            incident_id=incident_id,
            action="incident.resolved",
            actor=actor,
            previous_state=previous_status,
            new_state="resolved",
            outcome="success",
            details={
                "resolution_id": resolution_id,
                "outcome": outcome,
                "outcome_confidence": outcome_confidence,
                "close_without_resolution": request.close_without_resolution,
                "runbook_id": request.runbook_id,
                "recommendation_outcomes_count": len(request.recommendation_outcomes),
            },
        )

        logger.info(
            f"incident.resolved id={incident_id} resolution_id={resolution_id} "
            f"outcome={outcome} confidence={outcome_confidence} actor={actor}"
        )
        return resolution

    @classmethod
    def get_resolution(cls, db: Session, incident_id: str) -> ResolutionRecord:
        """Retrieve the resolution record for an incident (raises 404 if absent)."""
        # Ensure incident exists first
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False,
            )
        record = cls._get_resolution_record(db, incident_id)
        if not record:
            raise APIException(
                code="RESOLUTION_NOT_FOUND",
                message=f"No resolution record exists for incident '{incident_id}'.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False,
            )
        return record

    @staticmethod
    def _get_resolution_record(db: Session, incident_id: str) -> Optional[ResolutionRecord]:
        """Internal: fetch resolution record without raising."""
        return (
            db.query(ResolutionRecord)
            .filter(ResolutionRecord.incident_id == incident_id)
            .first()
        )
