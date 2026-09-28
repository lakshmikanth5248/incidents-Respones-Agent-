"""
Incident Analysis Database Model.
Conforms to PRD §9.7, API-005, API-006, and Feature 3 requirements.
Persists immutable, revisioned analysis artefacts allowing prior revisions to remain auditable.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentAnalysis(Base):
    __tablename__ = "incident_analyses"

    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(String(32), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision = Column(Integer, nullable=False, default=1, index=True)
    prompt_version = Column(String(32), nullable=False, default="v1.0.0")
    model_identifier = Column(String(64), nullable=False)

    # Structured interpretation produced by TL-001
    symptom_analysis = Column(JSON, nullable=False, default=dict)
    unknowns = Column(JSON, nullable=False, default=list)
    information_gaps = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=dict)

    # Reserved for Feature 4 & 5 (Must be empty/null before recall!)
    hypotheses = Column(JSON, nullable=False, default=list)
    comparisons = Column(JSON, nullable=False, default=list)
    recall_record = Column(JSON, nullable=True)
    memory_status = Column(String(32), nullable=True)

    # Observability & cost metrics (BE-022)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.id,
            "incident_id": self.incident_id,
            "revision": self.revision,
            "status": "ready_for_recall" if not self.hypotheses else "hypotheses_generated",
            "memory_status": self.memory_status,
            "recall_record": self.recall_record,
            "symptom_analysis": self.symptom_analysis,
            "comparisons": self.comparisons or [],
            "hypotheses": self.hypotheses or [],
            "unknowns": self.unknowns or [],
            "information_gaps": self.information_gaps or [],
            "model_metadata": {
                "model_identifier": self.model_identifier,
                "prompt_version": self.prompt_version,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "duration_ms": self.duration_ms,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
