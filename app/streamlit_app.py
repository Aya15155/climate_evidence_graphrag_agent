"""
Climate Evidence GraphRAG Agent — Streamlit demo
==================================================
Single front-door demo for the team's 15-minute presentation.

Tabs:
  Overview   — elevator pitch, architecture, tech stack
  D1         — foundations: data, AutoML retrieval tuning, online learning
  D2         — retrieval stack + knowledge graph build
  D3         — GraphRAG executor, online adaptation, safety, tuning
  Live Demo  — ask a real question through the real pipeline, with a
               validated "expected output" reference shown alongside it

Run locally:
    streamlit run app/streamlit_app.py

Optional, to light up the full graph-guided + real-LLM-answer path:
    docker compose up -d neo4j        # or use a Neo4j Aura free instance
    export GEMINI_API_KEY=your_key    # enables real generated answers
    export GEMINI_MODEL=gemini-3.1-flash-lite  # optional; this is the default primary model

Without those two, the app still runs end-to-end: GraphRAGExecutor.run()
already catches Neo4j connection errors internally and falls back to
hybrid_fallback, and AnswerGenerator returns a clearly-labeled mock answer
when no Gemini key is set — neither crashes the app. This is documented in
the team's own design doc as a deliberate "honesty over flexibility" choice.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Project root bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

CHUNKS_PATH = PROJECT_ROOT / "data" / "sample" / "sample_chunks.json"
DENSE_CACHE = PROJECT_ROOT / "data" / "embeddings" / "chunks_tfidf_lsa.npy"
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"
TABLES_DIR = PROJECT_ROOT / "reports" / "tables"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

# Reuse the project's own tiny .env loader (no extra dependency needed) so
# NEO4J_*/GEMINI_API_KEY/GEMINI_MODEL set in a local .env file are picked up app-wide
# before the app computes display/config values.
try:
    from src.rag.graphrag_executor import load_local_env
    load_local_env(PROJECT_ROOT, override=True)
except Exception:
    pass

PRIMARY_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite,gemini-2.5-flash,gemini-1.5-flash").split(",")
    if m.strip()
]

st.set_page_config(
    page_title="Climate Evidence GraphRAG Agent",
    page_icon="\U0001F30D",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_chunks():
    if not CHUNKS_PATH.exists():
        return None, f"Missing file: {CHUNKS_PATH}"
    try:
        with open(CHUNKS_PATH, "r", encoding="utf-8") as fh:
            chunks = json.load(fh)
    except json.JSONDecodeError:
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
    try:
        from src.rag.graphrag_executor import GraphRAGExecutor
        executor = GraphRAGExecutor.from_config(str(CONFIG_PATH))
        return executor, None
    except Exception as exc:
        return None, str(exc)


def neo4j_status() -> tuple[bool, str]:
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
        pwd = os.getenv("NEO4J_PASSWORD", "climate123")
        database = os.getenv("NEO4J_DATABASE")
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with (driver.session(database=database) if database else driver.session()) as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        driver.close()
        safe_uri = uri.split("://", 1)[0] + "://[redacted]" if "://" in uri else "[redacted]"
        return True, f"{safe_uri}; nodes={node_count}"
    except Exception as exc:
        return False, str(exc)


@st.cache_data(show_spinner=False)
def load_csv(filename: str):
    path = TABLES_DIR / filename
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def show_csv_table(filename: str, caption: str = "", cols=None):
    df = load_csv(filename)
    if df is None:
        st.warning(f"Not available: `reports/tables/{filename}`")
        return None
    if cols:
        present = [c for c in cols if c in df.columns]
        if present:
            df = df[present]
    st.dataframe(df, width="stretch")
    if caption:
        st.caption(caption)
    return df


def metric_row(items):
    """items: list of (label, value) tuples, rendered as st.metric columns."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("System status")

    chunks, chunk_err = load_chunks()
    if chunks is not None:
        st.success(f"Corpus loaded: {len(chunks):,} chunks")
    else:
        st.error(f"Corpus not loaded\n\n{chunk_err}")

    if st.button("Check Neo4j connection"):
        neo4j_ok, neo4j_info = neo4j_status()
        if neo4j_ok:
            st.success(f"Neo4j connected ({neo4j_info})")
        else:
            st.warning("Neo4j not reachable \u2014 graph-guided mode will fall back to hybrid retrieval.")

    st.caption("LLM config: Gemini 3.1 Flash Lite primary with retry/fallback to lighter Gemini models.")
    st.caption(f"Primary model: `{PRIMARY_GEMINI_MODEL}`")
    if GEMINI_FALLBACK_MODELS:
        st.caption("Fallback models: " + ", ".join(f"`{m}`" for m in GEMINI_FALLBACK_MODELS))

    gemini_set = bool(os.getenv("GEMINI_API_KEY"))
    if gemini_set:
        st.success("GEMINI_API_KEY is set")
    else:
        st.info("GEMINI_API_KEY not set \u2014 answers show as [MOCK] assembled evidence, by design (Gemini quota was unstable during final prep, see D3_FINAL_SUBMISSION_INDEX.md).")

    st.divider()
    st.caption("Climate Evidence GraphRAG Agent \u2014 CSAI415 \u2014 D1\u2013D3")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("\U0001F30D Climate Evidence GraphRAG Agent")
