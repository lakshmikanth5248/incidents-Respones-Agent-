"""
Memory API Endpoints.
Conforms strictly to PRD §12.3 (API-011, API-012, API-013, API-014) and Feature 04 Requirements.
Route handlers interact EXCLUSIVELY with the MemoryService interface.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from src.api.errors import APIException
from src.memory.schemas import (
    MemoryStatus,
    MemoryEntry,
    RecallRequest,
    RecallResult,
    RetainRequest,
    RetainResult,
    FlagExperienceRequest,
    FlagExperienceResponse,
)
from src.memory.service import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class ExperienceListResponse(BaseModel):
    """Response envelope for browsing retained experiences."""
    total: int
    entries: List[MemoryEntry] = Field(default_factory=list)


@router.post(
    "/recall",
    response_model=RecallResult,
    status_code=status.HTTP_200_OK,
    summary="Recall relevant memories (API-011)",
    description="Explicit operator-initiated recall independent of an incident analysis. Never returns empty on failure.",
)
def recall_memory(request: RecallRequest) -> RecallResult:
    """Execute recall query against Hindsight via MemoryService."""
    has_query = bool(request.query and request.query.strip())
    if not has_query and not request.service:
        raise APIException(
            code="INVALID_INPUT",
            message="Query cannot be empty when no service scope is specified.",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            retryable=False,
        )

    result = memory_service.recall(request)

    # API-011: 503 memory service unavailable with an explicit failure code — never an empty array with a success status
    if result.memory_status == MemoryStatus.DEGRADED:
        raise APIException(
            code="HINDSIGHT_UNAVAILABLE",
            message=result.degraded_reason or "Memory service unavailable or failed to process recall.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            details={"scope": result.scope, "query_recorded": result.query_recorded}
        )

    return result


@router.post(
    "/retain",
    response_model=RetainResult,
    status_code=status.HTTP_200_OK,
    summary="Retain confirmed operational experience (API-012)",
    description="Write validated memory entries for a confirmed incident. Gated by explicit server-side confirmation.",
)
def retain_memory(request: RetainRequest) -> RetainResult:
    """Retain memory candidates via MemoryService."""
    return memory_service.retain(request)


@router.get(
    "/experience",
    response_model=ExperienceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Browse retained experience (API-013)",
    description="Browse retained operational experience by service, failure mode, or entry type.",
)
def list_experience(
    service: Optional[str] = Query(None, description="Filter by service name"),
    failure_mode_label: Optional[str] = Query(None, description="Filter by failure mode label"),
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    outcome_label: Optional[str] = Query(None, description="Filter by outcome label"),
    include_flagged: bool = Query(True, description="Whether to include flagged records"),
    limit: int = Query(50, ge=1, le=100, description="Max entries to return"),
) -> ExperienceListResponse:
    """Browse stored experience records."""
    entries = memory_service.list_experiences(
        service=service,
        failure_mode_label=failure_mode_label,
        entry_type=entry_type,
        outcome_label=outcome_label,
        include_flagged=include_flagged,
        limit=limit,
    )
    return ExperienceListResponse(total=len(entries), entries=entries)


@router.post(
    "/experience/{entry_id}/flag",
    response_model=FlagExperienceResponse,
    status_code=status.HTTP_200_OK,
    summary="Flag a retained experience (API-014)",
    description="Report a retained memory record as incorrect, inapplicable, or outdated.",
)
def flag_experience(entry_id: str, request: FlagExperienceRequest) -> FlagExperienceResponse:
    """Flag a retained experience record."""
    entry = memory_service.flag_experience(
        entry_id=entry_id,
        flag_type=request.flag_type.value,
        reason=request.reason,
        note=request.note,
    )
    return FlagExperienceResponse(
        entry_id=entry.entry_id,
        flagged=entry.flagged,
        action_taken=f"Flagged as {request.flag_type.value} and deprioritized in future recall ranking."
    )
