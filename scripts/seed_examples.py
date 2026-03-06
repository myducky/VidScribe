from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sample_dir = root / "sample_data"
    sample_dir.mkdir(exist_ok=True)
    (sample_dir / "analyze_text_request.json").write_text(
        '{"raw_text":"这里是一段可直接调用 /v1/analyze-text 的示例文本。它描述如何把短视频内容转成公众号文章。","desired_length":1200,"language":"zh"}',
        encoding="utf-8",
    )
    (sample_dir / "create_job_request.json").write_text(
        '{"input_type":"raw_text","raw_text":"这里是一段可直接提交异步任务的示例文本。"}',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
