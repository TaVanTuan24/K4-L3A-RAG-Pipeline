"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 4/Task 5 (cùng ID, cùng nội dung). BM25 phù hợp
với từ khóa chính xác, mã tài liệu và tên riêng. Output theo SearchResult và sort
score giảm dần, không trùng ID.

``CORPUS`` là module-global để các contract test có thể monkeypatch; trong chạy
thật, ``load_corpus()`` nạp corpus từ standardization một lần và cache lại.
"""

from __future__ import annotations

CORPUS: list[dict] = []


def _tokenize(text: str) -> list[str]:
    return (text or "").lower().split()


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    tokenized = [_tokenize(item["content"]) for item in corpus]
    return BM25Okapi(tokenized)


def load_corpus() -> list[dict]:
    """Nạp lại corpus chunks một cách ổn định và cache vào ``CORPUS``."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    return CORPUS


def _overlap_scores(corpus: list[dict], tokens: list[str]) -> list[float]:
    """Fallback: đếm số query term xuất hiện trong mỗi document.

    Trên corpus rất nhỏ, BM25Okapi có thể trả toàn 0.0 (IDF = 0 khi một term
    xuất hiện trong khoảng một nửa số document). Fallback này đảm bảo keyword
    khớp chính xác vẫn xếp hạng đúng và ổn định.
    """
    query_terms = set(tokens)
    scores: list[float] = []
    for item in corpus:
        doc_terms = set(_tokenize(item["content"]))
        scores.append(float(len(query_terms & doc_terms)))
    return scores


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus = CORPUS or load_corpus()
    if not corpus or top_k <= 0:
        return []

    import numpy as np

    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = bm25_scores = build_bm25_index(corpus).get_scores(tokens)
    if float(np.max(bm25_scores)) <= 0.0:
        scores = _overlap_scores(corpus, tokens)

    order = np.argsort(np.asarray(scores, dtype=float))[::-1]

    seen: set[str] = set()
    results: list[dict] = []
    for index in order:
        if float(scores[index]) <= 0:
            continue
        item = corpus[int(index)]
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": item["metadata"],
                "retrieval_method": "bm25",
            }
        )
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    load_corpus()
    for result in lexical_search("scholarship", top_k=3):
        print(result)