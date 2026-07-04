# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REMS (RAG Evaluation & Monitoring System) is a reusable Python toolkit for evaluating and monitoring RAG chatbot performance. It operates as an external observer without modifying the chatbot itself.

**Evaluate any RAG system** - whether running locally or in the cloud - via API calls or JSON file input.

**Two usage modes:**
1. **Library**: Import `RAGEvaluator` directly in your RAG project (minimal dependencies)
2. **Full Application**: Web UI, database storage, PDF reports (requires `pip install rems[app]`)

## Project Structure

```
src/rems/
├── core/                  # Lightweight library (no DB dependency)
│   ├── __init__.py        # Exports RAGEvaluator, Interaction, etc.
│   ├── evaluator.py       # RAGEvaluator class - main API
│   ├── schemas.py         # Dataclass models (Interaction, EvaluationResults, etc.)
│   ├── metrics.py         # RAGAS wrapper (MetricsEvaluator)
│   ├── diagnostic.py      # diagnose() function
│   └── recommendations.py # generate_recommendations() function
├── __init__.py            # Re-exports core API
├── cli.py                 # CLI commands (init-db, collect, evaluate, web)
├── config.py              # Pydantic settings (env vars)
├── schemas.py             # Full app DTOs
├── collector/             # API/file data collection
├── evaluators/            # Full RAGAS evaluators with DB
├── diagnostic/            # Full diagnostic engine with DB
├── recommendations/       # Full recommendation engine with YAML export
├── models/                # SQLAlchemy models (Evaluation, Interaction, etc.)
├── reports/               # PDF/HTML generation (WeasyPrint + Jinja2)
└── web/                   # Streamlit interface
    ├── app.py             # Main Streamlit app
    └── pages/             # dashboard.py, history.py, evaluate.py
```

## Library Usage (Core)

```python
from rems import RAGEvaluator, Interaction, EvaluationConfig

evaluator = RAGEvaluator()
results = evaluator.evaluate([
    Interaction(query="...", response="...", contexts=["..."])
])
print(f"Score: {results.overall_score:.1%}")
```

## Development Commands

```bash
# Install dependencies (core only)
uv sync

# Install all dependencies (app + dev)
uv sync --all-extras

# Initialize database (PostgreSQL must be running)
uv run rems init-db

# Launch web interface
uv run rems web                    # Default port 8501
uv run rems web --port 8080        # Custom port

# Run evaluation from JSON file
uv run rems evaluate --file test_interactions.json --name "My Evaluation"

# Run evaluation from chatbot API (local or cloud)
uv run rems evaluate --start 2026-01-01 --end 2026-01-07 --limit 100

# Collect interactions without evaluating
uv run rems collect --start 2026-01-01 --limit 100 --store

# Simulate evaluation (no LLM required, for testing UI/reports)
uv run python scripts/simulate_evaluation.py

# Linting and type checking
uv run ruff check src/
uv run mypy src/
```

## Database Setup

```bash
# Start PostgreSQL (macOS)
brew services start postgresql@16

# Create database
createdb rems

# Initialize tables
uv run rems init-db
```

## Evaluation Pipeline

The evaluation flow follows this sequence:

1. **APICollector** fetches interactions from chatbot API or JSON file
2. **EvaluationOrchestrator** coordinates evaluators:
   - **RetrievalEvaluator**: Context Precision via RAGAS
   - **GeneratorEvaluator**: Faithfulness + Answer Relevancy via RAGAS
3. **DiagnosticEngine** analyzes results for root causes
4. **RecommendationEngine** generates actionable suggestions → YAML export
5. **ReportGenerator** creates PDF/HTML reports

Overall score = (Retrieval × 0.35) + (Generation × 0.65)

## RAGAS 0.4.x API

Uses class-based metric imports (not function-based):
```python
from ragas.metrics._context_precision import ContextPrecision
from ragas.metrics._faithfulness import Faithfulness
from ragas.metrics._answer_relevance import ResponseRelevancy
```

Dataset columns: `user_input`, `response`, `retrieved_contexts` (not the old `question`, `answer`, `contexts`)

## Configurable Thresholds

All diagnostic thresholds can be configured via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `REMS_DIAG_FAITHFULNESS` | 0.70 | Hallucination detection threshold |
| `REMS_DIAG_CONTEXT_PRECISION` | 0.70 | Minimum context precision |
| `REMS_DIAG_CONTEXT_RELEVANCY` | 0.70 | Minimum context relevancy |
| `REMS_DIAG_ANSWER_RELEVANCY` | 0.70 | Minimum answer relevancy |
| `REMS_DIAG_HALLUCINATION_RATE` | 0.10 | Maximum hallucination rate |

Quality level thresholds:
| Level | Score |
|-------|-------|
| Excellent | ≥ 90% |
| Good | 75-89% |
| Acceptable | 60-74% |
| Poor | 40-59% |
| Critical | < 40% |

## Environment Variables

```env
REMS_DATABASE_URL=postgresql://user:password@localhost:5432/rems
REMS_CHATBOT_API_URL=http://localhost:8000  # or cloud URL
REMS_CHATBOT_API_KEY=your-api-key
REMS_GOOGLE_API_KEY=your-google-api-key
REMS_EVALUATION_MODEL=gemini-2.0-flash
REMS_REPORTS_DIR=./reports
REMS_RECOMMENDATIONS_FILE=./recommendations.yaml
```

