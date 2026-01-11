# REMS - RAG Evaluation & Monitoring System

A reusable toolkit for evaluating and monitoring RAG (Retrieval-Augmented Generation) chatbot performance. REMS operates as an external observer without modifying the chatbot itself.

## Features

- **RAGAS Evaluation**: Faithfulness, Context Precision, Answer Relevancy metrics
- **Hallucination Detection**: Automatic identification of unfaithful responses
- **Diagnostic Engine**: Root cause analysis with actionable recommendations
- **Web Dashboard**: Streamlit interface with metric visualization and trends
- **Reports**: PDF, HTML and YAML exports

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXISTING RAG CHATBOT                     │
│                        (REST API)                           │
└─────────────────────────┬───────────────────────────────────┘
                          │ query + response + retrieved_docs
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                         REMS                                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ API         │  │ Data Store  │  │ Evaluators          │ │
│  │ Collector   │─▶│ PostgreSQL  │─▶│ (RAGAS)             │ │
│  └─────────────┘  └─────────────┘  └──────────┬──────────┘ │
│                                               │             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────▼──────────┐ │
│  │ Report      │◀─│ Recommend.  │◀─│ Diagnostic          │ │
│  │ Generator   │  │ Engine      │  │ Engine              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │                │                                  │
│         ▼                ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Web Interface (Streamlit)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.12+
- PostgreSQL 14+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Installation

```bash
# Clone the repository
git clone https://github.com/arielibaba/rag-evaluation-monitoring-system.git
cd rag-evaluation-monitoring-system

# Install dependencies
uv sync

# Configure environment variables
cp .env.example .env
```

## Configuration

Edit the `.env` file:

```env
# PostgreSQL database
REMS_DATABASE_URL=postgresql://user:password@localhost:5432/rems

# Chatbot API to evaluate
REMS_CHATBOT_API_URL=http://localhost:8000
REMS_CHATBOT_API_KEY=your-api-key

# Google API for LLM-as-judge evaluation (Gemini)
REMS_GOOGLE_API_KEY=your-google-api-key
REMS_EVALUATION_MODEL=gemini-2.0-flash

# Output directories
REMS_REPORTS_DIR=./reports
REMS_RECOMMENDATIONS_FILE=./recommendations.yaml

# Diagnostic thresholds (optional - these are the defaults)
REMS_DIAG_CONTEXT_PRECISION=0.70
REMS_DIAG_CONTEXT_RELEVANCY=0.70
REMS_DIAG_FAITHFULNESS=0.70
REMS_DIAG_ANSWER_RELEVANCY=0.70
REMS_DIAG_HALLUCINATION_RATE=0.10
```

### Database Setup

```bash
# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql@16

# Create database
createdb rems

# Initialize tables
uv run rems init-db
```

## Usage

### Web Interface (Streamlit)

```bash
# Launch the dashboard
uv run rems web

# Custom port
uv run rems web --port 8080
```

Access **http://localhost:8501** for:
- 📊 **Dashboard**: Overall score, component metrics, gauge
- 📜 **History**: Score evolution, comparison between evaluations
- 🚀 **New Evaluation**: Run evaluation from file or API

### CLI

```bash
# Initialize database
uv run rems init-db

# Run evaluation from JSON file
uv run rems evaluate --file interactions.json --name "January Eval"

# Run evaluation from chatbot API
uv run rems evaluate --start 2026-01-01 --end 2026-01-07 --limit 100

# Collect interactions without evaluating
uv run rems collect --start 2026-01-01 --limit 100 --store

# Display help
uv run rems --help
```

## Input Data Format

The JSON interactions file must follow this format:

```json
{
  "interactions": [
    {
      "query": "What is the tax filing procedure?",
      "response": "According to article 12, the filing must be done within 3 months...",
      "retrieved_documents": [
        {
          "content": "Article 12 - Filing deadlines. Companies must...",
          "source": "tax_code.pdf",
          "score": 0.89
        }
      ]
    }
  ]
}
```

## Outputs

### YAML Recommendations File

```yaml
evaluation_id: "abc123"
evaluation_date: "2026-01-10T08:00:00"
overall_score: 0.784
quality_level: good
scores:
  retrieval: 0.723
  generation: 0.817
metrics:
  avg_faithfulness: 0.775
  avg_answer_relevancy: 0.858
  avg_context_precision: 0.723
  hallucination_rate: 0.2
  total_hallucinations: 1
recommendations:
  - component: generator
    priority: high
    issue: "faithfulness too low: 45% (threshold: 70%)"
    suggestion: "Reduce LLM temperature"
    parameter_adjustments:
      generator.temperature:
        action: decrease
        suggested_value: 0.3
```

### PDF/HTML Reports

Generated in the `reports/` folder with:
- Overall score with visual gauge
- Detailed metrics by component (Retrieval, Generation)
- Score distribution (Excellent, Good, Acceptable, Poor, Critical)
- Recommendations sorted by priority

## Evaluated Metrics

| Metric | Description | Component |
|--------|-------------|-----------|
| **Faithfulness** | Response fidelity to source documents | Generator |
| **Answer Relevancy** | Response relevance to the question | Generator |
| **Context Precision** | Precision of retrieved documents | Retriever |
| **Hallucination Rate** | Rate of unfaithful responses | Generator |

## Quality Levels

| Level | Score | Action |
|-------|-------|--------|
| Excellent | ≥ 90% | No action required |
| Good | 75-89% | Minor improvements possible |
| Acceptable | 60-74% | Improvements recommended |
| Poor | 40-59% | Corrective actions needed |
| Critical | < 40% | Urgent intervention required |

## Technologies

| Component | Technology |
|-----------|------------|
| RAG Evaluation | RAGAS 0.4.x |
| LLM-as-judge | LangChain + Google Gemini |
| Database | PostgreSQL + SQLAlchemy |
| Web Interface | Streamlit + Plotly |
| PDF Generation | WeasyPrint + Jinja2 |
| Configuration | Pydantic Settings |

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Linting
uv run ruff check src/

# Type checking
uv run mypy src/
```

## License

MIT
