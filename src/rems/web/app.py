"""Main Streamlit application entry point."""

import streamlit as st

st.set_page_config(
    page_title="REMS - RAG Evaluation & Monitoring",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation
pages = {
    "Dashboard": "pages/1_dashboard.py",
    "Historique": "pages/2_history.py",
    "Nouvelle évaluation": "pages/3_evaluate.py",
}


def main():
    """Main application."""
    st.sidebar.title("🔍 REMS")
    st.sidebar.markdown("*RAG Evaluation & Monitoring System*")
    st.sidebar.divider()

    # Navigation links
    page = st.sidebar.radio(
        "Navigation",
        options=list(pages.keys()),
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        **Version** 0.1.0

        [Documentation](https://github.com/arielibaba/rag-evaluation-monitoring-system-for-regulatory)
        """
    )

    # Route to the selected page
    if page == "Dashboard":
        from rems.web.pages import dashboard
        dashboard.render()
    elif page == "Historique":
        from rems.web.pages import history
        history.render()
    elif page == "Nouvelle évaluation":
        from rems.web.pages import evaluate
        evaluate.render()


if __name__ == "__main__":
    main()
