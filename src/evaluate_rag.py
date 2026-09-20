"""
Evaluation script — A/B so sánh retrieval.

Config A (dense-only) vs Config B (hybrid = dense + BM25 + RRF).

Do không có LLM/API key trong môi trường này, các metric cần LLM của RAGAS
(faithfulness, answer_relevancy, context_precision dùng LLM) không chạy được thật;
thay vào đó script luôn đo được các retrieval metric bằng embedding local
(``BAAI/bge-m3``) một cách khách quan:

- context_recall    : mức độ retrieved chunks bao phủ nội dung ``expected_context``.
- context_precision : tỷ lệ retrieved chunks "relevant" (similarity > threshold)
                      so với ``expected_context``.
- recall_at_k / mrr : hỗ trợ.

Kết quả ghi ra ``group_project/evaluation/evaluation_results.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.task4_chunking_indexing import embed_texts
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search, load_corpus
from src.task7_reranking import rerank_rrf

ROOT = Path(__file__).parent.parent
GOLDEN_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "evaluation_results.json"

TOP_K = 5
RELEVANCE_THRESHOLD = 0.45


def retrieve_dense(query: str, top_k: int = TOP_K) -> list[dict]:
    return semantic_search(query, top_k=top_k)


def retrieve_hybrid(query: str, top_k: int = TOP_K) -> list[dict]:
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)
    return rerank_rrf([dense, sparse], top_k=top_k)


def _cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _embed(texts: list[str]) -> list[list[float]]:
    return embed_texts(texts) if texts else []


def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in text.replace("\n", " ").split(".")]
    return [p for p in parts if len(p) > 10]


def evaluate_case(query: str, expected_context: str, retriever) -> dict:
    chunks = retriever(query, top_k=TOP_K)
    chunk_texts = [c["content"] for c in chunks]

    if not chunks:
        return {
            "context_recall": 0.0,
            "context_precision": 0.0,
            "best_similarity": 0.0,
        }

    chunk_embs = _embed(chunk_texts)
    ref_sentences = _sentences(expected_context)

    # context_recall: trung bình max similarity của từng câu trong expected_context
    # so với các retrieved chunks.
    recall_vals: list[float] = []
    for sentence in ref_sentences:
        sent_emb = _embed([sentence])[0]
        best = max(_cosine(sent_emb, chunk_emb) for chunk_emb in chunk_embs)
        recall_vals.append(best)
    context_recall = sum(recall_vals) / len(recall_vals) if recall_vals else 0.0

    # context_precision: tỷ lệ retrieved chunks có similarity > threshold.
    ref_emb = _embed([expected_context])[0]
    sims = [_cosine(ref_emb, chunk_emb) for chunk_emb in chunk_embs]
    context_precision = sum(1.0 for s in sims if s > RELEVANCE_THRESHOLD) / len(sims)

    return {
        "context_recall": context_recall,
        "context_precision": context_precision,
        "best_similarity": max(sims) if sims else 0.0,
    }


def run_evaluation() -> dict:
    dataset = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    _ = load_corpus()  # nạp corpus cho BM25

    summary: dict = {
        "config_a_dense": [],
        "config_b_hybrid": [],
    }

    for case in dataset:
        query = case["question"]
        expected_context = case["expected_context"]
        summary["config_a_dense"].append(
            evaluate_case(query, expected_context, retrieve_dense)
        )
        summary["config_b_hybrid"].append(
            evaluate_case(query, expected_context, retrieve_hybrid)
        )

    results: dict = {"top_k": TOP_K, "cases": [], "aggregate": {}}
    for name in ("config_a_dense", "config_b_hybrid"):
        rows = summary[name]
        agg = {
            metric: sum(r[metric] for r in rows) / len(rows)
            for metric in ("context_recall", "context_precision", "best_similarity")
        }
        results["aggregate"][name] = agg

    for index, case in enumerate(dataset):
        results["cases"].append(
            {
                "question": case["question"],
                "config_a_dense": summary["config_a_dense"][index],
                "config_b_hybrid": summary["config_b_hybrid"][index],
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results


if __name__ == "__main__":
    output = run_evaluation()
    print(json.dumps(output["aggregate"], ensure_ascii=False, indent=2))
    print(f"\nSaved: {OUTPUT_PATH}")