st.caption("300 real climate documents \u00B7 49,541 chunks \u00B7 hybrid retrieval (BM25 + dense) \u00B7 knowledge-graph-guided reasoning \u00B7 page-level citations")

tab_overview, tab_d1, tab_d2, tab_d3, tab_demo = st.tabs(
    ["\U0001F3E0 Overview", "\U0001F4D8 D1", "\U0001F4D7 D2", "\U0001F4D9 D3", "\U0001F4AC Live Demo"]
)

# ===================== TAB: OVERVIEW =====================
with tab_overview:
    st.header("What this project does")
    st.markdown(
        "We built a system that answers climate questions using **300 real research documents** "
        "instead of letting an AI guess. It searches three ways at once \u2014 by **keyword**, by "
        "**meaning**, and by a **fact-graph** that knows how countries, policies, risks, and "
        "technologies connect \u2014 then an AI writes the final answer using only what was actually "
        "found, and always says **which document and page** it came from."
    )

    st.subheader("How a question flows through the system")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**1. Search**")
        st.caption("Keyword (BM25) + meaning (embeddings) search the 49,541 chunks.")
    with c2:
        st.markdown("**2. Graph check**")
        st.caption("If the question matches a known relationship pattern, Cypher queries the knowledge graph.")
    with c3:
        st.markdown("**3. Blend**")
        st.caption("Graph evidence + search evidence merged, duplicates removed (MMR).")
    with c4:
        st.markdown("**4. Answer**")
        st.caption("An LLM writes the answer from only that evidence, with page citations.")

    st.subheader("Tech stack")
    st.markdown(
        "- **Neo4j** \u2014 graph database storing the knowledge graph\n"
        "- **Cypher** \u2014 Neo4j's query language (pattern-matching, like SQL for graphs)\n"
        "- **BM25** \u2014 classic keyword-ranking algorithm\n"
        "- **Embeddings (TF-IDF + LSA / sentence-transformers)** \u2014 meaning-based search\n"
        "- **Gemini** \u2014 the LLM that writes the final cited answer\n"
        "- **Streamlit** \u2014 this app\n"
        "- **Optuna** \u2014 AutoML hyperparameter search (D1)\n"
        "- **River + ADWIN** \u2014 online learning / concept-drift detection (D1)\n"
        "- **QLoRA** \u2014 lightweight LLM fine-tuning, trained on Kaggle GPU (D3)"
    )

    st.subheader("Team \u2014 who owns what")
    st.dataframe(pd.DataFrame([
        {"Member": "Reem", "D1": "Data foundation, proxy benchmark", "D2": "Ingestion, data quality", "D3": "Page/citation verification"},
        {"Member": "Salma", "D1": "AutoML retrieval tuning (Optuna)", "D2": "BM25 / dense / hybrid retrieval", "D3": "Retrieval ablation, latency"},
        {"Member": "Rana", "D1": "Knowledge graph design plan", "D2": "Neo4j graph build, Cypher", "D3": "GraphRAG executor (the core pipeline)"},
        {"Member": "Aaya", "D1": "Online learning, ADWIN drift detection", "D2": "Online retrieval adaptation", "D3": "Online GraphRAG adaptation"},
        {"Member": "Alia", "D1": "Evaluation methodology", "D2": "API + integration tests", "D3": "Safety, citation verifier, RAG eval"},
    ]), width="stretch", hide_index=True)

