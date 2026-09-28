"""
Unit Tests for Request Validation and State Machine.
Conforms to PRD BE-012, ERR-05, FR-009, D-13.
"""

import pytest
from src.services.validation_service import ValidationService


def test_validate_symptom_description_valid():
    text = "Payment service is failing with database timeout errors."
    result = ValidationService.validate_symptom_description(text)
    assert result == text


def test_validate_symptom_description_empty():
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_symptom_description("")
    assert "MINIMUM_INPUT_REQUIRED" in str(exc.value)


def test_validate_symptom_description_whitespace():
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_symptom_description("     \n\t   ")
    assert "MINIMUM_INPUT_REQUIRED" in str(exc.value)


def test_validate_symptom_description_none():
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_symptom_description(None)
    assert "MINIMUM_INPUT_REQUIRED" in str(exc.value)


def test_validate_symptom_description_exceeds_max():
    huge_text = "a" * 10001
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_symptom_description(huge_text)
    assert "PAYLOAD_LIMIT_EXCEEDED" in str(exc.value)


def test_validate_severity_valid():
    assert ValidationService.validate_severity("critical") == "critical"
    assert ValidationService.validate_severity("HIGH") == "high"
    assert ValidationService.validate_severity("medium") == "medium"
    assert ValidationService.validate_severity("low") == "low"
    assert ValidationService.validate_severity(None) == "unknown"


def test_validate_severity_invalid():
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_severity("catastrophic")
    assert "INVALID_ENUM_VALUE" in str(exc.value)


def test_validate_environment_valid():
    assert ValidationService.validate_environment("production") == "production"
    assert ValidationService.validate_environment("STAGING") == "staging"
    assert ValidationService.validate_environment(None) == "unknown"


def test_validate_environment_invalid():
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_environment("mars_cluster")
    assert "INVALID_ENUM_VALUE" in str(exc.value)


def test_validate_state_transitions():
    # Legal transitions
    ValidationService.validate_status_transition("created", "investigating")
    ValidationService.validate_status_transition("investigating", "mitigated")
    ValidationService.validate_status_transition("mitigated", "resolved")
    ValidationService.validate_status_transition("resolved", "closed")

    # Illegal transition: created directly to resolved
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_status_transition("created", "resolved")
    assert "INVALID_STATE_TRANSITION" in str(exc.value)

    # Illegal transition: modify closed incident
    with pytest.raises(ValueError) as exc:
        ValidationService.validate_status_transition("closed", "investigating")
    assert "TERMINAL_STATE" in str(exc.value)
