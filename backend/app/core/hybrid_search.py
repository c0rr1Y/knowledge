"""Hybrid retrieval: BM25 keyword search + ChromaDB vector search, fused with RRF."""

import math
import re
from collections import defaultdict
from typing import Optional

_STAT_QUERY = re.compile(
    r"统计|汇总|合计|总共|一共|多少|几条|几笔|几份|数量|金额|总金额|求和|计数|平均|最高|最低|"
    r"total|sum|count|average|avg|max|min|how many|how much",
    re.IGNORECASE,
)


def is_statistics_query(query: str) -> bool:
    """True when the query looks like an aggregation/summary over document data."""
    return bool(_STAT_QUERY.search(query or ""))


class BM25Index:
    """In-memory BM25 index per knowledge base collection."""

    def __init__(self):
        self.documents: list[dict] = []  # [{"id": ..., "text": ..., "metadata": ...}]
        self.doc_count = 0
        self.avgdl = 0.0
        self.idf: dict[str, float] = {}
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lengths: list[int] = []
        self.term_freqs: list[dict[str, int]] = []

        self.k1 = 1.5
        self.b = 0.75

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for BM25 — supports Chinese + English."""
        tokens = []

        # Chinese: character unigrams + bigrams
        cleaned = re.sub(r'[^一-鿿\w]', ' ', text.lower())

        # English words
        for word in cleaned.split():
            if re.search(r'[a-z0-9]', word):
                tokens.append(word)
            else:
                # Chinese characters
                tokens.extend(word)

        # Add bigrams for Chinese
        chinese_chars = [c for c in cleaned if '一' <= c <= '鿿']
        for i in range(len(chinese_chars) - 1):
            tokens.append(chinese_chars[i] + chinese_chars[i + 1])

        return tokens

    def add_document(self, doc_id: str, text: str, metadata: dict):
        """Index a single document chunk."""
        tokens = self._tokenize(text)
        tf = defaultdict(int)
        for t in tokens:
            tf[t] += 1

        self.documents.append({"id": doc_id, "text": text, "metadata": metadata})
        self.doc_lengths.append(len(tokens))
        self.term_freqs.append(tf)
        self.doc_count += 1

        for term in set(tokens):
            self.doc_freqs[term] += 1

    def build_idf(self):
        """Compute IDF after all docs are added."""
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

        total_len = sum(self.doc_lengths)
        self.avgdl = total_len / max(self.doc_count, 1)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Search and return top_k results with scores."""
        if self.doc_count == 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []

        for i in range(self.doc_count):
            score = 0.0
            tf = self.term_freqs[i]
            dl = self.doc_lengths[i]

            for token in query_tokens:
                token_tf = tf.get(token, 0)
                token_idf = self.idf.get(token, 0)
                if token_idf == 0:
                    continue
                numerator = token_tf * (self.k1 + 1)
                denominator = token_tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += token_idf * numerator / denominator

            if score > 0:
                scores.append({
                    **self.documents[i],
                    "bm25_score": score,
                })

        scores.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scores[:top_k]

    def remove_document(self, doc_id: str):
        """Remove all chunks belonging to a document."""
        indices_to_remove = []
        for i, doc in enumerate(self.documents):
            if doc["id"].startswith(doc_id):
                indices_to_remove.append(i)

        for i in reversed(indices_to_remove):
            removed = self.documents.pop(i)
            self.doc_lengths.pop(i)
            self.term_freqs.pop(i)
            self.doc_count -= 1

            # Rebuild doc_freqs (expensive but rare operation)
            self.doc_freqs.clear()
            for tf_dict in self.term_freqs:
                for term in tf_dict:
                    self.doc_freqs[term] += 1

        self.build_idf()


# ---- Global BM25 index registry (keyed by collection_name) ----
_bm25_indexes: dict[str, BM25Index] = {}


def get_bm25_index(collection_name: str) -> BM25Index:
    """Get or create a BM25 index for a collection."""
    if collection_name not in _bm25_indexes:
        _bm25_indexes[collection_name] = BM25Index()
    return _bm25_indexes[collection_name]


