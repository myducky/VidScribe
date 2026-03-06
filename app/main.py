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
<html lang="zh-CN">
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
        <h1>把文本、视频或网页链接整理成可发布文章。</h1>
        <p class="lead">
          这是一个基于 FastAPI + Celery 的内容整理服务，支持文本分析、视频转写和异步任务。
          如果你要用网页链接，优先推荐公开的 B 站视频链接；抖音链接只做尽力解析。
        </p>
        <div class="actions">
          <a class="button primary" href="/docs">打开 Swagger UI</a>
          <a class="button secondary" href="/redoc">打开 ReDoc</a>
          <a class="button secondary" href="/health">健康检查</a>
          <a class="button secondary" href="{settings.api_prefix}/health">版本化健康检查</a>
        </div>
      </section>
      <section class="grid">
        <article class="card">
          <h2>核心接口</h2>
          <p>主流程使用 <code>POST {settings.api_prefix}/analyze-text</code>、<code>POST {settings.api_prefix}/analyze-video</code>、<code>POST {settings.api_prefix}/analyze-remote-video</code> 和 <code>POST {settings.api_prefix}/jobs</code>。探测网页链接时使用 <code>POST {settings.api_prefix}/probe-video-url</code>。</p>
        </article>
        <article class="card">
          <h2>本地开发</h2>
          <p>执行 <code>docker compose up --build</code> 启动完整栈，或分别启动 FastAPI 和 Celery worker 进行本地调试。</p>
        </article>
        <article class="card">
          <h2>使用建议</h2>
          <p>优先使用公开的 B 站视频链接。抖音解析成功率较低，建议同时准备 <code>raw_text</code> 或本地上传视频作为回退输入。</p>
        </article>
      </section>
    </main>
  </body>
</html>"""

app.include_router(router)
app.include_router(router, prefix=settings.api_prefix)
