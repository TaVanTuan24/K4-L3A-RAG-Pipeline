"""
Calibrate ``SCORE_THRESHOLD`` using in-domain vs out-of-domain queries.

Chạy sau khi đã build index (Task 4):

    python -m src.calibrate_threshold

In ra best dense cosine similarity cho từng nhóm query để chọn threshold có lý do.
Kết quả được dùng để điền ``SCORE_THRESHOLD`` vào ``.env`` và ``RESULT.md``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import load_corpus

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "group_project" / "evaluation" / "golden_dataset.json"

IN_DOMAIN = [
    "What scholarships are available for students?",
    "What does the Support for Students Policy cover?",
    "When do library services finish before closing time?",
    "How many libraries does Victoria University have?",
    "What happens if a student breaches the Student Conduct Policy?",
]

OUT_OF_DOMAIN = [
    "What is the capital of France?",
    "How do I cook spaghetti bolognese?",
    "Who won the FIFA World Cup in 1990?",
    "Explain quantum entanglement.",
    "What is the weather forecast for tomorrow?",
]


def _best_dense(query: str) -> float:
    results = semantic_search(query, top_k=3)
    return results[0]["score"] if results else 0.0


def main() -> None:
    load_corpus()
    in_scores = [_best_dense(q) for q in IN_DOMAIN]
    out_scores = [_best_dense(q) for q in OUT_OF_DOMAIN]

    print("=== In-domain best dense scores ===")
    for q, s in zip(IN_DOMAIN, in_scores):
        print(f"  {s:.4f}  {q}")
    print(f"  min={min(in_scores):.4f} mean={sum(in_scores)/len(in_scores):.4f}")

    print("\n=== Out-of-domain best dense scores ===")
    for q, s in zip(OUT_OF_DOMAIN, out_scores):
        print(f"  {s:.4f}  {q}")
    print(f"  max={max(out_scores):.4f} mean={sum(out_scores)/len(out_scores):.4f}")

    # Gợi ý threshold: tách tốt nhất giữa out-of-domain max và in-domain min.
    print("\nSuggested threshold: between out-of-domain max and in-domain min.")


if __name__ == "__main__":
    main()