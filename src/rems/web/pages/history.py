"""History page - View past evaluations and trends."""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml
from sqlalchemy import desc

from rems.models import Evaluation, get_session


def render():
    """Render the history page."""
    st.title("📜 Evaluation History")

    # Get all evaluations
    evaluations = get_all_evaluations()

    if not evaluations:
        st.warning("No evaluations available.")
        return

    # Trend chart
    st.subheader("Score Evolution")
    render_trend_chart(evaluations)

    st.divider()

    # Evaluation list
    st.subheader("Evaluation List")
    render_evaluation_list(evaluations)

    # Selected evaluation details
    if "selected_evaluation_id" in st.session_state:
        st.divider()
        render_evaluation_details(st.session_state.selected_evaluation_id)


def get_all_evaluations() -> list[Evaluation]:
    """Get all evaluations from the database."""
    with get_session() as session:
        evaluations = (
            session.query(Evaluation)
            .order_by(desc(Evaluation.created_at))
            .all()
        )
        # Detach from session
        for eval in evaluations:
            _ = eval.recommendations
            session.expunge(eval)
        return evaluations


def get_evaluation_by_id(evaluation_id: str) -> Evaluation | None:
    """Get a specific evaluation by ID."""
    with get_session() as session:
        evaluation = session.query(Evaluation).filter_by(id=evaluation_id).first()
        if evaluation:
            _ = evaluation.recommendations
            _ = evaluation.results
            session.expunge(evaluation)
        return evaluation


def render_trend_chart(evaluations: list[Evaluation]):
    """Render the score trend chart."""
    # Prepare data
    data = []
    for eval in reversed(evaluations):  # Chronological order
        data.append({
            "Date": eval.created_at,
            "Overall Score": (eval.overall_score or 0) * 100,
            "Retrieval": (eval.retrieval_score or 0) * 100,
            "Generation": (eval.generation_score or 0) * 100,
        })

    df = pd.DataFrame(data)

    if len(df) > 1:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Overall Score"],
            name="Overall Score",
            line=dict(color="#3498db", width=3),
            mode="lines+markers",
        ))

        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Retrieval"],
            name="Retrieval",
            line=dict(color="#2ecc71", width=2, dash="dash"),
            mode="lines+markers",
        ))

        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Generation"],
            name="Generation",
            line=dict(color="#9b59b6", width=2, dash="dash"),
            mode="lines+markers",
        ))

        # Add threshold line
        fig.add_hline(
            y=75,
            line_dash="dot",
            line_color="orange",
            annotation_text="Acceptable threshold (75%)",
        )

        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(range=[0, 100], title="Score (%)"),
            xaxis=dict(title="Date"),
        )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Not enough data to display trends. At least 2 evaluations are needed.")


def render_evaluation_list(evaluations: list[Evaluation]):
    """Render the list of evaluations."""
    # Create dataframe for display
    data = []
    for eval in evaluations:
        metrics = eval.metrics or {}
        data.append({
            "id": eval.id,
            "Date": eval.created_at.strftime("%Y-%m-%d %H:%M"),
            "Name": eval.name or "-",
            "Interactions": eval.interaction_count,
            "Overall Score": f"{(eval.overall_score or 0):.1%}",
            "Retrieval": f"{(eval.retrieval_score or 0):.1%}",
            "Generation": f"{(eval.generation_score or 0):.1%}",
            "Hallucinations": f"{(metrics.get('hallucination_rate', 0)):.1%}",
            "Recommendations": len(eval.recommendations),
        })

    df = pd.DataFrame(data)

    # Display as interactive table
    for idx, row in df.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])

        with col1:
            st.markdown(f"**{row['Date']}** - {row['Name']}")
        with col2:
            st.text(f"📊 {row['Overall Score']}")
        with col3:
            st.text(f"🔍 {row['Retrieval']}")
        with col4:
            st.text(f"🤖 {row['Generation']}")
        with col5:
            st.text(f"👁 {row['Interactions']} int.")
        with col6:
            if st.button("View details", key=f"detail_{row['id']}"):
                st.session_state.selected_evaluation_id = row["id"]
                st.rerun()


def render_evaluation_details(evaluation_id: str):
    """Render detailed view of a specific evaluation."""
    evaluation = get_evaluation_by_id(evaluation_id)

    if not evaluation:
        st.error("Evaluation not found.")
        return

    st.subheader(f"Details - {evaluation.created_at.strftime('%Y-%m-%d %H:%M')}")

    # Close button
    if st.button("✖ Close"):
        del st.session_state.selected_evaluation_id
        st.rerun()

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📈 Metrics", "💡 Recommendations", "📥 Exports"])

    with tab1:
        render_metrics_tab(evaluation)

    with tab2:
        render_recommendations_tab(evaluation)

    with tab3:
        render_exports_tab(evaluation)


