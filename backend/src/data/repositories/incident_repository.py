"""
Incident Repository Module.
Handles persistence, stable ID generation, duplicate detection, advanced filtering,
stable ordering, optimistic concurrency, and audit logging.
Conforms to PRD BE-005, BE-007, BE-019, BE-020, and Feature 2 requirements.
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from src.data.models.incident import Incident
from src.data.models.audit import AuditEvent


class IncidentRepository:
    """Repository for managing Incident and AuditEvent persistence."""

    @staticmethod
    def generate_next_incident_id(db: Session, year: Optional[int] = None) -> str:
        """Generate a unique, stable, sequential incident ID (e.g., INC-2026-0001)."""
        current_year = year or datetime.now(timezone.utc).year
        prefix = f"INC-{current_year}-"

        latest_incident = (
            db.query(Incident)
            .filter(Incident.id.like(f"{prefix}%"))
            .order_by(desc(Incident.id))
            .first()
        )

        if not latest_incident:
            next_seq = 1
        else:
            try:
                seq_str = latest_incident.id.replace(prefix, "")
                next_seq = int(seq_str) + 1
            except ValueError:
                next_seq = 1

        return f"{prefix}{next_seq:04d}"

    @staticmethod
    def create(db: Session, incident: Incident) -> Incident:
        """Persist a new incident and flush."""
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def get_by_id(db: Session, incident_id: str) -> Optional[Incident]:
        """Fetch an incident by its stable identifier."""
        return db.query(Incident).filter(Incident.id == incident_id).first()

    @staticmethod
    def get_by_idempotency_key(db: Session, idempotency_key: str) -> Optional[Incident]:
        """Fetch an existing incident created with the given idempotency key."""
        if not idempotency_key:
            return None
        return db.query(Incident).filter(Incident.idempotency_key == idempotency_key).first()

    @staticmethod
    def find_potential_duplicate(
        db: Session, service: str, failure_mode_label: Optional[str]
    ) -> Optional[str]:
        """Checks if there is a recently created incident with identical service and failure mode."""
        if not service or service == "unknown" or not failure_mode_label or failure_mode_label == "unknown":
            return None

        recent = (
            db.query(Incident)
            .filter(
                Incident.service == service,
                Incident.failure_mode_label == failure_mode_label,
                Incident.status.in_(["created", "analyzing", "investigating"])
            )
            .order_by(desc(Incident.created_at), desc(Incident.id))
            .first()
        )
        return recent.id if recent else None

    @staticmethod
    def list_all(
        db: Session,
        status: Optional[str] = None,
        service: Optional[str] = None,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Incident], int]:
        """
        Retrieve paginated incidents with comprehensive filtering and stable deterministic ordering.
        """
        query = db.query(Incident)

        if status:
            query = query.filter(Incident.status == status)
        if service:
            query = query.filter(Incident.service == service)
        if environment:
            query = query.filter(Incident.environment == environment)
        if severity:
            query = query.filter(Incident.severity == severity)
        if from_date:
            query = query.filter(Incident.created_at >= from_date)
        if to_date:
            query = query.filter(Incident.created_at <= to_date)

        total_count = query.count()

        # Stable deterministic ordering: primary sort attribute with secondary tiebreaker on ID
        sort_col = getattr(Incident, order_by, Incident.created_at)
        direction_fn = desc if order_dir.lower() == "desc" else asc

        query = query.order_by(direction_fn(sort_col), direction_fn(Incident.id))
        incidents = query.offset(offset).limit(limit).all()

        return incidents, total_count

    @staticmethod
    def update(db: Session, incident: Incident) -> Incident:
        """Update an incident record, increment revision, and commit."""
        incident.revision += 1
        incident.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def record_audit(
        db: Session,
        incident_id: Optional[str],
        action: str,
        actor: str = "sre-operator",
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        outcome: str = "success",
        details: Optional[dict] = None
    ) -> AuditEvent:
        """Record an audit event conforming to Feature 2 audit specification."""
        event = AuditEvent(
            incident_id=incident_id,
            action=action,
            actor=actor,
            previous_state=previous_state,
            new_state=new_state,
            outcome=outcome,
            details=details or {}
        )
        db.add(event)
        try:
            db.commit()
            db.refresh(event)
        except Exception:
            db.rollback()
        return event

    @staticmethod
    def get_audit_events(db: Session, incident_id: str) -> List[AuditEvent]:
        """Fetch ordered audit events for an incident."""
        return (
            db.query(AuditEvent)
            .filter(AuditEvent.incident_id == incident_id)
            .order_by(asc(AuditEvent.timestamp), asc(AuditEvent.id))
            .all()
        )
