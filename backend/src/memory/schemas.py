"""
Memory Schemas and Normalized Domain Models.
Conforms strictly to PRD §1.4 (HM-023 to HM-032), §3.4 (RL-011, RL-012), §9.4 (DM-003),
and Backend Feature 04 Requirements.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class MemoryStatus(str, Enum):
    """
    Normalized Memory Statuses.
    CRITICAL: Never confuse 'empty' with 'unavailable' (degraded)!
    """
    OK = "ok"
    EMPTY = "empty"
    DEGRADED = "degraded"
    SUPPRESSED = "suppressed"


class EntryType(str, Enum):
    """Supported reusable fact entry types (PRD HM-001 - HM-013, DM-003)."""
    INCIDENT_EXPERIENCE = "incident_experience"
    SYMPTOM_PROFILE = "symptom_profile"
    ROOT_CAUSE = "root_cause"
    CONTRIBUTING_FACTOR = "contributing_factor"
    RESOLUTION_PROCEDURE = "resolution_procedure"
    SUCCESSFUL_ACTION = "successful_action"
    FAILED_ACTION = "failed_action"
    RUNBOOK_OUTCOME = "runbook_outcome"
    LESSON = "lesson"
    PREVENTIVE_KNOWLEDGE = "preventive_knowledge"
    RECURRING_PATTERN = "recurring_pattern"


class OutcomeLabel(str, Enum):
    """Outcome qualification labels (PRD HM-010, RP-012)."""
    SUCCESSFUL = "successful"
    INEFFECTIVE = "ineffective"
    INCONCLUSIVE = "inconclusive"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence levels (PRD RP-011)."""
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    LOW = "low"


class FlagType(str, Enum):
    """User-reported memory flag categories (PRD FR-074, HM-030)."""
    INCORRECT = "incorrect"
    INAPPLICABLE = "inapplicable"
    OUTDATED = "outdated"


class FlagRecord(BaseModel):
    """Flagging state attached to a memory entry."""
    model_config = ConfigDict(extra="ignore")

    flag_type: FlagType
    reason: str
    note: Optional[str] = None
    flagged_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MemoryEntry(BaseModel):
    """
    Stable Internal Normalized Memory Entry Schema.
    Required by PRD DM-003 and Feature 04 specification.
    """
    model_config = ConfigDict(extra="ignore")

    entry_id: str
    entry_type: str
    service: str
    component: Optional[str] = None
    body: str
    outcome_label: Optional[str] = None
    confidence: Optional[str] = "confirmed"
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_basis: str = Field(default="Unspecified relevance")
    source_incident_ref: str
    retained_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    flagged: Optional[FlagRecord] = None
    provenance_group_id: Optional[str] = None
    is_synthetic: bool = True
    supersedes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "service": self.service,
            "component": self.component,
            "body": self.body,
            "outcome_label": self.outcome_label,
            "confidence": self.confidence,
            "relevance_score": round(self.relevance_score, 4),
            "relevance_basis": self.relevance_basis,
            "source_incident_ref": self.source_incident_ref,
            "retained_at": self.retained_at,
            "flagged": self.flagged.model_dump() if self.flagged else None,
            "provenance_group_id": self.provenance_group_id,
            "is_synthetic": self.is_synthetic,
            "supersedes": self.supersedes,
        }


class MemoryCandidate(BaseModel):
    """
    Composed Memory Candidate submitted for retention (PRD §5.1, DM-003).
    Must pass server-side validation and secret scanning before being retained in Hindsight.

    `service` and `source_incident_ref` are optional on the wire: provenance is
    server-authoritative (RP-013, D-03) and is derived from the incident record
    when the client omits or contradicts it.
    """
    model_config = ConfigDict(extra="ignore")

    entry_type: str
    service: Optional[str] = None
    component: Optional[str] = None
    body: str
    outcome_label: Optional[str] = None
    confidence: str = ConfidenceLevel.CONFIRMED.value
    source_incident_ref: Optional[str] = None
    provenance_group_id: Optional[str] = None
    is_synthetic: bool = True
    supersedes: Optional[str] = None


class RankingDetail(BaseModel):
    """Detailed deterministic ranking metadata per entry."""
    entry_id: str
    rank: int
    score: float
    relevance_basis: str


class RecallRecord(BaseModel):
    """
    Persisted recall record conforming strictly to PRD §3.4, §12.3, and Feature 05.
    Persists: query, query version, timestamp, memory_status, returned entries,
    ranking, relevance basis, duration.
    """
    model_config = ConfigDict(extra="ignore")

    query: str
    query_version: str = "v1.0.0"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    memory_status: str
    returned_entries: List[Dict[str, Any]] = Field(default_factory=list)
    ranking: List[RankingDetail] = Field(default_factory=list)
    relevance_basis: Dict[str, str] = Field(default_factory=dict)
    duration_ms: float = 0.0
    scope: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "query_version": self.query_version,
            "timestamp": self.timestamp,
            "memory_status": self.memory_status,
            "returned_entries": self.returned_entries,
            "ranking": [r.model_dump() for r in self.ranking],
            "relevance_basis": self.relevance_basis,
            "duration_ms": round(self.duration_ms, 2),
            "scope": self.scope,
            "error": self.error,
        }