# ===================== TAB: D1 =====================
with tab_d1:
    st.header("D1 \u2014 Foundations: data, AutoML, online learning")
    st.caption("Click each section to expand \u2014 each person narrates their own.")

    with st.expander("\U0001F4C4 Reem \u2014 Data foundation & proxy benchmark", expanded=False):
        metric_row([("Documents", "300"), ("Chunks", "49,541"), ("Benchmark questions", "120")])
        st.markdown(
            "- Built the corpus: 300 open-access climate PDFs, page-aware chunking, metadata "
            "(authors, year, topics, countries, sectors, technologies, policies).\n"
            "- The first auto-generated benchmark had labels not truly anchored to the right page, "
            "so a **repaired, page-grounded proxy benchmark** (120 questions) was built instead, "
            "to avoid reporting misleading retrieval scores.\n"
            "- Every row is still flagged `needs_manual_review=true` \u2014 honest about being a "
            "proxy, not a gold-standard human-reviewed set."
        )

    with st.expander("\U0001F50D Salma \u2014 AutoML retrieval tuning", expanded=False):
        st.markdown(
            "Used **Optuna** (30 trials) to auto-tune a BM25 + TF-IDF/SVD + kNN hybrid retriever "
            "against the objective `NDCG@5 + 0.25\u00D7Recall@5 \u2212 0.0005\u00D7p95_latency`."
        )
        show_csv_table("d1_baseline_vs_automl_metrics.csv", "Baseline vs. AutoML-tuned, on 36 held-out test questions.")
        st.caption("Winning config: k=20, metric=cosine, svd_dim=300, normalization=minmax, hybrid_weight\u22480.82")

    with st.expander("\U0001F578\uFE0F Rana \u2014 Knowledge graph design plan", expanded=False):
        st.markdown(
            "D1 didn't require a built graph \u2014 this section is the **design**: schema, "
            "rationale, and integration plan later executed in D2/D3.\n\n"
            "**Why a graph at all?** Plain retrieval treats documents as bags of chunks. A question "
            "like *\"which technologies mitigate flooding risk in the Middle East?\"* needs to "
            "connect a technology, a risk, and a region \u2014 concepts that rarely appear together "
            "in any single chunk. The graph stores those connections explicitly."
        )

    with st.expander("\U0001F4C8 Aaya \u2014 Online learning & concept drift (River + ADWIN)", expanded=False):
        metric_row([("Pre-drift accuracy", "89.97%"), ("Drift-window accuracy", "2.22%"), ("Post-drift accuracy", "95.65%")])
        st.markdown(
            "- A River online classifier (Bag-of-Words + Multinomial Naive Bayes) predicts the "
            "topic of each incoming climate query, across 600 simulated queries.\n"
            "- Concept drift was deliberately injected at query 350 (changed the relationship "
            "between query wording and topic labels).\n"
            "- **ADWIN** detected the drift at query 377 \u2014 a 27-query delay \u2014 then accuracy "
            "recovered to 95.65% as the model adapted.\n"
            "- This topic classifier is the same one later used to route queries in D2/D3's "
            "topic-gated retrieval."
        )
        fig_path = FIGURES_DIR / "prequential_accuracy_plot.png"
        if fig_path.exists():
            st.image(str(fig_path), caption="Rolling accuracy: drops at the injected drift, ADWIN alerts, then recovers.")

    with st.expander("\U00002705 Alia \u2014 Evaluation methodology", expanded=False):
        st.markdown(
            "Defined the metrics used throughout the project: **Recall@5**, **NDCG@5**, **MRR**, "
            "and **p95 latency**. Verified the AutoML numbers came from the runnable script (not "
            "placeholder examples) and that the D1 report stayed scoped to what D1 actually requires."
        )

