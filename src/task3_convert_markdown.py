"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

- Legal PDF/DOCX -> ``data/standardized/legal/*.md`` bằng MarkItDown.
- Article JSON -> ``data/standardized/news/*.md`` (giữ metadata nguồn).

Metadata (title/source/url/doc_type/crawled date) được nhúng vào đầu mỗi file
Markdown dưới dạng front-matter HTML comment để ``load_documents()`` (Task 4)
parse lại chính xác. Việc ghi đè (deterministic) đảm bảo chạy lại không tạo file
trùng; không ghi file rỗng.
"""

from __future__ import annotations

import json
from pathlib import Path

from .dataset_registry import LEGAL_TITLES, LEGAL_URLS

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _front_matter(
    title: str,
    source: str,
    doc_type: str,
    url: str | None,
    crawled: str | None = None,
) -> str:
    """Tạo header metadata cho một file Markdown chuẩn hóa."""
    lines = [
        "<!--",
        f"title: {title}",
        f"source: {source}",
        f"doc_type: {doc_type}",
        f"url: {url or ''}",
    ]
    if crawled:
        lines.append(f"date_crawled: {crawled}")
    lines.append("-->")
    return "\n".join(lines) + "\n\n"


def convert_legal_docs() -> None:
    """Convert PDF/DOCX trong landing/legal sang standardized/legal."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        stem = path.stem
        try:
            result = converter.convert(str(path))
            body = (result.text_content or "").strip()
        except Exception as error:  # pragma: no cover - depends on converter
            print(f"Failed to convert {path.name}: {error}")
            continue
        if len(body) < 50:
            print(f"Skipped empty/minimal content: {path.name}")
            continue

        header = _front_matter(
            title=LEGAL_TITLES.get(stem, stem.replace("_", " ").title()),
            source=path.name,
            doc_type="legal",
            url=LEGAL_URLS.get(stem),
        )
        output = output_dir / f"{stem}.md"
        output.write_text(header + body, encoding="utf-8")
        print(f"Converted legal: {output.name} ({len(body)} chars)")


def convert_news_articles() -> None:
    """Convert article JSON trong landing/news sang standardized/news."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"Skipped invalid JSON {path.name}: {error}")
            continue

        title = data.get("title", path.stem)
        source = data.get("url", "")
        crawled = data.get("date_crawled", "")
        body = (data.get("content_markdown") or "").strip()

        header = _front_matter(
            title=title,
            source=source,
            doc_type="news",
            url=source or None,
            crawled=crawled or None,
        )
        output = output_dir / f"{path.stem}.md"
        output.write_text(header + body, encoding="utf-8")
        print(f"Converted news: {output.name} ({len(body)} chars)")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()