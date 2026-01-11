# REMS - RAG Evaluation & Monitoring System

A reusable toolkit for evaluating and monitoring RAG (Retrieval-Augmented Generation) chatbot performance. REMS operates as an external observer without modifying the chatbot itself.

**Evaluate any RAG system** - whether running locally or in the cloud - via API calls or JSON file input.

## Features

- **RAGAS Evaluation**: Faithfulness, Context Precision, Answer Relevancy metrics
- **Hallucination Detection**: Automatic identification of unfaithful responses
- **Diagnostic Engine**: Root cause analysis with actionable recommendations
- **Lightweight Library**: Import directly in your RAG project for evaluation
- **Web Dashboard**: Streamlit interface with metric visualization and trends
- **Reports**: PDF, HTML and YAML exports

## Quick Start (Library Usage)

Install the core library with minimal dependencies:

```bash
pip install rems
```

Use it in your RAG project:

```python
from rems import RAGEvaluator, Interaction

# Initialize evaluator (uses RAGAS defaults)
evaluator = RAGEvaluator()

# Evaluate your RAG interactions
results = evaluator.evaluate([
    Interaction(
        query="What is the return policy?",
        response="Items can be returned within 30 days of purchase.",
        contexts=["Return Policy: Items may be returned within 30 days..."]
    )
])

# Access results
print(f"Overall score: {results.overall_score:.1%}")
print(f"Quality level: {results.quality_level.value}")

# Get diagnostic insights
for issue in results.issues:
    print(f"Issue: {issue.symptom} ({issue.severity.value})")

# Get recommendations
for rec in results.recommendations:
    print(f"Recommendation: {rec.suggestion}")
```

### With Custom LLM

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from rems import RAGEvaluator, EvaluationConfig

# Custom config with thresholds
config = EvaluationConfig(
    faithfulness_threshold=0.8,
    context_precision_threshold=0.75,
    hallucination_rate_threshold=0.05
)

# Custom LLM for evaluation
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

evaluator = RAGEvaluator(llm=llm, config=config)
results = evaluator.evaluate(interactions)
```

### Evaluate a Single Interaction

```python
result = evaluator.evaluate_single(
    query="What is the shipping cost?",
    response="Shipping is free for orders over $50.",
    contexts=["Shipping Policy: Free shipping on orders above $50..."]
)

print(f"Faithfulness: {result.faithfulness:.1%}")
print(f"Has hallucination: {result.has_hallucination}")
```

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

## Installation

### Library Only (Minimal Dependencies)

```bash
pip install rems
```

Core dependencies: `ragas`, `datasets`, `langchain`, `pydantic`

### Full Application (Web UI, Database, Reports)

```bash
pip install rems[app]
```

Additional dependencies: `streamlit`, `sqlalchemy`, `weasyprint`, etc.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/arielibaba/rag-evaluation-monitoring-system.git
cd rag-evaluation-monitoring-system

# Install all dependencies
uv sync --all-extras

# Configure environment variables
cp .env.example .env
```

Requirements for full application:
- Python 3.12+
- PostgreSQL 14+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

## Configuration

Edit the `.env` file:

```env
# PostgreSQL database
REMS_DATABASE_URL=postgresql://user:password@localhost:5432/rems

# RAG Chatbot API to evaluate (local or cloud)
# Examples:
#   Local:  http://localhost:8000
#   Cloud:  https://my-rag-chatbot.example.com/api
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

# Evaluate from JSON file (offline mode)
uv run rems evaluate --file interactions.json --name "January Eval"

# Evaluate from RAG API (local or cloud)
# Fetches interactions from REMS_CHATBOT_API_URL
uv run rems evaluate --start 2026-01-01 --end 2026-01-07 --limit 100

# Collect interactions from RAG API without evaluating
uv run rems collect --start 2026-01-01 --limit 100 --store

# Display help
uv run rems --help
```

**Two evaluation modes:**
1. **File-based**: Evaluate pre-collected interactions from a JSON file
2. **API-based**: Fetch and evaluate interactions directly from your RAG system's API

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
