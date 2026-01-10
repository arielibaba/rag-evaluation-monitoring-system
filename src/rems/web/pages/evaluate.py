"""Evaluate page - Trigger new evaluations."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from rems.collector import APICollector
from rems.config import settings
from rems.diagnostic import DiagnosticEngine
from rems.evaluators import EvaluationOrchestrator
from rems.models import init_db
from rems.recommendations import RecommendationEngine
from rems.reports import ReportGenerator
from rems.schemas import InteractionSchema


def render():
    """Render the evaluate page."""
    st.title("🚀 Nouvelle évaluation")
    st.markdown("Lancez une évaluation sur les interactions du chatbot")

    # Check configuration
    if not check_configuration():
        return

    # Data source selection
    st.subheader("Source des données")

    source = st.radio(
        "Choisissez la source des interactions :",
        options=["Fichier JSON", "API du chatbot"],
        horizontal=True,
    )

    if source == "Fichier JSON":
        render_file_upload()
    else:
        render_api_fetch()


def check_configuration() -> bool:
    """Check if the system is properly configured."""
    issues = []

    if not settings.google_api_key:
        issues.append("❌ `REMS_GOOGLE_API_KEY` non configuré")

    if issues:
        st.error("Configuration incomplète")
        for issue in issues:
            st.markdown(issue)
        st.markdown("""
        Configurez les variables d'environnement dans le fichier `.env` :
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
    Uploadez un fichier JSON contenant les interactions à évaluer.

    **Format attendu :**
    ```json
    {
        "interactions": [
            {
                "query": "Question de l'utilisateur",
                "response": "Réponse du chatbot",
                "retrieved_documents": [
                    {"content": "Contenu du document", "source": "source.pdf"}
                ]
            }
        ]
    }
    ```
    """)

    uploaded_file = st.file_uploader(
        "Choisir un fichier JSON",
        type=["json"],
        help="Fichier contenant les interactions à évaluer"
    )

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            interactions_data = data.get("interactions", data if isinstance(data, list) else [])

            st.success(f"✅ {len(interactions_data)} interactions trouvées")

            # Preview
            with st.expander("Aperçu des données"):
                st.json(interactions_data[:3])

            # Evaluation options
            render_evaluation_options(interactions_data, source="file")

        except json.JSONDecodeError as e:
            st.error(f"Erreur de parsing JSON : {e}")


def render_api_fetch():
    """Render the API fetch interface."""
    st.markdown(f"""
    Récupérez les interactions depuis l'API du chatbot.

    **URL configurée :** `{settings.chatbot_api_url}`
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Date range
        default_start = datetime.now() - timedelta(days=7)
        start_date = st.date_input("Date de début", value=default_start)

    with col2:
        end_date = st.date_input("Date de fin", value=datetime.now())

    limit = st.number_input(
        "Nombre maximum d'interactions",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
    )

    if st.button("🔍 Récupérer les interactions"):
        with st.spinner("Récupération des interactions..."):
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
                    st.success(f"✅ {len(interactions)} interactions récupérées")
                else:
                    st.warning("Aucune interaction trouvée pour cette période")

            except Exception as e:
                st.error(f"Erreur lors de la récupération : {e}")

    # If we have fetched interactions
    if "fetched_interactions" in st.session_state:
        interactions = st.session_state.fetched_interactions

        with st.expander("Aperçu des données"):
            preview = [
                {"query": i.query[:100], "response": i.response[:100]}
                for i in interactions[:5]
            ]
            st.json(preview)

        render_evaluation_options(interactions, source="api")


def render_evaluation_options(interactions_data, source: str):
    """Render evaluation options and trigger button."""
    st.divider()
    st.subheader("Options d'évaluation")

    col1, col2 = st.columns(2)

    with col1:
        eval_name = st.text_input(
            "Nom de l'évaluation",
            value=f"Évaluation {datetime.now().strftime('%d/%m/%Y')}",
        )

    with col2:
        generate_reports = st.checkbox("Générer les rapports PDF/HTML", value=True)

    # Run evaluation button
    if st.button("▶️ Lancer l'évaluation", type="primary"):
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
        status_text.text("🔧 Configuration du LLM...")
        progress_bar.progress(1 / total_steps)

        llm, embeddings = setup_llm()

        # Step 2: Run evaluation
        status_text.text("📊 Évaluation en cours...")
        progress_bar.progress(2 / total_steps)

        orchestrator = EvaluationOrchestrator(llm=llm, embeddings=embeddings)
        summary = orchestrator.evaluate(
            interactions=interactions,
            name=name,
            store_results=True,
        )

        # Step 3: Generate recommendations
        status_text.text("💡 Génération des recommandations...")
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
            status_text.text("📄 Génération des rapports...")
            progress_bar.progress(4 / total_steps)

            report_generator = ReportGenerator()
            output_files = report_generator.generate(summary, recommendations)

        # Complete
        progress_bar.progress(1.0)
        status_text.text("✅ Évaluation terminée !")

        # Show results
        st.success("Évaluation terminée avec succès !")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Score Global", f"{summary.overall_score:.1%}")
        with col2:
            st.metric("Retrieval", f"{summary.retrieval_score:.1%}")
        with col3:
            st.metric("Génération", f"{summary.generation_score:.1%}")
        with col4:
            st.metric("Qualité", summary.quality_level.upper())

        # Recommendations count
        if recommendations:
            critical = len([r for r in recommendations if r.priority == "critical"])
            high = len([r for r in recommendations if r.priority == "high"])

            if critical > 0:
                st.error(f"⚠️ {critical} recommandation(s) critique(s) détectée(s)")
            if high > 0:
                st.warning(f"⚡ {high} recommandation(s) haute priorité")

        st.info(f"📁 Fichier YAML : `{yaml_path}`")

        if generate_reports:
            st.info(f"📁 Rapports générés dans : `{settings.reports_dir}`")

        # Clear fetched interactions from session
        if "fetched_interactions" in st.session_state:
            del st.session_state.fetched_interactions

    except Exception as e:
        st.error(f"Erreur lors de l'évaluation : {e}")
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
