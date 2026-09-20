"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy ``semantic_search`` và ``lexical_search``.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi/rỗng, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau. ``score_threshold``
được đọc từ environment ``SCORE_THRESHOLD`` (default an toàn 0.30) và hiệu chỉnh
bằng query in-domain/out-of-domain (xem ``group_project/evaluation/RESULT.md``).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

load_dotenv()

DEFAULT_TOP_K = 5


def _default_score_threshold() -> float:
    """Đọc SCORE_THRESHOLD từ env, trả về default an toàn nếu không hợp lệ."""
    raw = os.getenv("SCORE_THRESHOLD", "0.30")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.30
    return value


SCORE_THRESHOLD = _default_score_threshold()


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float | None = None,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    if score_threshold is None:
        score_threshold = SCORE_THRESHOLD

    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)

    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking
        else dense[:top_k]
    )

    # Fallback quyết định bằng cosine similarity gốc của dense search.
    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback[:top_k]
        except Exception:
            # Provider lỗi -> trả hybrid, không crash.
            pass

    return hybrid[:top_k]


if __name__ == "__main__":
    for result in retrieve("Scholarships", top_k=3):
        print(result)