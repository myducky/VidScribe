# Clip2Article

Clip2Article is a FastAPI + Celery MVP that turns Douyin links, pasted text, or uploaded videos into a WeChat official account article package.

## Implementation Plan
1. Phase 1: make `raw_text` fully runnable through `/v1/analyze-text` and the async pipeline.
2. Phase 2: add uploaded video ingestion, audio extraction, and Whisper transcription.
3. Phase 3: add modular best-effort Douyin resolution without blocking the rest of the system.

## Features
- FastAPI API surface for direct analysis and async jobs
- PostgreSQL-backed job, step, and artifact metadata
- Redis + Celery async execution
- Local file storage for transcripts and exported JSON
- OpenAI-compatible LLM abstraction with deterministic fallback mode
- FFmpeg + Whisper integration for local video processing

## Repository Layout
- `app/`: application source
- `tests/`: automated tests
- `scripts/`: helper scripts
- `sample_data/`: example payloads and fixtures

## Quick Start
### 1. Configure environment
```bash
cp .env.example .env
```

### 2. Start services
```bash
docker-compose up --build
```

### 3. Run the API locally without Docker
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export DATABASE_URL=sqlite+pysqlite:///./clip2article.db
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
uvicorn app.main:app --reload
```

### 4. Start the worker
```bash
source .venv/bin/activate
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

`/v1/jobs` requires a reachable Celery broker and a running worker. In local development that means Redis must be running before you submit a job. Celery task results are not used by this app, so the Redis result backend is optional for request submission. The `.env.example` values point at Docker service names, so for non-Docker local runs you must override them to `localhost` as shown above.

## Startup Commands
```bash
docker-compose up --build
docker-compose exec api pytest
```

## Example API Requests
### Health
```bash
curl http://localhost:8000/health
```

### Analyze text
```bash
curl -X POST http://localhost:8000/v1/analyze-text \
  -H "Content-Type: application/json" \
  -d @sample_data/analyze_text_request.json
```

### Create async job from text
```bash
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d @sample_data/create_job_request.json
```

### Analyze uploaded video
```bash
curl -X POST http://localhost:8000/v1/analyze-video \
  -F "file=@sample_data/demo.mp4"
```

## Sample Response Shape
```json
{
  "job_id": "0d6d3ff3-f8e5-4f89-a5f6-2e02f7f5f5d8",
  "input_type": "raw_text",
  "status": "SUCCESS",
  "title_candidates": ["标题一", "标题二", "标题三"],
  "summary": "120 字以内摘要",
  "outline": ["背景", "核心内容", "结论"],
  "highlights": ["亮点 1", "亮点 2"],
  "tags": ["短视频", "公众号文章"],
  "article_markdown": "# 正文\n\n内容",
  "cover": {
    "prompt": "中文封面概念",
    "layout": "居中标题 + 副标题",
    "text_on_cover": "封面短文案"
  },
  "source": {
    "language": "zh",
    "duration_sec": 0,
    "transcript_raw": "原始文本",
    "transcript_clean": "清洗后文本"
  }
}
```

## Testing
```bash
pytest
```

## Known Limitations
- Douyin parsing is best-effort and may fail because of anti-bot protections or source changes.
- For reliable processing, prefer `raw_text` or uploaded local video input.
- Whisper transcription depends on local FFmpeg availability and model download/runtime environment.
- If no OpenAI-compatible API is configured, the app falls back to a deterministic local generator for MVP continuity.
