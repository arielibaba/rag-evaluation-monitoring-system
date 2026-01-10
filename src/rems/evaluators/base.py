"""Base evaluator class."""

from abc import ABC, abstractmethod

import structlog

from rems.schemas import EvaluationResultSchema, InteractionSchema

logger = structlog.get_logger()


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators."""

    name: str = "base"

    @abstractmethod
    def evaluate(
        self, interactions: list[InteractionSchema]
    ) -> dict[str, EvaluationResultSchema]:
        """
        Evaluate a list of interactions.

        Args:
            interactions: List of interactions to evaluate

        Returns:
            Dictionary mapping interaction IDs to their evaluation results
        """
        pass

    def _get_interaction_id(self, interaction: InteractionSchema, index: int) -> str:
        """Get or generate an ID for an interaction."""
        return interaction.id or f"interaction_{index}"
