from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def home() -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{settings.app_name}</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f4efe6;
        --card: #fffaf2;
        --text: #1f2937;
        --muted: #5b6472;
        --accent: #0f766e;
        --accent-soft: #dff3ef;
        --border: #e5dccd;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, #fff7e8 0, transparent 30%),
          linear-gradient(135deg, #f7f3eb 0%, var(--bg) 45%, #efe5d6 100%);
      }}
      main {{
        max-width: 860px;
        margin: 0 auto;
        min-height: 100vh;
        padding: 48px 20px 72px;
        display: grid;
        gap: 20px;
        align-content: start;
      }}
      .hero, .card {{
        background: color-mix(in srgb, var(--card) 92%, white 8%);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 18px 60px rgba(31, 41, 55, 0.08);
      }}
      h1, h2, p {{ margin: 0; }}
      h1 {{
        font-size: clamp(2.2rem, 5vw, 4rem);
        line-height: 0.95;
        letter-spacing: -0.04em;
      }}
      .eyebrow {{
        display: inline-block;
        margin-bottom: 14px;
        padding: 6px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font: 600 0.78rem/1.1 system-ui, sans-serif;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      .lead {{
        margin-top: 14px;
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.6;
        max-width: 58ch;
      }}
      .actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 22px;
      }}
      a.button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        padding: 0 16px;
        border-radius: 999px;
        text-decoration: none;
        font: 600 0.95rem/1.1 system-ui, sans-serif;
      }}
      a.primary {{
        background: var(--accent);
        color: white;
      }}
      a.secondary {{
        border: 1px solid var(--border);
        color: var(--text);
        background: white;
      }}
      .grid {{
        display: grid;
        gap: 20px;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      }}
      .card h2 {{
        font-size: 1.1rem;
        margin-bottom: 10px;
      }}
      .card p {{
        color: var(--muted);
        line-height: 1.55;
      }}
      code {{
        font-family: "SFMono-Regular", "Menlo", monospace;
        font-size: 0.92em;
      }}
      ul {{
        margin: 12px 0 0;
        padding-left: 20px;
        color: var(--muted);
      }}
      li + li {{ margin-top: 8px; }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <span class="eyebrow">VidScribe API</span>
        <h1>Turn text, video, or Douyin links into article-ready output.</h1>
        <p class="lead">
          This service exposes a FastAPI + Celery workflow for text analysis, video transcription,
          and async job processing. Start with the API docs or hit the health checks below.
        </p>
        <div class="actions">
          <a class="button primary" href="/docs">Open Swagger UI</a>
          <a class="button secondary" href="/redoc">Open ReDoc</a>
          <a class="button secondary" href="/health">Health</a>
          <a class="button secondary" href="{settings.api_prefix}/health">Versioned Health</a>
        </div>
      </section>
      <section class="grid">
        <article class="card">
          <h2>Core endpoints</h2>
          <p>Use <code>POST {settings.api_prefix}/analyze-text</code>, <code>POST {settings.api_prefix}/analyze-video</code>, and <code>POST {settings.api_prefix}/jobs</code> for the main flows.</p>
        </article>
        <article class="card">
          <h2>Local development</h2>
          <p>Run <code>docker compose up --build</code> for the full stack, or start FastAPI and the Celery worker separately for local iteration.</p>
        </article>
        <article class="card">
          <h2>Operational note</h2>
          <p>Douyin parsing is best-effort only. Keep <code>raw_text</code> or uploaded video available as fallback input when possible.</p>
        </article>
      </section>
    </main>
  </body>
</html>"""

app.include_router(router)
app.include_router(router, prefix=settings.api_prefix)
