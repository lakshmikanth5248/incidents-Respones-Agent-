"""
Deterministic Normalization Service.
Conforms strictly to PRD §9.2 (DM-001), FR-006, BE-005, and Feature 1 specification.
Extracts structured facts from raw symptom text without hallucinating or inventing root causes.
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel


class NormalizedIncidentData(BaseModel):
    service: str = "unknown"
    environment: str = "unknown"
    severity: str = "unknown"
    failure_mode_label: str = "unknown"
    symptoms: List[str] = []
    symptoms_normalized: str = ""
    observations: List[str] = []
    recent_changes: List[str] = []
    affected_components: List[str] = []
    error_signatures: List[str] = []
    impact: Optional[str] = None


class NormalizationService:
    """Provides deterministic extraction and normalization of incident data."""

    @classmethod
    def normalize(
        cls,
        raw_text: str,
        explicit_service: Optional[str] = None,
        explicit_environment: Optional[str] = None,
        explicit_severity: Optional[str] = None,
        explicit_recent_changes: Optional[List[str]] = None,
        explicit_error_text: Optional[List[str]] = None,
    ) -> NormalizedIncidentData:
        """
        Deterministically parses and normalizes incident information from input.
        Never fabricates root cause or unsupported facts.
        """
        # 1. Service Resolution
        service = "unknown"
        if explicit_service and explicit_service.strip():
            service = cls._clean_identifier(explicit_service)
        else:
            service = cls._extract_service(raw_text)

        # 2. Environment Resolution
        environment = "unknown"
        if explicit_environment and explicit_environment.strip():
            environment = explicit_environment.strip().lower()
        else:
            environment = cls._extract_environment(raw_text)

        # 3. Severity Resolution
        severity = "unknown"
        if explicit_severity and explicit_severity.strip():
            severity = explicit_severity.strip().lower()
        else:
            severity = cls._extract_severity(raw_text)

        # 4. Symptoms Extraction
        symptoms = cls._extract_symptoms(raw_text)

        # 5. Observations Extraction
        observations = cls._extract_observations(raw_text)

        # 6. Recent Changes Extraction
        recent_changes = list(explicit_recent_changes or [])
        extracted_changes = cls._extract_recent_changes(raw_text)
        for chg in extracted_changes:
            if chg not in recent_changes:
                recent_changes.append(chg)

        # 7. Affected Components
        affected_components = cls._extract_components(raw_text, service)

        # 8. Error Signatures
        error_signatures = list(explicit_error_text or [])
        extracted_signatures = cls._extract_error_signatures(raw_text)
        for sig in extracted_signatures:
            if sig not in error_signatures:
                error_signatures.append(sig)

        # 9. Failure Mode Label
        failure_mode_label = cls._derive_failure_mode(symptoms, raw_text)

        # 10. Impact
        impact = cls._extract_impact(raw_text)

        # 11. Normalized Symptoms Text
        symptoms_normalized = cls._build_symptoms_normalized(symptoms, failure_mode_label, raw_text)

        return NormalizedIncidentData(
            service=service,
            environment=environment,
            severity=severity,
            failure_mode_label=failure_mode_label,
            symptoms=symptoms,
            symptoms_normalized=symptoms_normalized,
            observations=observations,
            recent_changes=recent_changes,
            affected_components=affected_components,
            error_signatures=error_signatures,
            impact=impact
        )

    @staticmethod
    def _clean_identifier(val: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "-", val.strip().lower())
        cleaned = re.sub(r"-+", "-", cleaned).strip("-")
        return cleaned or "unknown"

    @classmethod
    def _extract_service(cls, text: str) -> str:
        candidates: List[Tuple[int, str]] = []

        # Match spaced form: "Payment API", "Order Service", "Auth Gateway"
        for m in re.finditer(r"\b([a-zA-Z0-9]+)\s+(API|Service|Gateway|Worker)\b", text, re.IGNORECASE):
            candidates.append((m.start(), f"{m.group(1).lower()}-{m.group(2).lower()}"))

        # Match hyphenated form: "payment-api", "payment-service", "auth-service"
        for m in re.finditer(r"\b([a-zA-Z0-9_\-]+(?:-api|-service|-worker|-gateway|-app))\b", text, re.IGNORECASE):
            candidates.append((m.start(), m.group(1).lower()))

        if candidates:
            # Sort by occurrence position in the text (earliest mention takes precedence)
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return "unknown"

    @classmethod
    def _extract_environment(cls, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\b(production|prod)\b", text_lower):
            return "production"
        if re.search(r"\b(staging|stage)\b", text_lower):
            return "staging"
        if re.search(r"\b(development|dev)\b", text_lower):
            return "development"
        return "unknown"

    @classmethod
    def _extract_severity(cls, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\b(critical|p0|p1|outage|sev-?1)\b", text_lower):
            return "critical"
        if re.search(r"\b(failing for customers|customer impact|high error rate)\b", text_lower):
            return "critical"
        if re.search(r"\b(high|sev-?2|major)\b", text_lower):
            return "high"
        if re.search(r"\b(medium|sev-?3|moderate)\b", text_lower):
            return "medium"
        if re.search(r"\b(low|sev-?4|minor)\b", text_lower):
            return "low"
        return "unknown"

    @classmethod
    def _extract_symptoms(cls, text: str) -> List[str]:
        symptoms = []
        text_lower = text.lower()

        if "payment" in text_lower and ("fail" in text_lower or "error" in text_lower):
            symptoms.append("payment failures")
        elif "fail" in text_lower:
            symptoms.append("service failures")

        if "latency" in text_lower:
            lat_match = re.search(r"latency\s+(?:increased\s+to\s+|is\s+|around\s+)?([0-9\.]+\s*(?:s|seconds|ms))", text_lower)
            if lat_match:
                symptoms.append(f"high latency ({lat_match.group(1).strip()})")
            else:
                symptoms.append("high latency")

        if "connection" in text_lower and ("exhaust" in text_lower or "pool" in text_lower or "limit" in text_lower or "100/100" in text_lower):
            symptoms.append("database connection exhaustion")
        elif "db" in text_lower and ("exhaust" in text_lower or "100/100" in text_lower):
            symptoms.append("database connection exhaustion")

        if "error rate" in text_lower:
            err_match = re.search(r"error rate\s+(?:is\s+|around\s+|at\s+)?([0-9]+%)", text_lower)
            if err_match:
                symptoms.append(f"elevated error rate ({err_match.group(1)})")
            else:
                symptoms.append("elevated error rate")

        if "out of memory" in text_lower or "oom" in text_lower:
            symptoms.append("out of memory (OOM)")

        if "cpu" in text_lower and ("spike" in text_lower or "saturation" in text_lower or "high" in text_lower):
            symptoms.append("high CPU utilization")

        # Fallback if no specific keyword matched: use first sentence or phrase
        if not symptoms:
            first_sentence = text.strip().split(".")[0].strip()
            if first_sentence:
                symptoms.append(first_sentence[:100])

        return symptoms

    @classmethod
    def _extract_observations(cls, text: str) -> List[str]:
        observations = []
        lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]

        for line in lines:
            if re.search(r"\b(error rate|latency|connections?|cpu|memory|db)\b", line, re.IGNORECASE):
                cleaned_line = line.strip(" -•*")
                if cleaned_line and cleaned_line not in observations:
                    observations.append(cleaned_line)

        return observations

    @classmethod
    def _extract_recent_changes(cls, text: str) -> List[str]:
        changes = []
        # Pattern 1: e.g., "payment-service v2.4 was deployed approximately 20 minutes before the incident"
        match1 = re.search(r"([a-zA-Z0-9_\-]+\s+v[0-9\.]+(?:\s+was)?\s+deployed[^\.\n]*)", text, re.IGNORECASE)
        if match1:
            changes.append(match1.group(1).strip())
            return changes

        # Pattern 2: e.g., "deployed payment-service v2.4"
        match2 = re.search(r"(?:deployed|release(?:d)?|updated)\s+([a-zA-Z0-9_\-]+\s+v[0-9\.]+[^\.\n]*)", text, re.IGNORECASE)
        if match2:
            changes.append(f"deployment of {match2.group(1).strip()}")
            return changes

        # Pattern 3: e.g., "payment-service v2.4 deployment"
        match3 = re.search(r"([a-zA-Z0-9_\-]+\s+v[0-9\.]+\s+deployment[^\.\n]*)", text, re.IGNORECASE)
        if match3:
            changes.append(match3.group(1).strip())
            return changes

        return changes

    @classmethod
    def _extract_components(cls, text: str, service: str) -> List[str]:
        components = set()
        if service and service != "unknown":
            components.add(service)

        text_lower = text.lower()
        if "database" in text_lower or "db" in text_lower:
            components.add("database")
        if "connection" in text_lower or "pool" in text_lower:
            components.add("connection-pool")
        if "redis" in text_lower or "cache" in text_lower:
            components.add("cache")
        if "gateway" in text_lower:
            components.add("api-gateway")

        return sorted(list(components))

    @classmethod
    def _extract_error_signatures(cls, text: str) -> List[str]:
        signatures = []
        # Look for HTTP status codes, exception names, error patterns
        http_matches = re.findall(r"\b(HTTP\s+[45][0-9]{2}|[45][0-9]{2}\s+(?:Internal Server Error|Bad Gateway|Gateway Timeout|Service Unavailable))\b", text, re.IGNORECASE)
        for m in http_matches:
            if m not in signatures:
                signatures.append(m)

        exc_matches = re.findall(r"\b([A-Z][a-zA-Z0-9_]*(?:Exception|Error))\b", text)
        for m in exc_matches:
            if m not in signatures:
                signatures.append(m)

        return signatures

    @classmethod
    def _derive_failure_mode(cls, symptoms: List[str], text: str) -> str:
        symptoms_str = " ".join(symptoms).lower()
        text_lower = text.lower()

        if "database connection exhaustion" in symptoms_str or ("db" in text_lower and "exhaust" in text_lower):
            return "database_connection_exhaustion"
        if "payment failures" in symptoms_str:
            return "payment_service_failure"
        if "high latency" in symptoms_str:
            return "high_latency"
        if "elevated error rate" in symptoms_str:
            return "api_error_spike"
        if "out of memory" in symptoms_str:
            return "out_of_memory"
        if "high cpu" in symptoms_str:
            return "cpu_saturation"

        return "unclassified_service_degradation"

    @classmethod
    def _extract_impact(cls, text: str) -> Optional[str]:
        match = re.search(r"([^.\n]*(?:failing for customers|customer impact|affecting users|downtime)[^.\n]*)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def _build_symptoms_normalized(cls, symptoms: List[str], failure_mode: str, raw_text: str) -> str:
        if symptoms:
            return f"Identified symptoms: {', '.join(symptoms)}. Primary failure classification: {failure_mode}."
        return raw_text[:200]
