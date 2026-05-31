"""
D2 retrieval smoke tests — Alia

Tests BM25, dense, and hybrid retrievers directly using in-memory chunks.
No external stores required.

Run:  pytest tests/test_search.py -v
"""
import pytest
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import NumpyDenseRetriever
from src.retrieval.hybrid_retriever import HybridRetriever


SAMPLE_CHUNKS = [
    {"chunk_id": "doc1_p1_c0", "document_id": "ipcc_ar6_2021",
     "text": "Global surface temperature has increased due to human influence on the climate system.",
     "start_page": 1, "end_page": 1, "source": "IPCC AR6 WG1 (2021)"},
    {"chunk_id": "doc1_p2_c0", "document_id": "ipcc_ar6_2021",
     "text": "Sea level rise accelerated from 1.3 mm per year in 1901-1971 to 3.7 mm per year in 2006-2018.",
     "start_page": 2, "end_page": 2, "source": "IPCC AR6 WG1 (2021)"},
    {"chunk_id": "doc2_p3_c0", "document_id": "carbon_budget_2020",
     "text": "Fossil fuel CO2 emissions reached 36.4 GtCO2 in 2019. Land-use change contributed 6 GtCO2.",
     "start_page": 3, "end_page": 3, "source": "Global Carbon Budget 2020"},
    {"chunk_id": "doc3_p8_c0", "document_id": "fire_emissions_2010",
     "text": "Deforestation and fire emissions in tropical regions account for approximately 2 GtC per year.",
     "start_page": 8, "end_page": 8, "source": "Global Fire Emissions Database"},
    {"chunk_id": "doc4_p9_c0", "document_id": "ccs_2018",
     "text": "Carbon capture and storage is a key climate mitigation strategy to limit warming to 1.5 degrees.",
     "start_page": 9, "end_page": 9, "source": "Carbon Capture and Storage (Bui et al., 2018)"},
]


# ---------------------------------------------------------------------------
# BM25 tests
# ---------------------------------------------------------------------------

class TestBM25Retriever:
    def test_returns_results(self):
        r = BM25Retriever(SAMPLE_CHUNKS)
        assert len(r.search("climate temperature", k=3)) > 0

    def test_result_has_required_fields(self):
        result = BM25Retriever(SAMPLE_CHUNKS).search("CO2 emissions fossil fuel", k=1)[0]
        for field in ("chunk_id", "document_id", "text", "score"):
            assert field in result

    def test_keyword_match_ranks_first(self):
        results = BM25Retriever(SAMPLE_CHUNKS).search("sea level rise", k=5)
        assert results[0]["chunk_id"] == "doc1_p2_c0"

    def test_empty_query_does_not_crash(self):
        assert isinstance(BM25Retriever(SAMPLE_CHUNKS).search("", k=3), list)

    def test_k_limits_results(self):
        assert len(BM25Retriever(SAMPLE_CHUNKS).search("carbon emissions fire", k=2)) <= 2

    def test_score_is_numeric(self):
        for r in BM25Retriever(SAMPLE_CHUNKS).search("climate", k=5):
            assert isinstance(r["score"], (int, float))

    def test_empty_corpus_returns_empty(self):
        assert BM25Retriever([]).search("climate", k=5) == []


# ---------------------------------------------------------------------------
# NumpyDenseRetriever tests
# ---------------------------------------------------------------------------

class TestNumpyDenseRetriever:
    def test_returns_results(self):
        assert len(NumpyDenseRetriever(SAMPLE_CHUNKS).search("global warming", k=3)) > 0

    def test_result_has_required_fields(self):
        result = NumpyDenseRetriever(SAMPLE_CHUNKS).search("CO2 emissions", k=1)[0]
        for field in ("chunk_id", "document_id", "text", "score"):
            assert field in result

    def test_k_limits_results(self):
        assert len(NumpyDenseRetriever(SAMPLE_CHUNKS).search("climate mitigation", k=2)) <= 2

    def test_score_is_numeric(self):
        for r in NumpyDenseRetriever(SAMPLE_CHUNKS).search("temperature", k=5):
            assert isinstance(r["score"], (int, float))


# ---------------------------------------------------------------------------
# HybridRetriever tests
# ---------------------------------------------------------------------------

class TestHybridRetriever:
    @pytest.fixture
    def hybrid(self):
        bm25 = BM25Retriever(SAMPLE_CHUNKS)
        dense = NumpyDenseRetriever(SAMPLE_CHUNKS)
        return HybridRetriever(bm25, dense, normalization="rrf")

    def test_returns_results(self, hybrid):
        assert len(hybrid.search("carbon emissions climate", k=3)) > 0

    def test_result_has_provenance_fields(self, hybrid):
        result = hybrid.search("deforestation fire emissions", k=1)[0]
        for field in ("chunk_id", "document_id", "text"):
            assert field in result

    def test_k_limits_results(self, hybrid):
        assert len(hybrid.search("climate", k=2)) <= 2

    def test_rrf_score_present(self, hybrid):
        for r in hybrid.search("sea level rise", k=5):
            assert "rrf_score" in r or "fused_score" in r or "score" in r

    def test_minmax_normalization_works(self):
        bm25 = BM25Retriever(SAMPLE_CHUNKS)
        dense = NumpyDenseRetriever(SAMPLE_CHUNKS)
        hybrid = HybridRetriever(bm25, dense, normalization="minmax")
        assert len(hybrid.search("CO2 fossil fuel", k=3)) > 0

    def test_no_dense_fallback_to_bm25_only(self):
        hybrid = HybridRetriever(BM25Retriever(SAMPLE_CHUNKS), dense_retriever=None, normalization="rrf")
        assert len(hybrid.search("climate", k=3)) > 0