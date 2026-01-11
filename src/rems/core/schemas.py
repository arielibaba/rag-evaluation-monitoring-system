"""Core schemas for REMS - lightweight Pydantic models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QualityLevel(str, Enum):
    """Quality level classification."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class Interaction:
    """A single RAG interaction to evaluate."""

    query: str
    response: str
    contexts: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Interaction":
        """Create an Interaction from a dictionary."""
        # Handle different field names for contexts
        contexts = data.get("contexts", [])
        if not contexts:
            contexts = data.get("retrieved_contexts", [])
        if not contexts:
            # Handle retrieved_documents format
            docs = data.get("retrieved_documents", [])
            contexts = [
                doc.get("content", "") if isinstance(doc, dict) else str(doc)
                for doc in docs
            ]

        return cls(
            query=data.get("query", data.get("question", "")),
            response=data.get("response", data.get("answer", "")),
            contexts=contexts,
            metadata=data.get("metadata", {}),
        )


@dataclass
class InteractionResult:
    """Evaluation result for a single interaction."""

    interaction: Interaction
    context_precision: float | None = None
    context_relevancy: float | None = None
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    overall_score: float | None = None
    has_hallucination: bool = False

    @property
    def retrieval_score(self) -> float | None:
        """Calculate retrieval component score."""
        scores = [
            s for s in [self.context_precision, self.context_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else None

    @property
    def generation_score(self) -> float | None:
        """Calculate generation component score."""
        scores = [
            s for s in [self.faithfulness, self.answer_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else None


@dataclass
class EvaluationConfig:
    """Configuration for evaluation thresholds."""

    # Diagnostic thresholds
    faithfulness_threshold: float = 0.7
    context_precision_threshold: float = 0.7
    context_relevancy_threshold: float = 0.7
    answer_relevancy_threshold: float = 0.7
    hallucination_rate_threshold: float = 0.1

    # Quality level thresholds
    excellent_threshold: float = 0.9
    good_threshold: float = 0.75
    acceptable_threshold: float = 0.6
    poor_threshold: float = 0.4

    # Scoring weights
    retrieval_weight: float = 0.35
    generation_weight: float = 0.65


@dataclass
class DiagnosedIssue:
    """A diagnosed issue with root cause analysis."""

    component: str  # "retriever" or "generator"
    symptom: str
    probable_causes: list[str]
    severity: Severity
    metric_name: str
    metric_value: float
    threshold: float


@dataclass
class Recommendation:
    """An actionable recommendation."""

    component: str
    priority: str  # "critical", "high", "medium", "low"
    issue: str
    suggestion: str
    parameter_adjustments: dict[str, Any] | None = None


@dataclass
class EvaluationResult:
    """Aggregated metrics for an evaluation."""

    # Averages
    avg_context_precision: float | None = None
    avg_context_relevancy: float | None = None
    avg_faithfulness: float | None = None
    avg_answer_relevancy: float | None = None

    # Hallucination stats
    hallucination_rate: float | None = None
    total_hallucinations: int = 0

    # Score distribution
    score_distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class EvaluationResults:
    """Complete evaluation results."""

    # Identification
    evaluation_id: str
    evaluation_date: datetime

    # Summary scores
    overall_score: float
    retrieval_score: float
    generation_score: float
    quality_level: QualityLevel

    # Counts
    interaction_count: int

    # Detailed metrics
    metrics: EvaluationResult

    # Per-interaction results
    interaction_results: list[InteractionResult]

    # Diagnostics
    issues: list[DiagnosedIssue]
    recommendations: list[Recommendation]

    def to_dict(self) -> dict[str, Any]:
        """Convert results to a dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "evaluation_date": self.evaluation_date.isoformat(),
            "overall_score": self.overall_score,
            "retrieval_score": self.retrieval_score,
            "generation_score": self.generation_score,
            "quality_level": self.quality_level.value,
            "interaction_count": self.interaction_count,
            "metrics": {
                "avg_context_precision": self.metrics.avg_context_precision,
                "avg_context_relevancy": self.metrics.avg_context_relevancy,
                "avg_faithfulness": self.metrics.avg_faithfulness,
                "avg_answer_relevancy": self.metrics.avg_answer_relevancy,
                "hallucination_rate": self.metrics.hallucination_rate,
                "total_hallucinations": self.metrics.total_hallucinations,
                "score_distribution": self.metrics.score_distribution,
            },
            "issues": [
                {
                    "component": issue.component,
                    "symptom": issue.symptom,
                    "severity": issue.severity.value,
                    "metric_name": issue.metric_name,
                    "metric_value": issue.metric_value,
                }
                for issue in self.issues
            ],
            "recommendations": [
                {
                    "component": rec.component,
                    "priority": rec.priority,
                    "issue": rec.issue,
                    "suggestion": rec.suggestion,
                    "parameter_adjustments": rec.parameter_adjustments,
                }
                for rec in self.recommendations
            ],
        }
