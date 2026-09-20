"""
Task 2 — Crawl bài viết/trang thông tin sinh viên.

Dùng ``requests`` + ``html.parser`` (stdlib) để tải và chuyển HTML thành
Markdown thô. Điều này tránh phụ thuộc vào một headless browser (Playwright)
khi chỉ cần nội dung tĩnh công khai, và ổn định hơn trên các môi trường không
cài được Chromium.

- Mỗi bài được lưu thành ``data/landing/news/article_XX.json``.
- Schema: ``url``, ``title``, ``date_crawled``, ``content_markdown``.
- Lỗi từng URL được xử lý riêng để một URL hỏng không làm chết cả pipeline.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

from .dataset_registry import NEWS_ARTICLES

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
TIMEOUT = 30

_SKIP_TAGS = {
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "form",
    "noscript",
    "iframe",
    "svg",
    "button",
    "aside",
}
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _MarkdownHTMLParser(HTMLParser):
    """Chuyển HTML sang Markdown tối giản, bỏ nav/footer/script/style."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        elif tag in _HEADINGS:
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag in _HEADINGS or tag in {"p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
            return
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text + " ")


def html_to_markdown(html: str) -> tuple[str, str]:
    """Trả về (title, markdown) từ nội dung HTML."""
    parser = _MarkdownHTMLParser()
    parser.feed(html)
    markdown = re.sub(r"[ \t]+\n", "\n", "".join(parser.parts))
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return _clean_title(parser.title), markdown


def _clean_title(raw_title: str) -> str:
    """Chuẩn hóa <title> kiểu "Current students | Victoria University"."""
    title = re.sub(r"\s+", " ", raw_title).strip()
    for marker in ("|", "–", "-", "—"):
        if marker in title:
            title = title.split(marker)[0].strip()
            break
    return title or "Untitled"


def crawl_article(url: str, fallback_title: str = "") -> dict:
    """Crawl một URL và trả về dict theo schema article JSON."""
    response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding

    title, markdown = html_to_markdown(response.text)
    title = title or fallback_title or url

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": markdown,
    }


def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON, không dừng khi 1 URL lỗi."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, article in enumerate(NEWS_ARTICLES, 1):
        output = DATA_DIR / f"article_{index:02d}.json"
        try:
            data = crawl_article(article.url, fallback_title=article.title)
            output.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(
                f"Saved: {output.name} — {data['title']} "
                f"({len(data['content_markdown'])} chars)"
            )
        except (requests.RequestException, ValueError) as error:
            print(f"Failed: {article.url} — {error}")

    print(f"News crawl finished for {len(NEWS_ARTICLES)} URLs.")


if __name__ == "__main__":
    crawl_all()