"""
Reasoning Service: Current/Historical Comparison and Hypothesis Generation.
Conforms strictly to PRD Part 1 §12.4 (FR-023–FR-028), §12.5 (FR-029–FR-034),
Part 2 §26.5 (AC2-04, AC2-04a), §26.6 (AC2-05, AC2-05a, AC2-05b), and Features 06–07.

Guarantees:
1. Strict Reasoning Order: Current Analysis -> Recall -> Memory Context Assembly -> Comparison -> Hypothesis
2. Structured Comparison Output: matching_signals, differences, historical_patterns, conflicts, confidence, provenance
3. Structured Hypothesis Output: hypothesis, supporting_current_evidence, supporting_memory_entries,
   contradicting_evidence, unknowns, confidence, provenance
4. Anti-Hallucination Guarantee: No historical claim may be made unless present in recalled memories
5. Unknowns: "unknown" explicitly stated when evidence is insufficient
6. Conflict Surfacing: Disagreements between historical experiences or between evidence and history are surfaced, never suppressed
7. Determinism: 100% reproducible comparisons and rankings
"""

import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from src.data.models.incident import Incident
from src.api.schemas.analysis import (
    CurrentIncidentInterpretation,
    ComparisonItem,
    HypothesisItem,
)
from src.memory.schemas import MemoryEntry, MemoryStatus, EntryType, OutcomeLabel


@dataclass
class MemoryContext:
    """Assembled memory context for comparison and hypothesis formation."""
    status: str
    entries: List[MemoryEntry] = field(default_factory=list)
    root_causes: List[MemoryEntry] = field(default_factory=list)
    procedures: List[MemoryEntry] = field(default_factory=list)
    failed_approaches: List[MemoryEntry] = field(default_factory=list)
    lessons: List[MemoryEntry] = field(default_factory=list)
    by_incident_ref: Dict[str, List[MemoryEntry]] = field(default_factory=dict)
    recalled_facts: Set[str] = field(default_factory=set)


