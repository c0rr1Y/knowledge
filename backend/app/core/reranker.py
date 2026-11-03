"""Cross-Encoder reranker using FlagEmbedding (bge-reranker-v2-m3) on GPU."""

from typing import Optional

_reranker_model: Optional[object] = None


def get_reranker():
    """Load bge-reranker-v2-m3 cross-encoder across GPU slices."""
    global _reranker_model
    if _reranker_model is None:
        from FlagEmbedding import FlagReranker
        _reranker_model = FlagReranker(
            "BAAI/bge-reranker-v2-m3",
            use_fp16=True,  # halves VRAM, negligible quality loss
            device="cuda",
        )
    return _reranker_model


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank chunks using bge-reranker-v2-m3 Cross-Encoder on GPU.
    Falls back to simple keyword rerank if model not available.
    """
    import torch
    if not torch.cuda.is_available():
        # CPU fallback — simple keyword scorer
        from app.core.hybrid_search import bm25_search
        query_keywords = set(query.lower().split())
        for i in range(len(query) - 1):
            if '一' <= query[i] <= '鿿':
                query_keywords.add(query[i:i + 2])
        scored = []
        for chunk in chunks:
            text = chunk["text"].lower()
            kw_score = sum(1 for kw in query_keywords if kw in text)
            vec_score = 1.0 / (1.0 + chunk.get("score", 1.0))
            chunk["rerank_score"] = 0.5 * kw_score / max(len(text.split()), 1) + 0.5 * vec_score
            scored.append(chunk)
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]

    try:
        reranker = get_reranker()
        pairs = [[query, chunk["text"]] for chunk in chunks]
        scores = reranker.compute_score(pairs, normalize=True)
        if not isinstance(scores, list):
            scores = [scores]

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i]) if i < len(scores) else 0.0

        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return chunks[:top_k]

    except Exception as e:
        # Fallback: keyword rerank
        print(f"[Reranker] GPU rerank failed ({e}), using keyword fallback")
        query_keywords = set(query.lower().split())
        for i in range(len(query) - 1):
            if '一' <= query[i] <= '鿿':
                query_keywords.add(query[i:i + 2])
        for chunk in chunks:
            text = chunk["text"].lower()
            kw_score = sum(1 for kw in query_keywords if kw in text)
            vec_score = 1.0 / (1.0 + chunk.get("score", 1.0))
            chunk["rerank_score"] = 0.5 * kw_score / max(len(text.split()), 1) + 0.5 * vec_score
        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return chunks[:top_k]
