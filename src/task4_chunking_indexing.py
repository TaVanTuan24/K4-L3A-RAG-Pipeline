"""
Task 4 — Chunking, embedding và indexing.

- Đọc toàn bộ Markdown trong ``data/standardized/``.
- Chia văn bản bằng ``RecursiveCharacterTextSplitter``.
- Embed bằng provider duy nhất (mặc định local ``sentence-transformers`` với
  ``BAAI/bge-m3``) — model được lazy-load và cache để không reload cho từng query.
- Upsert vào ChromaDB (persistent) với cosine distance; ``upsert`` đảm bảo chạy
  lại không tạo dữ liệu trùng (ID chunk deterministic).

Mọi document/chunk tuân thủ ``docs/MODULE_CONTRACTS.md``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_embedding_model = None

_FRONT_MATTER_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)


def _get_embedding_model():
    """Lazy-load và cache model embedding (dùng chung cho Task 4 và Task 5)."""
    global _embedding_model
    if _embedding_model is None:
        if EMBEDDING_PROVIDER == "sentence_transformers":
            from sentence_transformers import SentenceTransformer

            print(f"Loading embedding model: {EMBEDDING_MODEL} ...")
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        elif EMBEDDING_PROVIDER in {"openai", "gemini"}:
            key_var = (
                "OPENAI_API_KEY" if EMBEDDING_PROVIDER == "openai"
                else "GEMINI_API_KEY"
            )
            raise RuntimeError(
                f"EMBEDDING_PROVIDER={EMBEDDING_PROVIDER} cần {key_var}; "
                "hãy dùng sentence_transformers (local) để giảm API cost."
            )
        else:
            raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")
    return _embedding_model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text thành vector (dùng chung model với Task 5)."""
    if not texts:
        return []
    model = _get_embedding_model()
    vectors = model.encode(
        list(texts), normalize_embeddings=True, show_progress_bar=False
    )
    return vectors.tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _parse_front_matter(text: str) -> dict[str, str]:
    """Đọc metadata nhúng ở đầu file Markdown (HTML comment)."""
    metadata: dict[str, str] = {}
    match = _FRONT_MATTER_RE.search(text)
    if not match:
        return metadata
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def load_documents() -> list[dict]:
    """Đọc toàn bộ Markdown và trả về danh sách Document theo contract."""
    documents: list[dict] = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        meta = _parse_front_matter(text)
        rel_id = path.relative_to(STANDARDIZED_DIR).as_posix()
        doc_type = meta.get("doc_type") or (
            "legal" if "legal" in path.parts else "news"
        )
        documents.append(
            {
                "id": rel_id,
                "content": _FRONT_MATTER_RE.sub("", text, count=1).strip(),
                "metadata": {
                    "source": meta.get("source") or path.name,
                    "title": meta.get("title") or path.stem,
                    "doc_type": doc_type,
                    "url": meta.get("url") or None,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id ổn định và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[dict] = []
    for document in documents:
        for index, text in enumerate(splitter.split_text(document["content"])):
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk (không mutate input)."""
    if not chunks:
        return []
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    embedded: list[dict] = []
    for chunk, vector in zip(chunks, vectors):
        item = dict(chunk)
        item["embedding"] = vector
        embedded.append(item)
    return embedded


def _chroma_metadata(metadata: dict) -> dict:
    """Chuẩn hóa metadata cho Chroma (url None -> chuỗi rỗng)."""
    clean = dict(metadata)
    if clean.get("url") is None:
        clean["url"] = ""
    return clean


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB (idempotent, không tạo dữ liệu trùng)."""
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()