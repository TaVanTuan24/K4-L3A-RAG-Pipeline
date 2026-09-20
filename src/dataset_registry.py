"""
Dataset registry cho topic "University Student Services".

Toàn bộ dữ liệu thuộc một domain chính thức duy nhất — Victoria University
(https://www.vu.edu.au) và Victoria University Policy Library
(https://policy.vu.edu.au) — để corpus nhất quán và có metadata nguồn kiểm chứng được.

- Legal/policy documents: chính sách sinh viên (học phí, tuyển sinh, đăng ký học
  phần, quy chế sinh viên, hỗ trợ sinh viên, liêm chính học thuật).
- News/article pages: các trang thông tin sinh viên công khai.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalDocument:
    """Một tài liệu chính sách/quy định cần thu thập."""

    stem: str
    title: str
    policy_id: str
    url: str


@dataclass(frozen=True)
class NewsArticle:
    """Một bài viết/trang thông tin cần crawl."""

    url: str
    title: str


LEGAL_DOCUMENTS: list[LegalDocument] = [
    LegalDocument(
        stem="support_for_students_policy",
        title="Support for Students Policy",
        policy_id="513",
        url="https://policy.vu.edu.au/document/view.php?id=513",
    ),
    LegalDocument(
        stem="admissions_policy",
        title="Admissions Policy",
        policy_id="43",
        url="https://policy.vu.edu.au/document/view.php?id=43",
    ),
    LegalDocument(
        stem="enrolments_policy",
        title="Enrolments Policy",
        policy_id="223",
        url="https://policy.vu.edu.au/document/view.php?id=223",
    ),
    LegalDocument(
        stem="fee_adjustments_procedure",
        title="Fee Adjustments Procedure",
        policy_id="215",
        url="https://policy.vu.edu.au/document/view.php?id=215",
    ),
    LegalDocument(
        stem="student_conduct_policy",
        title="Student Conduct Policy",
        policy_id="510",
        url="https://policy.vu.edu.au/document/view.php?id=510",
    ),
    LegalDocument(
        stem="academic_integrity_policy",
        title="Academic Integrity Policy",
        policy_id="27",
        url="https://policy.vu.edu.au/document/view.php?id=27",
    ),
]

NEWS_ARTICLES: list[NewsArticle] = [
    NewsArticle(
        url="https://www.vu.edu.au/current-students",
        title="Current students",
    ),
    NewsArticle(
        url="https://www.vu.edu.au/study-at-vu/fees-scholarships/scholarships",
        title="Scholarships",
    ),
    NewsArticle(
        url="https://www.vu.edu.au/current-students/campus-life/advice-support/financial-advice-support",
        title="Financial advice and support",
    ),
    NewsArticle(
        url="https://www.vu.edu.au/library",
        title="Library",
    ),
    NewsArticle(
        url="https://www.vu.edu.au/library/about-the-library/campus-libraries-opening-hours",
        title="Library opening hours",
    ),
    NewsArticle(
        url="https://www.vu.edu.au/study-at-vu/international-students",
        title="International students",
    ),
]

LEGAL_URLS: dict[str, str] = {doc.stem: doc.url for doc in LEGAL_DOCUMENTS}
LEGAL_TITLES: dict[str, str] = {doc.stem: doc.title for doc in LEGAL_DOCUMENTS}