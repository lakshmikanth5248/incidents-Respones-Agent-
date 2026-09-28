"""
Incident Analysis Repository.
Handles persistence, retrieval, and revisioning of incident analysis artefacts.
Conforms to PRD BE-006, BE-007, BE-019, API-005, and API-006.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.data.models.analysis import IncidentAnalysis


class AnalysisRepository:
    """Repository for managing IncidentAnalysis persistence."""

    @staticmethod
    def get_next_revision(db: Session, incident_id: str) -> int:
        """Computes the next sequential revision number for this incident's analyses."""
        latest = (
            db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(desc(IncidentAnalysis.revision))
            .first()
        )
        return (latest.revision + 1) if latest else 1

    @staticmethod
    def create(db: Session, analysis: IncidentAnalysis) -> IncidentAnalysis:
        """Persist an analysis record."""
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def get_latest_for_incident(db: Session, incident_id: str) -> Optional[IncidentAnalysis]:
        """Fetch the most recent analysis artefact for an incident."""
        return (
            db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(desc(IncidentAnalysis.revision))
            .first()
        )

    @staticmethod
    def get_by_incident_and_revision(
        db: Session, incident_id: str, revision: int
    ) -> Optional[IncidentAnalysis]:
        """Fetch an exact revision of an analysis artefact for audit."""
        return (
            db.query(IncidentAnalysis)
            .filter(
                IncidentAnalysis.incident_id == incident_id,
                IncidentAnalysis.revision == revision
            )
            .first()
        )

    @staticmethod
    def list_revisions_for_incident(db: Session, incident_id: str) -> List[IncidentAnalysis]:
        """List all historical analysis revisions for an incident."""
        return (
            db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(desc(IncidentAnalysis.revision))
            .all()
        )
