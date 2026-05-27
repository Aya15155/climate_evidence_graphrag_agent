from __future__ import annotations

from typing import List, Dict, Optional
import numpy as np


class DenseRetriever:
    """Qdrant-backed dense retriever. Requires a live Qdrant instance."""

    def __init__(self, qdrant_client=None, embedder=None, collection: str = "climate_chunks"):
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.collection = collection

    def search(self, query: str, k: int = 5, filters: dict | None = None):
        if self.qdrant_client is None or self.embedder is None:
            return []
        vector = self.embedder.encode([query])[0]
        qdrant_filter = _build_qdrant_filter(filters) if filters else None
        hits = self.qdrant_client.search(
            self.collection,
            query_vector=vector,
            query_filter=qdrant_filter,
            limit=k,
        )
        return [dict(hit.payload, score=hit.score, retriever="dense") for hit in hits]


def _build_qdrant_filter(filters: dict):
    """Convert a dict like {"topics": ["mitigation"]} to a Qdrant Filter."""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        conditions = []
        for field, values in filters.items():
            if isinstance(values, list):
                conditions.append(FieldCondition(key=field, match=MatchAny(any=values)))
        return Filter(must=conditions) if conditions else None
    except ImportError:
        return None


class NumpyDenseRetriever:
    """Self-contained dense retriever using numpy cosine similarity.

    No Qdrant required.  Embeddings are computed once at build time and
    stored in a float32 matrix for fast dot-product search (vectors must
    already be L2-normalised, which is the default for BAAI/bge-* models).

    Falls back to sklearn TF-IDF + TruncatedSVD when sentence-transformers
    or torch is unavailable, preserving the BM25 vs dense vs hybrid
    comparison even in restricted environments.
    """

    def __init__(
        self,
        chunks: List[Dict],
        embedder=None,
        embedding_matrix: Optional[np.ndarray] = None,
    ):
        self.chunks = chunks
        self._index = {c["chunk_id"]: i for i, c in enumerate(chunks)}

        if embedding_matrix is not None:
            self.matrix = embedding_matrix.astype(np.float32)
        elif embedder is not None:
            texts = [c["text"] for c in chunks]
            raw = embedder.encode(texts, batch_size=256, show_progress_bar=True, normalize_embeddings=True)
            self.matrix = np.array(raw, dtype=np.float32)
        else:
            self._build_tfidf_index()
            self._tfidf_fallback = True

    def _build_tfidf_index(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

        texts = [c["text"] for c in self.chunks]
        # 8k features + 128-dim LSA keeps build time under 15s on 50k chunks
        self._tfidf_vec = TfidfVectorizer(max_features=8_000, sublinear_tf=True)
        X = self._tfidf_vec.fit_transform(texts)
        n_components = min(128, X.shape[1] - 1)
        self._tfidf_svd = TruncatedSVD(n_components=n_components, random_state=42, n_iter=5)
        dense = self._tfidf_svd.fit_transform(X)
        self.matrix = normalize(dense, norm="l2").astype(np.float32)

    def _embed_query(self, query: str) -> np.ndarray:
        if hasattr(self, "_tfidf_fallback"):
            return self._query_via_tfidf(query)
        return self._query_via_embedder(query)

    def _query_via_tfidf(self, query: str) -> np.ndarray:
        from sklearn.preprocessing import normalize

        q_vec = self._tfidf_vec.transform([query])
        q_dense = self._tfidf_svd.transform(q_vec)
        return normalize(q_dense, norm="l2")[0].astype(np.float32)

    def _query_via_embedder(self, query: str) -> np.ndarray:
        raise RuntimeError("Embedder not attached — call build_with_embedder()")

    def _filter_chunks(self, filters: Optional[dict]) -> List[int]:
        if not filters:
            return list(range(len(self.chunks)))
        indices = []
        for i, c in enumerate(self.chunks):
            match = True
            for field, values in filters.items():
                chunk_val = c.get(field, [])
                if isinstance(chunk_val, list):
                    if not any(v in chunk_val for v in values):
                        match = False
                        break
                else:
                    if chunk_val not in values:
                        match = False
                        break
            if match:
                indices.append(i)
        return indices

    def search(self, query: str, k: int = 5, filters: Optional[dict] = None) -> List[Dict]:
        q_vec = self._embed_query(query)
        indices = self._filter_chunks(filters)
        if not indices:
            return []
        sub_matrix = self.matrix[indices]
        sims = sub_matrix @ q_vec
        top_local = np.argsort(sims)[::-1][:k]
        results = []
        for li in top_local:
            gi = indices[li]
            results.append(dict(self.chunks[gi], score=float(sims[li]), retriever="dense"))
        return results

    def save(self, path: str):
        """Save the embedding matrix and (for TF-IDF) the fitted vectorizer/SVD."""
        np.save(path, self.matrix)
        meta_path = path.replace(".npy", ".meta")
        backend = "tfidf" if hasattr(self, "_tfidf_fallback") else "embedder"
        with open(meta_path, "w") as f:
            f.write(backend)
        if backend == "tfidf":
            import joblib
            joblib_path = path.replace(".npy", "_tfidf.pkl")
            joblib.dump({"vec": self._tfidf_vec, "svd": self._tfidf_svd}, joblib_path)

    @classmethod
    def load(cls, chunks: List[Dict], path: str) -> "NumpyDenseRetriever":
        """Load matrix from disk; restore TF-IDF objects if available."""
        matrix = np.load(path)
        meta_path = path.replace(".npy", ".meta")
        backend = "embedder"
        try:
            with open(meta_path) as f:
                backend = f.read().strip()
        except FileNotFoundError:
            if "tfidf" in path or "lsa" in path:
                backend = "tfidf"

        if backend == "tfidf":
            joblib_path = path.replace(".npy", "_tfidf.pkl")
            obj = cls.__new__(cls)
            obj.chunks = chunks
            obj._index = {c["chunk_id"]: i for i, c in enumerate(chunks)}
            obj.matrix = matrix.astype(np.float32)
            obj._tfidf_fallback = True
            try:
                import joblib
                saved = joblib.load(joblib_path)
                obj._tfidf_vec = saved["vec"]
                obj._tfidf_svd = saved["svd"]
            except (FileNotFoundError, Exception):
                # Fallback: rebuild (deterministic, ~10s on 50k chunks)
                obj._build_tfidf_index()
            return obj

        return cls(chunks, embedding_matrix=matrix)
