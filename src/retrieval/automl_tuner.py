"""D1 AutoML Track A: supervised hybrid kNN retrieval tuning.

This script is intentionally self-contained and uses the real D1 artifacts:

- data/sample/sample_chunks.json
- data/gold/d1_retrieval_eval_set.json

Pipeline
--------
1. Build a BM25 lexical retriever over all chunk texts.
2. Build a TF-IDF matrix and reduce it with TruncatedSVD.
3. Treat the SVD vectors as the dense kNN representation.
4. Tune the D1 search space requested in the brief with Optuna:
   - k
   - metric
   - SVD dimension
   - normalization
   - hybrid BM25 weight
5. Evaluate baseline and winning AutoML config on a held-out test split.
6. Save:
   - configs/run_card_d1.yaml
   - reports/tables/d1_baseline_vs_automl_metrics.csv
   - reports/tables/d1_automl_trials.csv

Run from the project root:
    python src/retrieval/automl_tuner.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import optuna
import yaml
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import normalize as l2_normalize


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
SEARCH_SPACE = {
    "k": [5, 10, 15, 20],
    "metric": ["cosine", "euclidean", "manhattan"],
    "svd_dim": [50, 100, 200, 300],
    "normalization": ["none", "minmax", "zscore"],
    "hybrid_weight": [0.0, 1.0],
}


@dataclass(frozen=True)
class QueryItem:
    question_id: str
    question: str
    relevant_chunk_ids: tuple[str, ...]


@dataclass
class RetrievalCache:
    chunk_ids: list[str]
    chunk_page_keys: dict[str, str]
    queries: list[QueryItem]
    bm25_rankings: dict[int, list[tuple[str, float]]]
    bm25_latencies_ms: dict[int, float]
    dense_rankings: dict[tuple[int, str, int], list[tuple[str, float]]]
    dense_latencies_ms: dict[tuple[int, str, int], float]


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_chunks(path: str | Path) -> tuple[list[str], list[str], dict[str, str]]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    chunk_ids = [row["chunk_id"] for row in rows]
    chunk_page_keys = {
        row["chunk_id"]: f"{row.get('document_id', '')}::page_{row.get('page_start', '')}"
        for row in rows
    }
    texts = []
    for row in rows:
        metadata_text = " ".join(
            str(value)
            for field in [
                "title",
                "topics",
                "countries",
                "regions",
                "sectors",
                "climate_risks",
                "technologies",
                "policies",
                "targets",
                "indicators",
            ]
            for value in (
                row.get(field, [])
                if isinstance(row.get(field, []), list)
                else [row.get(field, "")]
            )
        )
        page_text = f"page {row.get('page_start', '')} page {row.get('page_end', '')}"
        texts.append(
            f"{row['title']} {row.get('document_id', '')} {page_text} {metadata_text} {row['text']}"
        )
    return chunk_ids, texts, chunk_page_keys


def load_queries(path: str | Path) -> list[QueryItem]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        QueryItem(
            question_id=row["question_id"],
            question=row["question"],
            relevant_chunk_ids=tuple(row["relevant_chunk_ids"]),
        )
        for row in rows
    ]


def split_queries(
    queries: list[QueryItem],
    train_fraction: float = 0.70,
    seed: int = 42,
) -> tuple[list[QueryItem], list[QueryItem]]:
    shuffled = list(queries)
    random.Random(seed).shuffle(shuffled)
    split = int(len(shuffled) * train_fraction)
    return shuffled[:split], shuffled[split:]


def recall_at_k(retrieved_ids: list[str], relevant_ids: Iterable[str], k: int = 5) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(retrieved_ids[:k]) & relevant) / len(relevant)


def dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: Iterable[str], k: int = 5) -> float:
    relevant = set(relevant_ids)
    observed = [1 if rid in relevant else 0 for rid in retrieved_ids[:k]]
    ideal = [1] * min(len(relevant), k) + [0] * max(0, k - len(relevant))
    denom = dcg(ideal)
    return dcg(observed) / denom if denom else 0.0


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: Iterable[str]) -> float:
    relevant = set(relevant_ids)
    for idx, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant:
            return 1.0 / idx
    return 0.0


def normalize_scores(scores: np.ndarray, method: str) -> np.ndarray:
    scores = scores.astype(np.float64, copy=False)
    if method == "none":
        return scores
    if method == "minmax":
        lo = float(scores.min())
        hi = float(scores.max())
        return np.zeros_like(scores) if hi == lo else (scores - lo) / (hi - lo)
    if method == "zscore":
        std = float(scores.std())
        return np.zeros_like(scores) if std == 0.0 else (scores - scores.mean()) / std
    raise ValueError(f"Unknown normalization method: {method}")


def build_retrieval_cache(
    chunk_ids: list[str],
    chunk_page_keys: dict[str, str],
    chunk_texts: list[str],
    queries: list[QueryItem],
    max_k: int = 20,
    random_state: int = 42,
) -> RetrievalCache:
    """Precompute real BM25 and dense rankings for all query/config combinations."""

    tokenized_corpus = [tokenize(text) for text in chunk_texts]
    bm25 = BM25Okapi(tokenized_corpus)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        max_features=30000,
        sublinear_tf=True,
    )
    tfidf_docs = vectorizer.fit_transform(chunk_texts)
    tfidf_queries = vectorizer.transform([q.question for q in queries])

    svd = TruncatedSVD(
        n_components=max(SEARCH_SPACE["svd_dim"]),
        random_state=random_state,
        n_iter=7,
    )
    doc_svd = svd.fit_transform(tfidf_docs).astype(np.float32)
    query_svd = svd.transform(tfidf_queries).astype(np.float32)

    bm25_rankings: dict[int, list[tuple[str, float]]] = {}
    bm25_latencies_ms: dict[int, float] = {}

    for query_index, query in enumerate(queries):
        start = time.perf_counter()
        scores = bm25.get_scores(tokenize(query.question))
        top_indices = np.argpartition(scores, -max_k)[-max_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
        bm25_rankings[query_index] = [
            (chunk_ids[int(idx)], float(scores[int(idx)]))
            for idx in top_indices
        ]
        bm25_latencies_ms[query_index] = (time.perf_counter() - start) * 1000

    dense_rankings: dict[tuple[int, str, int], list[tuple[str, float]]] = {}
    dense_latencies_ms: dict[tuple[int, str, int], float] = {}

    for svd_dim in SEARCH_SPACE["svd_dim"]:
        doc_view = doc_svd[:, :svd_dim]
        query_view = query_svd[:, :svd_dim]

        cosine_docs = l2_normalize(doc_view, copy=True)
        cosine_queries = l2_normalize(query_view, copy=True)

        for metric in SEARCH_SPACE["metric"]:
            for query_index in range(len(queries)):
                start = time.perf_counter()

                if metric == "cosine":
                    scores = cosine_docs @ cosine_queries[query_index]
                else:
                    distances = pairwise_distances(
                        doc_view,
                        query_view[query_index : query_index + 1],
                        metric=metric,
                    ).ravel()
                    scores = -distances

                top_indices = np.argpartition(scores, -max_k)[-max_k:]
                top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
                dense_rankings[(svd_dim, metric, query_index)] = [
                    (chunk_ids[int(idx)], float(scores[int(idx)]))
                    for idx in top_indices
                ]
                dense_latencies_ms[(svd_dim, metric, query_index)] = (
                    time.perf_counter() - start
                ) * 1000

    return RetrievalCache(
        chunk_ids=chunk_ids,
        chunk_page_keys=chunk_page_keys,
        queries=queries,
        bm25_rankings=bm25_rankings,
        bm25_latencies_ms=bm25_latencies_ms,
        dense_rankings=dense_rankings,
        dense_latencies_ms=dense_latencies_ms,
    )


def fuse_rankings(
    bm25_ranking: list[tuple[str, float]],
    dense_ranking: list[tuple[str, float]],
    k: int,
    normalization: str,
    hybrid_weight: float,
) -> list[str]:
    """Fuse BM25 and dense scores; hybrid_weight is the BM25 weight."""

    candidate_ids = list(dict.fromkeys(
        [chunk_id for chunk_id, _ in bm25_ranking[:k]]
        + [chunk_id for chunk_id, _ in dense_ranking[:k]]
    ))

    bm25_lookup = dict(bm25_ranking[:k])
    dense_lookup = dict(dense_ranking[:k])

    bm25_scores = np.array([bm25_lookup.get(cid, 0.0) for cid in candidate_ids], dtype=float)
    dense_scores = np.array([dense_lookup.get(cid, 0.0) for cid in candidate_ids], dtype=float)

    norm_bm25 = normalize_scores(bm25_scores, normalization)
    norm_dense = normalize_scores(dense_scores, normalization)

    fused = hybrid_weight * norm_bm25 + (1.0 - hybrid_weight) * norm_dense
    ranked = sorted(zip(candidate_ids, fused), key=lambda item: item[1], reverse=True)
    return [chunk_id for chunk_id, _ in ranked]


def evaluate_config(
    cache: RetrievalCache,
    query_indices: list[int],
    params: dict[str, object],
) -> dict[str, float]:
    recall_scores: list[float] = []
    ndcg_scores: list[float] = []
    rr_scores: list[float] = []
    latencies: list[float] = []

    k = int(params["k"])
    metric = str(params["metric"])
    svd_dim = int(params["svd_dim"])
    normalization = str(params["normalization"])
    hybrid_weight = float(params["hybrid_weight"])

    for query_index in query_indices:
        query = cache.queries[query_index]
        start = time.perf_counter()
        fused_ids = fuse_rankings(
            cache.bm25_rankings[query_index],
            cache.dense_rankings[(svd_dim, metric, query_index)],
            k=k,
            normalization=normalization,
            hybrid_weight=hybrid_weight,
        )
        fusion_latency_ms = (time.perf_counter() - start) * 1000

        fused_page_ids = list(dict.fromkeys(cache.chunk_page_keys[cid] for cid in fused_ids))
        relevant_page_ids = list(
            dict.fromkeys(cache.chunk_page_keys[cid] for cid in query.relevant_chunk_ids)
        )
        recall_scores.append(recall_at_k(fused_page_ids, relevant_page_ids, k=5))
        ndcg_scores.append(ndcg_at_k(fused_page_ids, relevant_page_ids, k=5))
        rr_scores.append(reciprocal_rank(fused_page_ids, relevant_page_ids))
        latencies.append(
            cache.bm25_latencies_ms[query_index]
            + cache.dense_latencies_ms[(svd_dim, metric, query_index)]
            + fusion_latency_ms
        )

    return {
        "recall_at_5": float(np.mean(recall_scores)),
        "ndcg_at_5": float(np.mean(ndcg_scores)),
        "mrr": float(np.mean(rr_scores)),
        "p95_latency_ms": float(np.percentile(latencies, 95)),
    }


def objective_score(metrics: dict[str, float]) -> float:
    """Balance ranking quality, coverage, and latency for tuning."""

    return (
        metrics["ndcg_at_5"]
        + 0.25 * metrics["recall_at_5"]
        - 0.0005 * metrics["p95_latency_ms"]
    )


def run_optuna_search(
    cache: RetrievalCache,
    train_indices: list[int],
    n_trials: int,
    seed: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    trial_rows: list[dict[str, object]] = []

    def objective(trial: optuna.Trial) -> float:
        params = {
            "k": trial.suggest_categorical("k", SEARCH_SPACE["k"]),
            "metric": trial.suggest_categorical("metric", SEARCH_SPACE["metric"]),
            "svd_dim": trial.suggest_categorical("svd_dim", SEARCH_SPACE["svd_dim"]),
            "normalization": trial.suggest_categorical(
                "normalization", SEARCH_SPACE["normalization"]
            ),
            "hybrid_weight": trial.suggest_float("hybrid_weight", 0.0, 1.0),
        }
        metrics = evaluate_config(cache, train_indices, params)
        score = objective_score(metrics)
        trial_rows.append(
            {
                "trial_number": trial.number,
                **params,
                **metrics,
                "objective": score,
            }
        )
        return score

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials)
    return study.best_params, trial_rows


def write_metrics_table(
    path: str | Path,
    baseline_metrics: dict[str, float],
    tuned_metrics: dict[str, float],
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["system", "recall_at_5", "ndcg_at_5", "mrr", "p95_latency_ms"],
        )
        writer.writeheader()
        writer.writerow({"system": "baseline", **baseline_metrics})
        writer.writerow({"system": "automl_tuned", **tuned_metrics})


def write_trials_table(path: str | Path, trial_rows: list[dict[str, object]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not trial_rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(trial_rows[0].keys()))
        writer.writeheader()
        writer.writerows(trial_rows)


def write_run_card(
    path: str | Path,
    *,
    data_summary: dict[str, object],
    split_summary: dict[str, object],
    baseline_params: dict[str, object],
    baseline_metrics: dict[str, float],
    winning_params: dict[str, object],
    winning_metrics: dict[str, float],
    n_trials: int,
    seed: int,
) -> None:
    run_card = {
        "deliverable": "D1",
        "track": "A_supervised_auto_tuned_knn_retriever",
        "search_engine": "optuna_tpe",
        "seed": seed,
        "data": data_summary,
        "split": split_summary,
        "search_space": {
            "k": SEARCH_SPACE["k"],
            "metric": SEARCH_SPACE["metric"],
            "svd_dim": SEARCH_SPACE["svd_dim"],
            "normalization": SEARCH_SPACE["normalization"],
            "hybrid_weight": "float[0.0, 1.0] (BM25 lexical weight)",
        },
        "objective": "NDCG@5 + 0.25*Recall@5 - 0.0005*p95_latency_ms",
        "n_trials": n_trials,
        "baseline": {
            "config": baseline_params,
            "metrics_test": baseline_metrics,
        },
        "winning_config": winning_params,
        "metrics_test": winning_metrics,
        "notes": [
            "Evaluation uses page-level evidence units derived from data/gold/d1_retrieval_eval_set.json.",
            "All current gold items are auto-generated and marked needs_manual_review=true.",
            "hybrid_weight is the BM25 lexical contribution; dense weight is 1 - hybrid_weight.",
        ],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(run_card, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the repaired D1 AutoML experiment.")
    parser.add_argument("--chunks-path", default="data/sample/sample_chunks.json")
    parser.add_argument("--gold-path", default="data/gold/d1_retrieval_eval_set.json")
    parser.add_argument("--run-card-path", default="configs/run_card_d1.yaml")
    parser.add_argument(
        "--metrics-path",
        default="reports/tables/d1_baseline_vs_automl_metrics.csv",
    )
    parser.add_argument(
        "--trials-path",
        default="reports/tables/d1_automl_trials.csv",
    )
    parser.add_argument("--n-trials", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    chunk_ids, chunk_texts, chunk_page_keys = load_chunks(args.chunks_path)
    queries = load_queries(args.gold_path)
    train_queries, test_queries = split_queries(queries, seed=args.seed)

    query_to_index = {query.question_id: idx for idx, query in enumerate(queries)}
    train_indices = [query_to_index[q.question_id] for q in train_queries]
    test_indices = [query_to_index[q.question_id] for q in test_queries]

    print("Building real D1 retrieval cache...")
    cache = build_retrieval_cache(
        chunk_ids,
        chunk_page_keys,
        chunk_texts,
        queries,
        random_state=args.seed,
    )

    baseline_params = {
        "k": 10,
        "metric": "cosine",
        "svd_dim": 100,
        "normalization": "minmax",
        "hybrid_weight": 0.50,
    }

    print("Evaluating baseline...")
    baseline_metrics = evaluate_config(cache, test_indices, baseline_params)

    print("Running Optuna search...")
    best_params, trial_rows = run_optuna_search(
        cache=cache,
        train_indices=train_indices,
        n_trials=args.n_trials,
        seed=args.seed,
    )

    print("Evaluating winning AutoML configuration...")
    winning_metrics = evaluate_config(cache, test_indices, best_params)

    write_metrics_table(args.metrics_path, baseline_metrics, winning_metrics)
    write_trials_table(args.trials_path, trial_rows)
    write_run_card(
        args.run_card_path,
        data_summary={
            "chunks_path": args.chunks_path,
            "gold_path": args.gold_path,
            "n_chunks": len(chunk_ids),
            "n_queries": len(queries),
            "evaluation_unit": "page",
        },
        split_summary={
            "method": "random_holdout",
            "train_fraction": 0.70,
            "train_queries": len(train_queries),
            "test_queries": len(test_queries),
        },
        baseline_params=baseline_params,
        baseline_metrics=baseline_metrics,
        winning_params=best_params,
        winning_metrics=winning_metrics,
        n_trials=args.n_trials,
        seed=args.seed,
    )

    print("\nBaseline test metrics")
    print(baseline_metrics)
    print("\nWinning config")
    print(best_params)
    print("\nWinning test metrics")
    print(winning_metrics)
    print(f"\nSaved run card: {args.run_card_path}")
    print(f"Saved metrics : {args.metrics_path}")
    print(f"Saved trials  : {args.trials_path}")


if __name__ == "__main__":
    main()