# ===================== TAB: D2 =====================
with tab_d2:
    st.header("D2 \u2014 Retrieval stack + knowledge graph build")

    with st.expander("\U0001F4C4 Reem \u2014 Ingestion & data quality", expanded=False):
        st.markdown(
            "Built the ingestion pipeline that turns 300 raw PDFs into the page-aware chunk corpus "
            "and metadata table used by every other part of the system."
        )

    with st.expander("\U0001F50D Salma \u2014 BM25 + dense + hybrid retrieval", expanded=False):
        st.markdown(
            "**Why Reciprocal Rank Fusion (RRF) over min-max normalisation?** BM25 scores (0\u201330+) "
            "and dense cosine scores (0\u20131) live on incompatible scales. Min-max is fragile to "
            "outliers; z-score produces distorting negatives. RRF only uses rank position \u2014 "
            "scale-invariant, no tuning needed.\n\n"
            "**Dense backend fallback:** primary is sentence-transformers (BAAI/bge-small-en-v1.5); "
            "when torch isn't available, falls back to TF-IDF + TruncatedSVD so retrieval works on "
            "any machine, no GPU required."
        )
        df_ret = load_csv("d3_retrieval_ablation_summary.csv")
        if df_ret is not None:
            st.dataframe(df_ret[df_ret["System"].isin(["bm25_only", "dense_only", "hybrid_rrf"])], width="stretch")
            st.caption("(Full 5-system ablation including graph-guided is in the D3 tab.)")

    with st.expander("\U0001F578\uFE0F Rana \u2014 Neo4j graph build", expanded=False):
        metric_row([("Graph nodes", "552"), ("Finding nodes", "15")])
        st.markdown(
            "Built the real Neo4j knowledge graph from the corpus metadata: Countries, Policies, "
            "Targets, ClimateRisks, Sectors, Technologies, and page-anchored Finding nodes, "
            "connected by relationships like `HAS_POLICY`, `MITIGATES`, `IMPACTS`, `OCCURS_IN`."
        )
        show_csv_table("d2_graph_counts.csv", "Real node/relationship counts from the built graph.")

    with st.expander("\U0001F4C8 Aaya \u2014 Online retrieval adaptation", expanded=False):
        st.markdown(
            "Extended the D1 topic classifier into D2's retrieval stack \u2014 routing queries to "
            "topic-aware retrieval profiles instead of one fixed BM25/dense weighting for every query."
        )

    with st.expander("\U00002705 Alia \u2014 API + integration tests", expanded=False):
        st.markdown(
            "Built the FastAPI `/search` endpoint wrapping the hybrid retriever, plus integration "
            "tests (`tests/test_search.py`, `tests/test_api.py`) confirming retrieval and the API "
            "contract behave as expected."
        )

