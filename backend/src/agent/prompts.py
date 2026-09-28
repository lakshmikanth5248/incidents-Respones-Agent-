"""
Versioned Prompt Management Module.
Conforms to PRD §8.2 (LLM-007..LLM-012) and Feature 3 requirements.
Prompts are loaded from versioned files, not constructed dynamically across code.
"""

import os
import json
from typing import Dict, Any

PROMPTS_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
)


class PromptManager:
    """Loads and formats versioned prompts from disk."""

    @classmethod
    def load_prompt(cls, template_name: str, version: str = "v1") -> str:
        """Load raw prompt template string from disk."""
        candidate_paths = [
            os.path.join(PROMPTS_ROOT, version, f"{template_name}.txt"),
            os.path.join(PROMPTS_ROOT, version.split(".")[0], f"{template_name}.txt"),
        ]
        for filepath in candidate_paths:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()

        raise FileNotFoundError(
            f"Prompt template '{template_name}' for version '{version}' not found in candidates: {candidate_paths}"
        )

    @classmethod
    def format_interpretation_prompt(
        cls,
        incident_data: Dict[str, Any],
        version: str = "v1"
    ) -> str:
        """Format the Stage 1 Incident Interpretation prompt with incident evidence safely."""
        template = cls.load_prompt("incident_interpretation", version=version)
        replacements = {
            "{incident_id}": str(incident_data.get("id", "unknown")),
            "{service}": str(incident_data.get("service", "unknown")),
            "{environment}": str(incident_data.get("environment", "unknown")),
            "{severity}": str(incident_data.get("severity", "unknown")),
            "{detected_at}": str(incident_data.get("detected_at", "unknown")),
            "{symptoms_raw}": str(incident_data.get("symptoms_raw", "")),
            "{symptoms_normalized}": str(incident_data.get("symptoms_normalized", "")),
            "{error_signatures}": json.dumps(incident_data.get("error_signatures", [])),
            "{affected_components}": json.dumps(incident_data.get("affected_components", [])),
            "{recent_changes}": json.dumps(incident_data.get("recent_changes", [])),
            "{context}": json.dumps(incident_data.get("context", {})),
        }
        formatted = template
        for placeholder, val in replacements.items():
            formatted = formatted.replace(placeholder, val)
        return formatted
