"""
Hindsight Memory Service Module.
Single isolated gateway to Hindsight memory per Architectural Invariants.
Conforms strictly to PRD §11.2 (Hindsight Service), §1.4 (HM-023 to HM-032),
§3.4 (RL-009 to RL-017), §5 (Retain Workflow), and Feature 04 Requirements.
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import status
from src.config import settings
from src.observability.logger import logger
from src.services.validation_service import ValidationService
from src.api.errors import APIException
from src.memory.schemas import (
    MemoryStatus,
    OutcomeLabel,
    ConfidenceLevel,
    FlagType,
    FlagRecord,
    MemoryEntry,
    MemoryCandidate,
    RecallRequest,
    RecallResult,
    RecallRecord,
    RankingDetail,
    RetainRequest,
    RetainResult,
    RetainEntryResult,
)
from src.memory.ranking import rank_and_score_entries
from src.memory.query_builder import build_recall_intent
from src.memory.client import (
    HindsightClient,
    HindsightClientError,
    HindsightUnavailableError,
    HindsightTimeoutError,
    HindsightMalformedResponseError,
    HindsightAPIError,
)
from src.memory.test_double import HindsightTestDouble


class MemoryService:
    """
    Isolated Hindsight Integration Layer.
    CRITICAL RULE: Hindsight must be reachable through this single backend interface.
    """

    def __init__(self, client: Optional[Union[HindsightClient, HindsightTestDouble]] = None):
        if client is not None:
            self._client = client
        elif settings.HINDSIGHT_USE_TEST_DOUBLE or settings.APP_ENV in ("test", "demo"):
            self._client = HindsightTestDouble(bank_id=settings.HINDSIGHT_BANK_ID)
        else:
            self._client = HindsightClient(
                base_url=settings.HINDSIGHT_ENDPOINT,
                api_key=settings.HINDSIGHT_API_KEY,
                bank_id=settings.HINDSIGHT_BANK_ID,
                timeout=settings.HINDSIGHT_TIMEOUT_SECONDS,
                max_retries=settings.HINDSIGHT_MAX_RETRIES,
            )

    @property
    def client(self) -> Union[HindsightClient, HindsightTestDouble]:
        return self._client

    def set_client(self, client: Union[HindsightClient, HindsightTestDouble]):
        """Inject or swap client (useful for tests)."""
        self._client = client

    def health_check(self) -> Tuple[bool, str]:
        """Verify Hindsight service operational health."""
        try:
            return self._client.health_check()
        except Exception as e:
            logger.error(f"memory.health_check_failed error={str(e)}")
            return False, f"unavailable: {str(e)}"

    def recall(self, request: RecallRequest) -> RecallResult:
        """
        Recall relevant historical experiences from Hindsight.
        Guarantees:
        - memory_isolated=True -> status=suppressed
        - failure/timeout/5xx -> status=degraded (NEVER empty!)
        - no matching records -> status=empty (NEVER degraded!)
        - matching records -> status=ok with deterministic ranking & relevance_basis
        """
        start_time = time.perf_counter()

        # Derive intent if query is not explicitly provided or to augment
        intent = build_recall_intent(request, query_override=request.query)
        query_recorded = intent.composed_query
        query_version = request.query_version or intent.query_version

        scope = {
            "service": request.service or intent.service,
            "environment": request.environment or intent.environment,
            "failure_mode": request.failure_mode or intent.failure_mode,
        }

        # 1. Check memory-isolated mode (PRD FR-022, RL-017, D-08)
        if request.memory_isolated or settings.MEMORY_ISOLATED:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("memory.recall_suppressed memory_isolated=true")
            record = RecallRecord(
                query=query_recorded,
                query_version=query_version,
                memory_status=MemoryStatus.SUPPRESSED.value,
                returned_entries=[],
                ranking=[],
                relevance_basis={},
                duration_ms=duration_ms,
                scope=scope,
            )
            return RecallResult(
                memory_status=MemoryStatus.SUPPRESSED,
                query_recorded=query_recorded,
                scope=scope,
                total_found=0,
                entries=[],
                recall_record=record,
            )

        # 2. Build retrieval filters
        filters: Dict[str, Any] = {}
        if scope["service"]:
            filters["service"] = scope["service"]
        if request.entry_types and len(request.entry_types) == 1:
            filters["entry_type"] = request.entry_types[0]
        if request.outcome_labels and len(request.outcome_labels) == 1:
            filters["outcome_label"] = request.outcome_labels[0]

        # 3. Call Hindsight client with failure trapping
        try:
            raw_response = self._client.recall(
                query=query_recorded,
                filters=filters,
                limit=request.limit * 2,  # Fetch extra for ranking filtering
            )
        except (HindsightUnavailableError, HindsightTimeoutError, HindsightMalformedResponseError, HindsightClientError) as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = str(exc)
            logger.error(f"memory.recall_failed status=degraded error={error_msg}")
            # CRITICAL FAILURE BEHAVIOR:
            # If Hindsight fails: memory_status = degraded. Do NOT return as if recall succeeded.
            record = RecallRecord(
                query=query_recorded,
                query_version=query_version,
                memory_status=MemoryStatus.DEGRADED.value,
                returned_entries=[],
                ranking=[],
                relevance_basis={},
                duration_ms=duration_ms,
                scope=scope,
                error=error_msg,
            )
            return RecallResult(
                memory_status=MemoryStatus.DEGRADED,
                query_recorded=query_recorded,
                scope=scope,
                total_found=0,
                entries=[],
                recall_record=record,
                degraded_reason=error_msg,
                error_code="HINDSIGHT_UNAVAILABLE",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = f"Unexpected memory recall error: {str(exc)}"
            logger.error(f"memory.recall_unexpected_error status=degraded error={error_msg}")
            record = RecallRecord(
                query=query_recorded,
                query_version=query_version,
                memory_status=MemoryStatus.DEGRADED.value,
                returned_entries=[],
                ranking=[],
                relevance_basis={},
                duration_ms=duration_ms,
                scope=scope,
                error=error_msg,
            )
            return RecallResult(
                memory_status=MemoryStatus.DEGRADED,
                query_recorded=query_recorded,
                scope=scope,
                total_found=0,
                entries=[],
                recall_record=record,
                degraded_reason=error_msg,
                error_code="HINDSIGHT_UNAVAILABLE",
            )

        # 4. Normalize raw response entries into MemoryEntry objects
        raw_memories = raw_response.get("memories", [])
        if not raw_memories:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("memory.recall_empty no_memories_found=true")
            record = RecallRecord(
                query=query_recorded,
                query_version=query_version,
                memory_status=MemoryStatus.EMPTY.value,
                returned_entries=[],
                ranking=[],
                relevance_basis={},
                duration_ms=duration_ms,
                scope=scope,
            )
            return RecallResult(
                memory_status=MemoryStatus.EMPTY,
                query_recorded=query_recorded,
                scope=scope,
                total_found=0,
                entries=[],
                recall_record=record,
            )

        normalized_entries: List[MemoryEntry] = []
        for item in raw_memories:
            try:
                flag_data = item.get("flagged")
                flag_rec = None
                if flag_data and isinstance(flag_data, dict):
                    flag_rec = FlagRecord(
                        flag_type=FlagType(flag_data["flag_type"]),
                        reason=flag_data.get("reason", ""),
                        note=flag_data.get("note"),
                        flagged_at=flag_data.get("flagged_at", ""),
                    )

                entry = MemoryEntry(
                    entry_id=str(item.get("entry_id") or item.get("id")),
                    entry_type=str(item.get("entry_type", "incident_experience")),
                    service=str(item.get("service", scope["service"] or "unknown")),
                    component=item.get("component"),
                    body=str(item.get("body") or item.get("content", "")),
                    outcome_label=item.get("outcome_label"),
                    confidence=item.get("confidence", "confirmed"),
                    source_incident_ref=str(item.get("source_incident_ref") or item.get("source_incident_id", "unknown")),
                    retained_at=item.get("retained_at"),
                    flagged=flag_rec,
                    provenance_group_id=item.get("provenance_group_id"),
                    is_synthetic=item.get("is_synthetic", True),
                    supersedes=item.get("supersedes"),
                )
                normalized_entries.append(entry)
            except Exception as parse_err:
                logger.warning(f"memory.normalize_entry_failed error={str(parse_err)} item={item}")

        # 5. Execute deterministic ranking layer (RL-012, RL-013, RL-014)
        ranked = rank_and_score_entries(
            entries=normalized_entries,
            query=query_recorded,
            service=scope["service"],
            environment=scope["environment"],
            failure_mode=scope["failure_mode"],
            error_signatures=request.error_signatures,
        )

        # 6. Apply relevance filtering
        # If all candidates are completely irrelevant (score < 0.20 and not matching service/query)
        effective_entries = [e for e in ranked if e.relevance_score > 0.10]

        if not effective_entries:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("memory.recall_empty all_entries_weak=true")
            record = RecallRecord(
                query=query_recorded,
                query_version=query_version,
                memory_status=MemoryStatus.EMPTY.value,
                returned_entries=[],
                ranking=[],
                relevance_basis={},
                duration_ms=duration_ms,
                scope=scope,
            )
            return RecallResult(
                memory_status=MemoryStatus.EMPTY,
                query_recorded=query_recorded,
                scope=scope,
                total_found=0,
                entries=[],
                recall_record=record,
            )

        final_slice = effective_entries[: request.limit]
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"memory.recall_ok count={len(final_slice)} top_score={final_slice[0].relevance_score if final_slice else 0}"
        )

        ranking_details = [
            RankingDetail(
                entry_id=e.entry_id,
                rank=idx + 1,
                score=e.relevance_score,
                relevance_basis=e.relevance_basis
            )
            for idx, e in enumerate(final_slice)
        ]
        relevance_basis_map = {e.entry_id: e.relevance_basis for e in final_slice}
        record = RecallRecord(
            query=query_recorded,
            query_version=query_version,
            memory_status=MemoryStatus.OK.value,
            returned_entries=[e.to_dict() for e in final_slice],
            ranking=ranking_details,
            relevance_basis=relevance_basis_map,
            duration_ms=duration_ms,
            scope=scope,
        )

        return RecallResult(
            memory_status=MemoryStatus.OK,
            query_recorded=query_recorded,
            scope=scope,
            total_found=len(effective_entries),
            entries=final_slice,
            recall_record=record,
        )

    def persist_entry(self, payload: Dict[str, Any]) -> str:
        """
        Write exactly one composed entry to Hindsight and return its stable memory id.

        This is the single low-level write primitive. Callers own the failure policy
        (per-entry error capture, partial reporting, retry), so any Hindsight error is
        propagated rather than swallowed here.

        Raises HindsightClientError subclasses (unavailable / timeout / malformed / api)
        when the write cannot be completed.
        """
        response = self._client.retain(payload)
        mem_id = response.get("entry_id") or response.get("id")
        if not mem_id:
            raise HindsightMalformedResponseError(
                "Hindsight retain response did not include a memory entry id."
            )
        return str(mem_id)

    def build_retain_payload(self, candidate: MemoryCandidate) -> Dict[str, Any]:
        """Compose the Hindsight write payload for a validated memory candidate."""
        return {
            "entry_type": candidate.entry_type,
            "service": candidate.service,
            "component": candidate.component,
            "body": candidate.body,
            "outcome_label": candidate.outcome_label,
            "confidence": candidate.confidence,
            "source_incident_ref": candidate.source_incident_ref,
            "provenance_group_id": candidate.provenance_group_id,
            "provenance": candidate.provenance or {},
            "is_synthetic": candidate.is_synthetic,
            "supersedes": candidate.supersedes,
        }

    def retain(self, request: RetainRequest) -> RetainResult:
        """
        Retain structured, validated memory entries in Hindsight.
        Enforces:
        - Server-side confirmation requirement (D-12, API-021)
        - Secret scanning on entry bodies (SEC-008, HM-015)
        - Outcome label requirement for actions/procedures (RP-012)
        - Graceful handling of partial retention (AC2-07a, ERR-03)

        NOTE: this is the stateless memory-gateway path. The full retention workflow
        (incident + confirmed post-mortem preconditions, identity-based idempotency,
        retry ledger) lives in `src.services.retention_service.RetentionService`.
        """
        # 1. Enforce confirmation server-side
        if not request.confirmed:
            raise APIException(
                code="CONFLICT",
                message="Retention requires explicit operator confirmation (confirmed=true).",
                status_code=409,
                retryable=False,
            )

        if not request.entries:
            return RetainResult(
                status="retained",
                incident_id=request.incident_id,
                results=[],
                skipped=[],
                validation_report={
                    "submitted_entries": 0,
                    "valid_entries": 0,
                    "rejected_entries": 0,
                    "secret_scan": "passed",
                },
            )

        results: List[RetainEntryResult] = []
        skipped: List[Dict[str, str]] = []
        validation_report: Dict[str, Any] = {
            "submitted_entries": len(request.entries),
            "valid_entries": 0,
            "rejected_entries": 0,
            "secret_scan": "passed",
        }

        # 2. Validate and secret-scan each candidate
        validated_candidates: List[Tuple[int, MemoryCandidate]] = []
        for index, candidate in enumerate(request.entries):
            # Secret scan pre-write (SEC-008, HM-015)
            scan_res = ValidationService.scan_for_secrets(candidate.body)
            if scan_res.has_secrets:
                types_str = ", ".join(scan_res.detected_types)
                raise APIException(
                    code="SECRET_DETECTED",
                    message=(
                        f"Secret detected in memory entry body ({types_str}). "
                        "Retention blocked pre-write per SEC-008."
                    ),
                    status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
                    retryable=False,
                    details={
                        "entry_index": index,
                        "entry_type": candidate.entry_type,
                        "detected_secret_type": types_str,
                    }
                )

            # Procedure/Action outcome validation (RP-012)
            if ValidationService.memory_candidate_requires_outcome(candidate.entry_type) and not candidate.outcome_label:
                skipped.append({
                    "entry_index": str(index),
                    "entry_type": candidate.entry_type,
                    "reason": "Missing required outcome_label for procedure/action entry (RP-012)"
                })
                validation_report["rejected_entries"] += 1
                continue

            validated_candidates.append((index, candidate))
            validation_report["valid_entries"] += 1

        # 3. Write validated candidates to Hindsight
        succeeded_count = 0
        failed_count = 0
        memory_entry_ids: List[str] = []

        for index, candidate in validated_candidates:
            payload = self.build_retain_payload(candidate)

            try:
                mem_id = self.persist_entry(payload)
                memory_entry_ids.append(mem_id)
                results.append(RetainEntryResult(
                    status="retained",
                    memory_entry_id=mem_id,
                    entry_type=candidate.entry_type,
                    entry_index=index,
                ))
                succeeded_count += 1
            except Exception as retain_err:
                logger.error(
                    f"memory.retain_entry_failed type={candidate.entry_type} error={str(retain_err)}"
                )
                results.append(RetainEntryResult(
                    status="failed",
                    entry_type=candidate.entry_type,
                    entry_index=index,
                    error=str(retain_err)
                ))
                failed_count += 1

        # 4. Determine overall retain status
        if failed_count == 0 and succeeded_count > 0:
            overall_status = "retained"
        elif succeeded_count > 0 and failed_count > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        # If all failed due to service outage, surface 503
        if overall_status == "failed" and validated_candidates:
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message="Failed to retain entries in Hindsight. Memory service unavailable.",
                status_code=503,
                retryable=True,
                details={"results": [r.model_dump() for r in results]}
            )

        return RetainResult(
            status=overall_status,
            incident_id=request.incident_id,
            memory_entry_id=memory_entry_ids[0] if memory_entry_ids else None,
            memory_entry_ids=memory_entry_ids,
            results=results,
            skipped=skipped,
            validation_report=validation_report,
            retry_pending=failed_count > 0,
        )

    def get_experience(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a single retained memory entry by its ID."""
        try:
            raw = self._client.get_experience(entry_id)
            if not raw:
                return None
            flag_data = raw.get("flagged")
            flag_rec = None
            if flag_data and isinstance(flag_data, dict):
                flag_rec = FlagRecord(
                    flag_type=FlagType(flag_data["flag_type"]),
                    reason=flag_data.get("reason", ""),
                    note=flag_data.get("note"),
                    flagged_at=flag_data.get("flagged_at", ""),
                )

            return MemoryEntry(
                entry_id=str(raw.get("entry_id") or raw.get("id")),
                entry_type=str(raw.get("entry_type", "incident_experience")),
                service=str(raw.get("service", "unknown")),
                component=raw.get("component"),
                body=str(raw.get("body") or raw.get("content", "")),
                outcome_label=raw.get("outcome_label"),
                confidence=raw.get("confidence", "confirmed"),
                source_incident_ref=str(raw.get("source_incident_ref") or raw.get("source_incident_id", "unknown")),
                retained_at=raw.get("retained_at"),
                flagged=flag_rec,
                provenance_group_id=raw.get("provenance_group_id"),
                is_synthetic=raw.get("is_synthetic", True),
                supersedes=raw.get("supersedes"),
            )
        except (HindsightUnavailableError, HindsightTimeoutError, HindsightClientError) as exc:
            logger.error(f"memory.get_experience_unavailable id={entry_id} error={str(exc)}")
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message=f"Memory service unavailable: {str(exc)}",
                status_code=503,
                retryable=True,
            )

    def flag_experience(
        self,
        entry_id: str,
        flag_type: str,
        reason: str,
        note: Optional[str] = None,
    ) -> MemoryEntry:
        """Report a retained record as incorrect, inapplicable, or outdated (FR-074, API-014)."""
        valid_flags = [f.value for f in FlagType]
        if flag_type not in valid_flags:
            raise APIException(
                code="INVALID_FLAG_TYPE",
                message=f"Flag type must be one of {valid_flags}",
                status_code=400,
                retryable=False,
            )

        try:
            updated = self._client.flag_experience(
                entry_id=entry_id,
                flag_data={"flag_type": flag_type, "reason": reason, "note": note}
            )
            return self.get_experience(entry_id) or MemoryEntry(
                entry_id=entry_id,
                entry_type=updated.get("entry_type", "incident_experience"),
                service=updated.get("service", "unknown"),
                body=updated.get("body", ""),
                source_incident_ref=updated.get("source_incident_ref", "unknown"),
                flagged=FlagRecord(flag_type=FlagType(flag_type), reason=reason, note=note)
            )
        except HindsightAPIError as e:
            if e.status_code == 404:
                raise APIException(
                    code="NOT_FOUND",
                    message=f"Memory entry {entry_id} not found.",
                    status_code=404,
                    retryable=False,
                )
            raise APIException(
                code="HINDSIGHT_API_ERROR",
                message=f"Failed to flag memory entry: {str(e)}",
                status_code=e.status_code,
                retryable=False,
            )
        except (HindsightUnavailableError, HindsightTimeoutError, HindsightClientError) as exc:
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message=f"Memory service unavailable: {str(exc)}",
                status_code=503,
                retryable=True,
            )

    def list_experiences(
        self,
        service: Optional[str] = None,
        failure_mode_label: Optional[str] = None,
        entry_type: Optional[str] = None,
        outcome_label: Optional[str] = None,
        include_flagged: bool = True,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Browse retained experiences by service or class (PRD FR-075, API-013)."""
        filters: Dict[str, Any] = {}
        if service:
            filters["service"] = service
        if entry_type:
            filters["entry_type"] = entry_type
        if outcome_label:
            filters["outcome_label"] = outcome_label

        try:
            res = self._client.recall(query=failure_mode_label or "", filters=filters, limit=limit)
            memories = res.get("memories", [])
            entries: List[MemoryEntry] = []
            for item in memories:
                if not include_flagged and item.get("flagged"):
                    continue
                flag_data = item.get("flagged")
                flag_rec = None
                if flag_data and isinstance(flag_data, dict):
                    flag_rec = FlagRecord(
                        flag_type=FlagType(flag_data["flag_type"]),
                        reason=flag_data.get("reason", ""),
                        note=flag_data.get("note"),
                        flagged_at=flag_data.get("flagged_at", ""),
                    )

                entries.append(MemoryEntry(
                    entry_id=str(item.get("entry_id") or item.get("id")),
                    entry_type=str(item.get("entry_type", "incident_experience")),
                    service=str(item.get("service", "unknown")),
                    component=item.get("component"),
                    body=str(item.get("body") or item.get("content", "")),
                    outcome_label=item.get("outcome_label"),
                    confidence=item.get("confidence", "confirmed"),
                    source_incident_ref=str(item.get("source_incident_ref") or item.get("source_incident_id", "unknown")),
                    retained_at=item.get("retained_at"),
                    flagged=flag_rec,
                    provenance_group_id=item.get("provenance_group_id"),
                    is_synthetic=item.get("is_synthetic", True),
                    supersedes=item.get("supersedes"),
                ))
            return entries
        except (HindsightUnavailableError, HindsightTimeoutError, HindsightClientError) as exc:
            raise APIException(
                code="HINDSIGHT_UNAVAILABLE",
                message=f"Memory service unavailable: {str(exc)}",
                status_code=503,
                retryable=True,
            )


# Global singleton memory service instance
memory_service = MemoryService()
