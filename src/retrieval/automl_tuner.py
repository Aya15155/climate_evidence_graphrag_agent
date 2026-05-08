# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------
def objective(trial, evaluate_fn):
    """Optuna objective for Salma's D1 AutoML component."""
    params = {
        "k": trial.suggest_int("k", 3, 20),
        "svd_dim": trial.suggest_categorical("svd_dim", [50, 100, 200, 300]),
        "hybrid_weight": trial.suggest_float("hybrid_weight", 0.0, 1.0),
        "normalization": trial.suggest_categorical("normalization", ["none", "minmax", "l2"]),
    }
    metrics = evaluate_fn(params)
    # Reward NDCG and penalize high latency.
    return metrics["ndcg_at_5"] - 0.001 * metrics.get("p95_latency_ms", 0)


def run_optuna(evaluate_fn, n_trials: int = 60):
    import optuna
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, evaluate_fn), n_trials=n_trials)
    return study.best_params, study.best_value
