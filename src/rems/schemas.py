"""Pydantic schemas for data validation and transfer."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentSchema(BaseModel):
    """Schema for a retrieved document."""

    content: str
    source: str | None = None
    rank: int | None = None
    score: float | None = None
    metadata: dict | None = None


class InteractionSchema(BaseModel):
    """Schema for a chatbot interaction."""

    id: str | None = None
    query: str
    response: str
    retrieved_documents: list[DocumentSchema] = Field(default_factory=list)
    session_id: str | None = None
    user_id: str | None = None
    metadata: dict | None = None
    created_at: datetime | None = None


class EvaluationResultSchema(BaseModel):
    """Schema for evaluation results of a single interaction."""

    interaction_id: str
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_relevancy: float | None = None
    has_hallucination: bool | None = None
    hallucination_details: dict | None = None
    overall_score: float | None = None
    details: dict | None = None


class EvaluationMetrics(BaseModel):
    """Aggregate metrics for an evaluation run."""

    # Retrieval metrics
    avg_context_precision: float | None = None
    avg_context_relevancy: float | None = None

    # Generation metrics
    avg_faithfulness: float | None = None
    avg_answer_relevancy: float | None = None

    # Hallucination stats
    hallucination_rate: float | None = None
    total_hallucinations: int = 0

    # Score distributions
    score_distribution: dict[str, int] | None = None


class RecommendationSchema(BaseModel):
    """Schema for a recommendation."""

    component: str  # retriever, generator
    issue: str
    suggestion: str
    priority: str  # critical, high, medium, low
    parameter_adjustments: dict | None = None


class EvaluationSummary(BaseModel):
    """Summary of an evaluation run."""

    evaluation_id: str
    evaluation_date: datetime
    interaction_count: int
    overall_score: float
    retrieval_score: float
    generation_score: float
    metrics: EvaluationMetrics
    recommendations: list[RecommendationSchema]
    quality_level: str  # excellent, good, acceptable, poor, critical
