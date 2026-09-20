"""
Task 10 — Generation có citation.

- Retrieve top-k chunks qua Task 9.
- Reorder để giảm lost-in-the-middle (không mutate input, giữ ID).
- Format context kèm title/source và citation label ``[S#]``.
- Gọi provider được chọn trong ``LLM_PROVIDER``: openai | gemini | anthropic.
- Trả ``GenerationResult`` (answer, sources, retrieval_source).

Nếu context không đủ hoặc provider/API key lỗi, trả safe refusal; không bịa thông tin.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")

SAFE_REFUSAL = (
    "Tôi không thể xác minh thông tin này từ các nguồn hiện có."
)

SYSTEM_PROMPT = (
    "Bạn là trợ lý trả lời câu hỏi DỰA DUY NHẤT trên context được cung cấp bên dưới.\n"
    "Quy tắc bắt buộc:\n"
    "1. Chỉ trả lời từ các đoạn context có nhãn [S#]. Không dùng kiến thức ngoài corpus.\n"
    "2. Mỗi khẳng định factual phải kèm citation dạng [S#] tương ứng với nhãn trong context.\n"
    "3. Nếu context không đủ bằng chứng để trả lời, hãy từ chối an toàn: "
    "'Tôi không thể xác minh thông tin này từ các nguồn hiện có.'\n"
    "4. Không bịa số liệu, ngày tháng hoặc chính sách không có trong context."
)


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu/cuối context (giảm lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title/source và citation label [S#]."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        parts.append(
            f"[S{index} | Title: {metadata.get('title', '')} | "
            f"Source: {metadata.get('source', '')}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo ``LLM_PROVIDER``."""
    if LLM_PROVIDER == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    if LLM_PROVIDER == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=LLM_MODEL or "gemini-1.5-flash",
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""

    if LLM_PROVIDER == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=LLM_MODEL or "claude-3-5-haiku-latest",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text or ""

    raise RuntimeError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult với citation map được về ``sources``."""
    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        chunks = []

    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        # Provider/API key lỗi -> safe refusal thay vì làm UI crash.
        answer = SAFE_REFUSAL

    method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"

    # ``sources`` theo đúng thứ tự reordered để citation [S#] map chính xác.
    return {
        "answer": answer,
        "sources": reordered,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("What scholarships are available?"))