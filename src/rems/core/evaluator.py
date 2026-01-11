"""Main RAGEvaluator class - the simple API for evaluation."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from rems.core.diagnostic import diagnose
from rems.core.metrics import MetricsEvaluator
from rems.core.recommendations import generate_recommendations
from rems.core.schemas import (
    EvaluationConfig,
    EvaluationResult,
    EvaluationResults,
    Interaction,
    InteractionResult,
    QualityLevel,
)


class RAGEvaluator:
    """
    Simple API for evaluating RAG systems.

    Usage:
        from rems.core import RAGEvaluator, Interaction

        evaluator = RAGEvaluator()
        results = evaluator.evaluate([
            Interaction(
                query="What is X?",
                response="X is...",
                contexts=["Document about X..."]
            )
        ])

        print(f"Score: {results.overall_score:.1%}")
    """

    def __init__(
        self,
        llm: Any | None = None,
        embeddings: Any | None = None,
        config: EvaluationConfig | None = None,
    ):
        """
        Initialize the RAG evaluator.

        Args:
            llm: LangChain LLM instance for RAGAS evaluation.
                 If None, RAGAS will use its default.
            embeddings: LangChain embeddings instance.
                        If None, RAGAS will use its default.
            config: Evaluation configuration with thresholds.
        """
        self.config = config or EvaluationConfig()
        self._metrics_evaluator = MetricsEvaluator(
            llm=llm,
            embeddings=embeddings,
            config=self.config,
        )

    def evaluate(
        self,
        interactions: list[Interaction] | list[dict[str, Any]],
        evaluation_id: str | None = None,
    ) -> EvaluationResults:
        """
        Evaluate a list of RAG interactions.

        Args:
            interactions: List of Interaction objects or dicts with keys:
                         - query (or question): The user's query
                         - response (or answer): The RAG system's response
                         - contexts (or retrieved_contexts or retrieved_documents):
                           List of context strings or document dicts
            evaluation_id: Optional ID for this evaluation run

        Returns:
            EvaluationResults with scores, metrics, issues, and recommendations
        """
        # Convert dicts to Interaction objects if needed
        parsed_interactions = self._parse_interactions(interactions)

        if not parsed_interactions:
            raise ValueError("No interactions provided for evaluation")

        # Run RAGAS evaluation
        interaction_results = self._metrics_evaluator.evaluate_interactions(
            parsed_interactions
        )

        # Aggregate metrics
        metrics = self._aggregate_metrics(interaction_results)

        # Calculate scores
        retrieval_score = self._calculate_retrieval_score(metrics)
        generation_score = self._calculate_generation_score(metrics)
        overall_score = (
            self.config.retrieval_weight * retrieval_score
            + self.config.generation_weight * generation_score
        )

        # Determine quality level
        quality_level = self._get_quality_level(overall_score)

        # Run diagnostics
        issues = diagnose(metrics, self.config)

        # Generate recommendations
        recommendations = generate_recommendations(issues)

        return EvaluationResults(
            evaluation_id=evaluation_id or f"eval_{uuid4().hex[:12]}",
            evaluation_date=datetime.now(UTC),
            overall_score=overall_score,
            retrieval_score=retrieval_score,
            generation_score=generation_score,
            quality_level=quality_level,
            interaction_count=len(parsed_interactions),
            metrics=metrics,
            interaction_results=interaction_results,
            issues=issues,
            recommendations=recommendations,
        )

    def evaluate_single(
        self,
        query: str,
        response: str,
        contexts: list[str],
    ) -> InteractionResult:
        """
        Evaluate a single interaction.

        Args:
            query: The user's query
            response: The RAG system's response
            contexts: List of retrieved context strings

        Returns:
            InteractionResult with scores for this interaction
        """
        interaction = Interaction(query=query, response=response, contexts=contexts)
        results = self._metrics_evaluator.evaluate_interactions([interaction])
        return results[0] if results else InteractionResult(interaction=interaction)

    def _parse_interactions(
        self,
        interactions: list[Interaction] | list[dict[str, Any]],
    ) -> list[Interaction]:
        """Parse interactions from various input formats."""
        parsed: list[Interaction] = []

        for item in interactions:
            if isinstance(item, Interaction):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(Interaction.from_dict(item))
            else:
                raise TypeError(
                    f"Expected Interaction or dict, got {type(item).__name__}"
                )

        return parsed

    def _aggregate_metrics(
        self,
        results: list[InteractionResult],
    ) -> EvaluationResult:
        """Aggregate metrics from individual results."""
        if not results:
            return EvaluationResult()

        # Collect scores
        ctx_prec = [r.context_precision for r in results if r.context_precision]
        ctx_rel = [r.context_relevancy for r in results if r.context_relevancy]
        faith = [r.faithfulness for r in results if r.faithfulness]
        ans_rel = [r.answer_relevancy for r in results if r.answer_relevancy]

        # Hallucination stats
        hallucinations = [r for r in results if r.has_hallucination]
        total_hallucinations = len(hallucinations)
        hallucination_rate = total_hallucinations / len(results)

        # Score distribution
        scores = [r.overall_score for r in results if r.overall_score is not None]
        t_exc = self.config.excellent_threshold
        t_good = self.config.good_threshold
        t_acc = self.config.acceptable_threshold
        t_poor = self.config.poor_threshold

        distribution = {
            "excellent": len([s for s in scores if s >= t_exc]),
            "good": len([s for s in scores if t_good <= s < t_exc]),
            "acceptable": len([s for s in scores if t_acc <= s < t_good]),
            "poor": len([s for s in scores if t_poor <= s < t_acc]),
            "critical": len([s for s in scores if s < t_poor]),
        }

        return EvaluationResult(
            avg_context_precision=sum(ctx_prec) / len(ctx_prec) if ctx_prec else None,
            avg_context_relevancy=sum(ctx_rel) / len(ctx_rel) if ctx_rel else None,
            avg_faithfulness=sum(faith) / len(faith) if faith else None,
            avg_answer_relevancy=sum(ans_rel) / len(ans_rel) if ans_rel else None,
            hallucination_rate=hallucination_rate,
            total_hallucinations=total_hallucinations,
            score_distribution=distribution,
        )

    def _calculate_retrieval_score(self, metrics: EvaluationResult) -> float:
        """Calculate retrieval component score."""
        scores = [
            s for s in [metrics.avg_context_precision, metrics.avg_context_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_generation_score(self, metrics: EvaluationResult) -> float:
        """Calculate generation component score."""
        scores = [
            s for s in [metrics.avg_faithfulness, metrics.avg_answer_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _get_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        if score >= self.config.excellent_threshold:
            return QualityLevel.EXCELLENT
        elif score >= self.config.good_threshold:
            return QualityLevel.GOOD
        elif score >= self.config.acceptable_threshold:
            return QualityLevel.ACCEPTABLE
        elif score >= self.config.poor_threshold:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
