"""Recommendation Engine - Generates improvement recommendations."""

from pathlib import Path

import structlog
import yaml

from rems.config import settings
from rems.diagnostic.engine import DiagnosedIssue, DiagnosticEngine
from rems.models import Recommendation, get_session
from rems.schemas import EvaluationSummary, RecommendationSchema

logger = structlog.get_logger()


# Mapping from diagnosed issues to specific recommendations
RECOMMENDATION_RULES: dict[str, dict] = {
    # Retriever recommendations
    "low_context_precision": {
        "suggestion": (
            "Reduce the number of retrieved documents (top_k) "
            "or increase the similarity threshold"
        ),
        "parameter_adjustments": {
            "retriever.top_k": {"action": "decrease", "suggested_value": 3},
            "retriever.similarity_threshold": {"action": "increase", "suggested_value": 0.75},
        },
    },
    "low_context_relevancy": {
        "suggestion": "Optimize document chunking or improve embeddings quality",
        "parameter_adjustments": {
            "indexing.chunk_size": {"action": "adjust", "suggested_value": 512},
            "indexing.chunk_overlap": {"action": "adjust", "suggested_value": 50},
        },
    },
    # Generator recommendations
    "low_faithfulness": {
        "suggestion": (
            "Add explicit instructions in the prompt to cite sources "
            "and not invent information"
        ),
        "parameter_adjustments": {
            "generator.temperature": {"action": "decrease", "suggested_value": 0.3},
            "generator.system_prompt": {
                "action": "append",
                "suggested_value": (
                    "IMPORTANT: Base your answer ONLY on the provided documents. "
                    "If the information is not in the documents, say so explicitly. "
                    "Never invent information."
                ),
            },
        },
    },
    "low_answer_relevancy": {
        "suggestion": "Improve the prompt to guide towards more direct and relevant answers",
        "parameter_adjustments": {
            "generator.system_prompt": {
                "action": "append",
                "suggested_value": (
                    "Answer concisely and directly to the question asked. "
                    "Avoid digressions."
                ),
            },
        },
    },
    "high_hallucination_rate": {
        "suggestion": "Reduce LLM temperature and strengthen prompt guardrails",
        "parameter_adjustments": {
            "generator.temperature": {"action": "decrease", "suggested_value": 0.2},
            "generator.max_tokens": {"action": "decrease", "suggested_value": 1024},
            "generator.system_prompt": {
                "action": "append",
                "suggested_value": (
                    "ABSOLUTE RULE: You must NEVER invent facts, dates, or references. "
                    "If you don't have the exact information in the context, "
                    "respond 'I don't have this information in the provided documents.'"
                ),
            },
        },
    },
}


class RecommendationEngine:
    """Generates recommendations based on diagnostic results."""

    def __init__(self, diagnostic_engine: DiagnosticEngine | None = None):
        """
        Initialize the recommendation engine.

        Args:
            diagnostic_engine: DiagnosticEngine instance (creates one if None)
        """
        self.diagnostic_engine = diagnostic_engine or DiagnosticEngine()

    def generate_recommendations(
        self,
        summary: EvaluationSummary,
        store_in_db: bool = True,
    ) -> list[RecommendationSchema]:
        """
        Generate recommendations based on evaluation summary.

        Args:
            summary: Evaluation summary with metrics
            store_in_db: Whether to store recommendations in database

        Returns:
            List of recommendations
        """
        # Run diagnostic
        issues = self.diagnostic_engine.diagnose(summary)

        if not issues:
            logger.info("No issues found, no recommendations to generate")
            return []

        # Generate recommendations for each issue
        recommendations: list[RecommendationSchema] = []

        for issue in issues:
            recommendation = self._issue_to_recommendation(issue)
            recommendations.append(recommendation)

        # Store in database if requested
        if store_in_db:
            self._store_recommendations(summary.evaluation_id, recommendations)

        logger.info(
            "Generated recommendations",
            count=len(recommendations),
            critical_count=len([r for r in recommendations if r.priority == "critical"]),
        )

        return recommendations

    def _issue_to_recommendation(self, issue: DiagnosedIssue) -> RecommendationSchema:
        """Convert a diagnosed issue to a recommendation."""
        # Get rule-based recommendation
        rule_key = self._get_rule_key(issue.metric_name, issue.threshold, issue.metric_value)
        rule = RECOMMENDATION_RULES.get(rule_key, {})

        # Build suggestion text
        suggestion = rule.get("suggestion", f"Investigate the {issue.metric_name} issue")

        # Add probable causes to the issue description
        causes_text = "\n".join(f"  - {cause}" for cause in issue.probable_causes[:3])
        full_issue = f"{issue.symptom}\n\nProbable causes:\n{causes_text}"

        return RecommendationSchema(
            component=issue.component.value,
            issue=full_issue,
            suggestion=suggestion,
            priority=issue.severity.value,
            parameter_adjustments=rule.get("parameter_adjustments"),
        )

    def _get_rule_key(
        self, metric_name: str, threshold: float, value: float
    ) -> str:
        """Determine the rule key based on metric and comparison."""
        if metric_name == "hallucination_rate":
            return "high_hallucination_rate" if value > threshold else ""
        else:
            return f"low_{metric_name}" if value < threshold else ""

    def _store_recommendations(
        self,
        evaluation_id: str,
        recommendations: list[RecommendationSchema],
    ) -> None:
        """Store recommendations in the database."""
        with get_session() as session:
            for rec in recommendations:
                db_rec = Recommendation(
                    evaluation_id=evaluation_id,
                    component=rec.component,
                    issue=rec.issue,
                    suggestion=rec.suggestion,
                    priority=rec.priority,
                    parameter_adjustments=rec.parameter_adjustments,
                )
                session.add(db_rec)

    def export_to_yaml(
        self,
        summary: EvaluationSummary,
        recommendations: list[RecommendationSchema],
        output_path: Path | None = None,
    ) -> Path:
        """
        Export recommendations to a YAML file.

        Args:
            summary: Evaluation summary
            recommendations: List of recommendations
            output_path: Output file path (uses settings default if None)

        Returns:
            Path to the generated YAML file
        """
        output_path = output_path or settings.recommendations_file

        # Build YAML structure
        data = {
            "evaluation_id": summary.evaluation_id,
            "evaluation_date": summary.evaluation_date.isoformat(),
            "overall_score": round(summary.overall_score, 3),
            "quality_level": summary.quality_level,
            "scores": {
                "retrieval": round(summary.retrieval_score, 3),
                "generation": round(summary.generation_score, 3),
            },
            "metrics": {
                "avg_context_precision": self._safe_round(summary.metrics.avg_context_precision),
                "avg_context_relevancy": self._safe_round(summary.metrics.avg_context_relevancy),
                "avg_faithfulness": self._safe_round(summary.metrics.avg_faithfulness),
                "avg_answer_relevancy": self._safe_round(summary.metrics.avg_answer_relevancy),
                "hallucination_rate": self._safe_round(summary.metrics.hallucination_rate),
                "total_hallucinations": summary.metrics.total_hallucinations,
            },
            "recommendations": [
                {
                    "component": rec.component,
                    "priority": rec.priority,
                    "issue": rec.issue,
                    "suggestion": rec.suggestion,
                    "parameter_adjustments": rec.parameter_adjustments,
                }
                for rec in recommendations
            ],
        }

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML
        with output_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        logger.info("Exported recommendations to YAML", path=str(output_path))
        return output_path

    def _safe_round(self, value: float | None, decimals: int = 3) -> float | None:
        """Safely round a value that might be None."""
        return round(value, decimals) if value is not None else None
