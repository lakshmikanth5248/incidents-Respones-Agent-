"""
Runbook Reference Service.
Conforms strictly to PRD §12.4 (API-015), §12.6 (FR-036, FR-037, FR-041), and Feature 08.
Provides catalog access, search, and memory-joined track records.
"""

from typing import Dict, Any, List, Optional
from src.api.errors import APIException
from src.runbooks.schemas import Runbook, RunbookTrackRecord
from src.memory.schemas import MemoryEntry, OutcomeLabel


DEFAULT_RUNBOOKS: List[Dict[str, Any]] = [
    {
        "id": "RB-PAY-001",
        "title": "Payment API Connection Pool Recovery",
        "service": "payment-api",
        "failure_mode_label": "database_connection_exhaustion",
        "applicable_symptoms": [
            "connection pool exhausted",
            "HikariPool",
            "connection timeout",
            "HTTP 500 in payment processing",
            "database latency spike",
        ],
        "steps": [
            "1. Query pg_stat_activity for idle-in-transaction connections older than 60s.",
            "2. Inspect transaction manager connection leak timeout configuration.",
            "3. Gracefully terminate stale database connection leases.",
            "4. Verify active connection count drops below pool capacity ceiling.",
        ],
        "risk_level": "medium",
        "is_destructive": False,
        "safer_diagnostic_alternative": "Query pg_stat_activity read-only metrics before terminating any connection.",
    },
    {
        "id": "RB-PAY-ROLLBACK-002",
        "title": "Payment API Deployment Rollback",
        "service": "payment-api",
        "failure_mode_label": "database_connection_exhaustion",
        "applicable_symptoms": [
            "post-deployment regression",
            "regression after release",
            "pool leak after deployment",
        ],
        "steps": [
            "1. Identify previous healthy container image release tag.",
            "2. Confirm deployment rollback approval with incident commander.",
            "3. Revert deployment manifest to previous stable revision.",
            "4. Monitor error rate and connection pool stabilization.",
        ],
        "risk_level": "high",
        "is_destructive": True,
        "safer_diagnostic_alternative": "Compare deployment diff and connection pool configurations between current and previous revisions before rolling back.",
    },
    {
        "id": "RB-CHECKOUT-001",
        "title": "Checkout Service Lock Contention Mitigation",
        "service": "checkout-service",
        "failure_mode_label": "database_deadlock",
        "applicable_symptoms": [
            "transaction deadlock",
            "inventory row lock",
            "checkout timeout",
            "lock wait timeout",
        ],
        "steps": [
            "1. Inspect pg_locks and blocking transaction IDs.",
            "2. Identify long-running transactions holding pessimistic cart locks.",
            "3. Cancel blocking statement holding lock on inventory rows.",
            "4. Verify checkout queue processing resumes.",
        ],
        "risk_level": "medium",
        "is_destructive": False,
        "safer_diagnostic_alternative": "Inspect lock dependency graph in pg_stat_activity before canceling any transaction.",
    },
    {
        "id": "RB-CACHE-001",
        "title": "Redis Cache Node Eviction Recovery",
        "service": "session-service",
        "failure_mode_label": "cache_eviction",
        "applicable_symptoms": [
            "Redis maxmemory limit",
            "cache eviction avalanche",
            "session retrieval latency",
        ],
        "steps": [
            "1. Inspect Redis info memory and eviction metrics.",
            "2. Verify maxmemory-policy setting across cluster nodes.",
            "3. Flush volatile expired session keys to relieve memory pressure.",
            "4. Scale cache memory limit if persistent growth observed.",
        ],
        "risk_level": "medium",
        "is_destructive": False,
        "safer_diagnostic_alternative": "Sample memory usage keys without issuing flush commands.",
    },
    {
        "id": "RB-AUTH-001",
        "title": "Auth Gateway JWKS Key Refresh",
        "service": "auth-service",
        "failure_mode_label": "token_verification_failure",
        "applicable_symptoms": [
            "JWKS key rotation",
            "signature verification failed",
            "token invalid signature",
        ],
        "steps": [
            "1. Verify upstream identity provider JWKS endpoint availability.",
            "2. Clear local auth-gateway JWKS cache keys.",
            "3. Confirm dual-key signing grace period is active.",
        ],
        "risk_level": "low",
        "is_destructive": False,
        "safer_diagnostic_alternative": None,
    },
    {
        "id": "RB-SEARCH-001",
        "title": "Elasticsearch Unassigned Replica Shard Recovery",
        "service": "search-service",
        "failure_mode_label": "shard_allocation_failure",
        "applicable_symptoms": [
            "cluster yellow status",
            "unassigned replica shards",
            "search latency",
        ],
        "steps": [
            "1. Inspect cluster allocation explain API for unassigned shards.",
            "2. Check node disk thresholds and JVM garbage collection pauses.",
            "3. Trigger shard allocation retry for unassigned replica shards.",
        ],
        "risk_level": "medium",
        "is_destructive": False,
        "safer_diagnostic_alternative": "Query cluster health API without forcing allocation.",
    },
]


