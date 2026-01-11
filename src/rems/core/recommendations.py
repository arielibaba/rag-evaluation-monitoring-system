"""Lightweight recommendation engine for core evaluation."""

from typing import Any

from rems.core.schemas import DiagnosedIssue, Recommendation

# Mapping from diagnosed issues to specific recommendations
RECOMMENDATION_RULES: dict[str, dict[str, Any]] = {
    # Retriever recommendations
    "low_context_precision": {
        "suggestion": (
            "Reduce the number of retrieved documents (top_k) "
            "or increase the similarity threshold"
        ),
        "parameter_adjustments": {
            "retriever.top_k": {"action": "decrease", "suggested_value": 3},
            "retriever.similarity_threshold": {
                "action": "increase",
                "suggested_value": 0.75,
            },
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
        "suggestion": (
            "Improve the prompt to guide towards more direct and relevant answers"
        ),
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


def generate_recommendations(issues: list[DiagnosedIssue]) -> list[Recommendation]:
    """
    Generate recommendations based on diagnosed issues.

    Args:
        issues: List of diagnosed issues from the diagnostic engine

    Returns:
        List of actionable recommendations
    """
    if not issues:
        return []

    recommendations: list[Recommendation] = []

    for issue in issues:
        recommendation = _issue_to_recommendation(issue)
        recommendations.append(recommendation)

    return recommendations


def _issue_to_recommendation(issue: DiagnosedIssue) -> Recommendation:
    """Convert a diagnosed issue to a recommendation."""
    # Get rule-based recommendation
    rule_key = _get_rule_key(issue.metric_name, issue.threshold, issue.metric_value)
    rule = RECOMMENDATION_RULES.get(rule_key, {})

    # Build suggestion text
    suggestion = rule.get(
        "suggestion",
        f"Investigate the {issue.metric_name} issue",
    )

    # Add probable causes to the issue description
    causes_text = "\n".join(f"  - {cause}" for cause in issue.probable_causes[:3])
    full_issue = f"{issue.symptom}\n\nProbable causes:\n{causes_text}"

    return Recommendation(
        component=issue.component,
        issue=full_issue,
        suggestion=suggestion,
        priority=issue.severity.value,
        parameter_adjustments=rule.get("parameter_adjustments"),
    )


def _get_rule_key(metric_name: str, threshold: float, value: float) -> str:
    """Determine the rule key based on metric and comparison."""
    if metric_name == "hallucination_rate":
        return "high_hallucination_rate" if value > threshold else ""
    else:
        return f"low_{metric_name}" if value < threshold else ""
