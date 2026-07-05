# Backlog — REMS (RAG Evaluation & Monitoring System)

Tracking file for REMS, a reusable toolkit for evaluating and monitoring RAG
chatbot performance as an external observer.

## Done

- **Core library** (`src/rems/core/`) — lightweight, DB-free package importable
  as `from rems import RAGEvaluator, Interaction`: evaluator, schemas, RAGAS
  metrics wrapper, diagnostic, recommendations.
- **Full application layer** — API/file collector, SQLAlchemy models + session,
  full RAGAS evaluators (retrieval, generation, orchestrator), diagnostic engine,
  recommendation engine.
- **CLI** (`src/rems/cli.py`) — `init-db`, `collect`, `evaluate` (file-based and
  API-based modes), `web`.
- **Web dashboard** (Streamlit) — Dashboard, History, New Evaluation pages;
  Plotly gauges and trend charts.
- **Reports** — PDF/HTML generation (WeasyPrint + Jinja2 template) and YAML
  recommendations export.
- **Metrics** — Faithfulness, Answer Relevancy, Context Precision, Hallucination
  Rate; quality-level classification; configurable diagnostic thresholds via env.
- **Domain-agnostic generalization** — removed regulatory/compliance specifics,
  translated code and UI from French to English.
- **Optional dependency groups** — `pip install rems` (core) vs `rems[app]` (web,
  DB, reports).
- **RAGAS 0.4.x compatibility** and structlog config fixes.
- **Simulation script** (`scripts/simulate_evaluation.py`) — run an evaluation
  without an LLM.
- **Documentation** — README, CLAUDE.md, SESSION_RESUME.md.

## In progress

- (none currently — working tree clean)

## Planned

- **Test suite** — pytest coverage for the core library (README documents
  `uv run pytest` but no `tests/` package exists yet).
- **PyPI publish** — package and release `rems`.
- **OpenAI support** — add LangChain OpenAI as an alternative LLM-as-judge to
  Google Gemini.
- **Docker** — Dockerfile for containerized deployment.
- **REST API endpoint** — programmatic evaluation service.
