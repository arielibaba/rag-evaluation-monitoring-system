"""Configuration settings for REMS."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REMS_",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/rems",
        description="PostgreSQL connection URL",
    )

    # Chatbot API
    chatbot_api_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the chatbot API",
    )
    chatbot_api_key: str | None = Field(
        default=None,
        description="API key for chatbot authentication",
    )

    # LLM for evaluation (Gemini)
    google_api_key: str = Field(
        default="",
        description="Google API key for Gemini",
    )
    evaluation_model: str = Field(
        default="gemini-2.0-flash",
        description="Model to use for LLM-as-judge evaluation",
    )

    # Report output
    reports_dir: Path = Field(
        default=Path("./reports"),
        description="Directory for generated reports",
    )
    recommendations_file: Path = Field(
        default=Path("./recommendations.yaml"),
        description="Path for recommendations YAML file",
    )

    # Quality level thresholds
    threshold_excellent: float = Field(default=0.90)
    threshold_good: float = Field(default=0.75)
    threshold_acceptable: float = Field(default=0.60)
    threshold_poor: float = Field(default=0.40)

    # Diagnostic thresholds (for issue detection)
    diag_context_precision: float = Field(
        default=0.70,
        description="Minimum acceptable context precision",
    )
    diag_context_relevancy: float = Field(
        default=0.70,
        description="Minimum acceptable context relevancy",
    )
    diag_faithfulness: float = Field(
        default=0.70,
        description="Minimum acceptable faithfulness (hallucination threshold)",
    )
    diag_answer_relevancy: float = Field(
        default=0.70,
        description="Minimum acceptable answer relevancy",
    )
    diag_hallucination_rate: float = Field(
        default=0.10,
        description="Maximum acceptable hallucination rate",
    )


settings = Settings()
