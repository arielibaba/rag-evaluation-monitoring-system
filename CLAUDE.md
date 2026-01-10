# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REMS (RAG Evaluation & Monitoring System) is a Python module that evaluates and monitors the performance of an existing regulatory RAG chatbot. It operates as an external observer without modifying the chatbot itself.

## Development Commands

```bash
# Create/activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv sync

# Run the application
uv run python main.py
```

## Architecture

REMS is structured as a layered system with the following core modules (to be implemented):

1. **Data Collector** - Collects interactions from the chatbot via webhook, API polling, log reading, or database connection
2. **Evaluators** - Component-specific evaluators:
   - Retrieval Evaluator (context relevancy, precision, recall)
   - Query Reformulator Evaluator (intent preservation, semantic similarity)
   - Generator Evaluator (faithfulness, hallucination detection, answer relevancy)
   - Memory/History Evaluator (context coherence, contradiction detection)
   - End-to-End Evaluator (orchestration and global scoring)
3. **Root Cause Analyzer** - Diagnoses causes of quality issues
4. **Remediation Engine** - Generates recommendations and automated fixes
5. **Reporting** - Generates PDF/HTML reports and Grafana dashboards
6. **Alerting** - Real-time alerts based on configurable thresholds

## Key Dependencies (Planned)

- **RAGAS** - For standardized RAG metrics (faithfulness, context precision/recall, answer relevancy)
- **Giskard** - For hallucination detection, vulnerability scanning, LLM-as-judge evaluations

## Domain Context

This system evaluates a regulatory/legal domain chatbot where:
- Accuracy is critical (legal consequences for errors)
- All responses must be traceable to source documents
- Hallucinations must be detected and flagged
- Outdated information must be identified
