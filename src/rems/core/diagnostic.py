"""Lightweight diagnostic engine for core evaluation."""

from rems.core.schemas import (
    DiagnosedIssue,
    EvaluationConfig,
    EvaluationResult,
    Severity,
)

# Diagnostic rules: maps symptoms to probable causes
DIAGNOSTIC_RULES: dict[str, dict[str, str | list[str]]] = {
    "low_context_precision": {
        "component": "retriever",
        "causes": [
            "Similarity threshold too low (irrelevant documents included)",
            "Top-K too high (too many documents retrieved)",
            "Embedding quality insufficient for the domain",
        ],
    },
    "low_context_relevancy": {
        "component": "retriever",
        "causes": [
            "Query poorly formulated or too vague",
            "Chunking strategy inadequate (chunks too large or too small)",
            "Embeddings not optimized for domain vocabulary",
        ],
    },
    "low_faithfulness": {
        "component": "generator",
        "causes": [
            "LLM temperature too high (generation too creative)",
            "System prompt not constraining enough",
            "Insufficient context provided (top-K too low)",
            "Missing explicit instruction not to invent information",
        ],
    },
    "low_answer_relevancy": {
        "component": "generator",
        "causes": [
            "Prompt not guiding towards direct answers",
            "LLM too verbose or off-topic",
            "Poor understanding of the question by the LLM",
        ],
    },
    "high_hallucination_rate": {
        "component": "generator",
        "causes": [
            "Missing guardrails in system prompt",
            "LLM temperature too high",
            "Insufficient context to answer (retriever failing)",
            "LLM not well-suited for the domain",
        ],
    },
}


def diagnose(
    metrics: EvaluationResult,
    config: EvaluationConfig | None = None,
) -> list[DiagnosedIssue]:
    """
    Analyze evaluation metrics and diagnose issues.

    Args:
        metrics: Aggregated evaluation metrics
        config: Evaluation configuration with thresholds

    Returns:
        List of diagnosed issues with root cause analysis
    """
    config = config or EvaluationConfig()
    issues: list[DiagnosedIssue] = []

    # Check context precision
    if metrics.avg_context_precision is not None:
        if metrics.avg_context_precision < config.context_precision_threshold:
            issues.append(_create_issue(
                rule_key="low_context_precision",
                metric_name="context_precision",
                metric_value=metrics.avg_context_precision,
                threshold=config.context_precision_threshold,
            ))

    # Check context relevancy
    if metrics.avg_context_relevancy is not None:
        if metrics.avg_context_relevancy < config.context_relevancy_threshold:
            issues.append(_create_issue(
                rule_key="low_context_relevancy",
                metric_name="context_relevancy",
                metric_value=metrics.avg_context_relevancy,
                threshold=config.context_relevancy_threshold,
            ))

    # Check faithfulness
    if metrics.avg_faithfulness is not None:
        if metrics.avg_faithfulness < config.faithfulness_threshold:
            issues.append(_create_issue(
                rule_key="low_faithfulness",
                metric_name="faithfulness",
                metric_value=metrics.avg_faithfulness,
                threshold=config.faithfulness_threshold,
            ))

    # Check answer relevancy
    if metrics.avg_answer_relevancy is not None:
        if metrics.avg_answer_relevancy < config.answer_relevancy_threshold:
            issues.append(_create_issue(
                rule_key="low_answer_relevancy",
                metric_name="answer_relevancy",
                metric_value=metrics.avg_answer_relevancy,
                threshold=config.answer_relevancy_threshold,
            ))

    # Check hallucination rate
    if metrics.hallucination_rate is not None:
        if metrics.hallucination_rate > config.hallucination_rate_threshold:
            issues.append(_create_issue(
                rule_key="high_hallucination_rate",
                metric_name="hallucination_rate",
                metric_value=metrics.hallucination_rate,
                threshold=config.hallucination_rate_threshold,
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

    return issues


def _create_issue(
    rule_key: str,
    metric_name: str,
    metric_value: float,
    threshold: float,
    is_upper_bound: bool = False,
) -> DiagnosedIssue:
    """Create a diagnosed issue from a rule."""
    rule = DIAGNOSTIC_RULES[rule_key]

    # Calculate severity based on deviation from threshold
    if is_upper_bound:
        if threshold > 0:
            deviation = (metric_value - threshold) / threshold
        else:
            deviation = metric_value
    else:
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
        component=str(rule["component"]),
        symptom=symptom,
        probable_causes=[str(c) for c in rule["causes"]],
        severity=severity,
        metric_name=metric_name,
        metric_value=metric_value,
        threshold=threshold,
    )
