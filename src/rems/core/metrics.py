"""RAGAS metrics wrapper for core evaluation."""

from typing import Any

from datasets import Dataset  # type: ignore[import-untyped]

from rems.core.schemas import EvaluationConfig, Interaction, InteractionResult


def _safe_import_ragas() -> dict[str, Any]:
    """Safely import RAGAS metrics."""
    try:
        from ragas import evaluate  # type: ignore[import-not-found]
        from ragas.metrics._answer_relevance import (
            ResponseRelevancy,  # type: ignore[import-not-found]
        )
        from ragas.metrics._context_precision import (
            ContextPrecision,  # type: ignore[import-not-found]
        )
        from ragas.metrics._faithfulness import Faithfulness  # type: ignore[import-not-found]

        return {
            "evaluate": evaluate,
            "ContextPrecision": ContextPrecision,
            "Faithfulness": Faithfulness,
            "ResponseRelevancy": ResponseRelevancy,
        }
    except ImportError as e:
        raise ImportError(
            "RAGAS is required for evaluation. Install with: pip install ragas"
        ) from e


class MetricsEvaluator:
    """Evaluates RAG interactions using RAGAS metrics."""

    def __init__(
        self,
        llm: Any | None = None,
        embeddings: Any | None = None,
        config: EvaluationConfig | None = None,
    ):
        """
        Initialize the metrics evaluator.

        Args:
            llm: LangChain LLM instance for evaluation
            embeddings: LangChain embeddings instance
            config: Evaluation configuration
        """
        self.llm = llm
        self.embeddings = embeddings
        self.config = config or EvaluationConfig()
        self._ragas = _safe_import_ragas()

    def evaluate_interactions(
        self,
        interactions: list[Interaction],
    ) -> list[InteractionResult]:
        """
        Evaluate a list of interactions.

        Args:
            interactions: List of Interaction objects to evaluate

        Returns:
            List of InteractionResult objects with scores
        """
        if not interactions:
            return []

        # Prepare dataset for RAGAS
        data = {
            "user_input": [i.query for i in interactions],
            "response": [i.response for i in interactions],
            "retrieved_contexts": [i.contexts for i in interactions],
        }
        dataset = Dataset.from_dict(data)

        # Initialize metrics
        metrics = [
            self._ragas["ContextPrecision"](),
            self._ragas["Faithfulness"](),
            self._ragas["ResponseRelevancy"](),
        ]

        # Run evaluation
        eval_kwargs: dict[str, Any] = {"metrics": metrics}
        if self.llm:
            eval_kwargs["llm"] = self.llm
        if self.embeddings:
            eval_kwargs["embeddings"] = self.embeddings

        ragas_results = self._ragas["evaluate"](dataset, **eval_kwargs)

        # Convert to InteractionResults
        results: list[InteractionResult] = []
        df = ragas_results.to_pandas()

        for idx, interaction in enumerate(interactions):
            row = df.iloc[idx]

            # Extract scores
            ctx_precision = self._get_score(row, "context_precision")
            faithfulness = self._get_score(row, "faithfulness")
            answer_relevancy = self._get_score(row, "answer_relevancy")

            # Calculate overall score
            scores = [s for s in [ctx_precision, faithfulness, answer_relevancy] if s]
            overall = sum(scores) / len(scores) if scores else None

            # Check for hallucination
            has_hallucination = (
                faithfulness is not None
                and faithfulness < self.config.faithfulness_threshold
            )

            results.append(
                InteractionResult(
                    interaction=interaction,
                    context_precision=ctx_precision,
                    faithfulness=faithfulness,
                    answer_relevancy=answer_relevancy,
                    overall_score=overall,
                    has_hallucination=has_hallucination,
                )
            )

        return results

    def _get_score(self, row: Any, metric_name: str) -> float | None:
        """Safely extract a score from a dataframe row."""
        try:
            value = row.get(metric_name)
            if value is not None and not (isinstance(value, float) and value != value):
                return float(value)
        except (KeyError, TypeError, ValueError):
            pass
        return None