def index_chunks(collection_name: str, chunks: list[dict], chunk_ids: list[str]):
    """Index a batch of chunks into BM25."""
    bm25 = get_bm25_index(collection_name)
    for i, chunk in enumerate(chunks):
        bm25.add_document(chunk_ids[i], chunk["text"], chunk.get("metadata", {}))
    bm25.build_idf()


def remove_from_index(collection_name: str, doc_id: str):
    """Remove a document's chunks from BM25 index."""
    bm25 = get_bm25_index(collection_name)
    bm25.remove_document(doc_id)


def bm25_search(query: str, collection_name: str, top_k: int = 10) -> list[dict]:
    """Search BM25 index for a collection."""
    bm25 = get_bm25_index(collection_name)
    return bm25.search(query, top_k)


# ---- Reciprocal Rank Fusion ----

def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    top_k: int = 10,
    k: int = 60,
    vector_weight: float = 0.55,
) -> list[dict]:
    """Fuse vector and BM25 results using weighted RRF.

    Args:
        vector_results: Results from ChromaDB with "score" key (lower = better for L2 distance).
        bm25_results: Results from BM25 with "bm25_score" key (higher = better).
        top_k: Number of final results to return.
        k: RRF constant to dampen rank differences.
        vector_weight: Weight for vector results (0-1). BM25 weight = 1 - vector_weight.

    Returns:
        Fused and reranked results.
    """
    rrf_scores: dict[str, dict] = {}

    # Add vector results (lower distance = better rank)
    for rank, result in enumerate(vector_results):
        doc_id = result.get("metadata", {}).get("doc_id", "") + "_" + str(result.get("metadata", {}).get("chunk_index", rank))
        # Normalize: convert distance to similarity-like score (assumes L2 distance)
        distance = result.get("score", 1.0)
        # Invert distance — closer = higher score
        sim_score = 1.0 / (1.0 + float(distance))
        rrf = vector_weight / (k + rank + 1) * sim_score * 100
        rrf_scores[doc_id] = {**result, "rrf_score": rrf}

    # Add BM25 results (higher score = better)
    for rank, result in enumerate(bm25_results):
        doc_id = result.get("metadata", {}).get("doc_id", "") + "_" + str(result.get("metadata", {}).get("chunk_index", rank))
        bm25_weight = 1.0 - vector_weight
        rrf = bm25_weight / (k + rank + 1) * (result.get("bm25_score", 0) or 1)
        if doc_id in rrf_scores:
            rrf_scores[doc_id]["rrf_score"] += rrf
        else:
            rrf_scores[doc_id] = {**result, "rrf_score": rrf}

    # Sort by RRF score
    fused = sorted(rrf_scores.values(), key=lambda x: x.get("rrf_score", 0), reverse=True)
    return fused[:top_k]


# ---- Unified hybrid search ----

def hybrid_search(
    query: str,
    collection_name: str,
    vector_store,
    embedding_model,
    top_k: int = 10,
) -> list[dict]:
    """Perform hybrid search: vector + BM25, fused with RRF.

    Returns list of chunks with "text", "metadata", "rrf_score".
    """
    # Vector search
    vector_results = []
    try:
        collection = vector_store.get_collection(collection_name)
        query_embedding = embedding_model.encode([query], show_progress_bar=False)[0].tolist()
        vec_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        if vec_results["documents"] and vec_results["documents"][0]:
            for i, text in enumerate(vec_results["documents"][0]):
                metadata = vec_results["metadatas"][0][i] if vec_results["metadatas"] else {}
                distance = vec_results["distances"][0][i] if vec_results["distances"] else 0
                vector_results.append({
                    "text": text,
                    "metadata": metadata,
                    "score": float(distance),
                })
    except Exception:
        pass

    # BM25 search
    bm25_results = bm25_search(query, collection_name, top_k=top_k * 2)

    # Fuse
    if vector_results and bm25_results:
        return reciprocal_rank_fusion(vector_results, bm25_results, top_k=top_k)
    elif vector_results:
        return vector_results[:top_k]
    else:
        # Convert BM25 results to same format
        return [
            {"text": r["text"], "metadata": r["metadata"], "score": 1.0 / (1.0 + r.get("bm25_score", 0))}
            for r in bm25_results[:top_k]
        ]
