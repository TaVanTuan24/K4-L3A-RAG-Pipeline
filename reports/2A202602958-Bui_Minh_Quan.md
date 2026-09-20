# Individual contribution report

---

## Thông tin

- Họ và tên: Bui Minh Quan (Bùi Minh Quân)
- Mã học viên: 2A202602958
- Nhóm: K4
- Repository/branch: https://github.com/TaVanTuan24/K4-L3A-RAG-Pipeline (nhánh cá nhân chưa có trong snapshot hiện tại)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Contract và kiểm thử liên module | Phụ trách phần còn lại về hợp đồng giao tiếp và kiểm thử acceptance: đối chiếu schema Document/SearchResult/GenerationResult, kiểm tra interface Task 4–10, metadata và ID của chunk, thứ tự/kết quả retrieval, fallback khi PageIndex lỗi, cùng điều kiện corpus và golden dataset | `docs/MODULE_CONTRACTS.md`, `src/contracts.py`, `tests/test_contracts.py`, `tests/test_acceptance.py` (không có commit cá nhân trong snapshot) | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng schema và interface chung làm ranh giới kiểm tra giữa các module.
   **Lý do/evidence:** `docs/MODULE_CONTRACTS.md` định nghĩa các kiểu dữ liệu và hàm công khai; `src/contracts.py` kiểm tra metadata, chunk index, kết quả retrieval và đầu ra generation.
   **Trade-off:** Phát hiện sớm dữ liệu sai định dạng và thay đổi interface, đổi lại cần cập nhật contract cùng lúc khi schema thay đổi.

2. **Quyết định:** Tách kiểm thử contract khỏi kiểm thử acceptance ở mức dữ liệu và deliverable.
   **Lý do/evidence:** `tests/test_contracts.py` kiểm tra hành vi các module bằng fixture và mock; `tests/test_acceptance.py` kiểm tra corpus, dữ liệu chuẩn hóa, golden dataset và báo cáo evaluation.
   **Trade-off:** Bộ kiểm thử chạy ổn định mà không cần gọi dịch vụ thật, nhưng không tự xác nhận chất lượng của API bên ngoài.

## Kiểm thử và kết quả

- Test đã dùng: `pytest -q` — kết quả được ghi nhận trong báo cáo project là **20 passed** (15 contract tests + 5 acceptance tests).
- Kiểm tra contract: schema đầu vào/đầu ra, public function signatures, metadata và ID chunk, thứ tự/ID duy nhất của search results, RRF, citation context và fallback.
- Kiểm tra acceptance: đủ tài liệu legal/news, đầu ra Markdown, tối thiểu 15 câu grounded và báo cáo evaluation đã hoàn thành.
- Lỗi đã phát hiện và xử lý: bộ contract yêu cầu kết quả retrieval có ID duy nhất và được sắp giảm dần theo score; các trường hợp vi phạm được kiểm tra bằng test âm.

## Điều còn hạn chế

- Một hạn chế cụ thể: acceptance tests chủ yếu xác nhận cấu trúc và số lượng deliverable; contract tests dùng fixture/mock nên chưa bao phủ đầy đủ tích hợp với các provider thật.
- Nếu có thêm thời gian: bổ sung integration tests chạy pipeline trên corpus fixture nhỏ, kiểm tra mapping citation tới source và hành vi khi provider lỗi mà không phụ thuộc API trả phí.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Bui Minh Quan (Bùi Minh Quân)