# ===================== TAB: D3 =====================
with tab_d3:
    st.header("D3 \u2014 GraphRAG executor, online adaptation, safety, tuning")

    with st.expander("\U0001F4C4 Reem \u2014 Page citation verification", expanded=False):
        st.markdown(
            "Checked every citation in the GraphRAG answers against the real corpus: does the cited "
            "document exist, is the page in range, does the chunk text actually look substantial?"
        )
        metric_row([("Citation rows checked", "198"), ("Valid", "73.2%"), ("Flagged", "26.8%")])
        st.warning(
            "**Honest finding:** some citations failed verification because a page-number field "
            "accidentally held the document's **publication year** instead of a real page number "
            "for a subset of rows \u2014 a real data-quality bug this check caught, not a hidden flaw. "
            "All `missing_document` cases traced back to synthetic graph-node chunk IDs, not real "
            "extracted chunks."
        )
        show_csv_table("page_citation_check.csv")

    with st.expander("\U0001F50D Salma \u2014 Retrieval ablation (5 systems)", expanded=False):
        df = show_csv_table("d3_retrieval_ablation_summary.csv", "5 retrieval systems compared on the same questions.")
        if df is not None and "System" in df.columns:
            chart_cols = [c for c in ["Hit@5", "NDCG@5"] if c in df.columns]
            if chart_cols:
                st.bar_chart(df.set_index("System")[chart_cols])

    with st.expander("\U0001F578\uFE0F Rana \u2014 GraphRAG executor (the core pipeline)", expanded=True):
        st.markdown(
            "**4 stages:** Subgraph Selection (Cypher) \u2192 Graph Expansion (nodes \u2192 chunks) "
            "\u2192 Hybrid Blend (graph + BM25/dense, MMR) \u2192 Answer Generation (2-section prompt "
            "\u2192 LLM \u2192 citations).\n\n"
            "**3 success patterns tested:** country\u2192policy\u2192target, risk\u2192sector\u2192evidence, "
            "technology\u2192mitigates\u2192risk. **3 failure patterns tested on purpose:** too-broad "
            "expansion, missing/unsupported entity, graph genuinely has nothing relevant \u2014 each "
            "one falls back to hybrid retrieval honestly instead of forcing a bad answer."
        )
        show_csv_table("d3_graph_guided_results.csv", "All 6 validated examples \u2014 see the Live Demo tab to run these for real.",
                        cols=["query", "retrieval_type", "fallback_used", "latency_sec", "n_graph_hits"])

    with st.expander("\U0001F4C8 Aaya \u2014 Online GraphRAG adaptation", expanded=False):
        st.markdown(
            "Compared 3 retrieval modes inside the GraphRAG pipeline: **static** (fixed weights), "
            "**topic-gated** (routed by the D1 topic classifier), and **feedback-adaptive** "
            "(weights adjusted from query feedback over the stream)."
        )
        show_csv_table("d3_online_retrieval_comparison.csv",
                        cols=["method", "strict_chunk_recall@5", "document_recall@5", "faithfulness", "mean_latency_ms"])
        st.caption(
            "Honest finding: on this 15-question gold set, the adaptive method matched the static "
            "baseline on quality metrics, while topic-gated/feedback-adaptive cut **mean latency from "
            "~11.4s to ~3.0s** \u2014 the routing made it faster without losing quality."
        )

    with st.expander("\U0001F6E1\uFE0F Alia \u2014 Safety + RAG evaluation", expanded=False):
        st.markdown(
            "**Source pinning** (`src/safety/source_pinning.py`) blocks any answer citing a source "
            "outside the approved corpus. **Citation verifier** (`src/safety/citation_verifier.py`) "
            "checks every cited page actually exists in the supporting chunks."
        )
        show_csv_table("d3_safety_before_after.csv")
        st.markdown("**RAG quality \u2014 faithfulness & relevance on real evaluated answers:**")
        show_csv_table("d3_rag_eval_metrics.csv")

    with st.expander("\U0001F3CB\uFE0F Tuning \u2014 QLoRA fine-tuning (Kaggle GPU)", expanded=False):
        st.markdown(
            "Fine-tuned a small LLM (TinyLlama-1.1B) with **QLoRA** on Kaggle's free GPU, trained on "
            "15 gold question/answer pairs, comparing zero-shot vs. the tuned adapter."
        )
        show_csv_table("d3_or_final_zero_shot_vs_tuned.csv")
        st.caption(
            "Honest finding: citation correctness jumped from 0.27 \u2192 1.0 after tuning, but "
            "latency got worse (\u224810.3s \u2192 \u224818.0s) \u2014 a real, reported tradeoff, not hidden."
        )

