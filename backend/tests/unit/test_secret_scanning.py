"""
Unit Tests for Secret Scanning and Credential Detection.
Conforms to PRD SEC-002, SEC-008, SEC-015, T-SEC-01, T-SEC-02.
Uses safe synthetic credential fixtures.
"""

from src.services.validation_service import ValidationService
from src.observability.logger import redact_secrets_text


def test_scan_clean_incident_text():
    clean_text = "Payment API is returning 500 errors after payment-service v2.4 deployment. DB connections exhausted."
    result = ValidationService.scan_for_secrets(clean_text)
    assert result.has_secrets is False
    assert len(result.detected_types) == 0


def test_scan_detects_synthetic_api_key():
    synthetic_key = "sk-live-9999999999aaaaaaaaaabbbbbbbbbb"
    text = f"Connection failed with auth error using key {synthetic_key} in service."
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "api_key" in result.detected_types


def test_scan_detects_synthetic_aws_key():
    synthetic_aws = "AKIAIOSFODNN7EXAMPLE"
    text = f"S3 bucket sync failed with credential {synthetic_aws} access denied."
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "api_key" in result.detected_types


def test_scan_detects_synthetic_github_token():
    synthetic_ghp = "ghp_1234567890abcdef1234567890abcdef1234"
    text = f"Deployment failed to fetch repo with token {synthetic_ghp} expired."
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "api_key" in result.detected_types


def test_scan_detects_synthetic_private_key():
    synthetic_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    text = f"Found ssh key in logs:\n{synthetic_key}"
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "private_key" in result.detected_types


def test_scan_detects_synthetic_bearer_token():
    synthetic_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis"
    text = f"Incoming request header: Authorization: {synthetic_token}"
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "authorization_header" in result.detected_types


def test_scan_detects_synthetic_password():
    text = "Database connection failed with string postgres://postgres:SuperSecretP@ssword123@db.prod.internal:5432/main"
    result = ValidationService.scan_for_secrets(text)
    assert result.has_secrets is True
    assert "password" in result.detected_types


def test_redact_secrets_text():
    secret_text = "Log msg: sk-live-9999999999aaaaaaaaaabbbbbbbbbb failed with password=SuperSecretP@ssword123"
    sanitized = redact_secrets_text(secret_text)

    # Assert secret values are scrubbed
    assert "sk-live-9999999999aaaaaaaaaabbbbbbbbbb" not in sanitized
    assert "SuperSecretP@ssword123" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED" in sanitized
