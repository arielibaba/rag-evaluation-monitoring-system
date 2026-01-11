#!/usr/bin/env python
"""Simulate an evaluation with fake data for testing purposes."""

import random
from datetime import UTC, datetime

from rems.models import (
    Evaluation,
    EvaluationResult,
    Interaction,
    Recommendation,
    RetrievedDocument,
    get_session,
    init_db,
)


def simulate_evaluation():
    """Create a simulated evaluation with fake data."""
    print("Initializing database...")
    init_db()

    with get_session() as session:
        # Create sample interactions
        interactions_data = [
            {
                "query": "What is the return policy for electronics?",
                "response": (
                    "According to our store policy, electronics can be returned "
                    "within 30 days of purchase with the original receipt. "
                    "The item must be in its original packaging and in working condition."
                ),
                "docs": [
                    (
                        "Section 3.1 - Return Policy. Electronics may be returned "
                        "within 30 days...",
                        "store_policies.pdf",
                    ),
                    (
                        "Section 3.2 - Refund Processing. All refunds processed "
                        "within 5-7 days...",
                        "store_policies.pdf",
                    ),
                ],
            },
            {
                "query": "How do I track my order?",
                "response": (
                    "You can track your order by logging into your account and "
                    "navigating to 'Order History'. Click on the specific order "
                    "to view tracking information."
                ),
                "docs": [
                    (
                        "Order Tracking Guide. Customers can track orders through "
                        "their account dashboard...",
                        "customer_support.pdf",
                    ),
                ],
            },
            {
                "query": "What payment methods do you accept?",
                "response": (
                    "We accept all major credit cards including Visa, MasterCard, "
                    "American Express, PayPal, and Apple Pay. "
                    "For orders over $500, financing options are available."
                ),
                "docs": [
                    (
                        "Payment Methods. Accepted: Visa, MasterCard, "
                        "American Express, PayPal, Apple Pay...",
                        "checkout_faq.pdf",
                    ),
                ],
            },
            {
                "query": "What is your shipping policy?",
                "response": (
                    "Standard shipping takes 5-7 business days. "
                    "Express shipping (2-3 days) is available for an additional fee. "
                    "Free shipping on orders over $75."
                ),
                "docs": [
                    (
                        "Shipping Information. Standard: 5-7 days. "
                        "Express: 2-3 days. Free over $75...",
                        "shipping_policy.pdf",
                    ),
                ],
            },
            {
                "query": "How do I contact customer support?",
                "response": (
                    "You can reach our customer support team via email at "
                    "support@example.com, by phone at 1-800-EXAMPLE, "
                    "or through our live chat feature on the website."
                ),
                "docs": [
                    (
                        "Contact Us. Email: support@example.com. "
                        "Phone: 1-800-EXAMPLE. Live chat available...",
                        "contact_info.pdf",
                    ),
                ],
            },
        ]

        print(f"Creating {len(interactions_data)} interactions...")
        interactions = []
        for data in interactions_data:
            interaction = Interaction(
                query=data["query"],
                response=data["response"],
            )
            for content, source in data["docs"]:
                doc = RetrievedDocument(
                    content=content,
                    source=source,
                    rank=0,
                )
                interaction.retrieved_documents.append(doc)
            session.add(interaction)
            interactions.append(interaction)

        session.flush()

        # Create evaluation with simulated scores
        print("Creating simulated evaluation...")

        # Simulate realistic scores
        faithfulness_scores = [random.uniform(0.7, 0.95) for _ in interactions]
        relevancy_scores = [random.uniform(0.75, 0.92) for _ in interactions]
        precision_scores = [random.uniform(0.65, 0.88) for _ in interactions]

        avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
        avg_relevancy = sum(relevancy_scores) / len(relevancy_scores)
        avg_precision = sum(precision_scores) / len(precision_scores)

        # One hallucination for testing
        faithfulness_scores[2] = 0.45  # Simulate a hallucination

        retrieval_score = avg_precision
        generation_score = (avg_faithfulness + avg_relevancy) / 2
        overall_score = retrieval_score * 0.35 + generation_score * 0.65

        hallucination_count = sum(1 for s in faithfulness_scores if s < 0.7)
        hallucination_rate = hallucination_count / len(interactions)

        # Score distribution
        all_scores = [
            (f * 0.6 + r * 0.4) for f, r in zip(faithfulness_scores, relevancy_scores)
        ]
        distribution = {
            "excellent": len([s for s in all_scores if s >= 0.90]),
            "good": len([s for s in all_scores if 0.75 <= s < 0.90]),
            "acceptable": len([s for s in all_scores if 0.60 <= s < 0.75]),
            "poor": len([s for s in all_scores if 0.40 <= s < 0.60]),
            "critical": len([s for s in all_scores if s < 0.40]),
        }

        evaluation = Evaluation(
            name="Test Evaluation (Simulated)",
            description="Evaluation with simulated data for testing the interface",
            interaction_count=len(interactions),
            overall_score=overall_score,
            retrieval_score=retrieval_score,
            generation_score=generation_score,
            metrics={
                "avg_context_precision": avg_precision,
                "avg_context_relevancy": avg_precision,
                "avg_faithfulness": avg_faithfulness,
                "avg_answer_relevancy": avg_relevancy,
                "hallucination_rate": hallucination_rate,
                "total_hallucinations": hallucination_count,
                "score_distribution": distribution,
            },
            completed_at=datetime.now(UTC),
        )
        session.add(evaluation)
        session.flush()

        # Create evaluation results for each interaction
        print("Creating evaluation results...")
        for idx, interaction in enumerate(interactions):
            result = EvaluationResult(
                evaluation_id=evaluation.id,
                interaction_id=interaction.id,
                faithfulness=faithfulness_scores[idx],
                answer_relevancy=relevancy_scores[idx],
                context_precision=precision_scores[idx],
                context_relevancy=precision_scores[idx],
                has_hallucination=faithfulness_scores[idx] < 0.7,
                overall_score=all_scores[idx],
            )
            session.add(result)

        # Create recommendations
        print("Creating recommendations...")
        recommendations = [
            Recommendation(
                evaluation_id=evaluation.id,
                component="generator",
                issue=(
                    "Faithfulness too low on some responses: 45.0% (threshold: 70.0%)"
                    "\n\nProbable causes:"
                    "\n  - LLM temperature too high"
                    "\n  - Insufficient context provided to LLM"
                ),
                suggestion=(
                    "Reduce LLM temperature and strengthen source citation "
                    "instructions in the system prompt"
                ),
                priority="high",
                parameter_adjustments={
                    "generator.temperature": {
                        "action": "decrease",
                        "suggested_value": 0.3,
                    },
                },
            ),
            Recommendation(
                evaluation_id=evaluation.id,
                component="retriever",
                issue=(
                    f"Average context precision: {avg_precision:.1%} "
                    "(recommended threshold: 80%)"
                    "\n\nProbable causes:"
                    "\n  - Top-K potentially too high"
                    "\n  - Similarity threshold needs adjustment"
                ),
                suggestion=(
                    "Increase similarity threshold to filter out "
                    "less relevant documents"
                ),
                priority="medium",
                parameter_adjustments={
                    "retriever.similarity_threshold": {
                        "action": "increase",
                        "suggested_value": 0.75,
                    },
                },
            ),
        ]
        for rec in recommendations:
            session.add(rec)

        print("\n" + "=" * 60)
        print("SIMULATION COMPLETED")
        print("=" * 60)
        print(f"Interactions created: {len(interactions)}")
        print(f"Overall score: {overall_score:.1%}")
        print(f"Retrieval score: {retrieval_score:.1%}")
        print(f"Generation score: {generation_score:.1%}")
        print(f"Hallucination rate: {hallucination_rate:.1%}")
        print(f"Recommendations: {len(recommendations)}")
        print("=" * 60)
        print("\nOpen http://localhost:8501 to see the results!")


if __name__ == "__main__":
    simulate_evaluation()
