# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------

import time
import yaml
import numpy as np
import optuna


# ------------------------------------------------------------
# Fake climate retrieval examples for D1 prototype
# Replace later with:
# - BM25 retrieval
# - Qdrant dense retrieval
# - Neo4j graph retrieval
# ------------------------------------------------------------

gold_queries = [
    {
        "query": "Why is the UAE investing heavily in green hydrogen as part of its Net Zero 2050 strategy?",
        "relevant_docs": ["doc_1"],
    },

    {
        "query": "What evidence do IPCC reports provide about the impact of sea level rise on Gulf coastal cities?",
        "relevant_docs": ["doc_2"],
    },

    {
        "query": "How do COP28 documents describe the role of carbon capture in reducing industrial emissions?",
        "relevant_docs": ["doc_3"],
    },
]


# ------------------------------------------------------------
# Fake retrieval outputs
# ------------------------------------------------------------

def fake_retrieval(query, params):

    time.sleep(0.01)

    hybrid_weight = params["hybrid_weight"]

    if hybrid_weight > 0.6:

        return [
            "doc_1",
            "doc_2",
            "doc_3",
            "doc_4",
        ]

    return [
        "doc_3",
        "doc_1",
        "doc_5",
        "doc_2",
    ]


# ------------------------------------------------------------
# Retrieval metrics
# ------------------------------------------------------------

def recall_at_k(
    retrieved_ids,
    relevant_ids,
    k=5
):

    if not relevant_ids:
        return 0.0

    return len(
        set(retrieved_ids[:k])
        & set(relevant_ids)
    ) / len(set(relevant_ids))


def dcg(relevances):

    import math

    return sum(
        rel / math.log2(i + 2)
        for i, rel in enumerate(relevances)
    )


def ndcg_at_k(
    retrieved_ids,
    relevant_ids,
    k=5
):

    rels = [
        1 if rid in set(relevant_ids)
        else 0
        for rid in retrieved_ids[:k]
    ]

    ideal = sorted(
        rels,
        reverse=True
    )

    denom = dcg(ideal)

    return (
        dcg(rels) / denom
        if denom else 0.0
    )


def mean_reciprocal_rank(all_results):

    rr_scores = []

    for (
        retrieved_docs,
        relevant_docs
    ) in all_results:

        rank = 0

        for idx, doc_id in enumerate(
            retrieved_docs
        ):

            if doc_id in relevant_docs:

                rank = idx + 1
                break

        rr_scores.append(
            1 / rank if rank > 0 else 0
        )

    return float(
        np.mean(rr_scores)
    )


# ------------------------------------------------------------
# Evaluation pipeline
# ------------------------------------------------------------

def evaluate_fn(params):

    recall_scores = []
    ndcg_scores = []

    latencies = []

    all_rr = []

    for item in gold_queries:

        start = time.time()

        retrieved = fake_retrieval(
            item["query"],
            params
        )

        latency = (
            time.time() - start
        ) * 1000

        latencies.append(latency)

        relevant = item["relevant_docs"]

        recall_scores.append(
            recall_at_k(
                retrieved,
                relevant,
                k=5
            )
        )

        ndcg_scores.append(
            ndcg_at_k(
                retrieved,
                relevant,
                k=5
            )
        )

        all_rr.append(
            (retrieved, relevant)
        )

    return {
        "recall_at_5": float(
            np.mean(recall_scores)
        ),

        "ndcg_at_5": float(
            np.mean(ndcg_scores)
        ),

        "mrr": float(
            mean_reciprocal_rank(all_rr)
        ),

        "p95_latency_ms": float(
            np.percentile(latencies, 95)
        ),
    }


# ------------------------------------------------------------
# Optuna objective
# ------------------------------------------------------------

def objective(
    trial,
    evaluate_fn
):
    """
    Optuna objective for Salma's
    D1 AutoML component.
    """

    params = {

        "k": trial.suggest_int(
            "k",
            3,
            20
        ),

        "svd_dim":
        trial.suggest_categorical(
            "svd_dim",
            [50, 100, 200, 300]
        ),

        "hybrid_weight":
        trial.suggest_float(
            "hybrid_weight",
            0.0,
            1.0
        ),

        "normalization":
        trial.suggest_categorical(
            "normalization",
            [
                "none",
                "minmax",
                "l2"
            ]
        ),
    }

    metrics = evaluate_fn(params)

    # Reward NDCG
    # Penalize latency

    return (
        metrics["ndcg_at_5"]
        - 0.001
        * metrics.get(
            "p95_latency_ms",
            0
        )
    )


# ------------------------------------------------------------
# Run Optuna
# ------------------------------------------------------------

def run_optuna(
    evaluate_fn,
    n_trials: int = 20
):

    study = optuna.create_study(
        direction="maximize"
    )

    study.optimize(
        lambda trial:
        objective(
            trial,
            evaluate_fn
        ),
        n_trials=n_trials
    )

    return (
        study.best_params,
        study.best_value
    )


# ------------------------------------------------------------
# Execute D1 experiment
# ------------------------------------------------------------

if __name__ == "__main__":

    best_params, best_score = run_optuna(
        evaluate_fn
    )

    final_metrics = evaluate_fn(
        best_params
    )

    print("\nBest Parameters:")
    print(best_params)

    print("\nFinal Metrics:")
    print(final_metrics)

    run_card = {
        "retrieval": best_params,
        "metrics": final_metrics,
    }

    with open(
        "configs/run_card_d1.yaml",
        "w"
    ) as f:

        yaml.dump(
            run_card,
            f
        )

    print(
        "\nSaved best config "
        "to run_card_d1.yaml"
    )