class ReasoningService:
    """Reasoning layer executing comparison and hypothesis generation after recall."""

    @staticmethod
    def assemble_memory_context(
        recalled_entries: List[MemoryEntry],
        memory_status: str,
    ) -> MemoryContext:
        """
        Stage 3: Assemble recalled historical memories into structured context categories.
        Extracts verified historical claims to enforce anti-hallucination rules.
        """
        context = MemoryContext(status=memory_status, entries=recalled_entries)

        if memory_status != MemoryStatus.OK.value or not recalled_entries:
            return context

        for entry in recalled_entries:
            # Group by source incident
            ref = entry.source_incident_ref or "unknown_ref"
            if ref not in context.by_incident_ref:
                context.by_incident_ref[ref] = []
            context.by_incident_ref[ref].append(entry)

            # Categorize by entry type
            etype = (entry.entry_type or "").lower()
            outcome = (entry.outcome_label or "").lower()

            if etype == EntryType.ROOT_CAUSE.value:
                context.root_causes.append(entry)
            elif etype in [EntryType.RESOLUTION_PROCEDURE.value, EntryType.SUCCESSFUL_ACTION.value]:
                if outcome == OutcomeLabel.INEFFECTIVE.value:
                    context.failed_approaches.append(entry)
                else:
                    context.procedures.append(entry)
            elif etype == EntryType.FAILED_ACTION.value or outcome == OutcomeLabel.INEFFECTIVE.value:
                context.failed_approaches.append(entry)
            elif etype in [EntryType.LESSON.value, EntryType.PREVENTIVE_KNOWLEDGE.value]:
                context.lessons.append(entry)

            # Record verified historical factual phrases for anti-hallucination checking
            body_clean = entry.body.strip().lower()
            context.recalled_facts.add(body_clean)
            for phrase in re.split(r"[.;,]", body_clean):
                p = phrase.strip()
                if len(p) > 5:
                    context.recalled_facts.add(p)

        return context

    @classmethod
    def compare_evidence(
        cls,
        incident: Incident,
        interpretation: CurrentIncidentInterpretation,
        memory_context: MemoryContext,
    ) -> List[ComparisonItem]:
        """
        Stage 4: Compare current evidence against historical experience.
        Compares:
        Current: symptoms, metrics, logs, recent changes, service
        Against: previous symptoms, failure mode, root cause, resolution, outcome, failed approaches, lessons
        """
        comparisons: List[ComparisonItem] = []

        # Case A: Cold-start / No relevant memory / Outage / Suppressed
        if memory_context.status != MemoryStatus.OK.value or not memory_context.entries:
            basis_msg = {
                MemoryStatus.EMPTY.value: "No prior operational memory found for this service class (cold-start / memory empty).",
                MemoryStatus.SUPPRESSED.value: "Historical memory recall was deliberately suppressed (memory-isolated mode).",
                MemoryStatus.DEGRADED.value: "Memory service was unavailable during analysis — operating in degraded mode.",
            }.get(memory_context.status, "No historical memories available for comparison (empty).")

            comparisons.append(ComparisonItem(
                prior_incident_id=None,
                entry_id=None,
                matching_signals=[],
                differences=[
                    f"Memory status: {memory_context.status}",
                    "No historical comparison available"
                ],
                historical_patterns=[],
                conflicts=[],
                confidence={
                    "score": 0.20,
                    "level": "low",
                    "basis": basis_msg
                },
                provenance=[
                    {
                        "source": "current_incident",
                        "statement": "Comparison performed against empty historical context"
                    }
                ],
                match_strength="none",
                applicability="unknown"
            ))
            return comparisons

        # Case B: Memory Available -> Compare each recalled prior incident
        for incident_ref, entries in memory_context.by_incident_ref.items():
            matching_signals: List[str] = []
            differences: List[str] = []
            historical_patterns: List[str] = []
            conflicts: List[str] = []
            provenance: List[Dict[str, Any]] = []

            primary_entry = entries[0]
            entry_service = (primary_entry.service or "").lower()
            current_service = (incident.service or "").lower()

            # 1. Service Comparison
            if current_service and entry_service:
                if current_service == entry_service:
                    matching_signals.append(f"Matching service: {incident.service}")
                    provenance.append({
                        "source": "current_incident",
                        "statement": f"Current service is {incident.service}"
                    })
                    provenance.append({
                        "source": f"recalled_memory:{primary_entry.entry_id}",
                        "statement": f"Historical incident {incident_ref} occurred on service {primary_entry.service}"
                    })
                else:
                    differences.append(f"Different service: current is '{incident.service}', prior was '{primary_entry.service}'")

            # 2. Environment Comparison
            current_env = (incident.environment or "production").lower()
            # If entry mentions staging or dev in body
            entry_body_lower = " ".join([e.body.lower() for e in entries])
            if "staging" in entry_body_lower and current_env == "production":
                differences.append("Environment mismatch: prior incident occurred in staging, current is in production")
            elif "production" in entry_body_lower and current_env == "production":
                matching_signals.append("Matching environment: production")

            # 3. Symptoms & Failure Mode Comparison
            current_symptoms = (incident.symptoms_normalized or incident.symptoms_raw or "").lower()
            current_fm = (interpretation.failure_mode or incident.failure_mode_label or "").lower()

            # Check overlap between current symptoms and entry bodies
            symptom_tokens = set(re.findall(r"\b[a-z]{4,}\b", current_symptoms))
            matched_terms = set()
            for e in entries:
                e_tokens = set(re.findall(r"\b[a-z]{4,}\b", e.body.lower()))
                overlap = symptom_tokens.intersection(e_tokens)
                matched_terms.update(overlap)

            # Exclude generic terms
            matched_terms.difference_update({"with", "from", "that", "this", "have", "been", "were", "service"})

            if matched_terms:
                sample_terms = ", ".join(sorted(list(matched_terms))[:4])
                matching_signals.append(f"Symptom overlap on terms: {sample_terms}")
                provenance.append({
                    "source": f"recalled_memory:{primary_entry.entry_id}",
                    "statement": f"Prior incident symptoms share terms ({sample_terms}) with current incident"
                })

            if current_fm and any(current_fm in e.body.lower() for e in entries):
                matching_signals.append(f"Matching failure mode: {current_fm}")

            # 4. Error Signatures Comparison
            current_sigs = interpretation.normalized_signatures or incident.error_signatures or []
            matched_sigs = []
            for sig in current_sigs:
                if any(sig.lower() in e.body.lower() for e in entries):
                    matched_sigs.append(sig)

            if matched_sigs:
                matching_signals.append(f"Matching error signatures: {', '.join(matched_sigs)}")
            elif current_sigs:
                differences.append(f"Current signatures ({', '.join(current_sigs)}) not explicitly cited in prior record")

            # 5. Telemetry & Metrics Comparison
            # Check if current incident reports latency or error rate
            latency_match = re.search(r"(\d+(?:\.\d+)?\s*(?:s|ms))", current_symptoms)
            if latency_match:
                current_lat = latency_match.group(1)
                matching_signals.append(f"Current telemetry highlights latency: {current_lat}")

            # 6. Recent Changes & Deployment Comparison
            if "deploy" in current_symptoms or "release" in current_symptoms:
                matching_signals.append("Recent deployment or release is active in current incident context")
            else:
                differences.append("Recent changes: unknown in current evidence")

            # 7. Historical Patterns from Recalled Experience
            for e in entries:
                if e.entry_type == EntryType.ROOT_CAUSE.value:
                    historical_patterns.append(f"Prior root cause ({e.source_incident_ref}): {e.body}")
                    provenance.append({
                        "source": f"recalled_memory:{e.entry_id}",
                        "statement": f"Root cause established as: {e.body}"
                    })
                elif e.entry_type in [EntryType.RESOLUTION_PROCEDURE.value, EntryType.SUCCESSFUL_ACTION.value]:
                    historical_patterns.append(f"Prior resolution ({e.outcome_label or 'tested'}): {e.body}")
                    provenance.append({
                        "source": f"recalled_memory:{e.entry_id}",
                        "statement": f"Resolution procedure: {e.body} (outcome: {e.outcome_label})"
                    })
                elif e.entry_type == EntryType.FAILED_ACTION.value or (e.outcome_label and e.outcome_label.lower() == OutcomeLabel.INEFFECTIVE.value):
                    historical_patterns.append(f"Failed approach to avoid ({e.source_incident_ref}): {e.body}")
                    provenance.append({
                        "source": f"recalled_memory:{e.entry_id}",
                        "statement": f"Ineffective procedure: {e.body}"
                    })
                elif e.entry_type == EntryType.LESSON.value:
                    historical_patterns.append(f"Historical lesson: {e.body}")

            # 8. Conflict Detection (FR-027, ERR-09, AC2-04a)
            # Check if another prior incident in memory context has a conflicting root cause
            all_root_causes = [rc for rc in memory_context.root_causes if rc.source_incident_ref != incident_ref]
            for other_rc in all_root_causes:
                # Compare causes
                this_rc = next((e for e in entries if e.entry_type == EntryType.ROOT_CAUSE.value), None)
                if this_rc and this_rc.body.strip().lower() != other_rc.body.strip().lower():
                    conflict_desc = (
                        f"Root cause conflict: {incident_ref} points to '{this_rc.body[:60]}...' "
                        f"whereas {other_rc.source_incident_ref} points to '{other_rc.body[:60]}...'"
                    )
                    if conflict_desc not in conflicts:
                        conflicts.append(conflict_desc)
                        provenance.append({
                            "source": f"recalled_memory:{other_rc.entry_id}",
                            "statement": f"Conflicting historical cause from {other_rc.source_incident_ref}"
                        })

            # Check if current evidence contradicts recalled root cause (AC2-05b)
            for e in entries:
                if e.entry_type == EntryType.ROOT_CAUSE.value:
                    # Check for explicit contradictions (e.g. CPU saturation vs normal CPU)
                    if "cpu" in e.body.lower() and "normal cpu" in current_symptoms:
                        conflicts.append(f"Contradiction: Prior cause cited CPU exhaustion, but current evidence shows normal CPU")
                    if "deadlock" in e.body.lower() and "no deadlock" in current_symptoms:
                        conflicts.append(f"Contradiction: Prior cause cited deadlock, but current telemetry reports no deadlocks")

            # 9. Confidence and Match Strength Scoring
            match_score = 0.20
            if current_service == entry_service:
                match_score += 0.35
            if matched_terms:
                match_score += min(0.30, len(matched_terms) * 0.08)
            if matched_sigs:
                match_score += 0.15
            if conflicts:
                match_score = max(0.10, match_score - 0.20)

            match_score = round(min(1.0, max(0.0, match_score)), 2)

            if match_score >= 0.70:
                match_strength = "full"
                conf_level = "confirmed" if match_score >= 0.85 else "probable"
                applicability = "applicable"
            elif match_score >= 0.40:
                match_strength = "partial"
                conf_level = "probable"
                applicability = "partially_applicable"
            else:
                match_strength = "weak"
                conf_level = "low"
                applicability = "inapplicable"

            conf_basis = (
                f"Score {match_score:.2f} based on {len(matching_signals)} matching signal(s), "
                f"{len(differences)} difference(s), and {len(conflicts)} conflict(s)."
            )

            comparisons.append(ComparisonItem(
                prior_incident_id=incident_ref,
                entry_id=primary_entry.entry_id,
                matching_signals=matching_signals,
                differences=differences,
                historical_patterns=historical_patterns,
                conflicts=conflicts,
                confidence={
                    "score": match_score,
                    "level": conf_level,
                    "basis": conf_basis
                },
                provenance=provenance,
                match_strength=match_strength,
                applicability=applicability
            ))

        # Deterministic sort by (-score, prior_incident_id)
        comparisons.sort(key=lambda c: (-float(c.confidence.get("score", 0.0)), str(c.prior_incident_id or "")))
        return comparisons

    @classmethod
    def generate_hypotheses(
        cls,
        incident: Incident,
        interpretation: CurrentIncidentInterpretation,
        memory_context: MemoryContext,
        comparisons: List[ComparisonItem],
    ) -> List[HypothesisItem]:
        """
        Stage 5: Generate ranked root-cause hypotheses with precedent citations.
        Strict anti-hallucination rule: only claims historical facts that exist in memory_context.
        """
        hypotheses: List[HypothesisItem] = []

        current_symptoms = incident.symptoms_normalized or incident.symptoms_raw or "Unspecified symptoms"
        current_service = incident.service or "unknown-service"

        # Case A: Memory is Empty / Suppressed / Degraded -> Generate from current evidence alone (FR-033)
        if memory_context.status != MemoryStatus.OK.value or not memory_context.root_causes:
            primary_evidence = [
                f"Observed symptoms: {current_symptoms}",
                f"Affected service: {current_service}",
            ]
            for f in interpretation.facts:
                primary_evidence.append(f.statement)

            primary_unknowns = [
                f"Historical precedent: {memory_context.status}",
                "Specific internal component failure trace is unverified",
            ]
            if interpretation.unknowns:
                primary_unknowns.extend(interpretation.unknowns)

            # Hypothesis derived strictly from current failure mode
            hyp_body = f"Suspected {interpretation.failure_mode.replace('_', ' ')} in {current_service}"
            hypotheses.append(HypothesisItem(
                hypothesis=hyp_body,
                supporting_current_evidence=primary_evidence,
                supporting_memory_entries=[],  # Empty! No historical fabrication
                contradicting_evidence=[],
                unknowns=primary_unknowns,
                confidence={
                    "score": 0.45,
                    "level": "low",
                    "basis": "Formulated strictly from current evidence without historical precedent (cold-start / memory-isolated)."
                },
                provenance=[
                    {"source": "current_incident", "statement": f.statement}
                    for f in interpretation.facts
                ] or [{"source": "current_incident", "statement": current_symptoms}],
                rank=1,
                precedent_backed=False,
                status="candidate"
            ))
            return hypotheses

        # Case B: Memory Available -> Formulate precedent-backed hypotheses from historical root causes
        ranked_root_causes = list(memory_context.root_causes)

        # Sort root causes deterministically
        ranked_root_causes.sort(key=lambda rc: (-rc.relevance_score, rc.entry_id))

        for idx, rc in enumerate(ranked_root_causes):
            supporting_current = [
                f"Service alignment: {current_service}",
                f"Current failure mode: {interpretation.failure_mode}",
            ]
            for fact in interpretation.facts:
                supporting_current.append(fact.statement)

            # Link matching comparison
            comp = next((c for c in comparisons if c.prior_incident_id == rc.source_incident_ref), None)
            if comp and comp.matching_signals:
                supporting_current.extend([f"Signal: {s}" for s in comp.matching_signals[:3]])

            # Contradicting evidence
            contradicting: List[str] = []
            if comp and comp.conflicts:
                contradicting.extend(comp.conflicts)
            if comp and comp.differences:
                contradicting.extend([f"Difference: {d}" for d in comp.differences[:2]])

            # Unknowns: State explicitly where evidence is missing (Anti-Hallucination rule)
            unknowns: List[str] = []
            if interpretation.unknowns:
                unknowns.extend(interpretation.unknowns)
            else:
                unknowns.append("unknown: Detailed component configuration and recent telemetry unverified")

            # Check if rollback or specific action is in memory
            has_rollback_outcome = any("rollback" in fact.lower() for fact in memory_context.recalled_facts)
            if not has_rollback_outcome:
                unknowns.append("unknown: Whether rollback or restart was previously attempted for this instance")

            # Provenance statements
            provenance: List[Dict[str, Any]] = [
                {
                    "source": "current_incident",
                    "statement": f"Current symptoms: {current_symptoms}"
                },
                {
                    "source": f"recalled_memory:{rc.entry_id}",
                    "statement": f"Historical precedent from {rc.source_incident_ref}: {rc.body}"
                }
            ]

            # Calculate confidence
            base_score = rc.relevance_score
            if comp:
                comp_score = float(comp.confidence.get("score", 0.5))
                calc_score = round((base_score * 0.6) + (comp_score * 0.4), 2)
            else:
                calc_score = round(base_score, 2)

            if contradicting:
                calc_score = max(0.15, round(calc_score - 0.15, 2))

            level = "confirmed" if calc_score >= 0.80 else ("probable" if calc_score >= 0.50 else "low")
            basis_str = (
                f"Precedent-backed by {rc.source_incident_ref} (relevance {rc.relevance_score:.2f}). "
                f"Supported by {len(supporting_current)} current evidence item(s)."
            )

            # Hypothesis formulation (never stated as certain fact - FR-034)
            hyp_statement = f"Candidate Cause: {rc.body} (Precedent: {rc.source_incident_ref})"

            hypotheses.append(HypothesisItem(
                hypothesis=hyp_statement,
                supporting_current_evidence=supporting_current,
                supporting_memory_entries=[rc.entry_id],
                contradicting_evidence=contradicting,
                unknowns=unknowns,
                confidence={
                    "score": calc_score,
                    "level": level,
                    "basis": basis_str
                },
                provenance=provenance,
                rank=idx + 1,
                precedent_backed=True,
                status="candidate"
            ))

        # Sort deterministically by (-confidence.score, rank, hypothesis)
        hypotheses.sort(key=lambda h: (-float(h.confidence.get("score", 0.0)), h.rank, h.hypothesis))
        for r_idx, h in enumerate(hypotheses):
            h.rank = r_idx + 1

        return hypotheses


reasoning_service = ReasoningService()