## Non-negotiable Constraints

Global SOLID / layer-separation principles apply (see `~/.claude/CLAUDE.md`). Project-specific bindings:

- **The core/full seam is the central invariant.** `src/rems/core/` is a lightweight library with only the base deps (`ragas`, `datasets`, `langchain`, `pydantic`) — it must import and run under a plain `pip install rems`, with no DB, no `structlog`, no Streamlit, no `httpx`. The full-app layers (`collector/`, `evaluators/`, `diagnostic/`, `recommendations/`, `models/`, `reports/`, `web/`) require `rems[app]`. **`core/` must never import from an app layer or from `rems.config`.** The two tiers duplicate logic on purpose (`core/evaluator.py` `RAGEvaluator` vs `evaluators/orchestrator.py` `EvaluationOrchestrator`; `core/schemas.py` dataclasses vs `schemas.py` Pydantic DTOs; `core/diagnostic.py` vs `diagnostic/engine.py`; `core/recommendations.py` vs `recommendations/engine.py`) — do not collapse them into a shared module that drags app deps into core.
- **Dependency inversion for the LLM.** Evaluators (`RAGEvaluator`, `MetricsEvaluator`, `EvaluationOrchestrator`) take injected LangChain `llm`/`embeddings`; `None` falls back to RAGAS defaults. The concrete Gemini wiring lives only in `cli.py::setup_llm()` — keep provider construction there, not inside evaluator classes. New full-app evaluators subclass `evaluators/base.py::BaseEvaluator`.
- **Config home.** All app tunables live in `src/rems/config.py` (`Settings`, `REMS_` env prefix, `.env`). The core library instead reads its own `EvaluationConfig` dataclass (`core/schemas.py`) so library users need no `.env`. Add new thresholds/knobs to both only when they must exist in both tiers; check here before hardcoding a value.
- **Secrets home.** `.env` (gitignored), keys `REMS_GOOGLE_API_KEY`, `REMS_CHATBOT_API_KEY`, `REMS_DATABASE_URL`. No keyring. Never read secrets outside `config.py`.

## Do Not Modify

- `.env` — real secrets (gitignored).
- `uv.lock` — regenerate only via `uv` commands.
- `/reports/` (repo-root, gitignored generated PDF/HTML) — distinct from the tracked code module `src/rems/reports/`.
- `/recommendations.yaml` (repo-root, gitignored generated output) — distinct from `recommendations/` code.
- `*.db` / `*.sqlite3`, `htmlcov/`, `.coverage`.

## Invariants

Commit style and logging conventions are global (English conventional commits; `structlog` for app-layer logging). Project-specific:

- **CI-green locally** = `uv run ruff check src/` and `uv run mypy src/`. There are no `.github/workflows` yet — these two commands are the gate.
- **mypy is `strict = true`, scoped to `src/`.** Keep it clean; RAGAS/`datasets` are already suppressed via inline `# type: ignore`.
- **ruff**: line-length 100, `select = ["E","F","I","N","W","UP"]`. No E501 suppression — wrap long lines.
- **No test suite exists yet** despite `pytest` being in `[dev]`. If you add tests, mock all external deps (RAGAS/Gemini/DB) exactly as the global test-mocking rule requires; put them under `tests/` mirroring module names.

## Multi-agent Orchestration

Global methodology and report template apply (see `~/.claude/CLAUDE.md`). Project bindings:

- **Tracking-file source of truth:** there is no dedicated `BACKLOG.md`/`TODO.md`/`PLAN.md`. `SESSION_RESUME.md` (its "Next Steps (Potential)" list) is the closest roadmap — read it for intent, do not create a parallel tracker.
- **Sub-agent → layer map:**

  | Concern | Directory |
  |---------|-----------|
  | Core library (import-safe) | `src/rems/core/` |
  | Full evaluation pipeline | `src/rems/evaluators/`, `src/rems/collector/` |
  | Diagnostics & recommendations | `src/rems/diagnostic/`, `src/rems/recommendations/` |
  | Persistence (SQLAlchemy) | `src/rems/models/` |
  | Reporting (WeasyPrint + Jinja2) | `src/rems/reports/` |
  | Streamlit UI | `src/rems/web/` |
  | Config & CLI | `src/rems/config.py`, `src/rems/cli.py` |

## Established Facts (don't re-question)

- **On-demand only, no scheduler.** Weekly scheduling was deliberately removed when the tool was generalized; there is no scheduler module and none should be re-added without discussion.
- **Generalized from a French regulatory tool** into a domain-agnostic English toolkit — do not reintroduce compliance/regulatory-specific naming or French UI strings.
- **RAGAS 0.4.x pin**: class-based metric imports and the `user_input`/`response`/`retrieved_contexts` column names (see "RAGAS 0.4.x API" above) are required — the old function/column API breaks.
- **`GoogleGenerativeAIEmbeddings` uses `models/embedding-001`**, hardcoded in `cli.py::setup_llm()` (the eval LLM model is configurable via `REMS_EVALUATION_MODEL`, the embedding model is not).

## Key Files

- `test_interactions.json` - Sample interactions for testing
- `scripts/simulate_evaluation.py` - Creates fake evaluation data (no LLM needed)
- `.env.example` - Environment variables template
