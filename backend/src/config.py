"""
Application Configuration Module.
Conforms to PRD DEP-005, DEP-006, DEP-010, BE-018.
Reads configuration from environment variables with validated defaults.
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: Literal["development", "demo", "production", "test"] = Field(
        default="development",
        description="Application running environment"
    )
    DATABASE_URL: str = Field(
        default="sqlite:///./incident_agent.db",
        description="Relational database connection string (SQLite or PostgreSQL)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    CORS_ORIGIN: str = Field(
        default="http://localhost:3000",
        description="Permitted CORS origin for frontend"
    )
    MAX_SYMPTOM_LENGTH: int = Field(
        default=10000,
        description="Maximum allowed character length for symptom description"
    )
    MAX_PAYLOAD_BYTES: int = Field(
        default=1048576,  # 1MB
        description="Maximum allowed request payload size in bytes"
    )
    API_PREFIX: str = Field(
        default="/api",
        description="API prefix route"
    )
    DEFAULT_OPERATOR: str = Field(
        default="sre-operator",
        description="Implicit operator identity for MVP per BE-013"
    )
    MODEL_PROVIDER: Literal["mock", "openai", "anthropic"] = Field(
        default="mock",
        description="Configured model provider (PRD LLM-001, DEP-004)"
    )
    MODEL_NAME: str = Field(
        default="mock-reasoner-v1",
        description="Configured model name identifier"
    )
    MODEL_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for model provider (optional for mock)"
    )
    PROMPT_VERSION: str = Field(
        default="v1.0.0",
        description="Version identifier for active prompt templates"
    )
    HINDSIGHT_ENDPOINT: str = Field(
        default="http://localhost:8888",
        description="Vectorize Hindsight memory service base URL"
    )
    HINDSIGHT_API_KEY: Optional[str] = Field(
        default=None,
        description="API key / Bearer token for Hindsight service"
    )
    HINDSIGHT_BANK_ID: str = Field(
        default="incident-response-bank",
        description="Hindsight memory bank / entity ID scope"
    )
    HINDSIGHT_TIMEOUT_SECONDS: float = Field(
        default=5.0,
        description="Timeout for Hindsight network operations in seconds"
    )
    HINDSIGHT_MAX_RETRIES: int = Field(
        default=2,
        description="Maximum retry attempts on retryable network/5xx errors"
    )
    HINDSIGHT_USE_TEST_DOUBLE: bool = Field(
        default=True,
        description="Whether to use the in-process Hindsight test double"
    )
    MEMORY_ISOLATED: bool = Field(
        default=False,
        description="Global memory-isolated mode default (PRD FR-022, D-08)"
    )


# Singleton settings instance
settings = Settings()
