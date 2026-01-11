"""Diagnostic Engine - Analyzes evaluation results to identify root causes."""

from dataclasses import dataclass
from enum import Enum

import structlog

from rems.config import settings
from rems.schemas import EvaluationSummary

logger = structlog.get_logger()


class Component(str, Enum):
    """RAG pipeline components."""

    RETRIEVER = "retriever"
    GENERATOR = "generator"
    INDEXING = "indexing"


class Severity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DiagnosedIssue:
    """A diagnosed issue with its root cause analysis."""

    component: Component
    symptom: str
    probable_causes: list[str]
    severity: Severity
    metric_name: str
    metric_value: float
    threshold: float


# Diagnostic rules: maps symptoms to probable causes
DIAGNOSTIC_RULES = {
    "low_context_precision": {
        "component": Component.RETRIEVER,
        "causes": [
            "Similarity threshold too low (irrelevant documents included)",
            "Top-K too high (too many documents retrieved)",
            "Embedding quality insufficient for the domain",
        ],
    },
    "low_context_relevancy": {
        "component": Component.RETRIEVER,
        "causes": [
            "Query poorly formulated or too vague",
            "Chunking strategy inadequate (chunks too large or too small)",
            "Embeddings not optimized for domain vocabulary",
        ],
    },
    "low_faithfulness": {
        "component": Component.GENERATOR,
        "causes": [
            "LLM temperature too high (generation too creative)",
            "System prompt not constraining enough",
            "Insufficient context provided (top-K too low)",
            "Missing explicit instruction not to invent information",
        ],
    },
    "low_answer_relevancy": {
        "component": Component.GENERATOR,
        "causes": [
            "Prompt not guiding towards direct answers",
            "LLM too verbose or off-topic",
            "Poor understanding of the question by the LLM",
        ],
    },
    "high_hallucination_rate": {
        "component": Component.GENERATOR,
        "causes": [
            "Missing guardrails in system prompt",
            "LLM temperature too high",
            "Insufficient context to answer (retriever failing)",
            "LLM not well-suited for the domain",
        ],
    },
}