class RecallRequest(BaseModel):
    """Request parameters for recalling memory entries."""
    model_config = ConfigDict(extra="ignore")

    query: Optional[str] = None
    query_version: str = "v1.0.0"
    service: Optional[str] = None
    environment: Optional[str] = None
    failure_mode: Optional[str] = None
    normalized_symptoms: Optional[str] = None
    error_signatures: Optional[List[str]] = None
    affected_components: Optional[List[str]] = None
    entry_types: Optional[List[str]] = None
    outcome_labels: Optional[List[str]] = None
    limit: int = Field(default=5, ge=1, le=50)
    memory_isolated: bool = False


class RecallResult(BaseModel):
    """
    Structured outcome of a memory recall operation.
    Guarantees that a degraded state carries an explicit error and is NEVER confused with empty.
    """
    model_config = ConfigDict(extra="ignore")

    memory_status: MemoryStatus
    query_recorded: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    total_found: int = 0
    entries: List[MemoryEntry] = Field(default_factory=list)
    recall_record: Optional[RecallRecord] = None
    degraded_reason: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_status": self.memory_status.value,
            "query_recorded": self.query_recorded,
            "scope": self.scope,
            "total_found": self.total_found,
            "entries": [e.to_dict() for e in self.entries],
            "recall_record": self.recall_record.to_dict() if self.recall_record else None,
            "degraded_reason": self.degraded_reason,
            "error_code": self.error_code,
        }


class RetainRequest(BaseModel):
    """Retention request payload (PRD API-012, D-12)."""
    model_config = ConfigDict(extra="ignore")

    incident_id: str
    confirmed: bool = Field(
        ...,
        description="Explicit engineer confirmation flag (enforced server-side per D-12)"
    )
    entries: List[MemoryCandidate]


class RetainEntryResult(BaseModel):
    """
    Individual entry retention result.

    status values:
      retained           — the entry was written to Hindsight by this request
      already_retained   — the identical entry (same incident + entry identity) already
                           exists in Hindsight; no duplicate was written (RP-015, D-10)
      failed             — the write did not complete; the composed record is preserved
                           for retry (RP-014, FR-063)
      skipped            — rejected by server-side validation; never reached Hindsight
    """
    model_config = ConfigDict(extra="ignore")

    status: Literal["retained", "already_retained", "failed", "skipped"]
    memory_entry_id: Optional[str] = None
    entry_type: Optional[str] = None
    entry_index: Optional[int] = None
    entry_key: Optional[str] = None
    error: Optional[str] = None


class RetainSkippedEntry(BaseModel):
    """
    A submitted entry that never reached Hindsight because server-side validation
    rejected it (D-12). Reported separately from `results` so a client can tell a
    deliberate skip apart from a write failure.
    """
    model_config = ConfigDict(extra="ignore")

    entry_index: int = Field(..., description="Zero-based index in the submitted entries array")
    entry_type: Optional[str] = None
    reason: str


class RetainResult(BaseModel):
    """
    Aggregate response for a memory retention operation (API-012, FR-058–FR-066).

    `status` is never reported as complete success when any entry failed: a mixed
    outcome is always `partial` (D-11, RP-014, ERR-03).
    """
    model_config = ConfigDict(extra="ignore")

    status: Literal["retained", "partial", "failed"]
    incident_id: str
    retain_id: Optional[str] = None
    memory_entry_id: Optional[str] = None
    memory_entry_ids: List[str] = Field(default_factory=list)
    results: List[RetainEntryResult] = Field(default_factory=list)
    skipped: List[RetainSkippedEntry] = Field(default_factory=list)
    validation_report: Dict[str, Any] = Field(default_factory=dict)
    idempotent: bool = False
    retry_pending: bool = False
    retained_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "incident_id": self.incident_id,
            "retain_id": self.retain_id,
            "memory_entry_id": self.memory_entry_id,
            "memory_entry_ids": self.memory_entry_ids,
            "results": [r.model_dump() for r in self.results],
            "skipped": [s.model_dump() for s in self.skipped],
            "validation_report": self.validation_report,
            "idempotent": self.idempotent,
            "retry_pending": self.retry_pending,
            "retained_at": self.retained_at,
        }


class FlagExperienceRequest(BaseModel):
    """Experience flagging request (API-014)."""
    model_config = ConfigDict(extra="ignore")

    flag_type: FlagType
    reason: str
    note: Optional[str] = None


class FlagExperienceResponse(BaseModel):
    """Experience flagging response (API-014)."""
    model_config = ConfigDict(extra="ignore")

    entry_id: str
    flagged: FlagRecord
    action_taken: str
