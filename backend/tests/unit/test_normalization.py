"""
Unit Tests for Deterministic Normalization Service.
Conforms to PRD §9.2 (DM-001), FR-006, and Feature 1 Section 3 scenario.
"""

from src.services.normalization_service import NormalizationService


def test_shopkart_payment_api_scenario():
    """Verify the real-world ShopKart Payment API scenario from Section 3."""
    raw_symptom = (
        "Payment API is failing for customers.\n"
        "Error rate is around 31%.\n"
        "Latency increased to 4.8 seconds.\n"
        "Database connections are exhausted.\n"
        "Payment-service v2.4 was deployed approximately\n"
        "20 minutes before the incident."
    )

    normalized = NormalizationService.normalize(
        raw_text=raw_symptom,
        explicit_service=None,
        explicit_environment=None,
        explicit_severity=None,
    )

    assert normalized.service == "payment-api"
    assert normalized.severity == "critical"
    assert "database_connection_exhaustion" in normalized.failure_mode_label

    # Check symptoms
    assert any("payment" in s for s in normalized.symptoms)
    assert any("latency" in s for s in normalized.symptoms)
    assert any("database" in s or "connection" in s for s in normalized.symptoms)

    # Check observations
    assert any("31%" in obs for obs in normalized.observations)
    assert any("4.8" in obs for obs in normalized.observations)

    # Check recent changes
    assert any("v2.4" in chg for chg in normalized.recent_changes)

    # Check affected components
    assert "payment-api" in normalized.affected_components
    assert "database" in normalized.affected_components

    # Verify no root cause is fabricated
    assert not hasattr(normalized, "root_cause")


def test_normalization_with_explicit_overrides():
    raw_symptom = "Something seems slow on checkout."
    normalized = NormalizationService.normalize(
        raw_text=raw_symptom,
        explicit_service="checkout-service",
        explicit_environment="production",
        explicit_severity="high",
        explicit_recent_changes=["k8s-node-drain"],
        explicit_error_text=["TimeoutException"]
    )

    assert normalized.service == "checkout-service"
    assert normalized.environment == "production"
    assert normalized.severity == "high"
    assert "k8s-node-drain" in normalized.recent_changes
    assert "TimeoutException" in normalized.error_signatures


def test_normalization_handles_unknowns_gracefully():
    raw_symptom = "The system behaved strangely."
    normalized = NormalizationService.normalize(raw_symptom)

    assert normalized.service == "unknown"
    assert normalized.environment == "unknown"
    assert normalized.severity == "unknown"
    assert len(normalized.recent_changes) == 0
