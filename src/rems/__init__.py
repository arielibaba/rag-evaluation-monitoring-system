"""
REMS - RAG Evaluation & Monitoring System.

A toolkit for evaluating and monitoring RAG chatbot performance.

Quick Start (Core Library):
    from rems import RAGEvaluator, Interaction

    evaluator = RAGEvaluator()
    results = evaluator.evaluate([
        Interaction(
            query="What is the return policy?",
            response="Items can be returned within 30 days...",
            contexts=["Section 3.1 - Return Policy..."]
        )
    ])

    print(f"Overall score: {results.overall_score:.1%}")
    print(f"Quality level: {results.quality_level.value}")
    print(f"Recommendations: {len(results.recommendations)}")

Full Application:
    Install with: pip install rems[app]
    Then use the CLI: `rems web` or `rems evaluate --file interactions.json`
"""

__version__ = "0.1.0"

# Re-export core API for convenience
from rems.core import (
    DiagnosedIssue,
    EvaluationConfig,
    EvaluationResult,
    EvaluationResults,
    Interaction,
    InteractionResult,
    RAGEvaluator,
    Recommendation,
    Severity,
)

__all__ = [
    # Version
    "__version__",
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
