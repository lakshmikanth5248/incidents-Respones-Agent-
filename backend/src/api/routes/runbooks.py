"""
Runbook API Endpoints.
Conforms strictly to PRD §12.4 (API-015) and Feature 08.
"""

from typing import Optional
from fastapi import APIRouter, Query, status

from src.api.errors import APIException
from src.runbooks.schemas import Runbook, RunbookListResponse
from src.services.runbook_service import runbook_service

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


@router.get(
    "",
    response_model=RunbookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search runbooks (API-015)",
    description="Retrieve the runbook reference set, filtered by service, failure mode, or search query.",
)
def list_runbooks(
    service: Optional[str] = Query(None, description="Filter by service name"),
    failure_mode_label: Optional[str] = Query(None, description="Filter by failure mode label"),
    q: Optional[str] = Query(None, description="Full text search query"),
) -> RunbookListResponse:
    """List runbooks from reference set."""
    items = runbook_service.list_runbooks(
        service=service,
        failure_mode_label=failure_mode_label,
        q=q,
    )
    return RunbookListResponse(total=len(items), runbooks=items)


@router.get(
    "/{id}",
    response_model=Runbook,
    status_code=status.HTTP_200_OK,
    summary="Get single runbook (API-015)",
    description="Retrieve a single runbook joined with its historical outcome track record.",
)
def get_runbook(id: str) -> Runbook:
    """Retrieve runbook by ID."""
    rb = runbook_service.get_runbook(id)
    if not rb:
        raise APIException(
            code="RUNBOOK_NOT_FOUND",
            message=f"Runbook with ID '{id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
        )
    return rb
