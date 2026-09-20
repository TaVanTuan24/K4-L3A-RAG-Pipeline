"""
Task 5 — Semantic search (dense).

Embed query bằng chính ``embed_texts()`` của Task 4, query ChromaDB và đổi cosine
distance thành similarity. Output theo SearchResult, sort giảm dần, không quá
``top_k`` và không trùng ID.
"""

from __future__ import annotations

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0:
        return []

    query_vector = embed_texts([query])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict] = []
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append(
            {
                "id": item_id,
                "content": content,
                # cosine distance -> similarity: sim = 1 - distance
                "score": 1.0 - distance,
                "metadata": metadata,
                "retrieval_method": "dense",
            }
        )

    seen: set[str] = set()
    unique: list[dict] = []
    for result in sorted(results, key=lambda item: item["score"], reverse=True):
        if result["id"] not in seen:
            seen.add(result["id"])
            unique.append(result)
    return unique[:top_k]


if __name__ == "__main__":
    for result in semantic_search("Scholarships for students", top_k=3):
        print(result)