# ===================== TAB: LIVE DEMO =====================
with tab_demo:
    st.header("Ask the real system a question")
    st.caption("This runs your actual code \u2014 not a recording. Pick an example with a known validated result, or type your own.")

    if chunks is None:
        st.error("Can't run the live demo without the chunk corpus. See the sidebar error for the fix (usually `git lfs pull`).")
    else:
        examples = [
            ("Energy dataset evidence", "What makes the FeederBW low-voltage grid dataset useful for energy-transition planning research?"),
            ("Crop adaptation evidence", "How can sowing-date adjustment help cereal crops respond to warming-driven phenology changes?"),
            ("Grid resilience evidence", "Why do climate projections create vulnerability concerns for electrical substations and transformer loading practices?"),
            ("Carbon-free ammonia evidence", "How could carbon-free Haber-Bosch ammonia production align with intermittent renewable energy?"),
            ("Green recovery evidence", "How could post-COVID green stimulus choices affect future warming trajectories?"),
            ("Hybrid fallback: ML method", "What does the literature say about gradient boosting methods for wind power forecasting?"),
        ]

        st.markdown("**Pick a validated example:**")
        ex_cols = st.columns(3)
        for i, (label, q) in enumerate(examples):
            if ex_cols[i % 3].button(label, width="stretch"):
                st.session_state["query_input"] = q

        query = st.text_input(
            "Or ask your own climate question",
            key="query_input",
            placeholder="e.g. What renewable energy targets has the UAE committed to?",
        )
        run = st.button("Ask", type="primary")

        # Reference (validated) row, if this exact query was one of the 6 audited examples
        results_df = load_csv("d3_graph_guided_results.csv")
        ref_row = None
        if results_df is not None and query:
            match = results_df[results_df["query"] == query]
            if not match.empty:
                ref_row = match.iloc[0]

        if run and query.strip():
            hybrid = get_hybrid_retriever(chunks)
            executor, exec_err = get_graphrag_executor()

            col_left, col_right = st.columns([3, 2])

            with col_left:
                st.subheader("Live GraphRAG executor trace")
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
                            f"&nbsp;&nbsp;**Latency:** {result.latency_sec:.2f}s (wall: {elapsed:.2f}s)"
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
                            st.markdown("**Citations:** " + "; ".join(result.citation_pages[:6]))

                        if result.answer_quality_notes:
                            st.caption(f"Analysis: {result.answer_quality_notes}")

                if ref_row is not None:
                    with st.expander("\U0001F4CC Expected output (from the validated, audited run)", expanded=False):
                        st.markdown(
                            f"**Retrieval type:** `{ref_row.get('retrieval_type','?')}`  \n"
                            f"**Fallback used:** `{ref_row.get('fallback_used','?')}`  \n"
                            f"**Graph hits:** `{ref_row.get('n_graph_hits','?')}`  \n"
                            f"**Latency (validated run):** `{ref_row.get('latency_sec','?')}s`"
                        )
                        notes = ref_row.get("answer_quality_notes", "")
                        if isinstance(notes, str) and notes:
                            st.caption(notes)
                        st.caption("This reference comes straight from `reports/tables/d3_graph_guided_results.csv` \u2014 useful to compare against if live results look different (e.g. if Neo4j/Gemini aren't connected right now).")

            with col_right:
                st.subheader("Hybrid retrieval (BM25 + dense)")
                st.caption("Always works \u2014 no Neo4j needed.")
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
