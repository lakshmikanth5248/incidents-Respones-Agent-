"""
Audit Event Model.
Conforms to PRD BE-020, LC-008, LC-014, and Feature 2 Audit requirements.
Records lifecycle transitions, mutations, and security events.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(32), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # e.g., incident.created, incident.state_transition
    actor = Column(String(64), nullable=False, default="sre-operator")
    previous_state = Column(String(32), nullable=True)
    new_state = Column(String(32), nullable=True)
    outcome = Column(String(32), nullable=False, default="success")  # success, failure
    details = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "action": self.action,
            "actor": self.actor,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "outcome": self.outcome,
            "details": self.details or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
