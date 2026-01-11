"""
REMS Core - Lightweight RAG Evaluation Library.

A simple, dependency-light library for evaluating RAG systems.
No database, no web interface - just evaluation.

Usage:
    from rems.core import RAGEvaluator, Interaction

    # Create interactions to evaluate
    interactions = [
        Interaction(
            query="What is the return policy?",
            response="Items can be returned within 30 days...",
            contexts=["Section 3.1 - Return Policy..."]
        )
    ]

    # Evaluate
    evaluator = RAGEvaluator()
    results = evaluator.evaluate(interactions)

    print(f"Overall score: {results.overall_score:.1%}")
    print(f"Recommendations: {len(results.recommendations)}")
"""

from rems.core.evaluator import RAGEvaluator
from rems.core.schemas import (
    DiagnosedIssue,
    EvaluationConfig,
    EvaluationResult,
    EvaluationResults,
    Interaction,
    InteractionResult,
    Recommendation,
    Severity,
)

__all__ = [
    # Main class
    "RAGEvaluator",
    # Data classes
    "Interaction",
    "InteractionResult",
    "EvaluationResult",
    "EvaluationResults",
    "EvaluationConfig",
    "Recommendation",
    "DiagnosedIssue",
    "Severity",
]
