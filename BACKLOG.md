# Backlog — REMS (RAG Evaluation & Monitoring System)

Tracking file for REMS, a reusable toolkit for evaluating and monitoring RAG
chatbot performance as an external observer.

## Done

→ Closed section, moved verbatim to `BACKLOG-ARCHIVE.md` on 2026-10-19 (find it with `grep`).

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
