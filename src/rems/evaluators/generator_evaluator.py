"""Generator Evaluator - Evaluates LLM response quality and hallucinations."""

import structlog
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness

from rems.evaluators.base import BaseEvaluator
from rems.schemas import EvaluationResultSchema, InteractionSchema

logger = structlog.get_logger()

# Threshold below which we consider the response to have hallucinations
HALLUCINATION_THRESHOLD = 0.7


class GeneratorEvaluator(BaseEvaluator):
    """Evaluates generation quality using RAGAS metrics."""

    name = "generator"

    def __init__(
        self,
        llm=None,
        embeddings=None,
        hallucination_threshold: float = HALLUCINATION_THRESHOLD,
    ):
        """
        Initialize the generator evaluator.

        Args:
            llm: LangChain LLM instance for evaluation
            embeddings: LangChain embeddings instance
            hallucination_threshold: Faithfulness score below which
                                     we flag as hallucination
        """
        self.llm = llm
        self.embeddings = embeddings
        self.hallucination_threshold = hallucination_threshold

    def evaluate(
        self, interactions: list[InteractionSchema]
    ) -> dict[str, EvaluationResultSchema]:
        """
        Evaluate generation quality for a list of interactions.

        Metrics computed:
        - faithfulness: How faithful is the answer to the retrieved contexts
        - answer_relevancy: How relevant is the answer to the question

        Derived:
        - has_hallucination: True if faithfulness < threshold

        Args:
            interactions: List of interactions to evaluate

        Returns:
            Dictionary mapping interaction IDs to evaluation results
        """
        # Filter interactions that have retrieved documents (needed for faithfulness)
        valid_interactions = [
            (idx, i) for idx, i in enumerate(interactions)
            if i.retrieved_documents
        ]

        if not valid_interactions:
            logger.warning("No interactions with retrieved documents to evaluate")
            return {}

        # Prepare data for RAGAS
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
        }

        interaction_ids = []
        for idx, interaction in valid_interactions:
            interaction_id = self._get_interaction_id(interaction, idx)
            interaction_ids.append(interaction_id)

            data["question"].append(interaction.query)
            data["answer"].append(interaction.response)
            data["contexts"].append(
                [doc.content for doc in interaction.retrieved_documents]
            )

        dataset = Dataset.from_dict(data)

        logger.info(
            "Running generator evaluation",
            interaction_count=len(interaction_ids),
        )

        # Run RAGAS evaluation
        metrics = [faithfulness, answer_relevancy]
        eval_kwargs = {}
        if self.llm:
            eval_kwargs["llm"] = self.llm
        if self.embeddings:
            eval_kwargs["embeddings"] = self.embeddings

        result = evaluate(dataset, metrics=metrics, **eval_kwargs)

        # Map results back to interactions
        results_dict: dict[str, EvaluationResultSchema] = {}
        result_df = result.to_pandas()

        hallucination_count = 0

        for idx, interaction_id in enumerate(interaction_ids):
            row = result_df.iloc[idx]
            faithfulness_score = float(row.get("faithfulness", 0))
            relevancy_score = float(row.get("answer_relevancy", 0))

            # Detect hallucination based on faithfulness threshold
            has_hallucination = faithfulness_score < self.hallucination_threshold
            if has_hallucination:
                hallucination_count += 1

            # Calculate overall score for this interaction
            # Weighted average: faithfulness is more important for regulatory domain
            overall_score = (faithfulness_score * 0.6) + (relevancy_score * 0.4)

            results_dict[interaction_id] = EvaluationResultSchema(
                interaction_id=interaction_id,
                faithfulness=faithfulness_score,
                answer_relevancy=relevancy_score,
                has_hallucination=has_hallucination,
                hallucination_details={
                    "faithfulness_score": faithfulness_score,
                    "threshold": self.hallucination_threshold,
                    "detected": has_hallucination,
                } if has_hallucination else None,
                overall_score=overall_score,
                details={
                    "evaluator": self.name,
                    "metrics": {
                        "faithfulness": faithfulness_score,
                        "answer_relevancy": relevancy_score,
                    },
                },
            )

        hallucination_rate = hallucination_count / len(interaction_ids) if interaction_ids else 0

        logger.info(
            "Generator evaluation complete",
            evaluated_count=len(results_dict),
            avg_faithfulness=result_df["faithfulness"].mean(),
            avg_answer_relevancy=result_df["answer_relevancy"].mean(),
            hallucination_rate=hallucination_rate,
        )

        return results_dict
