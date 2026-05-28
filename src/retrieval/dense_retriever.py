from __future__ import annotations

from typing import List, Dict, Optional
import numpy as np


class DenseRetriever:
    """Qdrant-backed dense retriever. Requires a live Qdrant instance (Docker)."""

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
    """Self-contained dense retriever — no Qdrant required.

    Uses a pre-built float32 matrix of L2-normalised embeddings.
    Dot product on normalised vectors equals cosine similarity, so
    np.matmul gives the full ranking in one BLAS call.

    Primary backend  : sentence-transformers (BAAI/bge-small-en-v1.5, 384-dim)
    Fallback backend : TF-IDF + TruncatedSVD (LSA, 128-dim) — used when
                       torch/sentence-transformers are unavailable or on
                       low-RAM machines where the full model won't fit.
    """

    def __init__(
        self,
        chunks: List[Dict],
        embedder=None,
        embedding_matrix: Optional[np.ndarray] = None,
    ):
        self.chunks = chunks
        # chunk_id → row index for O(1) lookup by ID
        self._index = {c["chunk_id"]: i for i, c in enumerate(chunks)}

        if embedding_matrix is not None:
            # Caller pre-computed the matrix (e.g. loaded from .npy cache)
            self.matrix = embedding_matrix.astype(np.float32)
        elif embedder is not None:
            texts = [c["text"] for c in chunks]
            raw = embedder.encode(
                texts, batch_size=256, show_progress_bar=True, normalize_embeddings=True
            )
            self.matrix = np.array(raw, dtype=np.float32)
        else:
            # No embedder provided — build TF-IDF+LSA index from scratch
            self._build_tfidf_index()
            self._tfidf_fallback = True

    def _build_tfidf_index(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

        texts = [c["text"] for c in self.chunks]
        # 8k vocab + 128-dim SVD: fast enough on 50k chunks (~15s) and
        # fits in ~200MB RAM; larger values cause OOM on 1GB machines.
        self._tfidf_vec = TfidfVectorizer(max_features=8_000, sublinear_tf=True)
        X = self._tfidf_vec.fit_transform(texts)
        n_components = min(128, X.shape[1] - 1)
        self._tfidf_svd = TruncatedSVD(n_components=n_components, random_state=42, n_iter=5)
        dense = self._tfidf_svd.fit_transform(X)
        # L2-normalise so dot product == cosine similarity at search time
        self.matrix = normalize(dense, norm="l2").astype(np.float32)

    def _embed_query(self, query: str) -> np.ndarray:
        if hasattr(self, "_tfidf_fallback"):
            return self._query_via_tfidf(query)
        return self._query_via_embedder(query)

    def _query_via_tfidf(self, query: str) -> np.ndarray:
        from sklearn.preprocessing import normalize
        # Apply the same TF-IDF → SVD → L2-norm pipeline used at index time
        q_vec = self._tfidf_vec.transform([query])
        q_dense = self._tfidf_svd.transform(q_vec)
        return normalize(q_dense, norm="l2")[0].astype(np.float32)

    def _query_via_embedder(self, query: str) -> np.ndarray:
        raise RuntimeError("Embedder not attached — call build_with_embedder()")

    def _filter_chunks(self, filters: Optional[dict]) -> List[int]:
        """Return row indices of chunks that match ALL filter fields."""
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
        # Slice the matrix to only filtered rows before scoring — avoids
        # computing similarities for chunks that would be discarded anyway.
        sub_matrix = self.matrix[indices]
        sims = sub_matrix @ q_vec
        top_local = np.argsort(sims)[::-1][:k]
        results = []
        for li in top_local:
            gi = indices[li]
            results.append(dict(self.chunks[gi], score=float(sims[li]), retriever="dense"))
        return results

    def save(self, path: str):
        """Persist matrix to .npy and (for TF-IDF backend) sklearn objects to .pkl.

        The .meta file records which backend was used so load() can restore
        the correct query-embedding pipeline without refitting from scratch.
        """
        np.save(path, self.matrix)
        meta_path = path.replace(".npy", ".meta")
        backend = "tfidf" if hasattr(self, "_tfidf_fallback") else "embedder"
        with open(meta_path, "w") as f:
            f.write(backend)
        if backend == "tfidf":
            import joblib
            # joblib is faster and more memory-efficient than pickle for
            # large numpy arrays inside sklearn objects
            joblib_path = path.replace(".npy", "_tfidf.pkl")
            joblib.dump({"vec": self._tfidf_vec, "svd": self._tfidf_svd}, joblib_path)

    @classmethod
    def load(cls, chunks: List[Dict], path: str) -> "NumpyDenseRetriever":
        """Load a saved retriever.  Restores TF-IDF objects so queries work
        immediately without rebuilding the index."""
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
                # .pkl missing — rebuild deterministically (~10s on 50k chunks)
                obj._build_tfidf_index()
            return obj

        return cls(chunks, embedding_matrix=matrix)
