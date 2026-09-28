"""
Hindsight Recall Intent and Query Builder.
Conforms strictly to Feature 05 Requirements and PRD §3.3, §3.4 (RL-001 to RL-006).
Derives focused retrieval intent strictly from:
- service
- environment
- failure mode
- normalized symptoms
- error signatures
- affected component
Explicitly excludes arbitrary unrelated incident text, timestamps, or transient data.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

DEFAULT_QUERY_VERSION = "v1.0.0"


class RecallIntent(BaseModel):
    """Structured retrieval intent derived from normalized incident facts."""
    service: Optional[str] = None
    environment: Optional[str] = None
    failure_mode: Optional[str] = None
    normalized_symptoms: Optional[str] = None
    error_signatures: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)
    composed_query: str
    query_version: str = DEFAULT_QUERY_VERSION
    filters: Dict[str, Any] = Field(default_factory=dict)


def build_recall_intent(source: Union[Any, Dict[str, Any]], query_override: Optional[str] = None) -> RecallIntent:
    """
    Derives the retrieval intent from normalized incident attributes.
    Works with both Incident model instances and dictionary representations.
    """
    if isinstance(source, dict):
        service = source.get("service")
        environment = source.get("environment")
        failure_mode = source.get("failure_mode_label") or source.get("failure_mode")
        normalized_symptoms = source.get("symptoms_normalized") or source.get("symptoms_raw") or ""
        error_signatures = source.get("error_signatures") or []
        affected_components = source.get("affected_components") or []
    else:
        service = getattr(source, "service", None)
        environment = getattr(source, "environment", None)
        failure_mode = getattr(source, "failure_mode_label", None)
        normalized_symptoms = getattr(source, "symptoms_normalized", None) or getattr(source, "symptoms_raw", "")
        error_signatures = getattr(source, "error_signatures", None) or []
        affected_components = getattr(source, "affected_components", None) or []

    # Clean failure mode label
    clean_failure_mode = None
    if failure_mode and failure_mode not in ("unknown", "None", ""):
        clean_failure_mode = failure_mode.replace("_", " ").strip()

    # If query is explicitly supplied by user/operator, use it as core
    if query_override and query_override.strip():
        composed_query = query_override.strip()
    else:
        # Construct deterministic composed query from structured features
        query_parts = []
        if clean_failure_mode:
            query_parts.append(clean_failure_mode)

        if error_signatures:
            # Include unique, top error signature tokens/phrases
            signatures_str = " ".join([sig.strip() for sig in error_signatures if sig.strip()])
            if signatures_str:
                query_parts.append(signatures_str)

        if normalized_symptoms and len(normalized_symptoms.strip()) > 0:
            # Use concise summary of symptoms
            symptom_snippet = normalized_symptoms.strip()
            # If symptom snippet isn't identical to what we already added
            if clean_failure_mode and clean_failure_mode.lower() not in symptom_snippet.lower():
                query_parts.append(symptom_snippet[:300])
            elif not clean_failure_mode:
                query_parts.append(symptom_snippet[:300])

        if affected_components:
            comp_str = " ".join(affected_components)
            query_parts.append(f"component: {comp_str}")

        composed_query = " ".join(query_parts).strip()
        if not composed_query and service:
            composed_query = f"{service} operational incident"

    filters: Dict[str, Any] = {}
    if service:
        filters["service"] = service

    return RecallIntent(
        service=service,
        environment=environment,
        failure_mode=clean_failure_mode or failure_mode,
        normalized_symptoms=normalized_symptoms,
        error_signatures=list(error_signatures),
        affected_components=list(affected_components),
        composed_query=composed_query,
        query_version=DEFAULT_QUERY_VERSION,
        filters=filters,
    )
