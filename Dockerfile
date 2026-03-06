FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY tests /app/tests
COPY scripts /app/scripts
COPY sample_data /app/sample_data
COPY .env.example /app/.env.example
COPY AGENTS.md /app/AGENTS.md

RUN pip install --upgrade pip && pip install -e .[dev]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
