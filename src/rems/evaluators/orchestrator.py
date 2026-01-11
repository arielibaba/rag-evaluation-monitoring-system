"""Evaluation Orchestrator - Coordinates all evaluators and aggregates results."""

from datetime import UTC, datetime

import structlog

from rems.config import settings
from rems.evaluators.generator_evaluator import GeneratorEvaluator
from rems.evaluators.retrieval_evaluator import RetrievalEvaluator
from rems.models import Evaluation, EvaluationResult, get_session
from rems.schemas import (
    EvaluationMetrics,
    EvaluationResultSchema,
    EvaluationSummary,
    InteractionSchema,
)

logger = structlog.get_logger()

# Component weights for overall score calculation
RETRIEVAL_WEIGHT = 0.35
GENERATION_WEIGHT = 0.65


class EvaluationOrchestrator:
    """Orchestrates the evaluation process across all evaluators."""

    def __init__(self, llm=None, embeddings=None):
        """
        Initialize the orchestrator with evaluators.

        Args:
            llm: LangChain LLM instance for evaluation
            embeddings: LangChain embeddings instance
        """
        self.retrieval_evaluator = RetrievalEvaluator(llm=llm, embeddings=embeddings)
        self.generator_evaluator = GeneratorEvaluator(llm=llm, embeddings=embeddings)

    def evaluate(
        self,
        interactions: list[InteractionSchema],
        name: str | None = None,
        description: str | None = None,
        store_results: bool = True,
    ) -> EvaluationSummary:
        """
        Run a complete evaluation on a list of interactions.

        Args:
            interactions: List of interactions to evaluate
            name: Optional name for this evaluation run
            description: Optional description
            store_results: Whether to store results in database

        Returns:
            EvaluationSummary with all metrics and recommendations
        """
        logger.info(
            "Starting evaluation",
            interaction_count=len(interactions),
            name=name,
        )

        # Run evaluators
        retrieval_results = self.retrieval_evaluator.evaluate(interactions)
        generator_results = self.generator_evaluator.evaluate(interactions)

        # Merge results
        merged_results = self._merge_results(retrieval_results, generator_results)

        # Calculate aggregate metrics
        metrics = self._calculate_metrics(merged_results)

        # Calculate component and overall scores
        retrieval_score = self._calculate_retrieval_score(metrics)
        generation_score = self._calculate_generation_score(metrics)
        overall_score = (
            retrieval_score * RETRIEVAL_WEIGHT +
            generation_score * GENERATION_WEIGHT
        )

        # Determine quality level
        quality_level = self._get_quality_level(overall_score)

        # Store results if requested
        evaluation_id = ""
        if store_results:
            evaluation_id = self._store_results(
                interactions=interactions,
                results=merged_results,
                metrics=metrics,
                overall_score=overall_score,
                retrieval_score=retrieval_score,
                generation_score=generation_score,
                name=name,
                description=description,
            )
        else:
            evaluation_id = f"eval_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        # Create summary (recommendations will be added by RecommendationEngine)
        summary = EvaluationSummary(
            evaluation_id=evaluation_id,
            evaluation_date=datetime.now(UTC),
            interaction_count=len(interactions),
            overall_score=overall_score,
            retrieval_score=retrieval_score,
            generation_score=generation_score,
            metrics=metrics,
            recommendations=[],  # Filled by RecommendationEngine
            quality_level=quality_level,
        )

        logger.info(
            "Evaluation complete",
            evaluation_id=evaluation_id,
            overall_score=overall_score,
            quality_level=quality_level,
        )

        return summary

    def _merge_results(
        self,
        retrieval_results: dict[str, EvaluationResultSchema],
        generator_results: dict[str, EvaluationResultSchema],
    ) -> dict[str, EvaluationResultSchema]:
        """Merge results from all evaluators."""
        merged: dict[str, EvaluationResultSchema] = {}

        all_ids = set(retrieval_results.keys()) | set(generator_results.keys())

        for interaction_id in all_ids:
            retrieval = retrieval_results.get(interaction_id)
            generator = generator_results.get(interaction_id)

            # Start with generator results if available (has more fields)
            if generator:
                result = generator.model_copy()
            else:
                result = EvaluationResultSchema(interaction_id=interaction_id)

            # Add retrieval metrics
            if retrieval:
                result.context_precision = retrieval.context_precision
                result.context_relevancy = retrieval.context_relevancy

            # Recalculate overall score with all metrics
            scores = [
                s for s in [
                    result.faithfulness,
                    result.answer_relevancy,
                    result.context_precision,
                    result.context_relevancy,
                ] if s is not None
            ]
            if scores:
                result.overall_score = sum(scores) / len(scores)

            merged[interaction_id] = result

        return merged

    def _calculate_metrics(
        self, results: dict[str, EvaluationResultSchema]
    ) -> EvaluationMetrics:
        """Calculate aggregate metrics from individual results."""
        if not results:
            return EvaluationMetrics()

        values = list(results.values())

        # Calculate averages
        ctx_prec = [r.context_precision for r in values if r.context_precision is not None]
        ctx_rel = [r.context_relevancy for r in values if r.context_relevancy is not None]
        faith = [r.faithfulness for r in values if r.faithfulness is not None]
        ans_rel = [r.answer_relevancy for r in values if r.answer_relevancy is not None]

        # Hallucination stats
        hallucinations = [r for r in values if r.has_hallucination]
        total_hallucinations = len(hallucinations)
        hallucination_rate = total_hallucinations / len(values) if values else 0

        # Score distribution
        scores = [r.overall_score for r in values if r.overall_score is not None]
        t_exc = settings.threshold_excellent
        t_good = settings.threshold_good
        t_acc = settings.threshold_acceptable
        t_poor = settings.threshold_poor
        distribution = {
            "excellent": len([s for s in scores if s >= t_exc]),
            "good": len([s for s in scores if t_good <= s < t_exc]),
            "acceptable": len([s for s in scores if t_acc <= s < t_good]),
            "poor": len([s for s in scores if t_poor <= s < t_acc]),
            "critical": len([s for s in scores if s < t_poor]),
        }

        return EvaluationMetrics(
            avg_context_precision=sum(ctx_prec) / len(ctx_prec) if ctx_prec else None,
            avg_context_relevancy=sum(ctx_rel) / len(ctx_rel) if ctx_rel else None,
            avg_faithfulness=sum(faith) / len(faith) if faith else None,
            avg_answer_relevancy=sum(ans_rel) / len(ans_rel) if ans_rel else None,
            hallucination_rate=hallucination_rate,
            total_hallucinations=total_hallucinations,
            score_distribution=distribution,
        )

    def _calculate_retrieval_score(self, metrics: EvaluationMetrics) -> float:
        """Calculate retrieval component score."""
        scores = [
            s for s in [metrics.avg_context_precision, metrics.avg_context_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_generation_score(self, metrics: EvaluationMetrics) -> float:
        """Calculate generation component score."""
        scores = [
            s for s in [metrics.avg_faithfulness, metrics.avg_answer_relevancy]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _get_quality_level(self, score: float) -> str:
        """Determine quality level from overall score."""
        if score >= settings.threshold_excellent:
            return "excellent"
        elif score >= settings.threshold_good:
            return "good"
        elif score >= settings.threshold_acceptable:
            return "acceptable"
        elif score >= settings.threshold_poor:
            return "poor"
        else:
            return "critical"

    def _store_results(
        self,
        interactions: list[InteractionSchema],
        results: dict[str, EvaluationResultSchema],
        metrics: EvaluationMetrics,
        overall_score: float,
        retrieval_score: float,
        generation_score: float,
        name: str | None,
        description: str | None,
    ) -> str:
        """Store evaluation results in the database."""
        with get_session() as session:
            # Create evaluation record
            evaluation = Evaluation(
                name=name,
                description=description,
                interaction_count=len(interactions),
                overall_score=overall_score,
                retrieval_score=retrieval_score,
                generation_score=generation_score,
                metrics=metrics.model_dump(),
                completed_at=datetime.now(UTC),
            )
            session.add(evaluation)
            session.flush()

            # Store individual results
            for interaction_id, result in results.items():
                eval_result = EvaluationResult(
                    evaluation_id=evaluation.id,
                    interaction_id=interaction_id,
                    faithfulness=result.faithfulness,
                    answer_relevancy=result.answer_relevancy,
                    context_precision=result.context_precision,
                    context_relevancy=result.context_relevancy,
                    has_hallucination=result.has_hallucination,
                    hallucination_details=result.hallucination_details,
                    overall_score=result.overall_score,
                    details=result.details,
                )
                session.add(eval_result)

            return evaluation.id
