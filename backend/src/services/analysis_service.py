"""
Incident Analysis Service.
Conforms to PRD §11.2 (Agent service), §8, D-02, BE-006, ERR-04, and Feature 3 requirements.
Orchestrates:
1. Retrieval of incident evidence
2. Prompt formatting from versioned templates
3. Pluggable model provider execution
4. Strict Pydantic schema validation
5. Architectural invariant: NO HYPOTHESIS BEFORE RECALL
6. Revisioning, persistence, cost/token metrics, and audit logging.
"""

from typing import Optional
from sqlalchemy.orm import Session
from fastapi import status
from pydantic import ValidationError

from src.config import settings
from src.api.errors import APIException
from src.api.schemas.analysis import (
    AnalysisRequest,
    CurrentIncidentInterpretation,
)
from src.data.models.analysis import IncidentAnalysis
from src.data.repositories.analysis_repository import AnalysisRepository
from src.data.repositories.incident_repository import IncidentRepository
from src.services.incident_service import IncidentService
from src.agent.prompts import PromptManager
from src.memory.service import memory_service
from src.memory.schemas import RecallRequest, MemoryStatus
from src.services.reasoning_service import reasoning_service
from src.agent.provider import (
    get_model_provider,
    BaseProvider,
    ModelUnavailableException,
    ModelOutputInvalidException,
)
from src.observability.logger import logger


