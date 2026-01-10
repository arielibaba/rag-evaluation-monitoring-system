"""Dashboard page - Overview of the latest evaluation."""

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import desc

from rems.models import Evaluation, get_session


def render():
    """Render the dashboard page."""
    st.title("📊 Dashboard")
    st.markdown("Vue d'ensemble de la dernière évaluation")

    # Get the latest evaluation
    latest_eval = get_latest_evaluation()

    if latest_eval is None:
        st.warning("Aucune évaluation disponible. Lancez une première évaluation.")
        return

    # Header with evaluation info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Date d'évaluation", latest_eval.created_at.strftime("%d/%m/%Y"))
    with col2:
        st.metric("Interactions analysées", latest_eval.interaction_count)
    with col3:
        quality_level = get_quality_level(latest_eval.overall_score or 0)
        st.metric("Niveau de qualité", quality_level.upper())

    st.divider()

    # Main score card
    render_score_overview(latest_eval)

    st.divider()

    # Component scores
    st.subheader("Scores par composant")
    render_component_scores(latest_eval)

    st.divider()

    # Detailed metrics
    st.subheader("Métriques détaillées")
    render_detailed_metrics(latest_eval)

    # Recommendations summary
    if latest_eval.recommendations:
        st.divider()
        st.subheader("Recommandations prioritaires")
        render_recommendations_summary(latest_eval)


def get_latest_evaluation() -> Evaluation | None:
    """Get the most recent evaluation from the database."""
    with get_session() as session:
        evaluation = session.query(Evaluation).order_by(desc(Evaluation.created_at)).first()
        if evaluation:
            # Eagerly load relationships
            _ = evaluation.recommendations
            session.expunge(evaluation)
        return evaluation


def get_quality_level(score: float) -> str:
    """Determine quality level from score."""
    if score >= 0.90:
        return "excellent"
    elif score >= 0.75:
        return "bon"
    elif score >= 0.60:
        return "acceptable"
    elif score >= 0.40:
        return "faible"
    else:
        return "critique"


def get_quality_color(score: float) -> str:
    """Get color for quality level."""
    if score >= 0.90:
        return "#28a745"
    elif score >= 0.75:
        return "#20c997"
    elif score >= 0.60:
        return "#ffc107"
    elif score >= 0.40:
        return "#fd7e14"
    else:
        return "#dc3545"


def render_score_overview(evaluation: Evaluation):
    """Render the main score overview."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        score = evaluation.overall_score or 0
        color = get_quality_color(score)

        # Create gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Score Global", 'font': {'size': 24}},
            number={'suffix': "%", 'font': {'size': 48}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': color},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 40], 'color': '#ffebee'},
                    {'range': [40, 60], 'color': '#fff3e0'},
                    {'range': [60, 75], 'color': '#fffde7'},
                    {'range': [75, 90], 'color': '#e8f5e9'},
                    {'range': [90, 100], 'color': '#c8e6c9'},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 75
                }
            }
        ))

        fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)


def render_component_scores(evaluation: Evaluation):
    """Render component score cards."""
    col1, col2 = st.columns(2)

    with col1:
        retrieval_score = evaluation.retrieval_score or 0
        delta = None  # TODO: Calculate delta from previous evaluation

        st.metric(
            "🔍 Retrieval",
            f"{retrieval_score:.1%}",
            delta=delta,
            help="Qualité de la récupération des documents (context precision + relevancy)"
        )

        # Progress bar
        st.progress(retrieval_score)

    with col2:
        generation_score = evaluation.generation_score or 0

        st.metric(
            "🤖 Génération",
            f"{generation_score:.1%}",
            delta=None,
            help="Qualité de la génération (faithfulness + answer relevancy)"
        )

        st.progress(generation_score)


def render_detailed_metrics(evaluation: Evaluation):
    """Render detailed metrics table."""
    metrics = evaluation.metrics or {}

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Retrieval**")
        metrics_data = {
            "Context Precision": metrics.get("avg_context_precision"),
            "Context Relevancy": metrics.get("avg_context_relevancy"),
        }
        for name, value in metrics_data.items():
            if value is not None:
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.text(name)
                with col_b:
                    st.text(f"{value:.1%}")

    with col2:
        st.markdown("**Génération**")
        metrics_data = {
            "Faithfulness": metrics.get("avg_faithfulness"),
            "Answer Relevancy": metrics.get("avg_answer_relevancy"),
            "Taux d'hallucination": metrics.get("hallucination_rate"),
        }
        for name, value in metrics_data.items():
            if value is not None:
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.text(name)
                with col_b:
                    color = "red" if name == "Taux d'hallucination" and value > 0.1 else "inherit"
                    st.markdown(f"<span style='color:{color}'>{value:.1%}</span>", unsafe_allow_html=True)

    # Score distribution chart
    if metrics.get("score_distribution"):
        st.markdown("**Distribution des scores**")
        dist = metrics["score_distribution"]

        fig = px.bar(
            x=list(dist.keys()),
            y=list(dist.values()),
            color=list(dist.keys()),
            color_discrete_map={
                "excellent": "#28a745",
                "good": "#20c997",
                "acceptable": "#ffc107",
                "poor": "#fd7e14",
                "critical": "#dc3545",
            },
            labels={"x": "Niveau", "y": "Nombre d'interactions"},
        )
        fig.update_layout(showlegend=False, height=250)
        st.plotly_chart(fig, use_container_width=True)


def render_recommendations_summary(evaluation: Evaluation):
    """Render a summary of top recommendations."""
    recommendations = evaluation.recommendations

    # Count by priority
    critical = [r for r in recommendations if r.priority == "critical"]
    high = [r for r in recommendations if r.priority == "high"]

    if critical:
        st.error(f"⚠️ {len(critical)} recommandation(s) critique(s)")
        for rec in critical[:2]:
            with st.expander(f"🔴 [{rec.component.upper()}] {rec.suggestion[:80]}..."):
                st.markdown(f"**Problème:** {rec.issue}")
                st.markdown(f"**Suggestion:** {rec.suggestion}")

    if high:
        st.warning(f"⚡ {len(high)} recommandation(s) haute priorité")
        for rec in high[:2]:
            with st.expander(f"🟠 [{rec.component.upper()}] {rec.suggestion[:80]}..."):
                st.markdown(f"**Problème:** {rec.issue}")
                st.markdown(f"**Suggestion:** {rec.suggestion}")

    st.info("Voir l'historique pour les détails complets et le téléchargement du rapport.")
