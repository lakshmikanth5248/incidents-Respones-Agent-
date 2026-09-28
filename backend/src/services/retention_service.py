"""
Retention Service — Confirmed Operational Experience Retention Stage.

Conforms to PRD §12.10 (FR-058–FR-066), §2.2–§2.4 (RP-001–RP-016), UC-09, W-14,
and Backend Feature 13 requirements.

Flow enforced here:
    Resolved Incident -> Confirmed Post-Mortem -> Memory Candidate -> Validation
    -> Secret Scan -> Hindsight Retain -> Retained Entry IDs

Core guarantees:
  1. Preconditions are checked SERVER-SIDE (D-12, FR-061). The client never gets to
     assert that a post-mortem is confirmed; the stored record is the only authority.
  2. Validation and the secret scan run BEFORE any memory write (RP-010, SEC-008).
  3. Retention is idempotent per incident AND per entry identity (D-10, RP-015).
     A repeated request replays the original memory_entry_id instead of duplicating.
  4. A partial write is never reported as complete success (D-11, RP-014, ERR-03):
     status becomes `partial` and per-entry results are returned.
  5. Every composed record — successful or not — is preserved locally so a failed
     write is retryable (RP-014, FR-063, AC-24).
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import status
from sqlalchemy.orm import Session

from src.api.errors import APIException
from src.data.models.incident import Incident
from src.data.models.postmortem import PostMortem
from src.data.models.retention import MemoryRetention
from src.data.repositories.incident_repository import IncidentRepository
from src.memory.schemas import (
    MemoryCandidate,
    RetainEntryResult,
    RetainRequest,
    RetainResult,
    RetainSkippedEntry,
)
from src.memory.service import memory_service
from src.observability.logger import logger
from src.services.validation_service import (
    MemoryCandidateValidationError,
    ValidationService,
)


def compute_entry_key(incident_id: str, candidate: MemoryCandidate) -> str:
    """
    Derive the deterministic identity of a memory entry (D-10, RP-015).

    Identity is a function of the incident plus the entry's reusable content, so:
      - the same entry submitted twice produces the same key (idempotent replay)
      - a corrected body produces a new key, which may supersede the prior entry
        (RP-016) rather than contradicting it

    Whitespace and case are normalised so trivial reformatting is not treated as a
    new memory.
    """
    material = "|".join(
        [
            incident_id,
            (candidate.entry_type or "").strip(),
            (candidate.service or "").strip().lower(),
            (candidate.component or "").strip().lower(),
            " ".join((candidate.body or "").split()).lower(),
            (candidate.outcome_label or "").strip().lower(),
            (candidate.confidence or "").strip().lower(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


class RetentionService:
    """Orchestrates the confirmed-experience retention workflow."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    @classmethod
    def retain(
        cls,
        db: Session,
        request: RetainRequest,
        actor: str = "sre-operator",
    ) -> RetainResult:
        """
        Retain confirmed operational experience in Hindsight.

        Raises:
          404 INCIDENT_NOT_FOUND       — the incident does not exist
          409 CONFLICT                 — unconfirmed request, or no confirmed post-mortem
          422 INVALID_*  / SECRET_DETECTED — entry rejected before any write
          503 HINDSIGHT_UNAVAILABLE    — every write failed; records preserved for retry
        """
        # ── 1. Precondition: the incident must exist ──────────────────────
        incident = IncidentRepository.get_by_id(db, request.incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{request.incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False,
            )

        # ── 2. Precondition: explicit engineer confirmation (D-12) ───────
        if not request.confirmed:
            raise APIException(
                code="CONFLICT",
                message=(
                    "Retention requires explicit engineer confirmation "
                    "(confirmed=true). The client assertion is not trusted on its own."
                ),
                status_code=status.HTTP_409_CONFLICT,
                retryable=False,
                details={"incident_id": request.incident_id},
            )

        # ── 3. Precondition: the post-mortem must be CONFIRMED ────────────
        postmortem = (
            db.query(PostMortem)
            .filter(PostMortem.incident_id == request.incident_id)
            .first()
        )
        if not postmortem or postmortem.status != "confirmed":
            current = postmortem.status if postmortem else "none"
            raise APIException(
                code="POSTMORTEM_NOT_CONFIRMED",
                message=(
                    f"Incident '{request.incident_id}' has a post-mortem in state "
                    f"'{current}'. Experience may only be retained once the post-mortem "
                    "is confirmed (FR-056, FR-058)."
                ),
                status_code=status.HTTP_409_CONFLICT,
                retryable=False,
                details={
                    "incident_id": request.incident_id,
                    "postmortem_status": current,
                },
            )

        retain_id = f"RET-{request.incident_id}-{uuid.uuid4().hex[:8].upper()}"

        # ── 4. Validate, secret-scan and compose the entry set ────────────
        composed, results, skipped, validation_report = cls._validate_and_compose(
            request=request, incident=incident, postmortem=postmortem
        )

        if not composed:
            # Nothing is eligible for a write. No failure occurred, so this is an
            # explicit no-op, not a silent success: skipped[] and the report say why.
            validation_report.update({
                "written_entries": 0,
                "idempotent_entries": 0,
                "failed_entries": 0,
                "retain_id": retain_id,
                "postmortem_status": postmortem.status,
                "postmortem_id": postmortem.id,
            })
            cls._record_audit(
                db=db,
                incident=incident,
                retain_id=retain_id,
                postmortem=postmortem,
                actor=actor,
                status="retained",
                written=0,
                already_retained=0,
                failed=0,
                memory_entry_ids=[],
            )
            return RetainResult(
                status="retained",
                incident_id=request.incident_id,
                retain_id=retain_id,
                results=results,
                skipped=skipped,
                validation_report=validation_report,
            )

        # ── 5. Write eligible entries, honouring entry-identity idempotency ─
        succeeded_ids: List[str] = []
        already_retained = 0
        written_count = 0
        failed_count = 0
        pending: List[MemoryRetention] = []

        for index, candidate, entry_key in composed:
            ledger = cls._find_ledger_row(db, request.incident_id, entry_key)

            # D-10 / RP-015: identical entry already in Hindsight -> replay, no rewrite.
            if ledger is not None and ledger.status == "retained" and ledger.memory_entry_id:
                already_retained += 1
                succeeded_ids.append(ledger.memory_entry_id)
                results.append(RetainEntryResult(
                    status="already_retained",
                    memory_entry_id=ledger.memory_entry_id,
                    entry_type=candidate.entry_type,
                    entry_index=index,
                    entry_key=entry_key,
                ))
                ledger.retain_id = retain_id
                ledger.updated_at = datetime.now(timezone.utc)
                pending.append(ledger)
                continue

            payload = memory_service.build_retain_payload(candidate)
            is_new_row = ledger is None
            row = ledger or MemoryRetention(
                id=f"MRET-{uuid.uuid4().hex[:12]}",
                incident_id=request.incident_id,
                entry_key=entry_key,
                created_at=datetime.now(timezone.utc),
            )
            row.retain_id = retain_id
            row.entry_type = candidate.entry_type
            row.service = candidate.service
            row.component = candidate.component
            row.body = candidate.body
            row.outcome_label = candidate.outcome_label
            row.confidence = candidate.confidence
            row.source_incident_ref = candidate.source_incident_ref
            row.provenance_group_id = candidate.provenance_group_id
            row.is_synthetic = candidate.is_synthetic
            row.supersedes = candidate.supersedes
            row.confirmed_by = actor
            row.postmortem_id = postmortem.id
            row.updated_at = datetime.now(timezone.utc)
            row.attempts = (row.attempts or 0) + 1

            try:
                mem_id = memory_service.persist_entry(payload)
            except Exception as write_err:
                failed_count += 1
                error_text = str(write_err)
                row.status = "failed"
                row.error = error_text
                row.retained_at = None
                logger.error(
                    f"memory.retain_entry_failed retain_id={retain_id} "
                    f"incident_id={request.incident_id} entry_key={entry_key} "
                    f"error={error_text}"
                )
                results.append(RetainEntryResult(
                    status="failed",
                    entry_type=candidate.entry_type,
                    entry_index=index,
                    entry_key=entry_key,
                    error=error_text,
                ))
            else:
                written_count += 1
                succeeded_ids.append(mem_id)
                now = datetime.now(timezone.utc)
                row.status = "retained"
                row.memory_entry_id = mem_id
                row.error = None
                row.retained_at = now
                results.append(RetainEntryResult(
                    status="retained",
                    memory_entry_id=mem_id,
                    entry_type=candidate.entry_type,
                    entry_index=index,
                    entry_key=entry_key,
                ))

            if is_new_row:
                db.add(row)
            pending.append(row)

        # ── 6. Persist the retention ledger (successes AND failures) ──────
        # RP-014 / FR-063: the composed record survives so a failed write is retryable.
        db.add_all(pending)
        db.commit()

        validation_report["written_entries"] = written_count
        validation_report["idempotent_entries"] = already_retained
        validation_report["failed_entries"] = failed_count
        validation_report["retain_id"] = retain_id
        validation_report["postmortem_status"] = postmortem.status
        validation_report["postmortem_id"] = postmortem.id

        # ── 7. Determine the overall status; never report a partial as complete ──
        if failed_count == 0 and written_count > 0:
            overall_status = "retained"
        elif failed_count == 0 and already_retained > 0:
            overall_status = "retained"
        elif succeeded_ids and failed_count > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        # Per-entry results are reported in request order regardless of the order in
        # which validation skips and writes were interleaved.
        results.sort(key=lambda r: (r.entry_index is None, r.entry_index or 0))

        IncidentRepository.record_audit(
            db=db,
            incident_id=request.incident_id,
            action=f"memory.retained_{overall_status}",
            actor=actor,
            previous_state=incident.status,
            new_state=incident.status,
            outcome="success" if overall_status == "retained" else "failure",
            details={
                "retain_id": retain_id,
                "postmortem_id": postmortem.id,
                "written_entries": written_count,
                "idempotent_entries": already_retained,
                "failed_entries": failed_count,
                "memory_entry_ids": succeeded_ids,
            },
        )
        logger.info(
            f"memory.retain_complete retain_id={retain_id} incident_id={request.incident_id} "
            f"status={overall_status} written={written_count} "
            f"idempotent={already_retained} failed={failed_count} actor={actor}"
        )

        # ── 8. Total outage: 503, retryable, with the composed record preserved ──
        if overall_status == "failed" and composed:
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message=(
                    "Failed to retain entries in Hindsight. Memory service unavailable. "
                    "The composed entries have been preserved and the request is retryable."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                retryable=True,
                details={
                    "retain_id": retain_id,
                    "incident_id": request.incident_id,
                    "retryable": True,
                    "results": [r.model_dump() for r in results],
                },
            )

        return RetainResult(
            status=overall_status,
            incident_id=request.incident_id,
            retain_id=retain_id,
            memory_entry_id=succeeded_ids[0] if succeeded_ids else None,
            memory_entry_ids=succeeded_ids,
            results=results,
            skipped=skipped,
            validation_report=validation_report,
            idempotent=written_count == 0 and already_retained > 0,
            retry_pending=failed_count > 0,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @classmethod
    def _validate_and_compose(
        cls,
        request: RetainRequest,
        incident: Incident,
        postmortem: PostMortem,
    ) -> Tuple[
        List[Tuple[int, MemoryCandidate, str]],
        List[RetainEntryResult],
        List[RetainSkippedEntry],
        Dict[str, Any],
    ]:

        """
        Server-side validation, secret scan and provenance stamping.

        Returns (composed, results, skipped, validation_report) where `composed` holds
        (request_index, candidate, entry_key) for every entry eligible for a write.
        """
        composed: List[Tuple[int, MemoryCandidate, str]] = []
        results: List[RetainEntryResult] = []
        skipped: List[RetainSkippedEntry] = []
        validation_report: Dict[str, Any] = {
            "submitted_entries": len(request.entries),
            "valid_entries": 0,
            "rejected_entries": 0,
            "provenance_corrected": 0,
            "secret_scan": "passed",
            "incident_service": incident.service,
        }

        for index, candidate in enumerate(request.entries):
            # ── Server-side validation (never trust the client) ────────────
            try:
                ValidationService.validate_memory_candidate(
                    entry_type=candidate.entry_type,
                    body=candidate.body,
                    confidence=candidate.confidence,
                    outcome_label=candidate.outcome_label,
                )
            except MemoryCandidateValidationError as invalid:
                raise APIException(
                    code=invalid.code,
                    message=invalid.message,
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    retryable=False,
                    details={
                        "entry_index": index,
                        "entry_type": candidate.entry_type,
                        "field": invalid.field,
                    },
                )

            # ── Secret scan before any write (SEC-008, HM-015) ─────────────
            scan_res = ValidationService.scan_for_secrets(candidate.body)
            if scan_res.has_secrets:
                types_str = ", ".join(scan_res.detected_types)
                raise APIException(
                    code="SECRET_DETECTED",
                    message=(
                        f"Credential-shaped value detected in memory entry "
                        f"{index} ({types_str}). Retention blocked pre-write per "
                        "SEC-008. Remove the credential and retry. The offending "
                        "entry is identified by index and type only."
                    ),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    retryable=False,
                    details={
                        "entry_index": index,
                        "entry_type": candidate.entry_type,
                        "detected_secret_type": types_str,
                    },
                )

            # ── Provenance is server-authoritative (RP-013, D-03) ──────────
            if not candidate.source_incident_ref or candidate.source_incident_ref != request.incident_id:
                candidate.source_incident_ref = request.incident_id
                validation_report["provenance_corrected"] += 1
            if not candidate.service:
                candidate.service = incident.service
                validation_report["provenance_corrected"] += 1

            # ── RP-012: action/procedure entries require an outcome label ──
            if ValidationService.memory_candidate_requires_outcome(candidate.entry_type) and not candidate.outcome_label:
                reason = "Missing required outcome_label for procedure/action entry (RP-012)"
                validation_report["rejected_entries"] += 1
                skipped.append(RetainSkippedEntry(
                    entry_index=index,
                    entry_type=candidate.entry_type,
                    reason=reason,
                ))
                results.append(RetainEntryResult(
                    status="skipped",
                    entry_type=candidate.entry_type,
                    entry_index=index,
                    error=reason,
                ))
                continue

            # ── RP-011: confidence is mandatory ─────────────────────────────
            if not candidate.confidence:
                candidate.confidence = "low"

            validation_report["valid_entries"] += 1
            composed.append((index, candidate, compute_entry_key(request.incident_id, candidate)))

        return composed, results, skipped, validation_report

    @staticmethod
    def _find_ledger_row(db: Session, incident_id: str, entry_key: str) -> Optional[MemoryRetention]:
        """Look up the retention ledger row for an (incident, entry identity) pair."""
        return (
            db.query(MemoryRetention)
            .filter(
                MemoryRetention.incident_id == incident_id,
                MemoryRetention.entry_key == entry_key,
            )
            .first()
        )
