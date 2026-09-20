# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Python 3.11.15 · sentence-transformers 6.1.0 · chromadb 1.5.9 · numpy 2.4.6 · rank-bm25 0.2.2 |
| Evaluator model                    | BAAI/bge-small-en-v1.5 (local, embedding-based); RAGAS+Gemini LLM evaluator blocked by free-tier limits (xem ghi chú) |
| Generator model                    | gemini-3.5-flash-lite — grounded + citation + safe refusal đã verify thực tế |
| Embedding model                    | BAAI/bge-small-en-v1.5 (384-dim) — `BAAI/bge-m3` is the intended 1024-dim default but its 2.3 GB download is impractical in this environment |
| Corpus version/commit              | 12 documents (6 legal PDF + 6 news pages), 384 chunks; commit 523482e |
| Golden dataset size                | 20 |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.60 — calibrated: in-domain best dense sim min=0.7805; out-of-domain max=0.5416 |

## Configurations

- **Config A — dense-only:** `semantic_search(query, top_k=5)` (ChromaDB + bge-small cosine).
- **Config B — hybrid + RRF:** `rerank_rrf([semantic_search, lexical_search], top_k=5)` với BM25 trên cùng corpus chunks.

Hai config dùng cùng golden dataset, embedding model, corpus, `top_k`; chỉ khác retrieval strategy.

## Overall scores

Các metric "Faithfulness" và "Answer relevance" cần LLM (RAGAS). Đã thử chạy RAGAS với
`gemini-3.5-flash-lite` nhưng bị chặn bởi giới hạn của free-tier model, **không tạo số giả**:

- rate limit 15 req/min (429) — phải retry nhiều;
- `answer_relevancy` cần multi-candidate (n>1), model `-flash-lite` không hỗ trợ (400);
- `faithfulness` dùng structured output, model gây `OUTPUT_PARSING_FAILURE`.

Do đó 2 metric LLM này được ghi là blocked (không đo được). Generation bản thân đã chạy thật
và trả answer có citation + safe refusal đúng.

| Metric            | Config A (dense) | Config B (hybrid) | Delta B−A |
| ----------------- | ---------------: | ----------------: | --------: |
| Faithfulness      |           n/a*   |            n/a*   |       n/a |
| Answer relevance  |           n/a*   |            n/a*   |       n/a |
| Context recall    |          0.8593  |           0.8578  |   -0.0015 |
| Context precision |          1.000   |           0.990   |   -0.010  |
| **Average (measured)** |      0.9296 |           0.9239  |   -0.0058 |

\* blocked: RAGAS LLM metrics (free-tier model limits, xem ghi chú ở trên).

## A/B comparison

- Cấu hình tốt hơn: **gần như ngang nhau; dense-only nhỉnh hơn không đáng kể** trên corpus này.
- Evidence: context recall 0.8593 (A) vs 0.8578 (B); context precision 1.000 (A) vs 0.990 (B).
  Hybrid không cải thiện trung bình vì corpus nhỏ (384 chunks) và query đã được dense phủ tốt;
  BM25+RRF thỉnh thoảng đưa thêm chunk ít liên quan làm precision giảm nhẹ (0.80 ở 1 case).
- Trade-off về latency/cost: cả hai đều dùng embedding local (không API cost). Hybrid thêm
  bước BM25 (tốn ~ms) nên latency tăng nhẹ; đổi lại hybrid mạnh hơn cho query đúng từ khóa
  chính xác (mã quy định, tên riêng) — xem khuyến nghị.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | How much scholarship money is paid per semester? | A/B | n/a | n/a | 0.7426 | 1.0 | retrieval | expected_context quá ngắn (1 số liệu) nên embedding similarity thấp |
|   2 | What phone number can students call for support? | A/B | n/a | n/a | 0.7493 / 0.7225 | 1.0 | retrieval | câu trả lời là một số điện thoại đơn lẻ, khó match ngữ nghĩa |
|   3 | When do library services finish relative to closing time? | A/B | n/a | n/a | 0.7564 | 1.0 / 0.80 | retrieval | factual ngắn; hybrid thêm 1 chunk ít liên quan |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Query expansion / HyDE cho query ngắn và numeric | WFs đều là factual ngắn (số tiền, số điện thoại, giờ) có recall ~0.74 | Tăng recall các case ngắn | Re-run A/B, so recall từng case |
|        2 | Thêm metadata/key-value cho số liệu (Q&A-friendly chunk) | Số liệu nằm trong câu dài bị embedding phân tán | Tăng precision/recall cho factoid | Chạy lại evaluation |
|        3 | Sử dụng bge-m3 (1024-dim) khi có bandwidth | bge-small (384-dim) là fallback; bge-m3 mạnh hơn | Cải thiện semantic toàn cục | Đổi EMBEDDING_MODEL, re-index, re-eval |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| None       | —        |          n/a |                n/a | Không chạy để giữ baseline ổn định |