"""
Incident API Endpoints.
Conforms to PRD §12.2 (API-001, API-002, API-003, API-004) and Feature 2 Lifecycle.
Implements intake, normalization, retrieval, state transitions, concurrency control, and audit.
Feature 09: POST /api/incidents/{id}/resolve — human decision & resolution (FR-049–FR-052).
"""

from datetime import datetime, timezone
from typing import Optional, Literal, List
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from src.data.database import get_db
from src.api.schemas.incident import (
    IncidentCreateRequest,
    IncidentPatchRequest,
    StateTransitionRequest,
    IncidentResponse,
    IncidentListResponse,
    AuditListResponse,
    AuditEventResponse,
    IncidentMemoryResponse,
)
from src.api.schemas.analysis import AnalysisRequest, AnalysisResponse, RecommendationItem
from src.api.schemas.resolution import ResolveIncidentRequest, ResolutionResponse
from src.api.schemas.verification import VerificationRequest, VerificationResponse
from src.api.schemas.postmortem import (
    PostMortemConfirmRequest,
    PostMortemGenerateRequest,
    PostMortemResponse,
)
from src.api.errors import APIException
from src.data.repositories.incident_repository import IncidentRepository
from src.services.incident_service import IncidentService
from src.services.analysis_service import AnalysisService
from src.services.resolution_service import ResolutionService
from src.services.verification_service import VerificationService
from src.services.postmortem_service import PostMortemService
from src.memory.service import memory_service
from src.memory.schemas import RecallRequest, MemoryStatus

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and normalize a new incident (API-001)",
    description="Validates, scans for secrets, preserves verbatim raw input, deterministically normalizes, and persists the incident.",
)
def create_incident(
    request: IncidentCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    """Create incident with initial state 'created'."""
    incident = IncidentService.create_incident(
        db=db,
        request_data=request,
        idempotency_key=idempotency_key
    )
    return IncidentResponse(**incident.to_dict())


@router.get(
    "",
    response_model=IncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List incidents with filtering and pagination (API-002)",
    description="Retrieve paginated incidents with stable ordering and multi-criteria filtering without triggering memory recall or agent execution.",
)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (created, analyzing, investigated, etc.)"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    from_date: Optional[datetime] = Query(None, description="Filter incidents created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter incidents created on or before this timestamp"),
    order_by: Literal["created_at", "detected_at", "id", "updated_at"] = Query("created_at", description="Sort attribute"),
    order_dir: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    limit: int = Query(50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    incidents, total = IncidentService.list_incidents(
        db=db,
        status_filter=status,
        service_filter=service,
        environment_filter=environment,
        severity_filter=severity,
        from_date=from_date,
        to_date=to_date,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset
    )
    return IncidentListResponse(
        incidents=[IncidentResponse(**inc.to_dict()) for inc in incidents],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident by ID (API-003)",
    description="Retrieve a single full incident record without triggering memory recall or agent analysis.",
)
def get_incident(
    id: str,
    db: Session = Depends(get_db),
) -> IncidentResponse:
    incident = IncidentService.get_incident_by_id(db=db, incident_id=id)
    return IncidentResponse(**incident.to_dict())


@router.patch(
    "/{id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Patch incident (API-004)",
    description="Update mutable fields or correct normalization with optimistic concurrency guards.",
)
def patch_incident(
    id: str,
    request: IncidentPatchRequest,
    x_operator: Optional[str] = Header("sre-operator", alias="X-Operator"),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    updated = IncidentService.patch_incident(
        db=db, incident_id=id, patch_data=request, actor=x_operator or "sre-operator"
    )
    return IncidentResponse(**updated.to_dict())


@router.post(
    "/{id}/transition",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition incident lifecycle state",
    description="Executes a controlled state machine transition with concurrency protection and automatic audit logging.",
)
def transition_incident_state(
    id: str,
    request: StateTransitionRequest,
    x_operator: Optional[str] = Header(None, alias="X-Operator"),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    actor = request.actor or x_operator or "sre-operator"
    updated = IncidentService.transition_state(
        db=db,
        incident_id=id,
        new_status=request.new_status,
        expected_revision=request.expected_revision,
        from_status=request.from_status,
        actor=actor,
        reason=request.reason
    )
    return IncidentResponse(**updated.to_dict())


@router.get(
    "/{id}/audit",
    response_model=AuditListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident audit events",
    description="Retrieve chronological audit history of state transitions and modifications for this incident.",
)
def get_incident_audit(
    id: str,
    db: Session = Depends(get_db),
) -> AuditListResponse:
    events = IncidentService.get_audit_log(db=db, incident_id=id)
    return AuditListResponse(
        incident_id=id,
        events=[AuditEventResponse(**evt.to_dict()) for evt in events],
        total=len(events)
    )


@router.post(
    "/{id}/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze current incident (API-005)",
    description="Executes Stage 1 analysis (TL-001): structured interpretation of current incident facts without premature hypotheses.",
)
def analyze_incident(
    id: str,
    request: Optional[AnalysisRequest] = None,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    analysis = AnalysisService.analyze_incident(
        db=db,
        incident_id=id,
        request=request
    )
    return AnalysisResponse(**analysis.to_dict())


@router.get(
    "/{id}/analysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident analysis (API-006)",
    description="Retrieve the current or historical revision of an analysis artefact for audit.",
)
def get_incident_analysis(
    id: str,
    revision: Optional[int] = Query(None, description="Optional specific revision number to retrieve for audit"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    analysis = AnalysisService.get_analysis(
        db=db,
        incident_id=id,
        revision=revision
    )
    return AnalysisResponse(**analysis.to_dict())


@router.get(
    "/{id}/memory",
    response_model=IncidentMemoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recalled memory for incident (API-007)",
    description="Retrieve memory entries recalled for this incident. Returns 503 if memory unavailable (never empty on failure).",
)
def get_incident_memory(
    id: str,
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    outcome_label: Optional[str] = Query(None, description="Filter by outcome label"),
    relevance_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum relevance score threshold"),
    db: Session = Depends(get_db),
) -> IncidentMemoryResponse:
    incident = IncidentService.get_incident_by_id(db=db, incident_id=id)

    # 1. Operational health check to ensure Hindsight is currently reachable
    is_healthy, health_msg = memory_service.health_check()
    if not is_healthy:
        raise APIException(
            code="HINDSIGHT_UNAVAILABLE",
            message=f"Memory service unavailable: {health_msg}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            details={"health_msg": health_msg}
        )

    # 2. Check if incident recorded degraded status during analysis recall
    if incident.recall_record and incident.recall_record.get("memory_status") == "degraded":
        raise APIException(
            code="HINDSIGHT_UNAVAILABLE",
            message=incident.recall_record.get("error") or "Memory service unavailable during incident recall.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            details=incident.recall_record
        )

    # 3. Retrieve or execute recall
    if incident.recall_record and incident.status != "created":
        recall_record = incident.recall_record
        entries = recall_record.get("returned_entries", [])
        memory_status_str = incident.memory_status or recall_record.get("memory_status", "ok")
    else:
        # Perform recall using normalized incident details
        recall_req = RecallRequest(
            service=incident.service,
            environment=incident.environment,
            failure_mode=incident.failure_mode_label,
            normalized_symptoms=incident.symptoms_normalized or incident.symptoms_raw,
            error_signatures=incident.error_signatures,
            affected_components=incident.affected_components,
        )
        result = memory_service.recall(recall_req)

        if result.memory_status == MemoryStatus.DEGRADED:
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message=result.degraded_reason or "Memory service unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                retryable=True,
                details={
                    "scope": result.scope,
                    "query_recorded": result.query_recorded,
                    "error": result.recall_record.error if result.recall_record else None,
                }
            )

        recall_record = result.recall_record.to_dict() if result.recall_record else {
            "query": result.query_recorded,
            "query_version": "v1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_status": result.memory_status.value,
            "returned_entries": [e.to_dict() for e in result.entries],
            "ranking": [],
            "relevance_basis": {},
            "duration_ms": 0.0,
            "scope": result.scope,
        }
        entries = recall_record.get("returned_entries", [])
        memory_status_str = result.memory_status.value

        # Persist on incident
        incident.recall_record = recall_record
        incident.memory_status = memory_status_str
        IncidentRepository.update(db, incident)

    # 4. Apply optional filters
    filtered_entries = entries
    if entry_type:
        filtered_entries = [e for e in filtered_entries if e.get("entry_type") == entry_type]
    if outcome_label:
        filtered_entries = [e for e in filtered_entries if e.get("outcome_label") == outcome_label]
    if relevance_min is not None:
        filtered_entries = [e for e in filtered_entries if float(e.get("relevance_score", 0.0)) >= relevance_min]

    return IncidentMemoryResponse(
        incident_id=id,
        memory_status=memory_status_str,
        recall_record=recall_record,
        entries=filtered_entries,
    )


@router.get(
    "/{id}/recommendations",
    response_model=List[RecommendationItem],
    status_code=status.HTTP_200_OK,
    summary="Get incident recommendations (API-008)",
    description="Retrieve structured advisory recommendations generated for this incident.",
)
def get_incident_recommendations(
    id: str,
    db: Session = Depends(get_db),
) -> List[RecommendationItem]:
    """Retrieve recommendations generated for the incident."""
    analysis = AnalysisService.get_analysis(db=db, incident_id=id)
    return [RecommendationItem(**rec) for rec in (analysis.recommendations or [])]



@router.post(
    "/{id}/resolve",
    response_model=ResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record human resolution decision (API-009, FR-049-FR-052)",
    description=(
        "Records the engineer resolution decision for a production incident. "
        "The AI cannot resolve incidents. The engineer decides. "
        "Idempotent: repeated requests return the existing resolution record. "
        "Closing rule (FR-052): actions and outcome required unless "
        "close_without_resolution=True with a stated reason."
    ),
)
def resolve_incident(
    id: str,
    request: ResolveIncidentRequest,
    x_operator: str = Header(None, alias="X-Operator"),
    db: Session = Depends(get_db),
) -> ResolutionResponse:
    """Human-in-the-loop resolution endpoint."""
    actor = x_operator or "sre-operator"
    resolution = ResolutionService.resolve_incident(
        db=db,
        incident_id=id,
        request=request,
        actor=actor,
    )
    incident = IncidentRepository.get_by_id(db, id)
    record = resolution.to_dict()
    return ResolutionResponse(
        **record,
        incident_status=incident.status if incident else "unknown",
        resolution_status=incident.resolution_status if incident else "resolved",
    )


@router.get(
    "/{id}/resolution",
    response_model=ResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident resolution record (API-009)",
    description=(
        "Retrieve the recorded resolution for this incident. "
        "Returns 404 if no resolution has been recorded yet."
    ),
)
def get_incident_resolution(
    id: str,
    db: Session = Depends(get_db),
) -> ResolutionResponse:
    """Retrieve the resolution record for an incident."""
    resolution = ResolutionService.get_resolution(db=db, incident_id=id)
    incident = IncidentRepository.get_by_id(db, id)
    record = resolution.to_dict()
    return ResolutionResponse(
        **record,
        incident_status=incident.status if incident else "unknown",
        resolution_status=incident.resolution_status if incident else "resolved",
    )

@router.post(
    "/{id}/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify resolution outcome (Feature 10)",
    description=(
        "Verify what happened after the engineer's action. "
        "Evaluates before/after telemetry, observations, and operator claims without manufacturing measurements."
    ),
)
@router.post(
    "/{id}/verification",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify resolution outcome alias (Feature 10)",
    include_in_schema=False,
)
def verify_incident_outcome(
    id: str,
    request: VerificationRequest,
    x_operator: str = Header(None, alias="X-Operator"),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """Verify outcome of resolution actions."""
    actor = x_operator or "sre-verifier"
    record = VerificationService.verify_incident(
        db=db,
        incident_id=id,
        request=request,
        actor=actor,
    )
    incident = IncidentRepository.get_by_id(db, id)
    res_dict = record.to_dict()
    return VerificationResponse(
        **res_dict,
        incident_status=incident.status if incident else "unknown",
    )


@router.get(
    "/{id}/verification",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident outcome verification record (Feature 10)",
    description="Retrieve the verification record and evidence assessment for an incident.",
)
def get_incident_verification(
    id: str,
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """Retrieve outcome verification record for an incident."""
    record = VerificationService.get_verification(db=db, incident_id=id)
    incident = IncidentRepository.get_by_id(db, id)
    res_dict = record.to_dict()
    return VerificationResponse(
        **res_dict,
        incident_status=incident.status if incident else "unknown",
    )

@router.post(
    "/{id}/postmortem",
    response_model=PostMortemResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate post-mortem draft (Feature 11 / API-009)",
    description=(
        "Generate a structured post-mortem draft for a resolved or mitigated incident. "
        "Strictly enforces preconditions, provenance, root-cause source, and anti-hallucination guards."
    ),
)
def generate_incident_postmortem(
    id: str,
    request: PostMortemGenerateRequest = PostMortemGenerateRequest(),
    x_operator: str = Header(None, alias="X-Operator"),
    db: Session = Depends(get_db),
) -> PostMortemResponse:
    """Generate post-mortem draft for a resolved incident."""
    actor = x_operator or "sre-lead"
    record = PostMortemService.generate_postmortem(
        db=db,
        incident_id=id,
        request=request,
        actor=actor,
    )
    return PostMortemResponse(**record.to_dict())


@router.post(
    "/{id}/postmortem/confirm",
    response_model=PostMortemResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm post-mortem draft (FR-056, D-12)",
    description=(
        "Confirm the post-mortem as the authoritative incident record. "
        "Confirmation is the human gate that makes the incident's experience "
        "eligible for retention in Hindsight (FR-058). Idempotent."
    ),
)
def confirm_incident_postmortem(
    id: str,
    request: PostMortemConfirmRequest = PostMortemConfirmRequest(),
    x_operator: Optional[str] = Header("sre-lead", alias="X-Operator"),
    db: Session = Depends(get_db),
) -> PostMortemResponse:
    """Confirm a post-mortem draft, unlocking Hindsight retention."""
    actor = x_operator or "sre-lead"
    record = PostMortemService.confirm_postmortem(
        db=db,
        incident_id=id,
        request=request,
        actor=actor,
    )
    return PostMortemResponse(**record.to_dict())


@router.get(
    "/{id}/postmortem",
    response_model=PostMortemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get incident post-mortem draft (Feature 11 / API-010)",
    description="Retrieve the current post-mortem draft for an incident.",
)
def get_incident_postmortem(
    id: str,
    db: Session = Depends(get_db),
) -> PostMortemResponse:
    """Retrieve post-mortem draft for an incident."""
    record = PostMortemService.get_postmortem(db=db, incident_id=id)
    return PostMortemResponse(**record.to_dict())

