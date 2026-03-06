# VidScribe

VidScribe 是一个基于 FastAPI + Celery 的服务，用来把文本、上传视频，或可解析的视频网页链接整理成公众号文章素材包。

当前建议：
- 优先使用公开的 B 站视频链接，成功率更高
- 抖音链接仅做尽力解析，成功率明显低于 B 站
- 逐步增加对 YouTube 等公开视频网站的探测、下载与分析能力
- 计划支持英文、日文等其他语种视频内容，并在分析后直接整理成中文公众号文章
- 如果来源平台不稳定，优先准备 `raw_text` 或本地上传视频作为回退输入

## 当前能力

- `POST /v1/analyze-text`：直接分析粘贴文本
- `POST /v1/analyze-video`：上传本地视频并完成转写和内容整理
- `POST /v1/analyze-remote-video`：直接传远程视频链接并同步返回分析结果，当前优先推荐公开的 B 站视频链接
- `POST /v1/jobs`：提交异步任务，支持 `raw_text`、`uploaded_video`、`bilibili_url`、`douyin_url`
- `POST /v1/probe-video-url`：探测视频网页链接是否可解析，支持 B 站和抖音
- `POST /v1/probe-douyin`：保留的抖音专用探测接口

## 推荐输入策略

1. 最推荐：公开的 B 站视频链接
2. 次推荐：本地上传视频
3. 稳定兜底：`raw_text`
4. 可选尝试：抖音链接

原因：
- B 站公开视频通常可以直接解析元信息并下载
- 抖音经常受链接形态、cookies、反爬策略影响
- 文本和本地视频的整体可控性最高

## 环境要求

- Python 3.11
- FFmpeg
- Redis
- PostgreSQL
- 可选的 OpenAI 兼容接口

## 环境变量

先复制配置：

```bash
cp .env.example .env
```

主要变量：

```env
APP_NAME=VidScribe
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
API_PREFIX=/v1
LOG_LEVEL=INFO

DATABASE_URL=postgresql+psycopg://vidscribe:vidscribe@postgres:5432/vidscribe
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

OPENAI_BASE_URL=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SEC=60

WHISPER_MODEL=base
STORAGE_DIR=storage
MAX_UPLOAD_MB=300

DOUYIN_COOKIE_FILE=
DOUYIN_COOKIES_FROM_BROWSER=
```

说明：
- 如果没有配置 OpenAI 兼容接口，系统会退回本地确定性生成逻辑，方便开发联调
- 当抖音要求新鲜 cookies 时，可以配置 `DOUYIN_COOKIE_FILE` 或 `DOUYIN_COOKIES_FROM_BROWSER`
- 两者同时设置时，优先使用 `DOUYIN_COOKIE_FILE`

## 启动方式

### Docker

```bash
docker compose up --build
```

查看日志：

```bash
docker compose logs -f api worker
```

### 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export DATABASE_URL=sqlite+pysqlite:///./vidscribe.db
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
uvicorn app.main:app --reload
```

另开一个终端启动 worker：

```bash
source .venv/bin/activate
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## 常用地址

- 首页：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc：[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- 版本化健康检查：[http://127.0.0.1:8000/v1/health](http://127.0.0.1:8000/v1/health)

## 接口示例

### 1. 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 2. 分析文本

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze-text \
  -H "Content-Type: application/json" \
  -d @sample_data/analyze_text_request.json
```

### 3. 探测视频网页链接

推荐先探测，再决定是否下载或回退。

#### 推荐示例：B 站

```bash
curl -X POST http://127.0.0.1:8000/v1/probe-video-url \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://www.bilibili.com/video/BV1S5PrzZEzQ"}'
```

#### 抖音示例

```bash
curl -X POST http://127.0.0.1:8000/v1/probe-video-url \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://v.douyin.com/3aoA22_an4o/"}'
```

返回字段说明：
- `platform`：识别出的平台，当前为 `bilibili`、`douyin` 或 `unknown`
- `downloadable`：当前是否可下载
- `normalized_url`：规范化后的目标链接
- `reason_code`：失败原因码，如 `cookies_required`、`unsupported_url`
- `detail`：可直接展示给用户的说明

### 4. 上传视频分析

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze-video \
  -F "file=@sample_data/demo.mp4"
```

### 5. 同步分析远程视频链接

推荐公开的 B 站视频链接：

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze-remote-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_url":"https://www.bilibili.com/video/BV1S5PrzZEzQ",
    "raw_text":"可选回退文本"
  }'
```

### 6. 提交异步任务

```bash
curl -X POST http://127.0.0.1:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d @sample_data/create_job_request.json
```

直接提交 B 站链接任务：

```bash
curl -X POST http://127.0.0.1:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "input_type":"bilibili_url",
    "bilibili_url":"https://www.bilibili.com/video/BV1S5PrzZEzQ",
    "raw_text":"可选回退文本，建议在链接下载失败时备用"
  }'
```

## 返回结构示例

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

## 测试

```bash
pytest
```

## 已知限制

- B 站公开视频链接整体可行，但部分清晰度、会员内容、地区限制内容可能需要 cookies
- 抖音链接成功率较低，常见问题包括：
  - 链接形态不支持
  - 需要 fresh cookies
  - 平台反爬策略变化
- Whisper 转写依赖本地 FFmpeg 和模型运行环境
- 在 CPU 环境下，较长视频的转写耗时会明显上升

## 后续规划

- 在现有 B 站链路稳定的基础上，继续扩展更多视频平台支持
- 后续会把通用探测和远程分析入口扩展成统一的平台适配层，减少接入新站点时的重复开发
- 会逐步补齐跨平台的视频元信息抽取、下载、转写、翻译与中文成稿能力
- 对于需要登录、cookies 或地区限制的平台，会优先提供清晰的探测结果和可解释的失败原因

## 开发建议

- 如果你要做“先判断能不能下载，再决定是否继续分析”，优先用 `POST /v1/probe-video-url`
- 如果你要稳定产出，优先把主流程建立在 B 站链接、本地视频和 `raw_text` 上
- 不建议把抖音链接抓取当成唯一核心输入链路
