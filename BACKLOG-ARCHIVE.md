# BACKLOG — Archive

Closed sections of `BACKLOG.md`, moved here verbatim (tasks, motives and
measurements together). Search it with `grep`; do not read it in full. Created 2026-10-19.

## Root tracking and archive (2026-10-19 — done)

- [x] **TODO#suivi-racine-archive** — Tracking kept in `BACKLOG.md` at the root (open work)
  and `BACKLOG-ARCHIVE.md` beside it (done work): closed sections move here whole,
  each leaving its heading and a pointer line in `BACKLOG.md`.

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
