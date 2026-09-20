"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề: University Student Services (Victoria University).

Tài liệu được tải trực tiếp từ Victoria University Policy Library
(https://policy.vu.edu.au), nguồn chính thức và công khai. Mỗi chính sách có một
bản PDF hiện hành được export qua endpoint ``download.php``; script tự xác định
số hiệu "version" hiện hành từ trang "Status and Details" rồi tải PDF tương ứng.

- Ít nhất 3 PDF thật, có nội dung (>1KB và bắt đầu bằng ``%PDF``).
- Lưu vào ``data/landing/legal/`` với tên file rõ nghĩa (không dấu).
"""

from __future__ import annotations

import re
from pathlib import Path

import requests

from .dataset_registry import LEGAL_DOCUMENTS

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

POLICY_LIBRARY = "https://policy.vu.edu.au"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
MIN_FILE_SIZE = 1024


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _current_version(session: requests.Session, policy_id: str) -> str:
    """Trả về số hiệu version hiện hành của một policy document."""
    url = f"{POLICY_LIBRARY}/document/status-and-details.php?id={policy_id}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    match = re.search(
        rf'view\.php\?id={re.escape(policy_id)}&(?:amp;)?version=(\d+)', response.text
    )
    if not match:
        raise ValueError(f"Current version not found for policy id={policy_id}")
    return match.group(1)


def _download_pdf(
    session: requests.Session, policy_id: str, version: str
) -> bytes:
    """Tải bản PDF của một version và trả về nội dung nhị phân."""
    url = f"{POLICY_LIBRARY}/download.php?id={policy_id}&version={version}"
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def _is_valid_pdf(content: bytes) -> bool:
    """Kiểm tra nhanh một file có thực sự là PDF hợp lệ, không rỗng hay fake."""
    return len(content) > MIN_FILE_SIZE and content[:5] == b"%PDF-"


def download_documents() -> None:
    """Tải ít nhất 3 PDF chính sách từ nguồn công khai, bỏ qua file đã có."""
    session = _new_session()
    downloaded = 0
    for doc in LEGAL_DOCUMENTS:
        output = DATA_DIR / f"{doc.stem}.pdf"
        if output.is_file() and _is_valid_pdf(output.read_bytes()):
            print(f"Skipped (already valid): {output.name}")
            downloaded += 1
            continue

        try:
            version = _current_version(session, doc.policy_id)
            content = _download_pdf(session, doc.policy_id, version)
            if not _is_valid_pdf(content):
                raise ValueError(f"Response is not a valid PDF for {doc.stem}")
            output.write_bytes(content)
            downloaded += 1
            print(
                f"Downloaded: {output.name} "
                f"(id={doc.policy_id}, version={version}, "
                f"{len(content)} bytes)"
            )
        except (requests.RequestException, ValueError) as error:
            print(f"Failed: {doc.stem} - {error}")

    print(f"Legal documents ready: {downloaded}/{len(LEGAL_DOCUMENTS)}")


if __name__ == "__main__":
    setup_directory()
    download_documents()