class AnalysisService:
    """Service orchestrating Stage 1 incident analysis & interpretation."""

    @classmethod
    def analyze_incident(
        cls,
        db: Session,
        incident_id: str,
        request: Optional[AnalysisRequest] = None,
        provider_override: Optional[BaseProvider] = None,
        simulate_failure: Optional[str] = None,
    ) -> IncidentAnalysis:
        """
        Executes Stage 1 analysis: Current Incident Interpretation (TL-001).
        Enforces D-02 ordering: INTERPRET -> RECALL -> COMPARE -> HYPOTHESIZE.
        No hypotheses are formed at this stage.
        """
        incident = IncidentService.get_incident_by_id(db, incident_id)

        # 1. State eligibility check
        if incident.status == "closed":
            raise APIException(
                code="INCIDENT_CLOSED",
                message=f"Cannot analyze incident '{incident_id}' because it is closed.",
                status_code=status.HTTP_409_CONFLICT,
                retryable=False
            )

        # 2. Format versioned prompt
        try:
            prompt_text = PromptManager.format_interpretation_prompt(
                incident_data=incident.to_dict(),
                version=settings.PROMPT_VERSION
            )
        except Exception as e:
            logger.error(f"analysis.prompt_format_error {e}")
            raise APIException(
                code="PROMPT_LOAD_ERROR",
                message=f"Failed to load prompt template: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3. Model execution via configured provider
        provider = provider_override or get_model_provider(simulate_failure=simulate_failure)
        logger.info(f"analysis.started incident_id={incident_id} model={settings.MODEL_NAME}")

        try:
            model_output = provider.generate(prompt=prompt_text)
        except ModelUnavailableException as e:
            logger.error(f"analysis.model_unavailable incident_id={incident_id} error={e}")
            raise APIException(
                code="MODEL_UNAVAILABLE",
                message="The analysis model could not be reached. Nothing was changed — retry.",
                status_code=status.HTTP_502_BAD_GATEWAY,
                retryable=True,
                details={"cause": str(e)}
            )
        except Exception as e:
            logger.error(f"analysis.provider_error incident_id={incident_id} error={e}")
            raise APIException(
                code="MODEL_UNAVAILABLE",
                message=f"Model provider execution failed: {str(e)}",
                status_code=status.HTTP_502_BAD_GATEWAY,
                retryable=True
            )

        # 4. Strict Schema Validation (PRD LLM-013, ERR-04)
        if not model_output.parsed_json or not isinstance(model_output.parsed_json, dict):
            logger.error(f"analysis.model_output_invalid raw={model_output.raw_text[:200]}")
            raise APIException(
                code="MODEL_OUTPUT_INVALID",
                message="The analysis model returned non-JSON or unparseable output.",
                status_code=status.HTTP_502_BAD_GATEWAY,
                retryable=True
            )

        try:
            interpretation = CurrentIncidentInterpretation(**model_output.parsed_json)
        except ValidationError as e:
            logger.error(f"analysis.schema_validation_failed errors={e.errors()}")
            raise APIException(
                code="MODEL_OUTPUT_INVALID",
                message="Model output failed structured schema validation.",
                status_code=status.HTTP_502_BAD_GATEWAY,
                retryable=True,
                details={"validation_errors": e.errors()}
            )

        # 5. Core Reasoning Stage 2: RECALL (TL-002 Hindsight Recall)
        # Order: INTERPRET -> RECALL -> COMPARE -> HYPOTHESIZE (D-02)
        is_isolated = bool(request.memory_isolated) if request else False
        recall_req = RecallRequest(
            service=incident.service,
            environment=incident.environment,
            failure_mode=interpretation.failure_mode,
            normalized_symptoms=incident.symptoms_normalized or incident.symptoms_raw,
            error_signatures=interpretation.normalized_signatures or incident.error_signatures,
            affected_components=interpretation.affected_scope.affected_components or incident.affected_components,
            memory_isolated=is_isolated,
            limit=5,
        )
        recall_result = memory_service.recall(recall_req)
        recall_record_dict = recall_result.recall_record.to_dict() if recall_result.recall_record else None
        memory_status_str = recall_result.memory_status.value

        # 6. Core Reasoning Stage 3: Memory Context Assembly
        memory_context = reasoning_service.assemble_memory_context(
            recalled_entries=recall_result.entries,
            memory_status=memory_status_str,
        )

        target_stage = (request.stage or "hypothesize").lower() if request else "hypothesize"
        comparisons_list = []
        hypotheses_list = []

        # 7. Core Reasoning Stage 4: Comparison (FR-023..FR-028, AC2-04)
        # Order: INTERPRET -> RECALL -> CONTEXT ASSEMBLY -> COMPARE -> HYPOTHESIZE
        if target_stage not in ["interpret", "recall"]:
            comparisons_objs = reasoning_service.compare_evidence(
                incident=incident,
                interpretation=interpretation,
                memory_context=memory_context,
            )
            comparisons_list = [c.model_dump() for c in comparisons_objs]

            # 8. Core Reasoning Stage 5: Hypothesis Formation (FR-029..FR-034, AC2-05)
            if target_stage != "compare":
                hypotheses_objs = reasoning_service.generate_hypotheses(
                    incident=incident,
                    interpretation=interpretation,
                    memory_context=memory_context,
                    comparisons=comparisons_objs,
                )
                hypotheses_list = [h.model_dump() for h in hypotheses_objs]

        # 9. Revisioning & Persistence (PRD BE-019)
        next_revision = AnalysisRepository.get_next_revision(db, incident_id)
        analysis_id = f"ANA-{incident_id}-r{next_revision}"

        analysis_obj = IncidentAnalysis(
            id=analysis_id,
            incident_id=incident.id,
            revision=next_revision,
            prompt_version=settings.PROMPT_VERSION,
            model_identifier=model_output.model_identifier,
            symptom_analysis=interpretation.model_dump(),
            unknowns=interpretation.unknowns,
            information_gaps=interpretation.information_gaps,
            evidence=incident.to_dict(),
            hypotheses=hypotheses_list,
            comparisons=comparisons_list,
            recall_record=recall_record_dict,
            memory_status=memory_status_str,
            prompt_tokens=model_output.prompt_tokens,
            completion_tokens=model_output.completion_tokens,
            total_tokens=model_output.total_tokens,
            duration_ms=model_output.duration_ms
        )

        persisted = AnalysisRepository.create(db, analysis_obj)

        # 7. Update parent incident state and references
        incident.analysis_revision = next_revision
        incident.analysis_id = persisted.id
        incident.memory_status = memory_status_str
        incident.recall_record = recall_record_dict
        if incident.status in ["created", "analyzing"]:
            incident.status = "analyzed"

        IncidentRepository.update(db, incident)

        # 8. Record audit event
        IncidentRepository.record_audit(
            db=db,
            incident_id=incident.id,
            action="incident.analyzed",
            actor=incident.operator,
            previous_state="created" if incident.status == "analyzed" else incident.status,
            new_state="analyzed",
            outcome="success",
            details={
                "analysis_id": persisted.id,
                "revision": next_revision,
                "memory_status": memory_status_str,
                "duration_ms": model_output.duration_ms,
                "total_tokens": model_output.total_tokens
            }
        )

        logger.info(
            f"analysis.completed id={persisted.id} revision={next_revision} "
            f"tokens={model_output.total_tokens} duration_ms={model_output.duration_ms}"
        )
        return persisted

    @classmethod
    def get_analysis(
        cls,
        db: Session,
        incident_id: str,
        revision: Optional[int] = None
    ) -> IncidentAnalysis:
        """Retrieves current or prior revision of an analysis artefact for audit (API-006)."""
        # Ensure incident exists
        IncidentService.get_incident_by_id(db, incident_id)

        if revision is not None:
            analysis = AnalysisRepository.get_by_incident_and_revision(db, incident_id, revision)
            if not analysis:
                raise APIException(
                    code="ANALYSIS_NOT_FOUND",
                    message=f"Analysis revision {revision} was not found for incident '{incident_id}'.",
                    status_code=status.HTTP_404_NOT_FOUND,
                    retryable=False
                )
            return analysis

        latest = AnalysisRepository.get_latest_for_incident(db, incident_id)
        if not latest:
            raise APIException(
                code="ANALYSIS_NOT_FOUND",
                message=f"No analysis artefact has been generated yet for incident '{incident_id}'.",
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False
            )
        return latest
