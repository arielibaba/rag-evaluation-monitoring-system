# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REMS (RAG Evaluation & Monitoring System) is a Python module that evaluates and monitors the performance of an existing regulatory RAG chatbot. It operates as an external observer without modifying the chatbot itself.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras

# Initialize database
uv run rems init-db

# Launch web interface (Streamlit dashboard)
uv run rems web
uv run rems web --port 8080  # Custom port

# Run evaluation from JSON file
uv run rems evaluate --file interactions.json

# Run evaluation from chatbot API
uv run rems evaluate --start 2026-01-01 --limit 100

# Run tests
uv run pytest

# Run linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

## Weekly Scheduled Evaluation

Use cron for weekly evaluations:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Monday at 8:00 AM)
0 8 * * 1 /path/to/project/scripts/weekly_evaluation.sh
```

## Architecture

```
src/rems/
├── cli.py                 # CLI entry point (init-db, evaluate, web)
├── config.py              # Pydantic settings (env vars)
├── schemas.py             # Pydantic data transfer objects
├── models/                # SQLAlchemy models + database session
├── collector/             # API Collector (fetches interactions from chatbot)
├── evaluators/            # RAGAS-based evaluators
│   ├── retrieval_evaluator.py   # Context precision/relevancy
│   ├── generator_evaluator.py   # Faithfulness, hallucination detection
│   └── orchestrator.py          # Coordinates all evaluators
├── diagnostic/            # Root cause analysis engine
├── recommendations/       # Generates suggestions + YAML export
├── reports/               # PDF/HTML report generation
│   └── templates/         # Jinja2 HTML templates
└── web/                   # Streamlit web interface
    ├── app.py             # Main Streamlit app
    └── pages/             # Dashboard, History, Evaluate pages
```

## Key Dependencies

- **RAGAS** - RAG evaluation metrics (faithfulness, context precision/recall, answer relevancy)
- **LangChain + Gemini** - LLM-as-judge for evaluation
- **SQLAlchemy** - Database ORM (PostgreSQL)
- **WeasyPrint** - PDF generation from HTML
- **Streamlit + Plotly** - Web dashboard interface
- **Giskard** (optional) - Test dataset generation

## Configuration

Copy `.env.example` to `.env` and configure:
- `REMS_DATABASE_URL` - PostgreSQL connection string
- `REMS_CHATBOT_API_URL` - URL of the chatbot API to evaluate
- `REMS_GOOGLE_API_KEY` - Google API key for Gemini evaluation model

## Domain Context

This system evaluates a regulatory/legal domain chatbot where:
- Accuracy is critical (legal consequences for errors)
- All responses must be traceable to source documents
- Hallucinations must be detected and flagged (faithfulness < 0.7)
- Recommendations are output to YAML for manual application
