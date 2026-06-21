"""
Climate Evidence GraphRAG Agent — Streamlit demo
==================================================
Single front-door demo for the team's 15-minute presentation. Wraps the REAL
pipeline code already built by the team — no mocked logic lives in this file.

Two tabs:
  1. Ask a Question  — live query through hybrid retrieval + GraphRAG executor
  2. Team Evidence    — already-computed real results from every member's notebook

Run locally:
    streamlit run app/streamlit_app.py

Optional, to light up the full graph-guided + real-LLM-answer path:
    docker compose up -d neo4j        # enables real Cypher traversal
    export GEMINI_API_KEY=your_key    # enables real generated answers (not mock text)

Without those two, the app still runs end-to-end: GraphRAGExecutor.run() already
catches Neo4j connection errors internally and falls back to hybrid_fallback,
and AnswerGenerator returns a clearly-labeled mock answer when no Gemini key is
set — neither crashes the app. This is documented in the team's own design doc
as a deliberate "honesty over flexibility" choice, and it's why this app is
safe to demo live even if the graph isn't running.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Project root bootstrap (so `from src...` imports work no matter where
# streamlit was launched from)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

CHUNKS_PATH = PROJECT_ROOT / "data" / "sample" / "sample_chunks.json"
DENSE_CACHE = PROJECT_ROOT / "data" / "embeddings" / "chunks_tfidf_lsa.npy"
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"

st.set_page_config(
    page_title="Climate Evidence GraphRAG Agent",
    page_icon="\U0001F30D",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Cached loaders — built once per session, reused across reruns
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_chunks():
    """Load the chunk corpus. Returns (chunks, error_message)."""
    if not CHUNKS_PATH.exists():
        return None, f"Missing file: {CHUNKS_PATH}"
    try:
        with open(CHUNKS_PATH, "r", encoding="utf-8") as fh:
            chunks = json.load(fh)
    except json.JSONDecodeError:
        # This is the Git LFS pointer-file trap: the file exists but only
        # contains a pointer like "version https://git-lfs.github.com/...".
        # `git clone` resolves it automatically; GitHub's "Download ZIP"
        # button does NOT. Fix: `git lfs install && git lfs pull`.
        return None, (
            "This file looks like a Git LFS pointer, not real chunk data "
            "(common after downloading a ZIP from GitHub instead of cloning). "
            "Run: git lfs install && git lfs pull"
        )
    for i, c in enumerate(chunks):
        c.setdefault("chunk_id", f"chunk_{i:06d}")
    return chunks, None


@st.cache_resource(show_spinner=False)
def get_hybrid_retriever(_chunks):
    """Same construction pattern as src/api/main.py's /search endpoint."""
    from src.retrieval.bm25_retriever import BM25Retriever
    from src.retrieval.dense_retriever import NumpyDenseRetriever
    from src.retrieval.hybrid_retriever import HybridRetriever

    bm25 = BM25Retriever(_chunks)
    if DENSE_CACHE.exists():
        dense = NumpyDenseRetriever.load(_chunks, str(DENSE_CACHE))
    else:
        dense = NumpyDenseRetriever(_chunks)
    return HybridRetriever(bm25, dense, bm25_weight=0.5, normalization="rrf")


@st.cache_resource(show_spinner=False)
def get_graphrag_executor():
    """Builds the real GraphRAGExecutor. Returns (executor, error_message).

    Construction itself does not require a live Neo4j connection (the driver
    is lazy) — failures only surface inside .run() and are already caught
    there, returning retrieval_type='hybrid_fallback' instead of crashing.
    """
    try:
        from src.rag.graphrag_executor import GraphRAGExecutor
        executor = GraphRAGExecutor.from_config(str(CONFIG_PATH))
        return executor, None
    except Exception as exc:  # missing package, bad config, etc.
        return None, str(exc)


def neo4j_status() -> tuple[bool, str]:
    """Best-effort live connectivity probe, never raises."""
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        pwd = os.getenv("NEO4J_PASSWORD", "climate123")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        driver.verify_connectivity()
        driver.close()
        return True, uri
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Sidebar — system status + example queries
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("System status")

    chunks, chunk_err = load_chunks()
    if chunks is not None:
        st.success(f"Corpus loaded: {len(chunks):,} chunks")
    else:
        st.error(f"Corpus not loaded\n\n{chunk_err}")

    neo4j_ok, neo4j_info = (False, "not checked")
    if st.button("Check Neo4j connection"):
        neo4j_ok, neo4j_info = neo4j_status()
        if neo4j_ok:
            st.success(f"Neo4j connected ({neo4j_info})")
        else:
            st.warning("Neo4j not reachable — graph-guided mode will fall back to hybrid retrieval.")

    gemini_set = bool(os.getenv("GEMINI_API_KEY"))
    if gemini_set:
        st.success("GEMINI_API_KEY is set")
    else:
        st.info("GEMINI_API_KEY not set — answers will show as [MOCK] assembled evidence instead of a generated answer.")

    st.divider()
    st.header("Example queries")
    st.caption("Click to load a query that's known to exercise a specific pattern.")

    examples = [
        ("\U0001F1E6\U0001F1EA Country \u2192 Policy \u2192 Target", "What renewable energy targets has the UAE committed to under its Net Zero 2050 strategy?"),
        ("\U0001F525 Risk \u2192 Sector \u2192 Evidence", "What high-confidence climate risks in the MENA region are documented by findings, and which sectors do they impact?"),
        ("\u2699\uFE0F Technology \u2192 Mitigates \u2192 Risk", "Which technologies mitigate heatwave risk in the energy sector according to climate literature?"),
        ("\u274C Failure: missing entity", "List all climate adaptation policies adopted by Pacific Islands countries for coastal flooding."),
        ("\u274C Failure: graph adds no value", "What does the literature say about gradient boosting methods for wind power forecasting?"),
    ]
    for label, q in examples:
        if st.button(label, width="stretch"):
            st.session_state["query_input"] = q

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("\U0001F30D Climate Evidence GraphRAG Agent")
st.caption("300 real climate documents \u00B7 hybrid retrieval (BM25 + dense) \u00B7 knowledge-graph-guided reasoning \u00B7 page-level citations")

