"""
Deterministic Ranking Layer for Memory Entries.
Conforms strictly to PRD RL-012, RL-013, RL-014, FR-026, and AC-31.
Guarantees reproducible ordering and explanatory relevance basis in words.
"""

import re
from typing import List, Optional
from src.memory.schemas import MemoryEntry, EntryType, OutcomeLabel, ConfidenceLevel


ENTRY_TYPE_WEIGHTS = {
    EntryType.ROOT_CAUSE.value: 1.25,
    EntryType.RESOLUTION_PROCEDURE.value: 1.20,
    EntryType.SUCCESSFUL_ACTION.value: 1.15,
    EntryType.RUNBOOK_OUTCOME.value: 1.10,
    EntryType.LESSON.value: 1.05,
    EntryType.SYMPTOM_PROFILE.value: 1.00,
    EntryType.INCIDENT_EXPERIENCE.value: 1.00,
    EntryType.CONTRIBUTING_FACTOR.value: 0.95,
    EntryType.PREVENTIVE_KNOWLEDGE.value: 0.95,
    EntryType.RECURRING_PATTERN.value: 0.95,
    EntryType.FAILED_ACTION.value: 0.90,
}

CONFIDENCE_WEIGHTS = {
    ConfidenceLevel.CONFIRMED.value: 1.0,
    ConfidenceLevel.PROBABLE.value: 0.85,
    ConfidenceLevel.LOW.value: 0.65,
}

OUTCOME_BONUS = {
    OutcomeLabel.SUCCESSFUL.value: 0.10,
    OutcomeLabel.INEFFECTIVE.value: 0.05,
    OutcomeLabel.INCONCLUSIVE.value: 0.0,
    OutcomeLabel.UNKNOWN.value: 0.0,
}


SYNONYM_MAP = {
    "exhausted": {"exhaustion", "starved", "depleted", "saturated", "limit"},
    "exhaustion": {"exhausted", "starved", "depleted", "saturated", "limit"},
    "starved": {"exhausted", "exhaustion", "depleted"},
    "depleted": {"exhausted", "exhaustion", "starved"},
    "database": {"db", "postgres", "postgresql", "mysql", "sql", "rds"},
    "db": {"database", "postgres", "postgresql", "mysql", "sql", "rds"},
    "postgres": {"database", "db", "postgresql"},
    "latency": {"slow", "slowness", "timeout", "delay", "lag"},
    "slow": {"slowness", "latency", "delay", "lag"},
    "timeout": {"timed_out", "latency", "hang", "hanging"},
    "leak": {"leaking", "leaked", "growth", "unreleased"},
    "crash": {"crashed", "oom", "killed", "terminated", "panic"},
    "deadlock": {"contention", "blocking", "blocked", "lock"},
}


def _tokenize(text: str) -> set:
    """Extract lowercased alphanumeric tokens from text with stemming and synonym expansion."""
    if not text:
        return set()
    tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", text.lower())
    # Exclude common stop words
    stopwords = {"the", "and", "for", "with", "this", "that", "from", "are", "was", "were", "been"}
    base_tokens = {t for t in tokens if t not in stopwords}
    expanded = set(base_tokens)
    for t in base_tokens:
        if t.endswith("ing") and len(t) > 5:
            expanded.add(t[:-3])
        elif t.endswith("ed") and len(t) > 4:
            expanded.add(t[:-2])
        elif t.endswith("s") and len(t) > 4:
            expanded.add(t[:-1])
        if t in SYNONYM_MAP:
            expanded.update(SYNONYM_MAP[t])
    return expanded


