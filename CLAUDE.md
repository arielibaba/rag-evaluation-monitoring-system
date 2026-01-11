# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REMS (RAG Evaluation & Monitoring System) is a reusable Python toolkit for evaluating and monitoring RAG chatbot performance. It operates as an external observer without modifying the chatbot itself.

**Two usage modes:**
1. **Library**: Import `RAGEvaluator` directly in your RAG project (minimal dependencies)
2. **Full Application**: Web UI, database storage, PDF reports (requires `pip install rems[app]`)

## Library Usage

```python
from rems import RAGEvaluator, Interaction, EvaluationConfig

evaluator = RAGEvaluator()
results = evaluator.evaluate([
    Interaction(query="...", response="...", contexts=["..."])
])
print(f"Score: {results.overall_score:.1%}")
```

Core module location: `src/rems/core/` (schemas, evaluator, metrics, diagnostic, recommendations)

## Development Commands

```bash
# Install dependencies
uv sync

# Initialize database (PostgreSQL must be running)
uv run rems init-db

# Launch web interface
uv run rems web                    # Default port 8501
uv run rems web --port 8080        # Custom port

# Run evaluation from JSON file
uv run rems evaluate --file test_interactions.json --name "My Evaluation"

# Run evaluation from chatbot API
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
from ragas.metrics._context_recall import ContextRecall
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
REMS_CHATBOT_API_URL=http://localhost:8000
REMS_CHATBOT_API_KEY=your-api-key
REMS_GOOGLE_API_KEY=your-google-api-key
REMS_EVALUATION_MODEL=gemini-2.0-flash
REMS_REPORTS_DIR=./reports
REMS_RECOMMENDATIONS_FILE=./recommendations.yaml
```
