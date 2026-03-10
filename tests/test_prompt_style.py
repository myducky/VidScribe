from app.core.config import Settings
from app.services.article_writer import ArticleWriter
from app.services.prompt_loader import PromptLibrary
from app.services.summarizer import Summarizer


class StubLLMClient:
    def __init__(self, response: str = "LLM_FALLBACK::stub") -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def test_article_writer_prompt_includes_author_persona_and_style_constraints():
    llm = StubLLMClient("<h1>文章</h1>")
    writer = ArticleWriter(llm, Settings())

    writer.generate(
        "原始素材",
        {
            "summary": "摘要",
            "outline": ["一", "二"],
            "highlights": ["观察一", "观察二"],
            "title_candidates": ["标题"],
        },
        desired_length=1000,
    )

    system_prompt, user_prompt = llm.calls[0]
    assert "clean HTML" in system_prompt
    assert "长期趋势研究者" in system_prompt
    assert "不喊口号" in system_prompt
    assert "HTML 输出" in system_prompt
    assert "优先写出判断、观察和结构变化" in user_prompt
    assert "不要输出 Markdown" in user_prompt


def test_summarizer_prompt_includes_trend_and_structural_change_guidance():
    llm = StubLLMClient('{"summary":"摘要","outline":["一"],"highlights":["二"],"tags":["三"],"title_candidates":["四","五","六"]}')
    summarizer = Summarizer(llm, Settings())

    summarizer.summarize("原始素材")

    system_prompt, user_prompt = llm.calls[0]
    assert "long-term trend researcher" in system_prompt
    assert "structural change" in system_prompt
    assert "not clickbait headlines" in user_prompt
    assert "restrained judgment" in user_prompt


def test_article_writer_fallback_uses_more_natural_observation_style():
    llm = StubLLMClient("LLM_FALLBACK::stub")
    writer = ArticleWriter(llm, Settings())

    article = writer.generate(
        "原始素材",
        {
            "summary": "这是一段摘要。",
            "outline": ["一", "二"],
            "highlights": ["这件变化背后有更深的结构信号", "很多判断需要放在更长周期里看"],
            "title_candidates": ["一个标题"],
        },
    )

    assert article.startswith("<h1>")
    assert "这件事真正值得注意的地方在于" in article
    assert "很多人会先盯着表层信息" in article
    assert "如果把时间维度稍微拉长一点看" in article


def test_prompt_library_reads_sections_from_file(tmp_path):
    prompt_file = tmp_path / "writing_style.md"
    prompt_file.write_text(
        "## article_persona\n人格A\n\n## article_requirements\n要求B\n\n## summarizer_style\n风格C\n\n## transcript_refiner_style\n风格D\n",
        encoding="utf-8",
    )

    library = PromptLibrary(Settings(WRITING_STYLE_FILE=str(prompt_file)))

    assert library.get("article_persona") == "人格A"
    assert library.get("article_requirements") == "要求B"
    assert library.get("summarizer_style") == "风格C"
    assert library.get("transcript_refiner_style") == "风格D"
