"""Retrieval Evaluator - Evaluates the quality of document retrieval."""

import structlog
from datasets import Dataset
from ragas import evaluate
from ragas.metrics._context_precision import ContextPrecision

from rems.evaluators.base import BaseEvaluator
from rems.schemas import EvaluationResultSchema, InteractionSchema

logger = structlog.get_logger()


class RetrievalEvaluator(BaseEvaluator):
    """Evaluates retrieval quality using RAGAS metrics."""

    name = "retrieval"

    def __init__(self, llm=None, embeddings=None):
        """
        Initialize the retrieval evaluator.

        Args:
            llm: LangChain LLM instance for evaluation (uses default if None)
            embeddings: LangChain embeddings instance (uses default if None)
        """
        self.llm = llm
        self.embeddings = embeddings

    def evaluate(
        self, interactions: list[InteractionSchema]
    ) -> dict[str, EvaluationResultSchema]:
        """
        Evaluate retrieval quality for a list of interactions.

        Metrics computed:
        - context_precision: How precise are the retrieved contexts

        Args:
            interactions: List of interactions to evaluate

        Returns:
            Dictionary mapping interaction IDs to evaluation results
        """
        # Filter interactions that have retrieved documents
        valid_interactions = [
            (idx, i) for idx, i in enumerate(interactions)
            if i.retrieved_documents
        ]

        if not valid_interactions:
            logger.warning("No interactions with retrieved documents to evaluate")
            return {}

        # Prepare data for RAGAS
        data = {
            "user_input": [],
            "response": [],
            "retrieved_contexts": [],
        }

        interaction_ids = []
        for idx, interaction in valid_interactions:
            interaction_id = self._get_interaction_id(interaction, idx)
            interaction_ids.append(interaction_id)

            data["user_input"].append(interaction.query)
            data["response"].append(interaction.response)
            data["retrieved_contexts"].append(
                [doc.content for doc in interaction.retrieved_documents]
            )

        dataset = Dataset.from_dict(data)

        logger.info(
            "Running retrieval evaluation",
            interaction_count=len(interaction_ids),
        )

        # Run RAGAS evaluation
        context_precision = ContextPrecision()

        eval_kwargs = {"metrics": [context_precision]}
        if self.llm:
            eval_kwargs["llm"] = self.llm
        if self.embeddings:
            eval_kwargs["embeddings"] = self.embeddings

        result = evaluate(dataset, **eval_kwargs)

        # Map results back to interactions
        results_dict: dict[str, EvaluationResultSchema] = {}
        result_df = result.to_pandas()

        for idx, interaction_id in enumerate(interaction_ids):
            row = result_df.iloc[idx]

            precision_score = float(row.get("context_precision", 0))

            results_dict[interaction_id] = EvaluationResultSchema(
                interaction_id=interaction_id,
                context_precision=precision_score,
                context_relevancy=precision_score,  # Use same score as proxy
                details={
                    "evaluator": self.name,
                    "metrics": {
                        "context_precision": precision_score,
                    },
                },
            )

        logger.info(
            "Retrieval evaluation complete",
            evaluated_count=len(results_dict),
            avg_context_precision=result_df["context_precision"].mean(),
        )

        return results_dict