def rank_and_score_entries(
    entries: List[MemoryEntry],
    query: str,
    service: Optional[str] = None,
    environment: Optional[str] = None,
    failure_mode: Optional[str] = None,
    error_signatures: Optional[List[str]] = None,
    weak_threshold: float = 0.35,
) -> List[MemoryEntry]:
    """
    Ranks recalled entries using a deterministic scoring formula and attaches
    an explanatory relevance_basis string in words to every entry.
    """
    if not entries:
        return []

    query_tokens = _tokenize(query)
    sig_tokens = set()
    if error_signatures:
        for sig in error_signatures:
            sig_tokens.update(_tokenize(sig))

    ranked: List[MemoryEntry] = []

    for entry in entries:
        body_tokens = _tokenize(entry.body)
        raw_score = 0.20  # Base retrieval prior

        reasons = []

        # 1. Service match
        service_matched = False
        if service and entry.service and service.lower() == entry.service.lower():
            service_matched = True
            raw_score += 0.30
            reasons.append(f"Service match ({entry.service})")
        elif service and entry.service:
            reasons.append(f"Different service ({entry.service})")

        # 2. Token / Signature Overlap
        overlap_query = len(query_tokens.intersection(body_tokens))
        overlap_sig = len(sig_tokens.intersection(body_tokens))

        if sig_tokens and overlap_sig > 0:
            sig_boost = min(0.30, overlap_sig * 0.10)
            raw_score += sig_boost
            reasons.append(f"Error signature overlap ({overlap_sig} matching tokens)")
        elif query_tokens and overlap_query > 0:
            query_boost = min(0.20, overlap_query * 0.05)
            raw_score += query_boost
            reasons.append("Symptom query term overlap")

        # 3. Failure mode alignment
        if failure_mode and failure_mode.lower() in entry.body.lower():
            raw_score += 0.15
            reasons.append(f"Matching failure mode '{failure_mode}'")

        # 4. Entry Type Weighting
        type_weight = ENTRY_TYPE_WEIGHTS.get(entry.entry_type, 1.0)
        raw_score *= type_weight

        # 5. Outcome Bonus
        if entry.outcome_label:
            raw_score += OUTCOME_BONUS.get(entry.outcome_label.lower(), 0.0)
            if entry.outcome_label.lower() == OutcomeLabel.SUCCESSFUL.value:
                reasons.append("Prior successful outcome")
            elif entry.outcome_label.lower() == OutcomeLabel.INEFFECTIVE.value:
                reasons.append("Prior ineffective outcome recorded")

        # 6. Confidence multiplier
        conf_weight = CONFIDENCE_WEIGHTS.get((entry.confidence or "confirmed").lower(), 1.0)
        raw_score *= conf_weight

        # 7. Flag penalty
        if entry.flagged:
            raw_score = max(0.05, raw_score - 0.40)
            reasons.append(f"Flagged as {entry.flagged.flag_type.value} ({entry.flagged.reason})")

        # Cap score between 0.0 and 1.0
        final_score = min(1.0, max(0.0, raw_score))

        # Check weak match
        is_weak = final_score < weak_threshold or (not service_matched and overlap_sig == 0 and overlap_query == 0)

        if is_weak:
            basis_prefix = "Weak match: "
        else:
            basis_prefix = "Strong match: " if final_score >= 0.70 else "Relevant match: "

        relevance_basis = basis_prefix + "; ".join(reasons) if reasons else "General semantic relevance"

        # Construct updated entry copy
        updated_entry = MemoryEntry(
            entry_id=entry.entry_id,
            entry_type=entry.entry_type,
            service=entry.service,
            component=entry.component,
            body=entry.body,
            outcome_label=entry.outcome_label,
            confidence=entry.confidence,
            relevance_score=final_score,
            relevance_basis=relevance_basis,
            source_incident_ref=entry.source_incident_ref,
            retained_at=entry.retained_at,
            flagged=entry.flagged,
            provenance_group_id=entry.provenance_group_id,
            is_synthetic=entry.is_synthetic,
            supersedes=entry.supersedes,
        )
        ranked.append(updated_entry)

    # Surface conflicting root causes across returned records (PRD FR-027, ERR-09, HT-06)
    root_cause_entries = [e for e in ranked if e.entry_type == EntryType.ROOT_CAUSE.value]
    if len(root_cause_entries) >= 2:
        distinct_causes = {e.body.strip().lower() for e in root_cause_entries}
        if len(distinct_causes) > 1:
            # Conflict detected: update relevance basis of conflicting root causes
            updated_ranked = []
            for e in ranked:
                if e.entry_type == EntryType.ROOT_CAUSE.value:
                    other_causes = [rc.source_incident_ref for rc in root_cause_entries if rc.entry_id != e.entry_id]
                    conflict_note = f"; Conflict: Disagrees with root cause in prior incident ({', '.join(other_causes)})"
                    e_dict = e.model_dump()
                    e_dict["relevance_basis"] = e.relevance_basis + conflict_note
                    updated_ranked.append(MemoryEntry(**e_dict))
                else:
                    updated_ranked.append(e)
            ranked = updated_ranked

    # Sort deterministically: descending by relevance_score, ascending by entry_id
    ranked.sort(key=lambda e: (-e.relevance_score, e.entry_id))
    return ranked
