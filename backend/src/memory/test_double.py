"""
Hindsight Test Double for Offline Execution and Deterministic Testing.
Conforms strictly to Feature 04 Requirements and PRD §17.5.
Supports simulating:
- success
- empty
- unavailable (503)
- timeout
- malformed response
- partial retain
- retry with transient failures
- status mapping
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from src.memory.client import (
    HindsightClientError,
    HindsightUnavailableError,
    HindsightTimeoutError,
    HindsightMalformedResponseError,
    HindsightAPIError,
)


class HindsightTestDouble:
    """
    In-memory drop-in replacement for HindsightClient.
    Provides controllable failure modes and inspectable stored state.
    """

    def __init__(self, bank_id: str = "incident-response-agent"):
        self.default_bank_id = bank_id
        self.banks: Dict[str, Dict[str, Dict[str, Any]]] = {self.default_bank_id: {}}
        self.mode: Literal["normal", "unavailable", "timeout", "malformed", "partial_retain"] = "normal"
        self.fail_attempts_remaining: int = 0
        self.last_query: Optional[str] = None
        self.last_retain_payload: Optional[Dict[str, Any]] = None
        self.call_history: List[Dict[str, Any]] = []

    def set_mode(self, mode: Literal["normal", "unavailable", "timeout", "malformed", "partial_retain"]):
        """Set simulation mode for tests."""
        self.mode = mode

    def set_fail_attempts(self, count: int):
        """Simulate transient failures that resolve after `count` attempts (for retry testing)."""
        self.fail_attempts_remaining = count

    def reset(self):
        """Reset internal memory store and state."""
        self.banks = {self.default_bank_id: {}}
        self.mode = "normal"
        self.fail_attempts_remaining = 0
        self.call_history.clear()
        self.last_query = None
        self.last_retain_payload = None

    def _check_simulated_failures(self, op: str):
        """Evaluate failure modes and transient retry counters."""
        self.call_history.append({"operation": op, "mode": self.mode, "timestamp": datetime.now(timezone.utc).isoformat()})

        if self.fail_attempts_remaining > 0:
            self.fail_attempts_remaining -= 1
            raise HindsightUnavailableError(f"Transient network error on {op} (retries remaining)")

        if self.mode == "unavailable":
            raise HindsightUnavailableError(f"Hindsight service unavailable for {op} (HTTP 503)")
        elif self.mode == "timeout":
            raise HindsightTimeoutError(f"Hindsight request timed out during {op}")
        elif self.mode == "malformed":
            raise HindsightMalformedResponseError(f"Hindsight returned malformed non-JSON payload for {op}")

    def health_check(self) -> Tuple[bool, str]:
        """Dependency health check simulation."""
        if self.mode in ("unavailable", "timeout"):
            return False, f"degraded_{self.mode}"
        return True, "connected"

    def seed_entry(self, entry: Dict[str, Any], bank_id: Optional[str] = None) -> str:
        """Seed a raw entry directly into the test double."""
        bank = bank_id or self.default_bank_id
        if bank not in self.banks:
            self.banks[bank] = {}
        entry_id = entry.get("entry_id") or f"mem-{uuid.uuid4().hex[:8]}"
        entry["entry_id"] = entry_id
        if "retained_at" not in entry:
            entry["retained_at"] = datetime.now(timezone.utc).isoformat()
        self.banks[bank][entry_id] = entry
        return entry_id

    def seed_entries(self, entries: List[Dict[str, Any]], bank_id: Optional[str] = None) -> List[str]:
        """Seed a batch of entries into the test double."""
        return [self.seed_entry(e, bank_id) for e in entries]

    def recall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Simulate Hindsight memory recall."""
        self._check_simulated_failures("recall")
        self.last_query = query
        bank = bank_id or self.default_bank_id
        store = self.banks.get(bank, {})

        matched = []
        q_lower = query.lower()

        for entry_id, entry in store.items():
            # Check filters if present
            if filters:
                if "service" in filters and filters["service"]:
                    if entry.get("service", "").lower() != filters["service"].lower():
                        continue
                if "entry_type" in filters and filters["entry_type"]:
                    if entry.get("entry_type") != filters["entry_type"]:
                        continue
                if "outcome_label" in filters and filters["outcome_label"]:
                    if entry.get("outcome_label") != filters["outcome_label"]:
                        continue

            # Semantic / text match simulation
            body_text = entry.get("body", "").lower()
            service_text = entry.get("service", "").lower()
            entry_type_text = entry.get("entry_type", "").lower()

            # If query tokens appear or entry matches filters, count as hit
            query_words = [w for w in q_lower.split() if len(w) > 3]
            match_found = not query_words  # match all if query is empty

            synonym_map = {
                "exhausted": ["exhaustion", "starved", "depleted", "saturated", "limit"],
                "exhaustion": ["exhausted", "starved", "depleted", "saturated", "limit"],
                "starved": ["exhausted", "exhaustion", "depleted"],
                "depleted": ["exhausted", "exhaustion", "starved"],
                "database": ["db", "postgres", "postgresql", "mysql", "sql", "rds"],
                "db": ["database", "postgres", "postgresql", "mysql", "sql", "rds"],
                "postgres": ["database", "db", "postgresql"],
                "latency": ["slow", "slowness", "timeout", "delay", "lag"],
                "slow": ["slowness", "latency", "delay", "lag"],
                "timeout": ["timed_out", "latency", "hang", "hanging"],
                "leak": ["leaking", "leaked", "growth", "unreleased"],
                "crash": ["crashed", "oom", "killed", "terminated", "panic"],
                "deadlock": ["contention", "blocking", "blocked", "lock"],
            }

            for w in query_words:
                candidates = [w]
                if w in synonym_map:
                    candidates.extend(synonym_map[w])
                if any(cand in body_text or cand in service_text or cand in entry_type_text for cand in candidates):
                    match_found = True
                    break

            if match_found:
                matched.append(dict(entry))

        return {
            "bank_id": bank,
            "total": len(matched),
            "memories": matched[:limit],
        }

    def retain(
        self,
        entry: Dict[str, Any],
        bank_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate Hindsight memory retention."""
        self._check_simulated_failures("retain")
        self.last_retain_payload = entry

        # Handle partial retain simulation
        if self.mode == "partial_retain":
            # Arbitrary condition to fail certain types in partial retain tests
            if entry.get("entry_type") == "failed_action" or "fail_me" in entry.get("body", ""):
                raise HindsightAPIError("Simulated partial retain failure for specific entry", status_code=500)

        bank = bank_id or self.default_bank_id
        if bank not in self.banks:
            self.banks[bank] = {}

        entry_id = entry.get("entry_id") or f"mem-{uuid.uuid4().hex[:8]}"
        saved_entry = dict(entry)
        saved_entry["entry_id"] = entry_id
        if "retained_at" not in saved_entry:
            saved_entry["retained_at"] = datetime.now(timezone.utc).isoformat()

        self.banks[bank][entry_id] = saved_entry

        return {
            "entry_id": entry_id,
            "status": "stored",
            "created_at": saved_entry["retained_at"],
        }

    def get_experience(
        self,
        entry_id: str,
        bank_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Simulate retrieving a single memory entry by ID."""
        self._check_simulated_failures("get_experience")
        bank = bank_id or self.default_bank_id
        return self.banks.get(bank, {}).get(entry_id)

    def flag_experience(
        self,
        entry_id: str,
        flag_data: Dict[str, Any],
        bank_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate flagging a memory entry."""
        self._check_simulated_failures("flag_experience")
        bank = bank_id or self.default_bank_id
        entry = self.banks.get(bank, {}).get(entry_id)
        if not entry:
            raise HindsightAPIError(f"Memory entry {entry_id} not found", status_code=404)

        entry["flagged"] = {
            "flag_type": flag_data.get("flag_type"),
            "reason": flag_data.get("reason"),
            "note": flag_data.get("note"),
            "flagged_at": datetime.now(timezone.utc).isoformat(),
        }
        return entry