tab_ask, tab_evidence = st.tabs(["\U0001F4AC Ask a Question", "\U0001F4CA Team Evidence"])

# ===================== TAB 1: Live demo =====================
with tab_ask:
    if chunks is None:
        st.error(
            "Can't run the live demo without the chunk corpus. "
            "See the sidebar error for the fix (usually a Git LFS pull)."
        )
    else:
        query = st.text_input(
            "Ask a climate question",
            key="query_input",
            placeholder="e.g. What renewable energy targets has the UAE committed to?",
        )
        run = st.button("Ask", type="primary")

        if run and query.strip():
            hybrid = get_hybrid_retriever(chunks)
            executor, exec_err = get_graphrag_executor()

            col_left, col_right = st.columns([3, 2])

            # ---- GraphRAG full trace (left) ----
            with col_left:
                st.subheader("GraphRAG executor trace")
                if executor is None:
                    st.error(f"GraphRAG executor could not be built: {exec_err}")
                else:
                    with st.spinner("Running 4-stage GraphRAG pipeline..."):
                        t0 = time.perf_counter()
                        try:
                            result = executor.run(query)
                        except Exception as exc:
                            result = None
                            st.error(f"Pipeline error: {exc}")
                        elapsed = time.perf_counter() - t0

                    if result is not None:
                        fallback = result.retrieval_type in ("hybrid_fallback", "empty")
                        badge_color = "orange" if fallback else "green"
                        st.markdown(
                            f"**Retrieval type:** :{badge_color}[{result.retrieval_type}]  "
                            f"&nbsp;&nbsp;**Fallback used:** {fallback}  "
                            f"&nbsp;&nbsp;**Latency:** {result.latency_sec:.2f}s "
                            f"(wall: {elapsed:.2f}s)"
                        )

                        if result.cypher_query:
                            with st.expander("Cypher template used", expanded=False):
                                st.code(result.cypher_query, language="cypher")

                        if result.graph_hits:
                            st.markdown("**Graph path / hits:**")
                            for h in result.graph_hits[:5]:
                                st.markdown(f"- `{h.doc_id}` \u00B7 page {h.page} \u00B7 confidence {h.confidence}")
                        else:
                            st.markdown("**Graph path / hits:** _none \u2014 0 Cypher rows (graph had nothing here)_")

                        st.markdown("**Answer:**")
                        st.info(result.answer)

                        if result.citation_pages:
                            st.markdown("**Citations:** " + "; ".join(result.citation_pages))

                        if result.answer_quality_notes:
                            st.caption(f"Analysis: {result.answer_quality_notes}")

            # ---- Plain hybrid retrieval (right) — always works, no Neo4j needed ----
            with col_right:
                st.subheader("Hybrid retrieval (BM25 + dense)")
                with st.spinner("Searching..."):
                    hits = hybrid.search(query, k=5)
                for i, h in enumerate(hits, 1):
                    title = h.get("title") or h.get("document_id") or h.get("doc_id") or "Untitled"
                    page = h.get("page_start") or h.get("page")
                    snippet = (h.get("text") or h.get("snippet") or "")[:220]
                    st.markdown(f"**{i}. {title}**" + (f" \u00B7 p.{page}" if page else ""))
                    st.caption(snippet + ("..." if snippet else ""))
        elif run:
            st.warning("Type a question first.")

# ===================== TAB 2: Team evidence dashboard =====================
with tab_evidence:
    st.caption("Already-computed real results from each member's D2/D3 notebook \u2014 safe to show even if live services aren't running.")

    def show_csv(title, filename, owner):
        path = TABLES_DIR / filename
        st.subheader(f"{title}  \u2014  *{owner}*")
        if not path.exists():
            st.warning(f"Not generated yet: `reports/tables/{filename}`")
            return None
        df = pd.read_csv(path)
        st.dataframe(df, width="stretch")
        return df

    c1, c2 = st.columns(2)
    with c1:
        ablation_summary = show_csv("Retrieval ablation \u2014 5 systems compared", "d3_retrieval_ablation_summary.csv", "Salma")
        if ablation_summary is not None and "System" in ablation_summary.columns:
            chart_cols = [c for c in ["Hit@5", "Recall@5", "NDCG@5"] if c in ablation_summary.columns]
            if chart_cols:
                st.bar_chart(ablation_summary.set_index("System")[chart_cols])

    with c2:
        show_csv("Graph-guided results \u2014 success + failure examples", "d3_graph_guided_results.csv", "Rana")

    c3, c4 = st.columns(2)
    with c3:
        show_csv("Safety before/after \u2014 prompt injection & source pinning", "d3_safety_before_after.csv", "Alia")
    with c4:
        show_csv("RAG quality eval \u2014 faithfulness & relevance", "d3_rag_eval_metrics.csv", "Alia")

    st.subheader("Knowledge graph \u2014 node & relationship counts  \u2014  *Rana*")
    graph_counts_path = TABLES_DIR / "d2_graph_counts.csv"
    if graph_counts_path.exists():
        gdf = pd.read_csv(graph_counts_path)
        st.dataframe(gdf, width="stretch")
    else:
        st.warning("Not generated yet: `reports/tables/d2_graph_counts.csv`")
