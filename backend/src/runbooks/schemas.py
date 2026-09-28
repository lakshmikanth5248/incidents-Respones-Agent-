"""
Runbook Schemas and DTOs.
Conforms to PRD §12.4 (API-015) and Feature 08.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RunbookTrackRecord(BaseModel):
    """Retained outcome track record joined with a runbook (TL-004)."""
    model_config = ConfigDict(extra="ignore")

    times_applied: int = 0
    times_successful: int = 0
    times_ineffective: int = 0
    last_outcome: Optional[str] = "no_record"
    outcome_source: str = "no_record"  # "retained_memory" or "no_record"


class Runbook(BaseModel):
    """Runbook representation conforming to PRD API-015."""
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    service: str
    failure_mode_label: str
    steps: List[str] = Field(default_factory=list)
    applicable_symptoms: List[str] = Field(default_factory=list)
    risk_level: str = "low"  # "low", "medium", "high"
    is_destructive: bool = False
    safer_diagnostic_alternative: Optional[str] = None
    track_record: RunbookTrackRecord = Field(default_factory=RunbookTrackRecord)


class RunbookListResponse(BaseModel):
    """Response envelope for browsing runbooks."""
    total: int
    runbooks: List[Runbook] = Field(default_factory=list)
