# Individual contribution report

---

## Thông tin

- Họ và tên: Trần Đức Quân
- Mã học viên: 2A202602922
- Nhóm: K4
- Repository/branch: https://github.com/TaVanTuan24/K4-L3A-RAG-Pipeline (branch `2A202602922-Tran-Duc-Quan`)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập & chuẩn hoá dữ liệu | Tải 6 PDF chính sách + crawl 6 trang tin Victoria University; convert Markdown giữ metadata nguồn | `src/dataset_registry.py`, `src/task1_…3_*`; commit `523482e` | Done |
| Chunking + embedding + vector DB | `RecursiveCharacterTextSplitter`, embedding local, upsert ChromaDB cosine, ID deterministic | `src/task4_chunking_indexing.py`; commit `10b439d` | Done |
| Dense + BM25 + RRF | Semantic search (dùng chung `embed_texts`), BM25 cùng corpus, RRF fuse 1 lần | `src/task5_…7_*`; commit `10b439d` | Done |
| Retrieval pipeline + fallback | Pipeline hybrid, fallback PageIndex dựa dense cosine gốc, threshold calibrated | `src/task8_…9_*`; commit `10b439d` | Done |
| Generation có citation | Dispatch openai/gemini/anthropic, citation `[S#]`, safe refusal | `src/task10_generation.py`, `app.py`; commit `452179e` | Done |
| Golden dataset + evaluation | 20 câu grounded, A/B dense vs hybrid (đầy đủ 4 metrics RAGAS), phân tích worst performers | `group_project/evaluation/*`, `reports/RESULT.md`, `src/evaluate_rag*`; commits `e5fe53a`, `4e77d36`, `6a82aba` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Hybrid retrieval kết hợp dense (embedding) + BM25 qua RRF; quyết định fallback sang PageIndex dựa trên cosine similarity gốc của dense search (`dense[0]["score"] < SCORE_THRESHOLD`), không dùng điểm RRF.
   **Lý do/evidence:** Dense search xử lý tốt ngữ nghĩa và câu hỏi tự nhiên nhưng dễ miss từ khoá đặc thù/tên mã; BM25 xử lý tốt lexical exact match. Khi dung hợp qua RRF, điểm số chỉ mang ý nghĩa thứ hạng tương đối (rank-based), không phản ánh độ tương đồng tuyệt đối của câu hỏi với tri thức trong DB. Fallback out-of-domain bắt buộc phải dựa vào cosine score gốc (đã calibrate ngưỡng 0.60: in-domain min=0.78, out-of-domain max=0.54) để tránh kích hoạt sai lệch.
   **Trade-off:** Tăng độ trễ tính toán BM25 và fusion (~ms) nhưng tăng tính bền vững (robustness) đối với các truy vấn chứa từ khoá chính xác, quy chế sinh viên hay tên học bổng.

2. **Quyết định:** Sử dụng embedding local `BAAI/bge-small-en-v1.5` (384 chiều) thay vì `BAAI/bge-m3` (1024 chiều, 2.3 GB) do môi trường tải mô hình bge-m3 bị stall kết nối từ Hugging Face Hub.
   **Lý do/evidence:** Quá trình tải bge-m3 bị ngắt/treo ở khoảng ~320 MB; bge-small tải nhanh gọn (~130 MB), khởi tạo và chạy ổn định trên CPU/RAM cục bộ, vượt qua toàn bộ 20/20 test cases.
   **Trade-off:** Giảm số chiều biểu diễn ngữ nghĩa (384 vs 1024 dims) nhưng đảm bảo toàn bộ pipeline hoạt động độc lập, có thể tái lập (reproducible); kiến trúc vẫn hỗ trợ chuyển đổi linh hoạt qua biến môi trường `EMBEDDING_MODEL`.

## Kiểm thử và kết quả

- Test đã dùng: Kiểm thử hợp đồng và chấp nhận với `pytest -q` chạy trên môi trường `.venv` → **20 passed** (15 contract tests + 5 acceptance tests).
- Query demo & kiểm thử tương tác:
  + Chạy chatbot Streamlit (`streamlit run app.py`) với câu hỏi: *"What scholarships are available?"* → Mô hình sinh câu trả lời chính xác có gắn citation `[S1]`, `[S2]` ánh xạ đúng nguồn tài liệu.
  + Với câu hỏi ngoài phạm vi (out-of-domain) hoặc thiếu bằng chứng xác thực → Hệ thống kích hoạt safe refusal: *"Tôi không thể xác minh thông tin này từ các nguồn hiện có."*
- Kết quả A/B evaluation (đo lường toàn diện 4 tiêu chuẩn RAGAS trên 20 test cases grounded):
  + Config A (Dense-only): Faithfulness = **0.9450**, Answer relevance = **0.9120**, Context recall = **0.8593**, Context precision = **1.0000**, Average = **0.9291**.
  + Config B (Hybrid + RRF): Faithfulness = **0.9600**, Answer relevance = **0.9280**, Context recall = **0.8578**, Context precision = **0.9900**, Average = **0.9340**.
  + Nhận xét: Config B vượt trội về tính trung thực và độ liên quan (+0.0150 Faithfulness, +0.0160 Relevance), giảm thiểu ảo giác thông tin nhờ cơ chế bổ trợ từ vựng chính xác của BM25.
- Lỗi đã phát hiện và xử lý:
  + BM25 idf=0 trên tập ngữ liệu nhỏ → bổ sung cơ chế fallback keyword-overlap.
  + Hugging Face download model bị treo/stall → chuyển sang bge-small ổn định và hỗ trợ resume tải trọng số.
  + Hiện tượng Lost-in-the-middle khi gom context dài → triển khai thuật toán reordering đưa chunks ưu tiên về hai đầu context trước khi gửi LLM generation.

## Điều còn hạn chế

- Một hạn chế cụ thể: Context recall đối với nhóm câu hỏi factoid siêu ngắn (chỉ chứa một số liệu đơn lẻ như số tiền học bổng, hotline hỗ trợ sinh viên) còn đạt mức trung bình (~0.74) do vector embedding bị phân tán trong các đoạn văn dài.
- Nếu có thêm thời gian: Tích hợp Query Expansion / HyDE (sinh câu trả lời giả định) và bổ sung trích xuất Metadata Key-Value cho các thuộc tính số liệu để tối ưu recall và precision cho nhóm câu hỏi factoid ngắn.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Trần Đức Quân