class RunbookService:
    """Service managing the reference runbook catalog and joined track records."""

    def __init__(self):
        self._is_available: bool = True
        self._runbooks: Dict[str, Runbook] = {}
        self.reset()

    def reset(self):
        """Reset to initial default catalog."""
        self._is_available = True
        self._runbooks = {}
        for rb_data in DEFAULT_RUNBOOKS:
            self._runbooks[rb_data["id"]] = Runbook(**rb_data)

    def set_available(self, available: bool):
        """Simulate runbook reference set availability / outage."""
        self._is_available = available

    def is_available(self) -> bool:
        return self._is_available

    def _check_available(self):
        if not self._is_available:
            raise APIException(
                code="RUNBOOK_SET_UNAVAILABLE",
                message="The runbook reference set cannot be reached. No runbook coverage available.",
                status_code=503,
                retryable=True,
            )

    def list_runbooks(
        self,
        service: Optional[str] = None,
        failure_mode_label: Optional[str] = None,
        q: Optional[str] = None,
        recalled_memories: Optional[List[MemoryEntry]] = None,
    ) -> List[Runbook]:
        """List and search runbooks with memory-joined track records."""
        self._check_available()

        matched: List[Runbook] = []
        q_clean = q.strip().lower() if q else None
        svc_clean = service.strip().lower() if service else None
        fm_clean = failure_mode_label.strip().lower() if failure_mode_label else None

        for rb in self._runbooks.values():
            if svc_clean and rb.service.lower() != svc_clean:
                continue
            if fm_clean and rb.failure_mode_label.lower() != fm_clean:
                continue
            if q_clean:
                in_title = q_clean in rb.title.lower()
                in_steps = any(q_clean in s.lower() for s in rb.steps)
                in_symptoms = any(q_clean in s.lower() for s in rb.applicable_symptoms)
                if not (in_title or in_steps or in_symptoms):
                    continue

            # Join memory track record
            rb_copy = self._join_track_record(rb, recalled_memories)
            matched.append(rb_copy)

        return matched

    def get_runbook(
        self,
        runbook_id: str,
        recalled_memories: Optional[List[MemoryEntry]] = None,
    ) -> Optional[Runbook]:
        """Retrieve a specific runbook joined with its track record."""
        self._check_available()
        rb = self._runbooks.get(runbook_id)
        if not rb:
            return None
        return self._join_track_record(rb, recalled_memories)

    def find_matching_runbooks(
        self,
        service: str,
        failure_mode: str,
        symptoms: str = "",
        recalled_memories: Optional[List[MemoryEntry]] = None,
    ) -> List[Runbook]:
        """Find matching runbooks for an incident."""
        self._check_available()

        matched = []
        svc_clean = service.strip().lower() if service else ""
        fm_clean = failure_mode.strip().lower() if failure_mode else ""
        sym_clean = symptoms.strip().lower() if symptoms else ""

        for rb in self._runbooks.values():
            # Exact service + failure mode match
            if svc_clean and rb.service.lower() == svc_clean:
                if fm_clean and (fm_clean in rb.failure_mode_label.lower() or rb.failure_mode_label.lower() in fm_clean):
                    matched.append(self._join_track_record(rb, recalled_memories))
                    continue
                # Symptom overlap match
                if any(s.lower() in sym_clean for s in rb.applicable_symptoms):
                    matched.append(self._join_track_record(rb, recalled_memories))
                    continue

        return matched

    def _join_track_record(
        self,
        runbook: Runbook,
        recalled_memories: Optional[List[MemoryEntry]] = None,
    ) -> Runbook:
        """Join runbook with historical outcome track record from retained memories."""
        rb_dict = runbook.model_dump()
        track = RunbookTrackRecord()

        if recalled_memories:
            for mem in recalled_memories:
                body_lower = mem.body.lower()
                outcome = (mem.outcome_label or "").lower()

                # Check if memory references this runbook id or procedure title
                if runbook.id.lower() in body_lower or runbook.title.lower() in body_lower:
                    track.times_applied += 1
                    track.outcome_source = "retained_memory"
                    if outcome == OutcomeLabel.SUCCESSFUL.value:
                        track.times_successful += 1
                        track.last_outcome = OutcomeLabel.SUCCESSFUL.value
                    elif outcome == OutcomeLabel.INEFFECTIVE.value:
                        track.times_ineffective += 1
                        track.last_outcome = OutcomeLabel.INEFFECTIVE.value

        rb_dict["track_record"] = track.model_dump()
        return Runbook(**rb_dict)


# Global runbook service instance
runbook_service = RunbookService()
