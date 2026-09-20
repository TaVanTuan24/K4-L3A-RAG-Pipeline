"""
Streamlit chatbot cho RAG pipeline "University Student Services".

Chạy: ``streamlit run app.py``

Hiển thị: answer, citation/source (title, source/url, retrieval method, score)
dưới dạng expandable section. Không crash khi external provider (LLM/PageIndex) lỗi.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo import được package ``src`` khi chạy ``streamlit run app.py``.
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import SAFE_REFUSAL, generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="University Student Services — RAG Chatbot",
    page_icon="🎓",
    layout="wide",
)

st.title("🎓 University Student Services — RAG Chatbot")
st.caption(
    "Hỏi đáp dựa trên tài liệu chính sách sinh viên Victoria University "
    "(học phí, học bổng, tuyển sinh, thư viện, quy chế sinh viên, ...)."
)

with st.sidebar:
    st.header("Cấu hình")
    top_k = st.slider("Số chunks truy xuất (top_k)", 3, 10, 5)
    st.markdown("---")
    st.caption(
        "Retrieval: dense + BM25 → RRF (hybrid). "
        "Fallback PageIndex khi best cosine score thấp."
    )


def _render_sources(sources: list[dict], retrieval_source: str) -> None:
    """Hiển thị nguồn đã dùng dưới dạng expandable section."""
    if not sources:
        st.info("Không có nguồn nào được truy xuất (safe refusal).")
        return

    st.markdown(f"**Nguồn truy xuất:** `{retrieval_source}` — {len(sources)} chunks")
    for index, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        title = metadata.get("title", source.get("id", ""))
        url = metadata.get("url") or None
        method = source.get("retrieval_method", "")
        score = source.get("score", 0.0)
        with st.expander(
            f"[S{index}] {title} — {method} (score {score:.4f})"
        ):
            if url:
                st.markdown(f"**URL:** {url}")
            st.markdown(f"**Source:** `{metadata.get('source', '')}`")
            st.markdown("**Nội dung:**")
            st.markdown(source.get("content", ""))


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            _render_sources(
                message.get("sources", []),
                message.get("retrieval_source", "hybrid"),
            )

query = st.chat_input("Nhập câu hỏi (ví dụ: What scholarships are available?)")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang truy xuất và sinh câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception:
                # External provider lỗi -> không crash UI.
                result = {
                    "answer": SAFE_REFUSAL,
                    "sources": [],
                    "retrieval_source": "none",
                }
        answer = result.get("answer", SAFE_REFUSAL)
        sources = result.get("sources", [])
        retrieval_source = result.get("retrieval_source", "none")
        st.markdown(answer)
        _render_sources(sources, retrieval_source)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
    )