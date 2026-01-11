"""Evaluate page - Trigger new evaluations."""

import json
from datetime import datetime, timedelta

import streamlit as st

from rems.collector import APICollector
from rems.config import settings
from rems.evaluators import EvaluationOrchestrator
from rems.models import init_db
from rems.recommendations import RecommendationEngine
from rems.reports import ReportGenerator


def render():
    """Render the evaluate page."""
    st.title("🚀 New Evaluation")
    st.markdown("Run an evaluation on chatbot interactions")

    # Check configuration
    if not check_configuration():
        return

    # Data source selection
    st.subheader("Data Source")

    source = st.radio(
        "Choose the interactions source:",
        options=["JSON File", "Chatbot API"],
        horizontal=True,
    )

    if source == "JSON File":
        render_file_upload()
    else:
        render_api_fetch()


def check_configuration() -> bool:
    """Check if the system is properly configured."""
    issues = []

    if not settings.google_api_key:
        issues.append("❌ `REMS_GOOGLE_API_KEY` not configured")

    if issues:
        st.error("Incomplete configuration")
        for issue in issues:
            st.markdown(issue)
        st.markdown("""
        Configure environment variables in the `.env` file:
        ```
        REMS_GOOGLE_API_KEY=your-google-api-key
        REMS_DATABASE_URL=postgresql://user:pass@localhost:5432/rems
        ```
        """)
        return False

    return True


def render_file_upload():
    """Render the file upload interface."""
    st.markdown("""
    Upload a JSON file containing the interactions to evaluate.

    **Expected format:**
    ```json
    {
        "interactions": [
            {
                "query": "User question",
                "response": "Chatbot response",
                "retrieved_documents": [
                    {"content": "Document content", "source": "source.pdf"}
                ]
            }
        ]
    }
    ```
    """)

    uploaded_file = st.file_uploader(
        "Choose a JSON file",
        type=["json"],
        help="File containing interactions to evaluate"
    )

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            interactions_data = data.get("interactions", data if isinstance(data, list) else [])

            st.success(f"✅ {len(interactions_data)} interactions found")

            # Preview
            with st.expander("Data preview"):
                st.json(interactions_data[:3])

            # Evaluation options
            render_evaluation_options(interactions_data, source="file")

        except json.JSONDecodeError as e:
            st.error(f"JSON parsing error: {e}")


def render_api_fetch():
    """Render the API fetch interface."""
    st.markdown(f"""
    Fetch interactions from the chatbot API.

    **Configured URL:** `{settings.chatbot_api_url}`
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Date range
        default_start = datetime.now() - timedelta(days=7)
        start_date = st.date_input("Start date", value=default_start)

    with col2:
        end_date = st.date_input("End date", value=datetime.now())

    limit = st.number_input(
        "Maximum number of interactions",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
    )

    if st.button("🔍 Fetch interactions"):
        with st.spinner("Fetching interactions..."):
            try:
                collector = APICollector()
                interactions = collector.fetch_interactions(
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    limit=limit,
                )
                collector.close()

                if interactions:
                    st.session_state.fetched_interactions = interactions
                    st.success(f"✅ {len(interactions)} interactions fetched")
                else:
                    st.warning("No interactions found for this period")

            except Exception as e:
                st.error(f"Error fetching interactions: {e}")

    # If we have fetched interactions
    if "fetched_interactions" in st.session_state:
        interactions = st.session_state.fetched_interactions

        with st.expander("Data preview"):
            preview = [
                {"query": i.query[:100], "response": i.response[:100]}
                for i in interactions[:5]
            ]
            st.json(preview)

        render_evaluation_options(interactions, source="api")


def render_evaluation_options(interactions_data, source: str):
    """Render evaluation options and trigger button."""
    st.divider()
    st.subheader("Evaluation Options")

    col1, col2 = st.columns(2)

    with col1:
        eval_name = st.text_input(
            "Evaluation name",
            value=f"Evaluation {datetime.now().strftime('%Y-%m-%d')}",
        )

    with col2:
        generate_reports = st.checkbox("Generate PDF/HTML reports", value=True)

    # Run evaluation button
    if st.button("▶️ Run Evaluation", type="primary"):
        run_evaluation(
            interactions_data=interactions_data,
            source=source,
            name=eval_name,
            generate_reports=generate_reports,
        )


def run_evaluation(
    interactions_data,
    source: str,
    name: str,
    generate_reports: bool,
):
    """Run the evaluation process."""
    # Initialize database
    init_db()

    # Parse interactions if from file
    if source == "file":
        collector = APICollector()
        interactions = [collector._parse_interaction(item) for item in interactions_data]
    else:
        interactions = interactions_data

    total_steps = 5 if generate_reports else 4
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Setup LLM
        status_text.text("🔧 Configuring LLM...")
        progress_bar.progress(1 / total_steps)

        llm, embeddings = setup_llm()

        # Step 2: Run evaluation
        status_text.text("📊 Running evaluation...")
        progress_bar.progress(2 / total_steps)

        orchestrator = EvaluationOrchestrator(llm=llm, embeddings=embeddings)
        summary = orchestrator.evaluate(
            interactions=interactions,
            name=name,
            store_results=True,
        )

        # Step 3: Generate recommendations
        status_text.text("💡 Generating recommendations...")
        progress_bar.progress(3 / total_steps)

        recommendation_engine = RecommendationEngine()
        recommendations = recommendation_engine.generate_recommendations(
            summary,
            store_in_db=True,
        )
        summary.recommendations = recommendations

        # Export YAML
        yaml_path = recommendation_engine.export_to_yaml(summary, recommendations)

        # Step 4: Generate reports (optional)
        if generate_reports:
            status_text.text("📄 Generating reports...")
            progress_bar.progress(4 / total_steps)

            report_generator = ReportGenerator()
            report_generator.generate(summary, recommendations)

        # Complete
        progress_bar.progress(1.0)
        status_text.text("✅ Evaluation complete!")

        # Show results
        st.success("Evaluation completed successfully!")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Overall Score", f"{summary.overall_score:.1%}")
        with col2:
            st.metric("Retrieval", f"{summary.retrieval_score:.1%}")
        with col3:
            st.metric("Generation", f"{summary.generation_score:.1%}")
        with col4:
            st.metric("Quality", summary.quality_level.upper())

        # Recommendations count
        if recommendations:
            critical = len([r for r in recommendations if r.priority == "critical"])
            high = len([r for r in recommendations if r.priority == "high"])

            if critical > 0:
                st.error(f"⚠️ {critical} critical recommendation(s) detected")
            if high > 0:
                st.warning(f"⚡ {high} high priority recommendation(s)")

        st.info(f"📁 YAML file: `{yaml_path}`")

        if generate_reports:
            st.info(f"📁 Reports generated in: `{settings.reports_dir}`")

        # Clear fetched interactions from session
        if "fetched_interactions" in st.session_state:
            del st.session_state.fetched_interactions

    except Exception as e:
        st.error(f"Error during evaluation: {e}")
        st.exception(e)


def setup_llm():
    """Set up the LLM for evaluation."""
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

    llm = ChatGoogleGenerativeAI(
        model=settings.evaluation_model,
        google_api_key=settings.google_api_key,
    )
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.google_api_key,
    )

    return llm, embeddings