class DiagnosticEngine:
    """Analyzes evaluation results to identify root causes of issues."""

    def __init__(
        self,
        precision_threshold: float | None = None,
        relevancy_threshold: float | None = None,
        faithfulness_threshold: float | None = None,
        answer_relevancy_threshold: float | None = None,
        hallucination_rate_threshold: float | None = None,
    ):
        """
        Initialize the diagnostic engine with thresholds.

        Args:
            precision_threshold: Minimum acceptable context precision
            relevancy_threshold: Minimum acceptable context relevancy
            faithfulness_threshold: Minimum acceptable faithfulness
            answer_relevancy_threshold: Minimum acceptable answer relevancy
            hallucination_rate_threshold: Maximum acceptable hallucination rate

        If thresholds are not provided, they are loaded from settings.
        """
        self.thresholds = {
            "context_precision": precision_threshold or settings.diag_context_precision,
            "context_relevancy": relevancy_threshold or settings.diag_context_relevancy,
            "faithfulness": faithfulness_threshold or settings.diag_faithfulness,
            "answer_relevancy": answer_relevancy_threshold or settings.diag_answer_relevancy,
            "hallucination_rate": hallucination_rate_threshold or settings.diag_hallucination_rate,
        }

    def diagnose(self, summary: EvaluationSummary) -> list[DiagnosedIssue]:
        """
        Analyze evaluation summary and diagnose issues.

        Args:
            summary: Evaluation summary with metrics

        Returns:
            List of diagnosed issues with root cause analysis
        """
        issues: list[DiagnosedIssue] = []
        metrics = summary.metrics

        # Check context precision
        if metrics.avg_context_precision is not None:
            if metrics.avg_context_precision < self.thresholds["context_precision"]:
                issues.append(self._create_issue(
                    rule_key="low_context_precision",
                    metric_name="context_precision",
                    metric_value=metrics.avg_context_precision,
                    threshold=self.thresholds["context_precision"],
                ))

        # Check context relevancy
        if metrics.avg_context_relevancy is not None:
            if metrics.avg_context_relevancy < self.thresholds["context_relevancy"]:
                issues.append(self._create_issue(
                    rule_key="low_context_relevancy",
                    metric_name="context_relevancy",
                    metric_value=metrics.avg_context_relevancy,
                    threshold=self.thresholds["context_relevancy"],
                ))

        # Check faithfulness
        if metrics.avg_faithfulness is not None:
            if metrics.avg_faithfulness < self.thresholds["faithfulness"]:
                issues.append(self._create_issue(
                    rule_key="low_faithfulness",
                    metric_name="faithfulness",
                    metric_value=metrics.avg_faithfulness,
                    threshold=self.thresholds["faithfulness"],
                ))

        # Check answer relevancy
        if metrics.avg_answer_relevancy is not None:
            if metrics.avg_answer_relevancy < self.thresholds["answer_relevancy"]:
                issues.append(self._create_issue(
                    rule_key="low_answer_relevancy",
                    metric_name="answer_relevancy",
                    metric_value=metrics.avg_answer_relevancy,
                    threshold=self.thresholds["answer_relevancy"],
                ))

        # Check hallucination rate
        if metrics.hallucination_rate is not None:
            if metrics.hallucination_rate > self.thresholds["hallucination_rate"]:
                issues.append(self._create_issue(
                    rule_key="high_hallucination_rate",
                    metric_name="hallucination_rate",
                    metric_value=metrics.hallucination_rate,
                    threshold=self.thresholds["hallucination_rate"],
                    is_upper_bound=True,
                ))

        # Sort by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        issues.sort(key=lambda x: severity_order[x.severity])

        logger.info(
            "Diagnostic complete",
            issues_found=len(issues),
            critical_count=len([i for i in issues if i.severity == Severity.CRITICAL]),
            high_count=len([i for i in issues if i.severity == Severity.HIGH]),
        )

        return issues

    def _create_issue(
        self,
        rule_key: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        is_upper_bound: bool = False,
    ) -> DiagnosedIssue:
        """Create a diagnosed issue from a rule."""
        rule = DIAGNOSTIC_RULES[rule_key]

        # Calculate severity based on how far from threshold
        if is_upper_bound:
            # For metrics where exceeding threshold is bad (e.g., hallucination rate)
            deviation = (metric_value - threshold) / threshold if threshold > 0 else metric_value
        else:
            # For metrics where being below threshold is bad
            if threshold > 0:
                deviation = (threshold - metric_value) / threshold
            else:
                deviation = 1 - metric_value

        if deviation > 0.5:
            severity = Severity.CRITICAL
        elif deviation > 0.25:
            severity = Severity.HIGH
        elif deviation > 0.1:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        # Create symptom description
        if is_upper_bound:
            symptom = f"{metric_name} too high: {metric_value:.2%} (threshold: {threshold:.2%})"
        else:
            symptom = f"{metric_name} too low: {metric_value:.2%} (threshold: {threshold:.2%})"

        return DiagnosedIssue(
            component=rule["component"],
            symptom=symptom,
            probable_causes=rule["causes"],
            severity=severity,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
        )

    def get_component_health(self, summary: EvaluationSummary) -> dict[str, str]:
        """
        Get health status for each component.

        Returns:
            Dictionary mapping component name to health status
        """
        issues = self.diagnose(summary)

        # Count issues per component
        component_issues: dict[Component, list[DiagnosedIssue]] = {}
        for issue in issues:
            if issue.component not in component_issues:
                component_issues[issue.component] = []
            component_issues[issue.component].append(issue)

        # Determine health status
        health: dict[str, str] = {}

        for component in Component:
            comp_issues = component_issues.get(component, [])
            if not comp_issues:
                health[component.value] = "healthy"
            elif any(i.severity == Severity.CRITICAL for i in comp_issues):
                health[component.value] = "critical"
            elif any(i.severity == Severity.HIGH for i in comp_issues):
                health[component.value] = "degraded"
            else:
                health[component.value] = "warning"

        return health
