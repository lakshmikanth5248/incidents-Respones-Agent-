"""
Incident Service Module.
Conforms to PRD BE-005, DM-001, FR-001-FR-009, D-13, and Feature 2 State & Lifecycle.
Coordinates validation, secret scanning, normalization, persistence, lifecycle transitions,
optimistic concurrency control, and audit logging.
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import status

from src.api.errors import APIException
from src.api.schemas.incident import IncidentCreateRequest, IncidentPatchRequest
from src.data.models.incident import Incident
from src.data.models.audit import AuditEvent
from src.data.repositories.incident_repository import IncidentRepository
from src.services.validation_service import ValidationService
from src.services.normalization_service import NormalizationService
from src.observability.logger import logger


class IncidentService:
    """Core domain service for managing incident intake, lifecycle, and state machine."""

    @classmethod
    def create_incident(
        cls,
        db: Session,
        request_data: IncidentCreateRequest,
        idempotency_key: Optional[str] = None
    ) -> Incident:
        """Executes the Feature 1 Incident Intake workflow."""
        try:
            raw_symptom = ValidationService.validate_symptom_description(request_data.symptom_description)
        except ValueError as e:
            msg = str(e)
            if "MINIMUM_INPUT_REQUIRED" in msg:
                raise APIException(
                    code="MINIMUM_INPUT_REQUIRED",
                    message="A symptom description is required to create an incident.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    retryable=False
                )
            raise APIException(
                code="INVALID_INPUT",
                message=msg,
                status_code=status.HTTP_400_BAD_REQUEST,
                retryable=False
            )

        if request_data.severity:
            try:
                ValidationService.validate_severity(request_data.severity)
            except ValueError as e:
                raise APIException(
                    code="INVALID_ENUM_VALUE",
                    message=str(e),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    retryable=False
                )

        if request_data.environment:
            try:
                ValidationService.validate_environment(request_data.environment)
            except ValueError as e:
                raise APIException(
                    code="INVALID_ENUM_VALUE",
                    message=str(e),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    retryable=False
                )

        # Secret / sensitive data scan
        texts_to_scan = [raw_symptom]
        if request_data.log_excerpt:
            texts_to_scan.append(request_data.log_excerpt)
        if request_data.error_text:
            texts_to_scan.extend(request_data.error_text)

        for text_sample in texts_to_scan:
            scan_result = ValidationService.scan_for_secrets(text_sample)
            if scan_result.has_secrets:
                logger.warning(f"incident.secret_detected types={scan_result.detected_types}")
                raise APIException(
                    code="SENSITIVE_DATA_DETECTED",
                    message="Sensitive credential or secret pattern detected in input. Please remove all secrets or credentials before submitting.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    retryable=False,
                    details={"detected_types": scan_result.detected_types}
                )

        # Idempotency check
        if idempotency_key:
            existing = IncidentRepository.get_by_idempotency_key(db, idempotency_key)
            if existing:
                logger.info(f"incident.idempotent_hit id={existing.id} key={idempotency_key}")
                return existing

        # Deterministic Normalization
        normalized_obj = NormalizationService.normalize(
            raw_text=raw_symptom,
            explicit_service=request_data.service,
            explicit_environment=request_data.environment,
            explicit_severity=request_data.severity,
            explicit_recent_changes=request_data.recent_changes,
            explicit_error_text=request_data.error_text,
        )

        dup_id = IncidentRepository.find_potential_duplicate(
            db,
            service=normalized_obj.service,
            failure_mode_label=normalized_obj.failure_mode_label
        )
        is_duplicate = dup_id is not None

        incident_id = IncidentRepository.generate_next_incident_id(db)

        new_incident = Incident(
            id=incident_id,
            service=normalized_obj.service,
            environment=normalized_obj.environment,
            severity=normalized_obj.severity,
            status="created",  # Mandatory initial state
            symptoms_raw=raw_symptom,
            symptoms_normalized=normalized_obj.symptoms_normalized,
            normalized_data=normalized_obj.model_dump(),
            error_signatures=normalized_obj.error_signatures,
            failure_mode_label=normalized_obj.failure_mode_label,
            affected_components=normalized_obj.affected_components,
            recent_changes=normalized_obj.recent_changes,
            context=request_data.context or {},
            is_synthetic=bool(request_data.is_synthetic),
            possible_duplicate=is_duplicate,
            duplicate_of=dup_id,
            idempotency_key=idempotency_key,
            revision=1,
            analysis_revision=0,
            resolution_status="unresolved",
            postmortem_status="none"
        )

        saved = IncidentRepository.create(db, new_incident)
        IncidentRepository.record_audit(
            db=db,
            incident_id=saved.id,
            action="incident.created",
            actor=saved.operator,
            previous_state=None,
            new_state="created",
            outcome="success",
            details={
                "service": saved.service,
                "severity": saved.severity,
                "status": saved.status,
                "possible_duplicate": is_duplicate
            }
        )

        logger.info(f"incident.created id={saved.id} service={saved.service} status={saved.status}")
        return saved

    @classmethod
    def get_incident_by_id(cls, db: Session, incident_id: str) -> Incident:
        """Fetch incident by ID without triggering AI or Hindsight (API-003)."""
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident with ID '{incident_id}' was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False
            )
        return incident

    @classmethod
    def list_incidents(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        service_filter: Optional[str] = None,
        environment_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Incident], int]:
        """List incidents with comprehensive filtering, pagination, and stable ordering (API-002)."""
        return IncidentRepository.list_all(
            db=db,
            status=status_filter,
            service=service_filter,
            environment=environment_filter,
            severity=severity_filter,
            from_date=from_date,
            to_date=to_date,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset
        )

    @classmethod
    def transition_state(
        cls,
        db: Session,
        incident_id: str,
        new_status: str,
        expected_revision: Optional[int] = None,
        from_status: Optional[str] = None,
        actor: str = "sre-operator",
        reason: Optional[str] = None
    ) -> Incident:
        """
        Executes a controlled lifecycle state transition.
        Enforces:
        - Optimistic concurrency conflict detection
        - Legal state machine progression
        - Terminal state protection
        - Automatic audit recording
        """
        incident = cls.get_incident_by_id(db, incident_id)

        # 1. Optimistic Concurrency Checks (PRD BE-019 & Feature 2)
        if expected_revision is not None and incident.revision != expected_revision:
            logger.warning(
                f"incident.conflict id={incident_id} actual_revision={incident.revision} "
                f"expected_revision={expected_revision}"
            )
            raise APIException(
                code="CONFLICT",
                message=(
                    f"Concurrent modification conflict on incident '{incident_id}'. "
                    f"Current revision is {incident.revision}, but expected revision was {expected_revision}."
                ),
                status_code=status.HTTP_409_CONFLICT,
                retryable=True,
                details={
                    "incident_id": incident_id,
                    "current_revision": incident.revision,
                    "expected_revision": expected_revision
                }
            )

        if from_status is not None and incident.status != from_status:
            logger.warning(
                f"incident.conflict id={incident_id} actual_status='{incident.status}' "
                f"expected_from_status='{from_status}'"
            )
            raise APIException(
                code="CONFLICT",
                message=(
                    f"State conflict on incident '{incident_id}'. "
                    f"Current status is '{incident.status}', but expected previous status was '{from_status}'."
                ),
                status_code=status.HTTP_409_CONFLICT,
                retryable=True,
                details={
                    "incident_id": incident_id,
                    "current_status": incident.status,
                    "expected_status": from_status
                }
            )

        # 2. Terminal State Check
        if incident.status == "closed":
            raise APIException(
                code="INCIDENT_CLOSED",
                message="Cannot transition or modify an incident that is closed. Terminal states remain terminal.",
                status_code=status.HTTP_409_CONFLICT,
                retryable=False
            )

        # 3. State Machine Transition Validation
        try:
            ValidationService.validate_status_transition(incident.status, new_status)
        except ValueError as e:
            msg = str(e)
            if "TERMINAL_STATE" in msg:
                raise APIException(
                    code="TERMINAL_STATE_VIOLATION",
                    message=msg,
                    status_code=status.HTTP_409_CONFLICT
                )
            raise APIException(
                code="INVALID_STATE_TRANSITION",
                message=msg,
                status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
            )

        previous_status = incident.status
        incident.status = new_status

        # 4. Lifecycle Side-Effects
        if new_status == "resolved":
            incident.resolved_at = datetime.now(timezone.utc)
            incident.resolution_status = "resolved"
        elif new_status == "resolving":
            incident.resolution_status = "in_progress"
        elif new_status == "closed" and not incident.resolved_at:
            incident.resolved_at = datetime.now(timezone.utc)

        # 5. Persist Update
        updated = IncidentRepository.update(db, incident)

        # 6. Audit Logging
        IncidentRepository.record_audit(
            db=db,
            incident_id=updated.id,
            action="incident.state_transition",
            actor=actor,
            previous_state=previous_status,
            new_state=new_status,
            outcome="success",
            details={
                "reason": reason,
                "revision": updated.revision,
                "timestamp": updated.updated_at.isoformat()
            }
        )

        logger.info(
            f"incident.state_transition id={updated.id} from='{previous_status}' "
            f"to='{new_status}' revision={updated.revision} actor='{actor}'"
        )
        return updated

    @classmethod
    def patch_incident(
        cls,
        db: Session,
        incident_id: str,
        patch_data: IncidentPatchRequest,
        actor: str = "sre-operator"
    ) -> Incident:
        """Updates incident fields with concurrency protection and state machine enforcement."""
        incident = cls.get_incident_by_id(db, incident_id)

        # Concurrency guard
        if patch_data.expected_revision is not None and incident.revision != patch_data.expected_revision:
            raise APIException(
                code="CONFLICT",
                message=f"Concurrent modification detected. Incident revision is {incident.revision}, expected {patch_data.expected_revision}.",
                status_code=status.HTTP_409_CONFLICT,
                details={"current_revision": incident.revision, "expected_revision": patch_data.expected_revision}
            )

        if patch_data.from_status is not None and incident.status != patch_data.from_status:
            raise APIException(
                code="CONFLICT",
                message=f"Concurrent state conflict. Current status is '{incident.status}', expected '{patch_data.from_status}'.",
                status_code=status.HTTP_409_CONFLICT,
                details={"current_status": incident.status, "expected_status": patch_data.from_status}
            )

        if incident.status == "closed":
            raise APIException(
                code="INCIDENT_CLOSED",
                message="Cannot modify an incident that is already closed.",
                status_code=status.HTTP_409_CONFLICT
            )

        previous_status = incident.status
        status_changed = False

        if patch_data.status and patch_data.status != incident.status:
            try:
                ValidationService.validate_status_transition(incident.status, patch_data.status)
                incident.status = patch_data.status
                status_changed = True
                if patch_data.status == "resolved":
                    incident.resolved_at = datetime.now(timezone.utc)
                    incident.resolution_status = "resolved"
                elif patch_data.status == "resolving":
                    incident.resolution_status = "in_progress"
            except ValueError as e:
                raise APIException(
                    code="INVALID_STATE_TRANSITION",
                    message=str(e),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
                )

        if patch_data.severity:
            try:
                incident.severity = ValidationService.validate_severity(patch_data.severity)
            except ValueError as e:
                raise APIException(
                    code="INVALID_ENUM_VALUE",
                    message=str(e),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
                )

        if patch_data.environment:
            try:
                incident.environment = ValidationService.validate_environment(patch_data.environment)
            except ValueError as e:
                raise APIException(
                    code="INVALID_ENUM_VALUE",
                    message=str(e),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
                )

        if patch_data.service:
            incident.service = NormalizationService._clean_identifier(patch_data.service)

        if patch_data.recent_changes is not None:
            incident.recent_changes = patch_data.recent_changes

        if patch_data.error_text is not None:
            incident.error_signatures = patch_data.error_text

        if patch_data.context is not None:
            incident.context = patch_data.context

        if patch_data.symptom_description_correction:
            ValidationService.validate_symptom_description(patch_data.symptom_description_correction)
            scan = ValidationService.scan_for_secrets(patch_data.symptom_description_correction)
            if scan.has_secrets:
                raise APIException(
                    code="SENSITIVE_DATA_DETECTED",
                    message="Sensitive credential or secret detected in symptom correction.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            re_norm = NormalizationService.normalize(
                raw_text=patch_data.symptom_description_correction,
                explicit_service=incident.service,
                explicit_environment=incident.environment,
                explicit_severity=incident.severity
            )
            incident.symptoms_normalized = re_norm.symptoms_normalized
            incident.normalized_data = re_norm.model_dump()
            incident.failure_mode_label = re_norm.failure_mode_label
            incident.affected_components = re_norm.affected_components

        updated = IncidentRepository.update(db, incident)

        action = "incident.state_transition" if status_changed else "incident.updated"
        IncidentRepository.record_audit(
            db=db,
            incident_id=updated.id,
            action=action,
            actor=actor,
            previous_state=previous_status if status_changed else None,
            new_state=updated.status if status_changed else None,
            outcome="success",
            details={"revision": updated.revision, "status": updated.status}
        )
        logger.info(f"incident.patched id={updated.id} revision={updated.revision}")
        return updated

    @classmethod
    def get_audit_log(cls, db: Session, incident_id: str) -> List[AuditEvent]:
        """Fetch audit history for an incident without invoking external services."""
        cls.get_incident_by_id(db, incident_id)  # verify existence
        return IncidentRepository.get_audit_events(db, incident_id)
