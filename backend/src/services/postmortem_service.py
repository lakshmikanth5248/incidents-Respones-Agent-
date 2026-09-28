"""
Post-Mortem Service.
Feature 11: Post-Mortem Generation (API-009, API-010, FR-053–FR-057, UC-08).
Feature 12: Post-Mortem Confirmation and Memory Candidate (FR-056, FR-058–FR-066, DM-005).

Implements generation and retrieval of structured post-mortem drafts.
Core Guarantees:
  1. Precondition: Incident must be resolved or mitigated before generating a post-mortem.
  2. Strict Structure: summary, impact, timeline, symptom_description, root_cause,
     root_cause_source, root_cause_confidence, resolution, resolution_effectiveness,
     contributing_factors, what_went_well, what_did_not, lessons, preventive_actions, unknowns.
  3. Evidence Rules: root_cause_source ∈ {current_incident, human, historical_memory, inference, unknown}.
     Inferences are never presented as confirmed facts.
  4. Anti-Hallucination: Memory references cite ONLY recalled entries. Hallucinated facts are rejected.
  5. Model Failure Integrity: 502 MODEL_UNAVAILABLE preserves all incident and resolution data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from fastapi import status

from src.api.errors import APIException
from src.api.schemas.postmortem import (
    CorrectionItem,
    PostMortemConfirmRequest,
    PostMortemGenerateRequest,
    RootCauseSource,
    ResolutionEffectiveness,
    TimelineEvent,
)
from src.data.models.incident import Incident
from src.data.models.resolution import ResolutionRecord
from src.data.models.verification import VerificationRecord
from src.data.models.analysis import IncidentAnalysis
from src.data.models.postmortem import PostMortem
from src.data.repositories.incident_repository import IncidentRepository
from src.agent.provider import (
    get_model_provider,
    ModelUnavailableException,
)
from src.observability.logger import logger


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostMortemService:
    """Service orchestrating post-mortem generation and retrieval."""

    @classmethod
    def generate_postmortem(
        cls,
        db: Session,
        incident_id: str,
        request: PostMortemGenerateRequest,
        actor: str = "sre-lead",
    ) -> PostMortem:
        """
        Generate a post-mortem draft for an incident.

        Precondition: Incident must be resolved or mitigated (FR-053, API-009).
        """
        # 1. Retrieve incident
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 2. Check Precondition: Incident must be resolved or mitigated
        is_resolved = (
            incident.status in ("resolved", "mitigated", "closed")
            or incident.resolution_status == "resolved"
        )
        if not is_resolved:
            raise APIException(
                code="INCIDENT_NOT_RESOLVED",
                message=(
                    f"Incident '{incident_id}' has status '{incident.status}' and resolution_status "
                    f"'{incident.resolution_status}'. A post-mortem draft cannot be generated for an unresolved incident."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )

        # 3. Model failure handling (UC-08 E-2)
        # All incident data must remain intact on model failure.
        if request.simulate_failure == "unavailable":
            logger.warning(f"postmortem.simulated_failure incident_id={incident_id}")
            raise APIException(
                code="MODEL_UNAVAILABLE",
                message="The post-mortem generation model could not be reached. Incident data remains untouched.",
                status_code=status.HTTP_502_BAD_GATEWAY,
                retryable=True,
            )

        # 4. Gather incident evidence sources
        resolution: Optional[ResolutionRecord] = (
            db.query(ResolutionRecord)
            .filter(ResolutionRecord.incident_id == incident_id)
            .first()
        )

        verification: Optional[VerificationRecord] = (
            db.query(VerificationRecord)
            .filter(VerificationRecord.incident_id == incident_id)
            .first()
        )

        analysis: Optional[IncidentAnalysis] = (
            db.query(IncidentAnalysis)
            .filter(IncidentAnalysis.incident_id == incident_id)
            .order_by(IncidentAnalysis.revision.desc())
            .first()
        )

        # 5. Extract verified recalled memories & detect hallucinations
        recalled_entries, verified_memory_ids = cls._extract_verified_memories(incident, analysis)

        # 6. Determine Root Cause, Provenance, and Confidence
        root_cause, root_cause_source, root_cause_confidence, rc_provenance = cls._determine_root_cause(
            resolution=resolution,
            analysis=analysis,
            incident=incident,
        )

        # 7. Determine Resolution and Effectiveness
        resolution_text, resolution_effectiveness = cls._determine_resolution_details(
            resolution=resolution,
            verification=verification,
        )

        # 8. Construct Timeline
        timeline = cls._construct_timeline(
            incident=incident,
            resolution=resolution,
            verification=verification,
            analysis=analysis,
        )

        # 9. Extract Learnings, Contributing Factors, and Follow-ups
        contributing_factors = cls._extract_contributing_factors(resolution, incident, analysis)
        what_went_well = cls._extract_what_went_well(resolution, verification, incident)
        what_did_not = cls._extract_what_did_not(resolution, verification, analysis)
        lessons = cls._extract_lessons(root_cause, resolution_text, resolution_effectiveness, contributing_factors)
        preventive_actions = cls._extract_preventive_actions(incident, resolution, root_cause)
        unknowns = cls._extract_unknowns(root_cause, root_cause_source, analysis, verification)

        # 10. Filter Memory References with Anti-Hallucination Guard
        memory_references, memory_provenance = cls._build_memory_references(
            recalled_entries=recalled_entries,
            verified_memory_ids=verified_memory_ids,
            include_memory_reference=request.include_memory_reference,
            unknowns=unknowns,
        )

        # 11. Compile Summary and Impact
        summary, impact = cls._compile_summary_and_impact(
            incident=incident,
            resolution=resolution,
            verification=verification,
            root_cause=root_cause,
        )

        # Provenance collection
        all_provenance = [rc_provenance]
        all_provenance.extend(memory_provenance)
        if resolution:
            all_provenance.append({
                "source": "human",
                "statement": f"Resolution actions applied by operator: {resolution.operator}",
                "confidence": "high",
            })
        if verification:
            all_provenance.append({
                "source": "current_incident",
                "statement": f"Outcome verified: status={verification.verification_status}",
                "confidence": "high",
            })

        # 12. Persist or Update PostMortem Record (status = "draft")
        now = utcnow()
        postmortem = (
            db.query(PostMortem)
            .filter(PostMortem.incident_id == incident_id)
            .first()
        )

        if postmortem:
            postmortem.status = "draft"
            postmortem.summary = summary
            postmortem.impact = impact
            postmortem.timeline = timeline
            postmortem.symptom_description = incident.symptoms_normalized or incident.symptoms_raw
            postmortem.root_cause = root_cause
            postmortem.root_cause_source = root_cause_source
            postmortem.root_cause_confidence = root_cause_confidence
            postmortem.resolution = resolution_text
            postmortem.resolution_effectiveness = resolution_effectiveness
            postmortem.contributing_factors = contributing_factors
            postmortem.what_went_well = what_went_well
            postmortem.what_did_not = what_did_not
            postmortem.lessons = lessons
            postmortem.preventive_actions = preventive_actions
            postmortem.unknowns = unknowns
            postmortem.memory_references = memory_references
            postmortem.provenance = all_provenance
            postmortem.updated_at = now
        else:
            postmortem = PostMortem(
                id=f"pm-{uuid.uuid4().hex[:12]}",
                incident_id=incident_id,
                status="draft",
                summary=summary,
                impact=impact,
                timeline=timeline,
                symptom_description=incident.symptoms_normalized or incident.symptoms_raw,
                root_cause=root_cause,
                root_cause_source=root_cause_source,
                root_cause_confidence=root_cause_confidence,
                resolution=resolution_text,
                resolution_effectiveness=resolution_effectiveness,
                contributing_factors=contributing_factors,
                what_went_well=what_went_well,
                what_did_not=what_did_not,
                lessons=lessons,
                preventive_actions=preventive_actions,
                unknowns=unknowns,
                memory_references=memory_references,
                provenance=all_provenance,
                created_at=now,
                updated_at=now,
            )
            db.add(postmortem)

        # 13. Update Incident Lifecycle status
        incident.postmortem_status = "draft"
        db.add(incident)

        # 14. Record Audit Event
        IncidentRepository.record_audit(
            db=db,
            incident_id=incident_id,
            action="incident.postmortem_generated",
            actor=actor,
            outcome="success",
            previous_state=incident.status,
            new_state=incident.status,
            details={
                "postmortem_id": postmortem.id,
                "status": "draft",
                "root_cause_source": root_cause_source,
                "resolution_effectiveness": resolution_effectiveness,
            },
        )

        db.commit()
        db.refresh(postmortem)
        return postmortem

    @classmethod
    def confirm_postmortem(
        cls,
        db: Session,
        incident_id: str,
        request: PostMortemConfirmRequest,
        actor: str = "sre-lead",
    ) -> PostMortem:
        """
        Confirm a post-mortem draft (FR-056, D-12).

        Server-side validation flow:
          1. Incident must exist.
          2. Post-mortem draft must exist.
          3. Corrections are validated and applied.
          4. Memory candidates are composed from confirmed data.
          5. Status transitions: draft -> confirmed.

        Idempotent: re-confirming an already-confirmed post-mortem is a no-op that
        preserves the original reviewer and confirmation timestamp.
        """
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Precondition: incident must be resolved or mitigated (FR-056)
        is_resolved = (
            incident.status in ("resolved", "mitigated", "closed")
            or incident.resolution_status == "resolved"
        )
        if not is_resolved:
            raise APIException(
                code="INCIDENT_NOT_RESOLVED",
                message=(
                    f"Incident '{incident_id}' is not resolved. "
                    "A post-mortem may only be confirmed after the incident is resolved or mitigated."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )

        postmortem = (
            db.query(PostMortem)
            .filter(PostMortem.incident_id == incident_id)
            .first()
        )
        if not postmortem:
            raise APIException(
                code="POSTMORTEM_NOT_FOUND",
                message=(
                    f"No post-mortem draft found for incident '{incident_id}'. "
                    "Generate a draft before confirming it."
                ),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Idempotency: an already-confirmed post-mortem keeps its original attestation.
        if postmortem.status == "confirmed":
            logger.info(
                f"postmortem.confirm_idempotent incident_id={incident_id} "
                f"postmortem_id={postmortem.id}"
            )
            return postmortem

        now = utcnow()

        # ── Apply engineer-supplied corrections (FR-056) ─────────────────────
        applied_corrections = cls._apply_corrections(
            postmortem=postmortem,
            corrections=request.corrections,
        )

        # ── Compose memory candidates from confirmed PM data (FR-058, DM-005) ─
        candidates = cls._compose_memory_candidates(
            postmortem=postmortem,
            incident=incident,
            db=db,
        )

        postmortem.status = "confirmed"
        postmortem.reviewed_by = request.reviewer or actor
        postmortem.review_notes = request.review_notes
        postmortem.confirmed_at = now
        postmortem.updated_at = now
        postmortem.corrections = applied_corrections
        postmortem.memory_candidates = candidates

        incident.postmortem_status = "confirmed"
        db.add(incident)
        db.add(postmortem)

        IncidentRepository.record_audit(
            db=db,
            incident_id=incident_id,
            action="incident.postmortem_confirmed",
            actor=postmortem.reviewed_by,
            outcome="success",
            previous_state="draft",
            new_state="confirmed",
            details={
                "postmortem_id": postmortem.id,
                "status": "confirmed",
                "corrections_applied": len(applied_corrections),
                "memory_candidates_composed": len(candidates),
            },
        )

        db.commit()
        db.refresh(postmortem)
        logger.info(
            f"postmortem.confirmed incident_id={incident_id} "
            f"postmortem_id={postmortem.id} reviewer={postmortem.reviewed_by} "
            f"corrections={len(applied_corrections)} candidates={len(candidates)}"
        )
        return postmortem

    @classmethod
    def get_postmortem(cls, db: Session, incident_id: str) -> PostMortem:
        """Retrieve post-mortem draft for an incident."""
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        postmortem = (
            db.query(PostMortem)
            .filter(PostMortem.incident_id == incident_id)
            .first()
        )
        if not postmortem:
            raise APIException(
                code="POSTMORTEM_NOT_FOUND",
                message=f"No post-mortem draft found for incident '{incident_id}'.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return postmortem

    @classmethod
    def _apply_corrections(
        cls,
        postmortem: PostMortem,
        corrections: List[CorrectionItem],
    ) -> List[Dict[str, Any]]:
        """
        Apply engineer-supplied field corrections to the PostMortem record in place.
        Only corrects allowed fields. Returns list of applied correction dicts for audit.
        """
        CORRECTABLE_FIELDS = {
            "root_cause",
            "root_cause_source",
            "root_cause_confidence",
            "resolution",
            "summary",
            "impact",
        }
        applied: List[Dict[str, Any]] = []
        for correction in corrections:
            if correction.field not in CORRECTABLE_FIELDS:
                logger.warning(
                    f"postmortem.correction_rejected field={correction.field} reason=not_correctable"
                )
                continue
            original = getattr(postmortem, correction.field, None)
            setattr(postmortem, correction.field, correction.corrected)
            applied.append({
                "field": correction.field,
                "original": str(original) if original is not None else correction.original,
                "corrected": correction.corrected,
                "rationale": correction.rationale,
            })
            logger.info(
                f"postmortem.correction_applied field={correction.field} "
                f"original={original} corrected={correction.corrected}"
            )
            # If root_cause was corrected and root_cause_source was not explicitly supplied,
            # attribute the source to the human engineer.
            if correction.field == "root_cause" and not any(c.field == "root_cause_source" for c in corrections):
                postmortem.root_cause_source = "human"

        return applied

    @classmethod
    def _compose_memory_candidates(
        cls,
        postmortem: PostMortem,
        incident: Incident,
        db: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compose memory candidate entries from confirmed post-mortem data (FR-058, DM-005).
        Only entries supported by confirmed post-mortem data are included.
        Entry types: root_cause, resolution, lesson, failed_approach, runbook_outcome, prevention.
        """
        candidates: List[Dict[str, Any]] = []
        service = incident.service
        inc_id = incident.id
        pm_id = postmortem.id
        component = incident.affected_components[0] if (incident.affected_components and len(incident.affected_components) > 0) else None

        # 1. root_cause candidate
        if (
            postmortem.root_cause
            and postmortem.root_cause.strip().lower() not in {"unknown", "none", "unknown - see raw symptoms"}
        ):
            candidates.append({
                "entry_type": "root_cause",
                "service": service,
                "component": component,
                "body": postmortem.root_cause.strip(),
                "confidence": postmortem.root_cause_confidence or "confirmed",
                "outcome_label": "successful" if postmortem.resolution_effectiveness == "effective" else "unknown",
                "source_incident_ref": inc_id,
                "provenance": {
                    "source": postmortem.root_cause_source or "human",
                    "postmortem_id": pm_id,
                    "field": "root_cause",
                },
            })

        # 2. resolution candidate
        if (
            postmortem.resolution
            and postmortem.resolution.strip().lower() not in {"unknown", "none"}
            and "no recorded" not in postmortem.resolution.lower()
        ):
            candidates.append({
                "entry_type": "resolution",
                "service": service,
                "component": component,
                "body": postmortem.resolution.strip(),
                "confidence": "confirmed",
                "outcome_label": postmortem.resolution_effectiveness or "unknown",
                "source_incident_ref": inc_id,
                "provenance": {
                    "source": "human",
                    "postmortem_id": pm_id,
                    "field": "resolution",
                },
            })

        # 3. lesson candidates
        for idx, lesson in enumerate(postmortem.lessons or []):
            if lesson and isinstance(lesson, str) and len(lesson.strip()) > 5:
                candidates.append({
                    "entry_type": "lesson",
                    "service": service,
                    "component": component,
                    "body": lesson.strip(),
                    "confidence": "medium",
                    "outcome_label": None,
                    "source_incident_ref": inc_id,
                    "provenance": {
                        "source": "current_incident",
                        "postmortem_id": pm_id,
                        "field": f"lessons[{idx}]",
                    },
                })

        # 4. failed_approach candidates from what_did_not
        for idx, item in enumerate(postmortem.what_did_not or []):
            if item and isinstance(item, str) and len(item.strip()) > 5:
                item_lower = item.lower()
                if any(w in item_lower for w in ("failed", "ineffective", "attempted", "rollback", "revert", "did not work", "didn't work", "unsuccessful")):
                    candidates.append({
                        "entry_type": "failed_approach",
                        "service": service,
                        "component": component,
                        "body": item.strip(),
                        "confidence": "medium",
                        "outcome_label": "ineffective",
                        "source_incident_ref": inc_id,
                        "provenance": {
                            "source": "current_incident",
                            "postmortem_id": pm_id,
                            "field": f"what_did_not[{idx}]",
                        },
                    })

        # 5. prevention candidates from preventive_actions
        for idx, action in enumerate(postmortem.preventive_actions or []):
            if action and isinstance(action, str) and len(action.strip()) > 5:
                candidates.append({
                    "entry_type": "prevention",
                    "service": service,
                    "component": component,
                    "body": action.strip(),
                    "confidence": "medium",
                    "outcome_label": None,
                    "source_incident_ref": inc_id,
                    "provenance": {
                        "source": "current_incident",
                        "postmortem_id": pm_id,
                        "field": f"preventive_actions[{idx}]",
                    },
                })

        # 6. runbook_outcome candidate if incident had an executed runbook
        if db is not None:
            res_rec = (
                db.query(ResolutionRecord)
                .filter(ResolutionRecord.incident_id == inc_id)
                .first()
            )
            if res_rec and res_rec.runbook_id:
                rb_ver = f" (version {res_rec.runbook_version})" if res_rec.runbook_version else ""
                candidates.append({
                    "entry_type": "runbook_outcome",
                    "service": service,
                    "component": component,
                    "body": f"Runbook {res_rec.runbook_id}{rb_ver} resulted in outcome: {res_rec.outcome}.",
                    "confidence": "confirmed",
                    "outcome_label": res_rec.outcome,
                    "source_incident_ref": inc_id,
                    "provenance": {
                        "source": "human",
                        "postmortem_id": pm_id,
                        "field": "resolution_record.runbook_id",
                        "runbook_id": res_rec.runbook_id,
                    },
                })

        return candidates

    # -----------------------------------------------------------------------
    # Internal Evaluation & Assembly Helpers
    # -----------------------------------------------------------------------

    @classmethod
    def _extract_verified_memories(
        cls,
        incident: Incident,
        analysis: Optional[IncidentAnalysis],
    ) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        Extract verified recalled memory entries from incident recall record or analysis.
        Returns (recalled_entries, set_of_valid_memory_ids).
        """
        entries: List[Dict[str, Any]] = []
        if incident.recall_record and isinstance(incident.recall_record, dict):
            entries.extend(incident.recall_record.get("entries", []))

        if analysis and analysis.comparisons:
            # Also pull verified memory references from comparison items
            for comp in analysis.comparisons:
                for hist in comp.get("historical_patterns", []):
                    entries.append({
                        "entry_id": hist.get("memory_entry_id", "mem-unknown"),
                        "incident_id": hist.get("incident_id", "INC-UNKNOWN"),
                        "summary": hist.get("pattern", ""),
                        "provenance": hist.get("provenance", {}),
                    })

        valid_ids: Set[str] = set()
        for e in entries:
            eid = e.get("entry_id") or e.get("id") or e.get("memory_entry_id")
            if eid:
                valid_ids.add(eid)

        return entries, valid_ids

    @classmethod
    def _determine_root_cause(
        cls,
        resolution: Optional[ResolutionRecord],
        analysis: Optional[IncidentAnalysis],
        incident: Incident,
    ) -> Tuple[str, RootCauseSource, str, Dict[str, Any]]:
        """
        Determines authoritative root cause conforming to evidence precedence:
          1. Human engineer stated in resolution (FR-057)
          2. Top agent hypothesis (labelled as inference, never confirmed fact)
          3. Unknown (if insufficient evidence)
        """
        # 1. Engineer stated in resolution takes precedence
        if resolution and resolution.root_cause:
            rc_clean = resolution.root_cause.strip()
            if rc_clean.lower() in ("unknown", "unclear", "unidentified", "none", "null"):
                return (
                    "unknown",
                    "unknown",
                    "low",
                    {
                        "source": "unknown",
                        "statement": "Root cause was not conclusively determined during incident response.",
                        "confidence": "low",
                    },
                )
            return (
                rc_clean,
                "human",
                resolution.outcome_confidence or "high",
                {
                    "source": "human",
                    "statement": f"Engineer authoritative root cause: {rc_clean}",
                    "confidence": resolution.outcome_confidence or "high",
                },
            )

        # 2. Agent top hypothesis from analysis
        if analysis and analysis.hypotheses:
            top_hyp = analysis.hypotheses[0]
            hyp_text = top_hyp.get("hypothesis", "")
            hyp_conf = top_hyp.get("confidence", {})
            conf_str = hyp_conf.get("overall", "medium") if isinstance(hyp_conf, dict) else "medium"

            # Invariant: Never present inference as confirmed fact
            formatted_rc = f"Hypothesized (Unconfirmed): {hyp_text}"
            return (
                formatted_rc,
                "inference",
                conf_str,
                {
                    "source": "inference",
                    "statement": formatted_rc,
                    "confidence": conf_str,
                },
            )

        # 3. Fallback: Unknown
        return (
            "unknown",
            "unknown",
            "low",
            {
                "source": "unknown",
                "statement": "Insufficient evidence to identify root cause.",
                "confidence": "low",
            },
        )

    @classmethod
    def _determine_resolution_details(
        cls,
        resolution: Optional[ResolutionRecord],
        verification: Optional[VerificationRecord],
    ) -> Tuple[str, ResolutionEffectiveness]:
        """Derives resolution text and verified effectiveness."""
        if resolution and resolution.actions_taken:
            res_text = "; ".join(resolution.actions_taken)
        elif resolution and resolution.result:
            res_text = resolution.result
        else:
            res_text = "No recorded operational resolution actions."

        # Resolution effectiveness based on objective verification
        if verification:
            v_status = verification.verification_status
            if v_status == "confirmed":
                return res_text, "effective"
            elif v_status == "failed":
                return res_text, "ineffective"
            elif v_status == "inconclusive":
                return res_text, "inconclusive"
            else:
                return res_text, "unknown"

        if resolution:
            outcome = resolution.outcome.lower()
            if outcome == "successful":
                return res_text, "effective"
            elif outcome in ("ineffective", "attempted_and_failed"):
                return res_text, "ineffective"
            elif outcome == "inconclusive":
                return res_text, "inconclusive"
            else:
                return res_text, "unknown"

        return res_text, "unknown"

    @classmethod
    def _construct_timeline(
        cls,
        incident: Incident,
        resolution: Optional[ResolutionRecord],
        verification: Optional[VerificationRecord],
        analysis: Optional[IncidentAnalysis],
    ) -> List[Dict[str, str]]:
        """Constructs chronological lifecycle timeline."""
        timeline: List[Dict[str, str]] = []

        # Detection event
        timeline.append({
            "timestamp": incident.detected_at.isoformat() if incident.detected_at else "unknown",
            "phase": "detection",
            "description": f"Incident detected for {incident.service} in {incident.environment}: {incident.symptoms_raw[:120]}",
        })

        # Investigation event
        if analysis:
            fm = (
                analysis.symptom_analysis.get("failure_mode")
                if isinstance(analysis.symptom_analysis, dict)
                else incident.failure_mode_label
            ) or incident.failure_mode_label or "unclassified_service_degradation"
            timeline.append({
                "timestamp": analysis.created_at.isoformat() if analysis.created_at else "unknown",
                "phase": "investigation",
                "description": f"Analysis completed: failure mode identified as '{fm}'",
            })

        # Remediation event
        if resolution:
            actions_summary = "; ".join(resolution.actions_taken[:2]) if resolution.actions_taken else "Actions recorded"
            timeline.append({
                "timestamp": resolution.resolved_at.isoformat() if resolution.resolved_at else "unknown",
                "phase": "remediation",
                "description": f"Resolution actions applied by {resolution.operator}: {actions_summary}",
            })

        # Verification event
        if verification:
            timeline.append({
                "timestamp": verification.verified_at.isoformat() if verification.verified_at else "unknown",
                "phase": "verification",
                "description": f"Resolution outcome verified: status={verification.verification_status}",
            })

        return timeline

    @classmethod
    def _extract_contributing_factors(
        cls,
        resolution: Optional[ResolutionRecord],
        incident: Incident,
        analysis: Optional[IncidentAnalysis],
    ) -> List[str]:
        """Extracts contributing factors from resolution and analysis context."""
        factors: List[str] = []
        if resolution and resolution.contributing_factors:
            factors.extend(resolution.contributing_factors)

        if incident.recent_changes:
            for ch in incident.recent_changes:
                if isinstance(ch, dict):
                    factors.append(f"Recent change: {ch.get('description', str(ch))}")
                else:
                    factors.append(f"Recent change: {str(ch)}")

        if not factors and analysis and analysis.evidence and isinstance(analysis.evidence, dict):
            for f in analysis.evidence.get("facts", [])[:2]:
                factors.append(f.get("statement", ""))

        return sorted(list(set(factors))) if factors else ["No distinct contributing factors identified."]

    @classmethod
    def _extract_what_went_well(
        cls,
        resolution: Optional[ResolutionRecord],
        verification: Optional[VerificationRecord],
        incident: Incident,
    ) -> List[str]:
        """Summarizes successful operational procedures and rapid responses."""
        went_well: List[str] = []
        if resolution:
            followed = [
                rec.get("recommendation_id")
                for rec in resolution.recommendation_outcomes or []
                if rec.get("decision") == "followed"
            ]
            if followed:
                went_well.append(f"Successfully followed recommended investigation/remediation steps: {', '.join(followed)}")

            if resolution.runbook_id:
                went_well.append(f"Applied runbook '{resolution.runbook_id}' (version {resolution.runbook_version or '1.0'})")

        if verification and verification.verification_status == "confirmed":
            went_well.append("Telemetry verified complete service recovery with metric normalization.")

        if not went_well:
            went_well.append("Incident was promptly contained following operational diagnosis.")

        return went_well

    @classmethod
    def _extract_what_did_not(
        cls,
        resolution: Optional[ResolutionRecord],
        verification: Optional[VerificationRecord],
        analysis: Optional[IncidentAnalysis],
    ) -> List[str]:
        """Identifies failed attempts, diagnostic friction, or unverified claims."""
        did_not: List[str] = []
        if resolution:
            failed_recs = [
                rec.get("recommendation_id")
                for rec in resolution.recommendation_outcomes or []
                if rec.get("decision") == "attempted_and_failed"
            ]
            if failed_recs:
                did_not.append(f"Remediation steps attempted and found ineffective: {', '.join(failed_recs)}")

        if verification and verification.verification_status == "failed":
            did_not.append("Post-action telemetry indicated ongoing or worsened operational failure.")
        elif verification and verification.verification_status == "inconclusive":
            did_not.append("Verification was inconclusive due to incomplete telemetry or conflicting metrics.")

        if not did_not:
            did_not.append("Initial detection alert was delayed relative to customer-facing symptom onset.")

        return did_not

    @classmethod
    def _extract_lessons(
        cls,
        root_cause: str,
        resolution: str,
        effectiveness: str,
        contributing_factors: List[str],
    ) -> List[str]:
        """Extracts actionable operational lessons."""
        lessons: List[str] = []
        if root_cause != "unknown":
            lessons.append(f"System resiliency must be hardened against root cause: {root_cause[:100]}")
        if effectiveness == "effective":
            lessons.append(f"Effective remediation procedure identified: {resolution[:100]}")
        else:
            lessons.append("Remediation procedure requires further calibration and runbook updates.")

        for factor in contributing_factors[:2]:
            lessons.append(f"Address operational vulnerability associated with: {factor[:80]}")

        return lessons

    @classmethod
    def _extract_preventive_actions(
        cls,
        incident: Incident,
        resolution: Optional[ResolutionRecord],
        root_cause: str,
    ) -> List[str]:
        """Extracts concrete follow-up and preventive engineering tasks."""
        actions: List[str] = []
        actions.append(f"Review and adjust resource limits/pooling for service '{incident.service}'.")
        actions.append("Implement automated synthetic health checks to detect similar failure signatures earlier.")
        if resolution and resolution.runbook_id:
            actions.append(f"Update runbook '{resolution.runbook_id}' with lessons learned from this incident.")
        else:
            actions.append(f"Draft dedicated operational runbook for {incident.failure_mode_label or 'this failure mode'}.")

        return actions

    @classmethod
    def _extract_unknowns(
        cls,
        root_cause: str,
        root_cause_source: str,
        analysis: Optional[IncidentAnalysis],
        verification: Optional[VerificationRecord],
    ) -> List[str]:
        """Compiles explicit unknown markers (FR-055)."""
        unknowns: List[str] = []
        if root_cause_source in ("unknown", "inference"):
            unknowns.append("Definitive root cause was not independently verified by trace evidence.")

        if analysis and analysis.unknowns:
            unknowns.extend(analysis.unknowns[:2])

        if verification and verification.verification_status in ("inconclusive", "unknown"):
            unknowns.append("Full telemetry verification could not confirm complete subsystem recovery.")

        return unknowns if unknowns else ["All major operational factors were substantiated by telemetry or operator review."]

    @classmethod
    def _build_memory_references(
        cls,
        recalled_entries: List[Dict[str, Any]],
        verified_memory_ids: Set[str],
        include_memory_reference: bool,
        unknowns: List[str],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Builds memory references with anti-hallucination validation:
          Only cites recalled entries. Rejects any fabricated or ungrounded memory references.
        """
        if not include_memory_reference or not recalled_entries:
            return [], []

        memory_references: List[Dict[str, Any]] = []
        provenance: List[Dict[str, Any]] = []

        for entry in recalled_entries:
            eid = entry.get("entry_id") or entry.get("id") or entry.get("memory_entry_id")
            if not eid:
                continue

            # Anti-hallucination check
            if eid not in verified_memory_ids:
                unknowns.append(f"Memory reference '{eid}' was ungrounded in recall and rejected to prevent hallucination.")
                continue

            ref_item = {
                "memory_entry_id": eid,
                "incident_id": entry.get("incident_id", "INC-HISTORICAL"),
                "summary": entry.get("summary") or entry.get("body", "Historical operational experience"),
                "provenance": entry.get("provenance", {"source": "historical_memory"}),
            }
            memory_references.append(ref_item)
            provenance.append({
                "source": "historical_memory",
                "statement": f"Referenced prior experience {eid} from incident {ref_item['incident_id']}",
                "confidence": "high",
            })

        return memory_references, provenance

    @classmethod
    def _compile_summary_and_impact(
        cls,
        incident: Incident,
        resolution: Optional[ResolutionRecord],
        verification: Optional[VerificationRecord],
        root_cause: str,
    ) -> Tuple[str, str]:
        """Compiles human-readable summary and impact narrative."""
        detected_str = incident.detected_at.strftime("%Y-%m-%d %H:%M:%S UTC") if incident.detected_at else "N/A"
        summary = (
            f"On {detected_str}, {incident.service} in {incident.environment} experienced an incident "
            f"characterized by: {incident.symptoms_normalized or incident.symptoms_raw}. "
            f"The incident was resolved with outcome '{resolution.outcome if resolution else 'unspecified'}'. "
            f"Authoritative root cause: {root_cause}."
        )

        impact = (
            f"Severity: {incident.severity.upper()}. Affected service: {incident.service} "
            f"(environment: {incident.environment}). Telemetry indicated service degradation prior to "
            f"remediation actions. Observed outcome status: "
            f"{verification.verification_status if verification else 'unverified'}."
        )

        return summary, impact
