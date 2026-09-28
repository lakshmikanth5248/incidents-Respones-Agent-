"""
Verification Service.
Feature 10: Resolution Outcome Verification.

Implements verification of what happened after the engineer's action.
Core Invariants:
  1. Do not assume an action worked merely because the engineer marked it successful.
  2. Record available evidence.
  3. Do not manufacture measurements (no fabricated metrics).
  4. Resolution feeds verification; verification feeds post-mortem & memory candidate.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.api.errors import APIException
from src.api.schemas.verification import (
    VerificationRequest,
    VerificationStatus,
    MetricDirection,
    EvidenceAssessment,
    ObservedChange,
    VerificationEvidenceItem,
)
from src.data.models.incident import Incident
from src.data.models.resolution import ResolutionRecord
from src.data.models.verification import VerificationRecord
from src.data.repositories.incident_repository import IncidentRepository


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Metrics where LOWER is better (degrade = higher, improve = lower)
LOWER_IS_BETTER_KEYWORDS = (
    "error",
    "latency",
    "time",
    "connection",
    "conn",
    "cpu",
    "mem",
    "memory",
    "fail",
    "loss",
    "drop",
    "queue",
    "depth",
    "saturation",
    "rst",
    "timeout",
    "5xx",
    "4xx",
    "backlog",
)

# Metrics where HIGHER is better (improve = higher, degrade = lower)
HIGHER_IS_BETTER_KEYWORDS = (
    "success",
    "avail",
    "availability",
    "uptime",
    "throughput",
    "rps",
    "qps",
    "healthy",
    "health",
    "capacity",
)


class MetricParser:
    """Helper for parsing heterogeneous operational telemetry without fabricating measurements."""

    @staticmethod
    def parse_value(raw: Any) -> Tuple[Optional[float], Optional[str], Optional[float]]:
        """
        Parses a raw metric value into:
          (normalized_numeric_value, unit, capacity_or_denominator)

        Examples:
          - 31 -> (31.0, None, None)
          - "31%" -> (31.0, "%", 100.0)
          - "4.8s" -> (4800.0, "ms", None)
          - "420ms" -> (420.0, "ms", None)
          - "100/100" -> (100.0, "ratio", 100.0)
          - "38/100" -> (38.0, "ratio", 100.0)
          - "500" -> (500.0, None, None)
        """
        if raw is None:
            return None, None, None

        if isinstance(raw, (int, float)):
            return float(raw), None, None

        text = str(raw).strip()

        # Fraction/Ratio pattern: "100/100", "38/100", "5 / 10"
        ratio_match = re.match(r"^(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)$", text)
        if ratio_match:
            numerator = float(ratio_match.group(1))
            denominator = float(ratio_match.group(2))
            return numerator, "ratio", denominator

        # Percentage pattern: "31%", "2.5 %"
        pct_match = re.match(r"^(\d+(?:\.\d+)?)\s*%$", text)
        if pct_match:
            val = float(pct_match.group(1))
            return val, "%", 100.0

        # Latency pattern: "4.8s", "420ms", "1.5s", "100us"
        latency_match = re.match(r"^(\d+(?:\.\d+)?)\s*(ms|s|sec|m|min|us)$", text, re.IGNORECASE)
        if latency_match:
            val = float(latency_match.group(1))
            unit = latency_match.group(2).lower()
            if unit in ("s", "sec"):
                return val * 1000.0, "ms", None
            elif unit in ("m", "min"):
                return val * 60000.0, "ms", None
            elif unit == "us":
                return val / 1000.0, "ms", None
            return val, "ms", None

        # General numeric string: "420", "3.14"
        numeric_match = re.match(r"^[+-]?(\d+(?:\.\d+)?)$", text)
        if numeric_match:
            return float(numeric_match.group(1)), None, None

        return None, None, None

    @staticmethod
    def infer_desired_direction(metric_name: str) -> str:
        """Infers whether lower or higher is better based on standard operational conventions."""
        lower_name = metric_name.lower()
        for kw in LOWER_IS_BETTER_KEYWORDS:
            if kw in lower_name:
                return "lower"
        for kw in HIGHER_IS_BETTER_KEYWORDS:
            if kw in lower_name:
                return "higher"
        return "lower"  # Default assumption for incident metrics (symptoms/errors)


class VerificationService:
    """Service implementing resolution outcome verification (Feature 10)."""

    @classmethod
    def verify_incident(
        cls,
        db: Session,
        incident_id: str,
        request: VerificationRequest,
        actor: str = "sre-verifier",
    ) -> VerificationRecord:
        """
        Verify the outcome of actions taken for an incident.

        Conforms strictly to:
          - Do not assume an action worked because engineer marked it successful
          - Record available evidence
          - Do not manufacture measurements
          - Possible verification statuses: confirmed, inconclusive, failed, unknown
        """
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=404,
            )

        # 1. Integration: Resolution feeds verification
        resolution: Optional[ResolutionRecord] = (
            db.query(ResolutionRecord)
            .filter(ResolutionRecord.incident_id == incident_id)
            .first()
        )

        resolution_id = resolution.id if resolution else None
        operator_result = request.operator_result
        if not operator_result and resolution:
            operator_result = resolution.outcome

        # Verbatim states without manufacturing measurements
        before_state: Dict[str, Any] = dict(request.before_metrics or {})
        after_state: Dict[str, Any] = dict(request.after_metrics or {})
        observations: List[str] = list(request.observations or [])

        # 2. Evaluate observed changes and evidence
        observed_changes, evidence = cls._evaluate_changes_and_evidence(
            before_state=before_state,
            after_state=after_state,
            observations=observations,
            operator_result=operator_result,
            resolution=resolution,
        )

        # 3. Determine verification status
        verification_status = cls._determine_verification_status(
            before_state=before_state,
            after_state=after_state,
            observed_changes=observed_changes,
            evidence=evidence,
            operator_result=operator_result,
            observations=observations,
        )

        # 4. Upsert verification record (idempotency by incident_id)
        now = utcnow()
        verification_rec: Optional[VerificationRecord] = (
            db.query(VerificationRecord)
            .filter(VerificationRecord.incident_id == incident_id)
            .first()
        )

        if verification_rec:
            verification_rec.resolution_id = resolution_id
            verification_rec.verification_status = verification_status
            verification_rec.operator_result = operator_result
            verification_rec.before_state = before_state
            verification_rec.after_state = after_state
            verification_rec.observed_changes = observed_changes
            verification_rec.evidence = evidence
            verification_rec.verification_notes = request.verification_notes
            verification_rec.verified_by = actor
            verification_rec.verified_at = now
        else:
            verification_rec = VerificationRecord(
                id=f"ver-{uuid.uuid4().hex[:12]}",
                incident_id=incident_id,
                resolution_id=resolution_id,
                verification_status=verification_status,
                operator_result=operator_result,
                before_state=before_state,
                after_state=after_state,
                observed_changes=observed_changes,
                evidence=evidence,
                verification_notes=request.verification_notes,
                verified_by=actor,
                verified_at=now,
                created_at=now,
            )
            db.add(verification_rec)

        # 5. Integration: Update incident verification status
        incident.verification_status = verification_status
        db.add(incident)

        # 6. Audit Trail
        IncidentRepository.record_audit(
            db=db,
            incident_id=incident_id,
            action="incident.verified",
            actor=actor,
            outcome="success",
            previous_state=incident.status,
            new_state=incident.status,
            details={
                "verification_status": verification_status,
                "operator_result": operator_result,
                "metrics_evaluated": len(observed_changes),
                "resolution_id": resolution_id,
            },
        )

        db.commit()
        db.refresh(verification_rec)
        return verification_rec

    @classmethod
    def get_verification(cls, db: Session, incident_id: str) -> VerificationRecord:
        """Retrieve verification record for an incident."""
        incident = IncidentRepository.get_by_id(db, incident_id)
        if not incident:
            raise APIException(
                code="INCIDENT_NOT_FOUND",
                message=f"Incident '{incident_id}' not found.",
                status_code=404,
            )

        verification_rec = (
            db.query(VerificationRecord)
            .filter(VerificationRecord.incident_id == incident_id)
            .first()
        )
        if not verification_rec:
            raise APIException(
                code="VERIFICATION_NOT_FOUND",
                message=f"No verification record found for incident '{incident_id}'.",
                status_code=404,
            )
        return verification_rec

    @classmethod
    def _evaluate_changes_and_evidence(
        cls,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        observations: List[str],
        operator_result: Optional[str],
        resolution: Optional[ResolutionRecord],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Calculates observed metric changes and compiles structured evidence.
        Strictly preserves raw measurements without manufacturing data.
        """
        observed_changes: List[Dict[str, Any]] = []
        evidence: List[Dict[str, Any]] = []

        # Corroborate operator claim with resolution context
        if resolution:
            evidence.append({
                "source": "resolution_record",
                "claim": f"Operator marked resolution outcome as '{resolution.outcome}'",
                "assessment": "unverified",
                "details": f"Actions applied: {', '.join(resolution.actions_taken or [])}",
            })
        elif operator_result:
            evidence.append({
                "source": "operator_input",
                "claim": f"Operator declared outcome as '{operator_result}'",
                "assessment": "unverified",
                "details": f"Declared operator outcome: {operator_result}",
            })

        # Evaluate metrics present in BOTH before and after
        common_metrics = set(before_state.keys()) & set(after_state.keys())

        for metric in sorted(common_metrics):
            b_raw = before_state[metric]
            a_raw = after_state[metric]

            b_val, b_unit, b_denom = MetricParser.parse_value(b_raw)
            a_val, a_unit, a_denom = MetricParser.parse_value(a_raw)

            desired_dir = MetricParser.infer_desired_direction(metric)
            direction: MetricDirection = "unknown"
            delta_str: Optional[str] = None
            details: str = f"{metric}: {b_raw} -> {a_raw}"

            if b_val is not None and a_val is not None:
                numeric_delta = a_val - b_val

                # Format delta based on unit
                if b_unit == "%" or a_unit == "%":
                    delta_str = f"{numeric_delta:+.1f}%"
                elif b_unit == "ms" or a_unit == "ms":
                    delta_str = f"{numeric_delta:+.0f}ms"
                elif b_unit == "ratio" and b_denom:
                    delta_str = f"{numeric_delta:+.0f}/{int(b_denom)}"
                else:
                    delta_str = f"{numeric_delta:+.2f}"

                # Determine improvement / degradation
                # Significance threshold: 2% of baseline or minimum 0.001
                threshold = max(abs(b_val) * 0.02, 0.001)

                if desired_dir == "lower":
                    if numeric_delta < -threshold:
                        direction = "improved"
                    elif numeric_delta > threshold:
                        direction = "degraded"
                    else:
                        direction = "unchanged"
                else:  # higher is better
                    if numeric_delta > threshold:
                        direction = "improved"
                    elif numeric_delta < -threshold:
                        direction = "degraded"
                    else:
                        direction = "unchanged"

                details = f"{metric} changed from {b_raw} to {a_raw} ({delta_str}, {direction})"

            observed_change = {
                "metric": metric,
                "before": b_raw,
                "after": a_raw,
                "delta": delta_str,
                "direction": direction,
                "details": details,
            }
            observed_changes.append(observed_change)

            # Add metric evidence item
            if direction == "improved":
                assessment: EvidenceAssessment = "supports_recovery"
            elif direction == "degraded":
                assessment = "indicates_failure"
            elif direction == "unchanged":
                assessment = "indicates_failure" if desired_dir == "lower" and b_val and b_val > 0 else "inconclusive"
            else:
                assessment = "inconclusive"

            evidence.append({
                "source": f"metric:{metric}",
                "claim": f"{metric} moved from {b_raw} to {a_raw}",
                "assessment": assessment,
                "details": details,
            })

        # Record metrics present in before ONLY (missing after measurement)
        before_only = set(before_state.keys()) - set(after_state.keys())
        for metric in sorted(before_only):
            evidence.append({
                "source": f"metric:{metric}",
                "claim": f"Baseline for {metric} was {before_state[metric]}, but post-action measurement was omitted",
                "assessment": "inconclusive",
                "details": f"Missing post-action measurement for {metric}",
            })

        # Record metrics present in after ONLY (no baseline to compare)
        after_only = set(after_state.keys()) - set(before_state.keys())
        for metric in sorted(after_only):
            evidence.append({
                "source": f"metric:{metric}",
                "claim": f"Post-action measurement for {metric} was {after_state[metric]}, but baseline was omitted",
                "assessment": "inconclusive",
                "details": f"Missing baseline measurement for {metric}",
            })

        # Evaluate qualitative observations
        for obs in observations:
            obs_lower = obs.lower()
            if any(k in obs_lower for k in (
                "subsided", "cleared", "stopped", "no error", "no alert",
                "healthy", "recovered", "normal", "stabilized", "resolved",
                "dropped", "nominal", "down from", "nominal baselines"
            )):
                evidence.append({
                    "source": "observation",
                    "claim": obs,
                    "assessment": "supports_recovery",
                    "details": f"Positive observation: {obs}",
                })
            elif any(k in obs_lower for k in (
                "still firing", "still failing", "persisting", "active failure",
                "remains high", "ongoing outage", "still escalating", "worsened"
            )):
                evidence.append({
                    "source": "observation",
                    "claim": obs,
                    "assessment": "indicates_failure",
                    "details": f"Negative observation: {obs}",
                })
            else:
                evidence.append({
                    "source": "observation",
                    "claim": obs,
                    "assessment": "inconclusive",
                    "details": f"Informational observation: {obs}",
                })

        return observed_changes, evidence

    @classmethod
    def _determine_verification_status(
        cls,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        observed_changes: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        operator_result: Optional[str],
        observations: List[str],
    ) -> VerificationStatus:
        """
        Applies deterministic verification rules across evidence:
          - confirmed: all evaluated metrics improved, no conflicting degradation
          - failed: measurements degraded or stayed at failure levels
          - inconclusive: incomplete evidence or conflicting metrics
          - unknown: outcome cannot be established from available data
        """
        # Case 1: Unknown outcome declared with no decisive metrics
        if operator_result == "unknown" and not observed_changes:
            return "unknown"

        # Case 2: Incomplete evidence (no after metrics or no before metrics)
        if not after_state and not before_state:
            if operator_result == "unknown":
                return "unknown"
            return "inconclusive"

        if not after_state or not before_state:
            return "inconclusive"

        if not observed_changes:
            # Metrics were provided, but none matched between before and after
            return "inconclusive"

        # Count directions among comparable metrics
        improved = [c for c in observed_changes if c["direction"] == "improved"]
        degraded = [c for c in observed_changes if c["direction"] == "degraded"]
        unchanged = [c for c in observed_changes if c["direction"] == "unchanged"]

        # Case 3: Conflicting metrics (some improved, some degraded)
        if improved and degraded:
            # Update evidence to highlight conflict
            evidence.append({
                "source": "telemetry_conflict",
                "claim": f"{len(improved)} metrics improved while {len(degraded)} metrics degraded",
                "assessment": "conflicting",
                "details": (
                    f"Conflicting metrics: improved={[c['metric'] for c in improved]}, "
                    f"degraded={[c['metric'] for c in degraded]}"
                ),
            })
            return "inconclusive"

        # Case 4: Failed recovery (degraded metrics or unchanged failure metrics)
        if degraded and not improved:
            evidence.append({
                "source": "telemetry_failure",
                "claim": f"{len(degraded)} metrics deteriorated following resolution action",
                "assessment": "indicates_failure",
                "details": f"Deteriorated metrics: {[c['metric'] for c in degraded]}",
            })
            return "failed"

        if unchanged and not improved:
            evidence.append({
                "source": "telemetry_stagnant",
                "claim": "Metrics remained unchanged at incident failure levels",
                "assessment": "indicates_failure",
                "details": f"Unchanged metrics: {[c['metric'] for c in unchanged]}",
            })
            return "failed"

        # Case 5: Operator marked failure / ineffective despite metrics or with mixed observations
        if operator_result in ("ineffective", "attempted_and_failed") and not improved:
            return "failed"

        # Case 6: Successful recovery confirmed
        if improved and not degraded:
            # Check if any observation directly indicates ongoing failure
            negative_obs = [e for e in evidence if e.get("source") == "observation" and e.get("assessment") == "indicates_failure"]
            if negative_obs:
                return "inconclusive"

            evidence.append({
                "source": "telemetry_recovery",
                "claim": f"All {len(improved)} evaluated metrics improved to recovered state",
                "assessment": "supports_recovery",
                "details": f"Improved metrics: {[c['metric'] for c in improved]}",
            })
            return "confirmed"

        return "inconclusive"
