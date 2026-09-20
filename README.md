# University Student Services — RAG Pipeline

Hệ thống **Retrieval-Augmented Generation (RAG)** trả lời câu hỏi về các dịch vụ
và chính sách sinh viên của **Victoria University (VU, Melbourne, Australia)** —
học phí, học bổng, tuyển sinh, đăng ký học phần, quy chế sinh viên, liêm chính
học thuật và các dịch vụ hỗ trợ sinh viên (thư viện, hỗ trợ tài chính, ...).

Chatbot gồm pipeline **hybrid retrieval** (dense semantic + BM25 lexical → RRF),
**fallback vectorless** bằng PageIndex khi cosine score thấp, và **generation có
citation** với safe refusal. Sản phẩm đi kèm golden dataset và đánh giá A/B
(dense-only so với hybrid).

---

## 1. Problem statement

Sinh viên thường phải tra cứu chính sách nằm rải rác trong nhiều văn bản PDF và
trang web khác nhau. Một chatbot RAG cho phép hỏi bằng ngôn ngữ tự nhiên và nhận
câu trả lời **kèm citation trỏ về đúng nguồn**, thay vì phải tự đọc tài liệu.

Khó khăn kỹ thuật cần giải quyết:

- **Hybrid retrieval**: dense (ngữ nghĩa) bắt ý diễn đạt khác, BM25 (lexical) bắt
  từ khóa chính xác, tên riêng, mã quy định. RRF gộp thứ hạng hai nguồn này.
- **Fallback an toàn**: khi cosine similarity gốc của dense search quá thấp (query
  ngoài domain), thử nguồn vectorless (PageIndex) thay vì trả kết quả nhiễu.
- **Grounded generation**: mỗi khẳng định phải có citation; thiếu bằng chứng thì
  từ chối an toàn thay vì bịa.

## 2. Architecture

```text
data/landing/ (PDF + article JSON)
        │  Task 1–2: collect/crawl (Victoria University public sources)
        ▼
data/standardized/ (*.md, có metadata front-matter)
        │  Task 3: markitdown + metadata header
        ▼
Task 4: chunk (RecursiveCharacterTextSplitter) → embed (BAAI/bge-m3) → ChromaDB (cosine)
        │
        ├── Task 5: dense semantic search (embed_texts dùng chung model)
        ├── Task 6: BM25 lexical search (cùng corpus chunks)
        │        └── Task 7: RRF fusion (đúng 1 lần) → hybrid
        ▼
Task 9: retrieval pipeline
        dense[0].score < SCORE_THRESHOLD ?
          └─ yes → Task 8: PageIndex vectorless fallback (graceful)
          └─ no  → hybrid result
        ▼
Task 10: generation (reorder → context → LLM theo LLM_PROVIDER) + citation
        ▼
app.py: Streamlit chatbot (answer + sources hiển thị dạng expandable)
```

## 3. Data sources

Tất cả dữ liệu là tài liệu **công khai chính thức** của Victoria University:

| Loại | Nguồn | Số lượng |
| ---- | ----- | -------- |
| Legal/policy PDF | [Victoria University Policy Library](https://policy.vu.edu.au) | 6 |
| News/article pages | [vu.edu.au](https://www.vu.edu.au) | 6 |

Các tài liệu chính sách:

- Support for Students Policy
- Admissions Policy
- Enrolments Policy
- Fee Adjustments Procedure
- Student Conduct Policy
- Academic Integrity Policy

Danh sách cụ thể (ID, tiêu đề, URL) được khai báo tại
[`src/dataset_registry.py`](src/dataset_registry.py).

## 4. Setup

Yêu cầu Python 3.10–3.13 (repo được kiểm thử trên Python 3.11).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    # Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
cp .env.example .env
```

> Lưu ý: trên một số máy, Hugging Face Hub dùng Xet CDN có thể bị stall; nếu gặp
> lỗi tải model, đặt `HF_HUB_DISABLE_XET=1` trước khi chạy indexing.

## 5. Environment variables (`.env`)

Sao chép từ [`.env.example`](.env.example); **không commit `.env`**.

| Biến | Mô tả |
| ---- | ----- |
| `LLM_PROVIDER` | `openai` / `gemini` / `anthropic` |
| `LLM_MODEL` | model generation (để trống để dùng default) |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` | key của provider generation |
| `EMBEDDING_PROVIDER` | `sentence_transformers` (mặc định) / `openai` / `gemini` |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` (mặc định, local) |
| `PAGEINDEX_API_KEY` | key cho fallback PageIndex (optional) |
| `SCORE_THRESHOLD` | ngưỡng fallback cosine (đã hiệu chỉnh, xem RESULT.md) |

## 6. Commands

```bash
# 1. Thu thập và chuẩn hoá data
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Build index (chunk + embed + ChromaDB)
python -m src.task4_chunking_indexing

# 3. Chạy chatbot
streamlit run app.py

# 4. Chạy evaluation A/B
python -m src.evaluate_rag

# 5. Chạy tests
pytest tests/test_contracts.py -q
pytest tests/test_acceptance.py -q
pytest -q
```

## 7. Project structure

```text
src/
  contracts.py                 # schema & validators
  dataset_registry.py          # topic + nguồn dữ liệu khai báo tập trung
  task1_collect_legal_docs.py  # tải ≥3 PDF chính sách thật
  task2_crawl_news.py          # crawl ≥5 article → JSON
  task3_convert_markdown.py    # chuẩn hoá sang Markdown (giữ metadata)
  task4_chunking_indexing.py   # chunk + embed + ChromaDB
  task5_semantic_search.py     # dense search
  task6_lexical_search.py      # BM25
  task7_reranking.py           # RRF
  task8_pageindex_vectorless.py# PageIndex fallback
  task9_retrieval_pipeline.py  # full retrieval + fallback decision
  task10_generation.py         # generation có citation
  evaluate_rag.py              # A/B evaluation
app.py                         # Streamlit chatbot
tests/                         # contract + acceptance tests
data/landing/                  # dữ liệu gốc (PDF/JSON)
data/standardized/             # Markdown chuẩn hoá
group_project/evaluation/      # golden dataset + RESULT.md
chroma_db/                     # vector store (rebuildable, gitignored)
```
## 8. Retrieval design

- **Chunking**: `RecursiveCharacterTextSplitter`, `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`.
  ID chunk deterministic: `<document-id>::chunk-<index>`, ổn định giữa các lần chạy.
- **Embedding**: `BAAI/bge-m3` (1024 dims), model được lazy-load/cache và dùng chung
  giữa Task 4 và Task 5 (`embed_texts()`).
- **Dense search**: cosine similarity = `1 - distance` (ChromaDB `hnsw:space=cosine`).
- **BM25**: `rank_bm25.BM25Okapi` trên **cùng corpus chunks** với dense (cùng ID, nội dung).
- **RRF**: `score(d) = Σ 1/(k + rank)`, `k=60`, rank bắt đầu từ 1, **chỉ fuse một lần**.

## 9. Fallback logic

`retrieve()` chạy dense + BM25 → RRF. Quyết định fallback dựa trên **cosine
similarity gốc** `dense[0]["score"]` (không dùng RRF score):

- Nếu `dense[0].score >= SCORE_THRESHOLD` → trả hybrid.
- Nếu `< SCORE_THRESHOLD` → thử `pageindex_search()`; lỗi/rỗng → trả hybrid (không crash).

`SCORE_THRESHOLD` được hiệu chỉnh trên query in-domain/out-of-domain (xem
[`group_project/evaluation/RESULT.md`](group_project/evaluation/RESULT.md)).

## 10. Citation

`format_context()` gắn nhãn `[S1 | Title: ... | Source: ...]` cho từng chunk.
System prompt yêu cầu LLM chỉ trả lời từ context, mỗi khẳng định factual kèm
`[S#]`. `sources` trong `GenerationResult` được sắp theo **đúng thứ tự reordered**
để citation map chính xác. Thiếu bằng chứng → safe refusal:
*"Tôi không thể xác minh thông tin này từ các nguồn hiện có."*

## 11. Evaluation summary

Xem chi tiết và các metric tại
[`group_project/evaluation/RESULT.md`](group_project/evaluation/RESULT.md).
Kết quả A/B (dense-only vs hybrid+RRF) và phân tích worst performers nằm trong đó;
golden dataset gồm 20 câu grounded trong corpus.

## 12. Limitations

- **Generation cần API key**: `generate_with_citation` trả safe refusal khi chưa
  đặt `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`. Retrieval vẫn chạy
  đầy đủ (embedding local).
- **RAGAS metrics cần LLM** (faithfulness, answer relevance) không chạy được khi
  thiếu key; các retrieval metric (context recall/precision) được đo local bằng
  embedding `bge-m3`.
- **PageIndex** cần `PAGEINDEX_API_KEY`; nếu thiếu, pipeline fallback về hybrid.
- Corpus giới hạn ở 12 tài liệu của một trường (VU); nội dung có thể đổi theo thời
  gian — chạy lại Task 1–3 để cập nhật.