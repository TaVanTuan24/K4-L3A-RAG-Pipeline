"""
Task 8 — PageIndex vectorless fallback.

PageIndex (https://pageindex.ai) là dịch vụ retrieval không dùng vector DB. SDK
cài trong repo là ``pageindex==0.2.8``:

- ``PageIndexClient(api_key)``
- ``submit_document(file_path) -> {"doc_id": ...}``
- ``submit_query(doc_id, query) -> {"retrieval_id": ...}``
- ``get_retrieval(retrieval_id) -> {...}``

Luồng: nếu có ``PAGEINDEX_API_KEY``, standardize Markdown được chuyển thành PDF
tạm (fpdf2) rồi upload; document ID được cache vào ``pageindex_doc_ids.json``
(gitignored) để không upload lại. Khi search, query từng document và parse kết
quả retrieval thành ``SearchResult`` có ``retrieval_method="pageindex"``.

PageIndex là dịch vụ ngoài: mọi lỗi (thiếu API key, timeout, network failure,
provider unavailable, malformed response) đều được xử lý để pipeline không crash.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_FILE = PROJECT_ROOT / "pageindex_doc_ids.json"
TMP_PDF_DIR = PROJECT_ROOT / "data" / "_tmp_pdf"


def _load_cache() -> dict[str, str]:
    """Đọc mapping source-stem -> PageIndex doc_id đã cache."""
    if not CACHE_FILE.is_file():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_cache(cache: dict[str, str]) -> None:
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _get_client():
    """Tạo PageIndex client; raise rõ ràng khi thiếu API key."""
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY is not set")
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _markdown_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Chuyển Markdown thành PDF tạm để PageIndex upload (nó nhận PDF)."""
    from fpdf import FPDF

    text = md_path.read_text(encoding="utf-8")
    # Core font (helvetica) chỉ hỗ trợ latin-1; thay ký tự ngoài bảng mã.
    latin_text = text.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    for line in latin_text.splitlines():
        pdf.multi_cell(0, 4, line if line else " ")
    pdf.output(str(pdf_path))


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY missing — skip PageIndex upload (no-op).")
        return

    try:
        client = _get_client()
    except Exception as error:
        print(f"PageIndex unavailable during upload: {error}")
        return

    cache = _load_cache()
    TMP_PDF_DIR.mkdir(parents=True, exist_ok=True)
    changed = False

    for md_path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        stem = md_path.relative_to(STANDARDIZED_DIR).as_posix()
        if stem in cache:
            continue
        try:
            tmp_pdf = TMP_PDF_DIR / f"{md_path.stem}.pdf"
            _markdown_to_pdf(md_path, tmp_pdf)
            result = client.submit_document(str(tmp_pdf))
            doc_id = result.get("doc_id") if isinstance(result, dict) else None
            if not doc_id:
                print(f"No doc_id returned for {stem}: {result}")
                continue
            cache[stem] = doc_id
            changed = True
            print(f"Uploaded: {stem} -> {doc_id}")
        except Exception as error:
            print(f"Failed to upload {stem}: {error}")

    if changed:
        _save_cache(cache)
def _extract_passages(payload: object) -> list[dict]:
    """Parse defensive: tìm các đoạn text trong response retrieval của PageIndex."""
    passages: list[dict] = []

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            text = (
                node.get("text")
                or node.get("content")
                or node.get("snippet")
                or node.get("markdown")
            )
            if isinstance(text, str) and text.strip():
                passages.append(node)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return passages


def _metadata_for(stem: str, rank: int) -> dict:
    doc_type = "legal" if "legal" in stem else "news"
    title = stem.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ").title()
    return {
        "source": stem,
        "title": title,
        "doc_type": doc_type,
        "url": None,
        "chunk_index": rank,
    }


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult (fallback vectorless)."""
    if not PAGEINDEX_API_KEY or top_k <= 0:
        return []

    try:
        client = _get_client()
    except Exception as error:
        print(f"PageIndex unavailable during search: {error}")
        return []

    cache = _load_cache()
    if not cache:
        return []

    results: list[dict] = []
    for stem, doc_id in cache.items():
        try:
            submit = client.submit_query(doc_id, query)
            retrieval_id = (
                submit.get("retrieval_id") if isinstance(submit, dict) else None
            )
            if not retrieval_id:
                continue
            retrieval = client.get_retrieval(retrieval_id)
            for passage in _extract_passages(retrieval):
                content = (
                    passage.get("text")
                    or passage.get("content")
                    or passage.get("snippet")
                    or passage.get("markdown")
                    or ""
                ).strip()
                if not content:
                    continue
                results.append(
                    {
                        "id": f"pageindex::{doc_id}::{len(results)}",
                        "content": content,
                        # PageIndex không trả cosine score; gán giảm dần theo rank.
                        "score": max(0.0, 1.0 - 0.02 * len(results)),
                        "metadata": _metadata_for(stem, len(results)),
                        "retrieval_method": "pageindex",
                    }
                )
        except Exception as error:
            print(f"PageIndex search failed for {doc_id}: {error}")
            continue

    # Dedupe theo ID và giới hạn top_k.
    seen: set[str] = set()
    unique: list[dict] = []
    for result in results:
        if result["id"] in seen:
            continue
        seen.add(result["id"])
        unique.append(result)

    return unique[:top_k]


if __name__ == "__main__":
    upload_documents()
    print(pageindex_search("example query", top_k=3))