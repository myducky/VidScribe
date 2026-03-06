# Repository Guidelines

## Coding Rules
- Target Python 3.11 and keep all new code fully type hinted.
- Prefer small, testable service modules with explicit inputs and outputs.
- Keep FastAPI handlers thin; business logic belongs in `app/services/` or `app/tasks/`.
- Treat Douyin parsing as best-effort only. Do not block core flows on it.
- Preserve graceful fallback across `douyin_url`, `raw_text`, and `uploaded_video`.
- Use environment variables from `.env`; do not hardcode secrets.
- Add structured logging for operationally relevant events and failures.
- Return predictable JSON shapes and Pydantic-validated payloads.
- When an external dependency may be unavailable, provide a clean fallback or raise a clear domain error.
- Write or update tests for schema changes, service logic, and API behavior.

## Implementation Priorities
1. Keep `/health` and `/v1/analyze-text` stable.
2. Maintain the async job pipeline contract and per-step status tracking.
3. Prefer reliable local processing over brittle scraping behavior.
4. Keep Docker-based local startup working.
