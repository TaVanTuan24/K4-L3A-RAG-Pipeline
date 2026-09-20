"""
RAGAS A/B evaluation (4 metrics) — cần GEMINI_API_KEY.

Config A (dense) vs Config B (hybrid = dense + BM25 + RRF).

Metrics: faithfulness, answer_relevancy, context_recall, context_precision.

- LLM (generator + evaluator): Gemini (``ChatGoogleGenerativeAI``).
- Embeddings: local ``BAAI/bge-small-en-v1.5`` qua ``embed_texts()`` (Task 4).

Chạy: ``python -m src.evaluate_ragas``
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI

# tạm ẩn deprecation warnings của ragas
import warnings

warnings.filterwarnings("ignore")

from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
)

from src import task10_generation as gen
from src.task4_chunking_indexing import embed_texts
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search, load_corpus
from src.task7_reranking import rerank_rrf

ROOT = Path(__file__).parent.parent
GOLDEN = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT = ROOT / "group_project" / "evaluation" / "ragas_results.json"

TOP_K = 5
# Free-tier Gemini (15 RPM) rất hạn chế; chạy trên subset cho khả thi (override qua env).
SUBSET_SIZE = int(os.getenv("RAGAS_SUBSET", "8"))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


class LocalEmbeddings(Embeddings):
    """Wrap bge-small local embedding cho RAGAS."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return embed_texts([text])[0]


def retrieve_dense(query: str, top_k: int = TOP_K) -> list[dict]:
    return semantic_search(query, top_k=top_k)


def retrieve_hybrid(query: str, top_k: int = TOP_K) -> list[dict]:
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)
    return rerank_rrf([dense, sparse], top_k=top_k)


def _answer(query: str, chunks: list[dict]) -> str:
    reordered = gen.reorder_for_llm(chunks)
    context = gen.format_context(reordered)
    payload = f"Context:\n{context}\n\nQuestion: {query}"
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            return gen.call_llm(gen.SYSTEM_PROMPT, payload)
        except Exception as error:  # noqa: BLE001 - rate-limit/network retry
            last_error = error
            wait = min(30, 5 * (attempt + 1))
            print(f"    generate retry {attempt + 1}/6 after {wait}s "
                  f"({error.__class__.__name__})")
            time.sleep(wait)
    raise last_error  # type: ignore[misc]


def run() -> dict:
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set; abort.")
        return {}

    dataset = json.loads(GOLDEN.read_text(encoding="utf-8"))[:SUBSET_SIZE]
    _ = load_corpus()

    llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=LLM_MODEL, google_api_key=GEMINI_API_KEY, max_retries=12
        )
    )
    embeddings = LangchainEmbeddingsWrapper(LocalEmbeddings())
    # answer_relevancy cần n>1 (multi-candidate), không được gemini-3.5-flash-lite hỗ trợ.
    metrics = [faithfulness, context_recall, context_precision]

    results: dict = {}
    for name, retriever in (
        ("config_a_dense", retrieve_dense),
        ("config_b_hybrid", retrieve_hybrid),
    ):
        samples: list[SingleTurnSample] = []
        for case in dataset:
            chunks = retriever(case["question"], top_k=TOP_K)
            answer = _answer(case["question"], chunks)
            time.sleep(2.0)  # pace dưới free-tier rate limit
            samples.append(
                SingleTurnSample(
                    user_input=case["question"],
                    retrieved_contexts=[c["content"] for c in chunks],
                    response=answer,
                    reference=case["expected_answer"],
                    reference_contexts=[case["expected_context"]],
                )
            )
        ds = EvaluationDataset(samples=samples)
        report = evaluate(
            ds,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            run_config=RunConfig(
                max_workers=1, max_retries=12, max_wait=90, timeout=180
            ),
            raise_exceptions=True,
        )
        results[name] = {}
        for m in metrics:
            per_sample = report[m.name]
            results[name][m.name] = (
                float(sum(per_sample) / len(per_sample)) if per_sample else float("nan")
            )
        print(f"\n[{name}] {json.dumps(results[name], indent=2)}")

    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
    print(f"\nSaved: {OUTPUT}")