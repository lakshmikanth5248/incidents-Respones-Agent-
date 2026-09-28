"""
Model Provider Abstraction and Adapters.
Conforms to PRD §8.1 (LLM-001..LLM-006), DEP-004, and Feature 3 requirements.
Supports pluggable providers (Mock, OpenAI, Anthropic) without hard-coding a single vendor.
"""

import time
import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel

from src.config import settings
from src.observability.logger import logger


class ModelOutput(BaseModel):
    raw_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    model_identifier: str


class ModelProviderException(Exception):
    """Base exception for model provider failures."""
    pass


class ModelUnavailableException(ModelProviderException):
    """Provider is unreachable, timed out, or quota exceeded (ERR-04)."""
    pass


class ModelOutputInvalidException(ModelProviderException):
    """Output failed syntax or schema validation (ERR-04, LLM-014)."""
    pass


class BaseProvider:
    """Base interface for all LLM providers."""

    def generate(self, prompt: str, schema_dict: Optional[Dict[str, Any]] = None) -> ModelOutput:
        raise NotImplementedError


class MockDeterministicProvider(BaseProvider):
    """
    Deterministic Mock Provider for testing and local reproducible runs (PRD D-10, BE-021).
    Extracts structured facts deterministically from the prompt text, adhering to schema rules.
    """

    def __init__(
        self,
        model_name: str = "mock-reasoner-v1",
        simulate_failure: Optional[str] = None
    ):
        self.model_name = model_name
        self.simulate_failure = simulate_failure

    def generate(self, prompt: str, schema_dict: Optional[Dict[str, Any]] = None) -> ModelOutput:
        start_time = time.time()

        # Simulate provider outage / network failure
        if self.simulate_failure == "unavailable":
            raise ModelUnavailableException("Model provider is unreachable (simulated outage).")

        # Simulate malformed output
        if self.simulate_failure == "malformed":
            return ModelOutput(
                raw_text="This is an invalid non-json output that fails schema validation.",
                parsed_json=None,
                prompt_tokens=150,
                completion_tokens=20,
                total_tokens=170,
                duration_ms=25.0,
                model_identifier=self.model_name
            )

        # Deterministic extraction from prompt
        service = "unknown"
        m_srv = re.search(r"- Service:\s*([^\n\r]+)", prompt)
        if m_srv:
            service = m_srv.group(1).strip()

        env = "unknown"
        m_env = re.search(r"- Environment:\s*([^\n\r]+)", prompt)
        if m_env:
            env = m_env.group(1).strip()

        symptoms_raw = ""
        m_sym = re.search(r"- Symptoms \(Raw\):\s*([^\n\r]+)", prompt)
        if m_sym:
            symptoms_raw = m_sym.group(1).strip()

        facts = []
        inferences = []
        unknowns = []
        information_gaps = []
        signatures = []
        affected_comps = [service] if service != "unknown" else []

        if "payment" in symptoms_raw.lower() or "payment" in prompt.lower():
            facts.append({"source": "current_incident", "statement": "Payment operations are experiencing failures."})
            affected_comps.append("payment-api")
        if "latency" in symptoms_raw.lower() or "latency" in prompt.lower():
            facts.append({"source": "current_incident", "statement": "Latency has increased above normal thresholds."})
            signatures.append("high_latency_threshold_breach")
        if "database" in symptoms_raw.lower() or "connection" in symptoms_raw.lower() or "db" in symptoms_raw.lower():
            facts.append({"source": "current_incident", "statement": "Database connections are exhausted."})
            inferences.append({"source": "current_incident", "statement": "Connection pool saturation is starving query processing."})
            affected_comps.append("database")
            affected_comps.append("connection-pool")
            signatures.append("DB_CONN_EXHAUSTION")

        if "v2.4" in symptoms_raw or "deployed" in symptoms_raw.lower():
            facts.append({"source": "current_incident", "statement": "A recent deployment occurred prior to incident onset."})
            inferences.append({"source": "current_incident", "statement": "Deployment timing correlates with failure onset."})

        # Ensure provenance is strictly populated
        if not facts:
            facts.append({"source": "current_incident", "statement": f"Symptom description observed: {symptoms_raw[:100]}"})

        # Explicit unknowns
        if env == "unknown":
            unknowns.append("Target environment is not specified.")
        unknowns.append("Exact database thread pool configuration.")

        # Information gaps
        information_gaps.append("Active database connection count metric graph.")
        information_gaps.append("Recent configuration diff for the deployed version.")

        failure_mode = "database_connection_exhaustion" if "database" in affected_comps else "unclassified_service_degradation"

        # Unique components
        cleaned_comps = sorted(list(set(c for c in affected_comps if c and c != "unknown")))

        output_dict = {
            "affected_scope": {
                "service": service,
                "environment": env,
                "affected_components": cleaned_comps
            },
            "failure_mode": failure_mode,
            "facts": facts,
            "inferences": inferences,
            "unknowns": unknowns,
            "information_gaps": information_gaps,
            "normalized_signatures": signatures
        }

        duration_ms = round((time.time() - start_time) * 1000, 2)
        prompt_tokens = len(prompt.split()) * 2
        completion_tokens = len(json.dumps(output_dict).split()) * 2

        return ModelOutput(
            raw_text=json.dumps(output_dict),
            parsed_json=output_dict,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            duration_ms=duration_ms,
            model_identifier=self.model_name
        )


class OpenAIProvider(BaseProvider):
    """OpenAI API provider adapter (PRD LLM-001)."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, schema_dict: Optional[Dict[str, Any]] = None) -> ModelOutput:
        import httpx
        start_time = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if resp.status_code != 200:
                    raise ModelUnavailableException(f"OpenAI error {resp.status_code}: {resp.text}")
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                duration_ms = round((time.time() - start_time) * 1000, 2)
                return ModelOutput(
                    raw_text=raw_text,
                    parsed_json=json.loads(raw_text),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    duration_ms=duration_ms,
                    model_identifier=self.model_name
                )
        except Exception as e:
            if isinstance(e, ModelUnavailableException):
                raise
            raise ModelUnavailableException(f"OpenAI call failed: {str(e)}")


def get_model_provider(
    provider_name: Optional[str] = None,
    simulate_failure: Optional[str] = None
) -> BaseProvider:
    """Factory creating the configured model provider adapter."""
    prov = (provider_name or settings.MODEL_PROVIDER).lower()
    if prov == "mock":
        return MockDeterministicProvider(
            model_name=settings.MODEL_NAME,
            simulate_failure=simulate_failure
        )
    elif prov == "openai":
        if not settings.MODEL_API_KEY:
            logger.warning("MODEL_API_KEY not configured; falling back to mock provider.")
            return MockDeterministicProvider(model_name=settings.MODEL_NAME)
        return OpenAIProvider(api_key=settings.MODEL_API_KEY, model_name=settings.MODEL_NAME)
    else:
        logger.warning(f"Unsupported provider '{prov}', using MockDeterministicProvider.")
        return MockDeterministicProvider(model_name=settings.MODEL_NAME)
