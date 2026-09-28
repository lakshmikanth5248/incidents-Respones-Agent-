"""
Incident Analysis Schemas and DTOs.
Conforms to PRD §12.2 (API-005, API-006), §8.3 (LLM-013), and Feature 3 requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ProvenanceStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        ...,
        description="Source of this statement (e.g., 'current_incident')"
    )
    statement: str = Field(
        ...,
        description="Factual claim or logical deduction from evidence"
    )


class AffectedScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    environment: str
    affected_components: List[str] = Field(default_factory=list)


class CurrentIncidentInterpretation(BaseModel):
    """Structured reading produced by TL-001 Incident Analyzer."""
    model_config = ConfigDict(extra="forbid")

    affected_scope: AffectedScope
    failure_mode: str
    facts: List[ProvenanceStatement]
    inferences: List[ProvenanceStatement]
    unknowns: List[str] = Field(default_factory=list)
    information_gaps: List[str] = Field(default_factory=list)
    normalized_signatures: List[str] = Field(default_factory=list)


class ModelMetadata(BaseModel):
    model_identifier: str
    prompt_version: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float


class ComparisonItem(BaseModel):
    """
    Structured comparison conforming to PRD §12.4 and Features 06-07.
    Contains: matching_signals, differences, historical_patterns, conflicts, confidence, provenance.
    """
    model_config = ConfigDict(extra="ignore")

    prior_incident_id: Optional[str] = None
    entry_id: Optional[str] = None
    matching_signals: List[str] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    historical_patterns: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    match_strength: Optional[str] = "partial"
    applicability: Optional[str] = "applicable"


class HypothesisItem(BaseModel):
    """
    Structured root-cause hypothesis conforming to PRD §12.5 and Features 06-07.
    Contains: hypothesis, supporting_current_evidence, supporting_memory_entries,
    contradicting_evidence, unknowns, confidence, provenance.
    """
    model_config = ConfigDict(extra="ignore")

    hypothesis: str
    supporting_current_evidence: List[str] = Field(default_factory=list)
    supporting_memory_entries: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    confidence: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    rank: int = 1
    precedent_backed: bool = False
    status: str = "candidate"

class RecommendationItem(BaseModel):
    """
    Structured recommendation conforming to PRD §12.6 (FR-035 - FR-043) and Feature 08.
    Contains:
    - recommendation_id
    - action / investigation
    - reason
    - supporting_evidence
    - memory_references
    - runbook_reference
    - risk
    - expected_observation
    - confidence
    - provenance
    """
    model_config = ConfigDict(extra="ignore")

    recommendation_id: str
    action: str = Field(..., description="Action or investigation to perform")
    investigation: Optional[str] = Field(default=None, description="Detailed diagnostic or investigative steps")
    action_type: str = Field(default="diagnostic", description="'diagnostic' or 'remediation'")
    reason: str = Field(..., description="Justification grounded in evidence or hypothesis")
    supporting_evidence: List[str] = Field(default_factory=list)
    memory_references: List[str] = Field(default_factory=list)
    runbook_reference: Optional[str] = Field(default=None, description="Runbook ID if applicable, None if no runbook coverage")
    runbook_outcome: Optional[str] = Field(default="no_record", description="'successful', 'ineffective', 'untested', or 'RUNBOOK_SET_UNAVAILABLE'")
    hypothesis_reference: Optional[str] = Field(default=None, description="Hypothesis ID or statement this addresses")
    risk: str = Field(default="low", description="Risk level: 'low', 'medium', 'high'")
    is_destructive: bool = Field(default=False, description="Flag indicating if procedure alters production state")
    safer_alternative: Optional[str] = Field(default=None, description="Safer diagnostic alternative if procedure is risky or destructive")
    expected_observation: str = Field(..., description="What the engineer expects to observe to verify effectiveness")
    confidence: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    advisory: bool = Field(default=True, description="Always True: agent does not execute production actions")
    advisory_note: str = Field(
        default="Advisory only. The agent does not execute production actions. Human engineer authorization required.",
        description="Explicit advisory disclaimer",
    )


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    memory_isolated: Optional[bool] = Field(
        default=False,
        description="Whether to run in memory-isolated mode (Feature 12)"
    )
    operator_note: Optional[str] = Field(
        default=None,
        description="Optional human operator guidance for analysis"
    )
    stage: Optional[str] = Field(
        default=None,
        description="Optional halting stage: 'interpret', 'recall', 'compare', 'hypothesize', 'recommend'"
    )


class AnalysisResponse(BaseModel):
    """Full analysis response for API-005 and API-006."""
    analysis_id: str
    incident_id: str
    revision: int
    status: str
    memory_status: Optional[str] = None
    recall_record: Optional[Dict[str, Any]] = None
    symptom_analysis: CurrentIncidentInterpretation
    comparisons: List[ComparisonItem] = Field(default_factory=list)
    hypotheses: List[HypothesisItem] = Field(default_factory=list)
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    information_gaps: List[str] = Field(default_factory=list)
    model_metadata: ModelMetadata
    created_at: str