def render_metrics_tab(evaluation: Evaluation):
    """Render the metrics tab."""
    metrics = evaluation.metrics or {}

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Overall Score", f"{(evaluation.overall_score or 0):.1%}")
    with col2:
        st.metric("Retrieval", f"{(evaluation.retrieval_score or 0):.1%}")
    with col3:
        st.metric("Generation", f"{(evaluation.generation_score or 0):.1%}")
    with col4:
        hall_rate = metrics.get("hallucination_rate", 0)
        st.metric(
            "Hallucinations",
            f"{hall_rate:.1%}",
            delta=f"{metrics.get('total_hallucinations', 0)} cases",
            delta_color="inverse" if hall_rate > 0.1 else "normal"
        )

    st.markdown("---")

    # Detailed metrics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Retrieval Metrics**")
        st.json({
            "Context Precision": metrics.get("avg_context_precision"),
            "Context Relevancy": metrics.get("avg_context_relevancy"),
        })

    with col2:
        st.markdown("**Generation Metrics**")
        st.json({
            "Faithfulness": metrics.get("avg_faithfulness"),
            "Answer Relevancy": metrics.get("avg_answer_relevancy"),
        })

    # Score distribution
    if metrics.get("score_distribution"):
        st.markdown("**Score Distribution**")
        dist = metrics["score_distribution"]
        fig = px.pie(
            names=list(dist.keys()),
            values=list(dist.values()),
            color=list(dist.keys()),
            color_discrete_map={
                "excellent": "#28a745",
                "good": "#20c997",
                "acceptable": "#ffc107",
                "poor": "#fd7e14",
                "critical": "#dc3545",
            },
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, width="stretch")


def render_recommendations_tab(evaluation: Evaluation):
    """Render the recommendations tab."""
    recommendations = evaluation.recommendations

    if not recommendations:
        st.success("No recommendations - The system is working correctly!")
        return

    # Group by priority
    priority_order = ["critical", "high", "medium", "low"]
    priority_labels = {
        "critical": ("🔴 Critical", "error"),
        "high": ("🟠 High", "warning"),
        "medium": ("🟡 Medium", "info"),
        "low": ("🟢 Low", "success"),
    }

    for priority in priority_order:
        recs = [r for r in recommendations if r.priority == priority]
        if recs:
            label, msg_type = priority_labels[priority]
            st.markdown(f"### {label} ({len(recs)})")

            for rec in recs:
                with st.expander(f"[{rec.component.upper()}] {rec.suggestion[:100]}..."):
                    st.markdown(f"**Issue detected:**\n{rec.issue}")
                    st.markdown(f"**Suggestion:**\n{rec.suggestion}")

                    if rec.parameter_adjustments:
                        st.markdown("**Parameters to adjust:**")
                        st.json(rec.parameter_adjustments)


def render_exports_tab(evaluation: Evaluation):
    """Render the exports tab."""
    st.markdown("### Download Exports")

    col1, col2 = st.columns(2)

    with col1:
        # Generate YAML content
        yaml_content = generate_yaml_export(evaluation)
        st.download_button(
            label="📄 Download YAML",
            data=yaml_content,
            file_name=f"recommendations_{evaluation.created_at.strftime('%Y%m%d')}.yaml",
            mime="text/yaml",
        )

    with col2:
        # Check if PDF/HTML reports exist
        st.markdown("*PDF/HTML reports are generated in the `reports/` folder*")

    # Show YAML preview
    st.markdown("### YAML Preview")
    st.code(yaml_content, language="yaml")


def generate_yaml_export(evaluation: Evaluation) -> str:
    """Generate YAML export for an evaluation."""
    metrics = evaluation.metrics or {}

    data = {
        "evaluation_id": evaluation.id,
        "evaluation_date": evaluation.created_at.isoformat(),
        "overall_score": round(evaluation.overall_score or 0, 3),
        "quality_level": get_quality_level(evaluation.overall_score or 0),
        "scores": {
            "retrieval": round(evaluation.retrieval_score or 0, 3),
            "generation": round(evaluation.generation_score or 0, 3),
        },
        "metrics": {
            "avg_context_precision": metrics.get("avg_context_precision"),
            "avg_context_relevancy": metrics.get("avg_context_relevancy"),
            "avg_faithfulness": metrics.get("avg_faithfulness"),
            "avg_answer_relevancy": metrics.get("avg_answer_relevancy"),
            "hallucination_rate": metrics.get("hallucination_rate"),
            "total_hallucinations": metrics.get("total_hallucinations", 0),
        },
        "recommendations": [
            {
                "component": rec.component,
                "priority": rec.priority,
                "issue": rec.issue,
                "suggestion": rec.suggestion,
                "parameter_adjustments": rec.parameter_adjustments,
            }
            for rec in evaluation.recommendations
        ],
    }

    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_quality_level(score: float) -> str:
    """Determine quality level from score."""
    if score >= 0.90:
        return "excellent"
    elif score >= 0.75:
        return "good"
    elif score >= 0.60:
        return "acceptable"
    elif score >= 0.40:
        return "poor"
    else:
        return "critical"
