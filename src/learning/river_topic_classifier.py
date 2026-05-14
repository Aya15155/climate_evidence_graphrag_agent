"""River online topic classifier for D1.

This file implements Member 4's D1 online learning task only:
- River query-topic classifier
- simulated climate query stream with drift around query 350
- ADWIN drift detection through the helper in drift_detector.py
- prequential evaluation
- rolling accuracy plot saved to reports/figures/prequential_accuracy_plot.png

Run from the project root:
    python -m src.learning.river_topic_classifier

Or run this file directly while developing:
    python src/learning/river_topic_classifier.py
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Iterable, Optional

try:
    from .drift_detector import ADWINDriftDetector
except ImportError:
    from drift_detector import ADWINDriftDetector


CLIMATE_TOPICS = [
    "mitigation",
    "adaptation",
    "climate_science",
    "policy_governance",
    "technology_innovation",
    "uae_cop28",
]


@dataclass
class QueryExample:
    index: int
    query: str
    topic: str
    phase: str


@dataclass
class PrequentialRecord:
    index: int
    query: str
    actual_topic: str
    predicted_topic: str
    correct: bool
    cumulative_accuracy: float
    rolling_accuracy: float
    drift_alert: bool
    phase: str


class RiverTopicClassifier:
    """Online River classifier for climate query topics."""

    def __init__(self):
        from river import compose, feature_extraction, naive_bayes

        self.model = compose.Pipeline(
            feature_extraction.BagOfWords(lowercase=True),
            naive_bayes.MultinomialNB(alpha=1.0),
        )

    def predict(self, query: str) -> Optional[str]:
        return self.model.predict_one(query)

    def predict_proba(self, query: str) -> dict:
        return self.model.predict_proba_one(query)

    def learn(self, query: str, topic: str) -> None:
        if topic not in CLIMATE_TOPICS:
            raise ValueError(f"Unknown topic {topic!r}. Expected one of {CLIMATE_TOPICS}")
        self.model.learn_one(query, topic)


PRE_DRIFT_TEMPLATES: dict[str, list[str]] = {
    "mitigation": [
        "how can renewable energy reduce greenhouse gas emissions",
        "what evidence links carbon pricing to emissions reduction",
        "which documents discuss net zero mitigation pathways",
        "how does energy efficiency support climate mitigation",
        "what mitigation actions reduce fossil fuel dependence",
        "show climate evidence about methane reduction strategies",
    ],
    "adaptation": [
        "how can cities adapt to extreme heat and flooding",
        "what evidence discusses climate resilience for agriculture",
        "which adaptation measures protect coastal communities",
        "how does drought planning reduce climate risk",
        "what adaptation policies help water security",
        "show evidence about disaster risk reduction and resilience",
    ],
    "climate_science": [
        "what does climate science say about sea level rise",
        "which papers explain global temperature anomalies",
        "how do climate models project future warming",
        "what evidence links emissions to radiative forcing",
        "explain the science behind climate feedback loops",
        "show findings about ocean warming and ice melt",
    ],
    "policy_governance": [
        "which climate policies address renewable energy targets",
        "what governance mechanisms support national climate plans",
        "how do NDCs guide climate policy implementation",
        "which regulations support climate accountability",
        "what evidence discusses carbon market governance",
        "show documents about climate finance policy",
    ],
    "technology_innovation": [
        "which AI methods are used in climate forecasting papers",
        "what technologies support carbon capture and storage",
        "how can smart grids improve clean energy integration",
        "which innovations support green hydrogen deployment",
        "show evidence about satellite monitoring for climate risks",
        "what role does machine learning play in climate analysis",
    ],
    "uae_cop28": [
        "what were the major climate outcomes from COP28 in the UAE",
        "which UAE initiatives were discussed in the COP28 documents",
        "how did COP28 address the global stocktake",
        "what evidence mentions the UAE consensus and transition away from fossil fuels",
        "which documents discuss UAE renewable energy commitments",
        "show COP28 evidence about loss and damage finance",
    ],
}


DRIFT_LABEL_MAP: dict[str, str] = {
    "mitigation": "policy_governance",
    "adaptation": "uae_cop28",
    "climate_science": "technology_innovation",
    "policy_governance": "mitigation",
    "technology_innovation": "climate_science",
    "uae_cop28": "adaptation",
}


POST_DRIFT_TEMPLATES: dict[str, list[str]] = {
    "mitigation": [
        "policy aligned emissions cuts and fossil fuel phase down evidence",
        "mitigation route for national carbon budget after global stocktake",
        "renewable target evidence for reducing fossil fuel reliance",
        "sectoral emissions reduction pathway linked to climate policy",
    ],
    "adaptation": [
        "post COP28 resilience planning for heat and water security",
        "adaptation finance evidence for vulnerable communities",
        "loss and damage adaptation support for coastal climate risk",
        "climate resilience planning after extreme weather events",
    ],
    "climate_science": [
        "new climate model evidence for attribution and warming trends",
        "scientific assessment of temperature overshoot and feedbacks",
        "observed sea level rise evidence from climate indicators",
        "climate science basis for extreme event attribution",
    ],
    "policy_governance": [
        "governance evidence for implementing COP28 climate commitments",
        "policy accountability for national climate targets and NDCs",
        "climate finance governance and transparent reporting evidence",
        "carbon market regulation and policy implementation evidence",
    ],
    "technology_innovation": [
        "AI enabled climate monitoring and early warning innovation",
        "green hydrogen innovation for industrial decarbonization",
        "satellite and machine learning tools for climate evidence extraction",
        "carbon capture technology evidence after COP28 transition goals",
    ],
    "uae_cop28": [
        "UAE consensus evidence on energy transition and global stocktake",
        "COP28 UAE renewable energy and climate finance outcomes",
        "Dubai COP28 agreement evidence for transition away from fossil fuels",
        "UAE hosted COP28 documents on loss and damage and adaptation finance",
    ],
}


TOPIC_HINTS: dict[str, list[str]] = {
    "mitigation": ["emissions", "decarbonization", "net zero", "renewables"],
    "adaptation": ["resilience", "flood risk", "heat stress", "water security"],
    "climate_science": ["models", "temperature", "sea level", "attribution"],
    "policy_governance": ["NDC", "regulation", "finance", "accountability"],
    "technology_innovation": ["AI", "satellite", "green hydrogen", "carbon capture"],
    "uae_cop28": ["COP28", "UAE consensus", "global stocktake", "loss and damage"],
}


def _add_variation(query: str, topic: str, rng: random.Random) -> str:
    """Add small wording variation so the stream is not just duplicated text."""

    prefixes = [
        "find evidence on",
        "summarize documents about",
        "what does the dataset say about",
        "which source explains",
        "retrieve climate evidence for",
        "answer using citations about",
    ]
    suffixes = [
        "with source support",
        "from the climate PDFs",
        "for the GraphRAG agent",
        "in the evidence graph",
        "using reliable citations",
        "for the project report",
    ]
    hint = rng.choice(TOPIC_HINTS[topic])

    mode = rng.random()
    if mode < 0.35:
        return f"{rng.choice(prefixes)} {query}"
    if mode < 0.70:
        return f"{query} {rng.choice(suffixes)}"
    return f"{query} focusing on {hint}"


def generate_climate_query_stream(
    n_queries: int = 600,
    drift_at: int = 350,
    seed: int = 42,
    drift_window: int = 90,
) -> list[QueryExample]:
    """Generate a labelled climate query stream with concept drift."""

    if n_queries < 500:
        raise ValueError("D1 requires at least 500 simulated queries.")
    if not 1 < drift_at < n_queries:
        raise ValueError("drift_at must be inside the query stream.")

    rng = random.Random(seed)
    stream: list[QueryExample] = []

    for i in range(1, n_queries + 1):
        if i < drift_at:
            topic = rng.choice(CLIMATE_TOPICS)
            query = rng.choice(PRE_DRIFT_TEMPLATES[topic])
            phase = "stable_pre_drift"

        elif i < drift_at + drift_window:
            original_topic = rng.choice(CLIMATE_TOPICS)
            topic = DRIFT_LABEL_MAP[original_topic]
            query = rng.choice(PRE_DRIFT_TEMPLATES[original_topic])
            phase = "concept_drift"

        else:
            topic = rng.choices(
                CLIMATE_TOPICS,
                weights=[0.12, 0.13, 0.13, 0.22, 0.18, 0.22],
                k=1,
            )[0]
            query = rng.choice(POST_DRIFT_TEMPLATES[topic])
            phase = "stable_post_drift"

        stream.append(
            QueryExample(
                index=i,
                query=_add_variation(query, topic, rng),
                topic=topic,
                phase=phase,
            )
        )

    return stream


def run_prequential_evaluation(
    stream: Iterable[QueryExample],
    rolling_window: int = 50,
    adwin_delta: float = 0.01,
    adwin_min_instances: int = 250,
    reset_on_drift: bool = False,
) -> tuple[list[PrequentialRecord], list[int]]:
    """Evaluate with test-then-train prequential evaluation."""

    classifier = RiverTopicClassifier()
    detector = ADWINDriftDetector(delta=adwin_delta, min_num_instances=adwin_min_instances)
    rolling: Deque[int] = deque(maxlen=rolling_window)

    records: list[PrequentialRecord] = []
    n_correct = 0

    for example in stream:
        prediction = classifier.predict(example.query)
        predicted_topic = prediction if prediction is not None else "__none__"
        correct = predicted_topic == example.topic

        rolling.append(1 if correct else 0)
        n_correct += 1 if correct else 0

        cumulative_accuracy = n_correct / example.index
        rolling_accuracy = sum(rolling) / len(rolling)

        drift_alert = detector.update(correct=correct, index=example.index)

        if drift_alert and reset_on_drift:
            classifier = RiverTopicClassifier()

        classifier.learn(example.query, example.topic)

        records.append(
            PrequentialRecord(
                index=example.index,
                query=example.query,
                actual_topic=example.topic,
                predicted_topic=predicted_topic,
                correct=correct,
                cumulative_accuracy=round(cumulative_accuracy, 4),
                rolling_accuracy=round(rolling_accuracy, 4),
                drift_alert=drift_alert,
                phase=example.phase,
            )
        )

    return records, detector.get_alert_indices()


def save_records_csv(records: list[PrequentialRecord], output_path: str | Path) -> Path:
    """Save prequential predictions and accuracy values for the report."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "query",
                "actual_topic",
                "predicted_topic",
                "correct",
                "cumulative_accuracy",
                "rolling_accuracy",
                "drift_alert",
                "phase",
            ],
        )
        writer.writeheader()
        for row in records:
            writer.writerow(row.__dict__)

    return output_path


def plot_prequential_accuracy(
    records: list[PrequentialRecord],
    output_path: str | Path,
    drift_at: int = 350,
    title: str = "Prequential rolling accuracy with ADWIN drift alerts",
) -> Path:
    """Generate rolling accuracy plot for reports/figures."""

    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    xs = [r.index for r in records]
    rolling_acc = [r.rolling_accuracy for r in records]
    cumulative_acc = [r.cumulative_accuracy for r in records]
    alert_xs = [r.index for r in records if r.drift_alert]
    alert_ys = [r.rolling_accuracy for r in records if r.drift_alert]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(xs, rolling_acc, label="Rolling accuracy")
    ax.plot(xs, cumulative_acc, label="Cumulative accuracy", linestyle="--", alpha=0.75)
    ax.axvline(drift_at, linestyle=":", linewidth=2, label=f"Injected drift at {drift_at}")

    if alert_xs:
        ax.scatter(alert_xs, alert_ys, marker="x", s=80, label="ADWIN alert")
        for x, y in zip(alert_xs, alert_ys):
            ax.annotate(f"ADWIN {x}", (x, y), textcoords="offset points", xytext=(6, 8))

    ax.set_xlabel("Query index")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return output_path


def summarize_run(records: list[PrequentialRecord], drift_alerts: list[int]) -> dict[str, object]:
    """Return key values for the D1 report."""

    final_record = records[-1]
    first_alert = drift_alerts[0] if drift_alerts else None

    pre_drift = [r.correct for r in records if r.phase == "stable_pre_drift"]
    drift = [r.correct for r in records if r.phase == "concept_drift"]
    post_drift = [r.correct for r in records if r.phase == "stable_post_drift"]

    def acc(values: list[bool]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "n_queries": len(records),
        "final_cumulative_accuracy": final_record.cumulative_accuracy,
        "final_rolling_accuracy": final_record.rolling_accuracy,
        "pre_drift_accuracy": acc(pre_drift),
        "drift_window_accuracy": acc(drift),
        "post_drift_accuracy": acc(post_drift),
        "drift_alerts": drift_alerts,
        "first_adwin_alert": first_alert,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run D1 River online learning demo.")
    parser.add_argument("--n-queries", type=int, default=600)
    parser.add_argument("--drift-at", type=int, default=350)
    parser.add_argument("--drift-window", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rolling-window", type=int, default=50)
    parser.add_argument("--adwin-delta", type=float, default=0.01)
    parser.add_argument("--adwin-min-instances", type=int, default=250)
    parser.add_argument("--reset-on-drift", action="store_true")
    parser.add_argument(
        "--plot-path",
        default="reports/figures/prequential_accuracy_plot.png",
    )
    parser.add_argument(
        "--csv-path",
        default="reports/tables/prequential_online_learning_results.csv",
    )

    args = parser.parse_args()

    stream = generate_climate_query_stream(
        n_queries=args.n_queries,
        drift_at=args.drift_at,
        seed=args.seed,
        drift_window=args.drift_window,
    )

    records, drift_alerts = run_prequential_evaluation(
        stream,
        rolling_window=args.rolling_window,
        adwin_delta=args.adwin_delta,
        adwin_min_instances=args.adwin_min_instances,
        reset_on_drift=args.reset_on_drift,
    )

    csv_path = save_records_csv(records, args.csv_path)
    plot_path = plot_prequential_accuracy(records, args.plot_path, drift_at=args.drift_at)
    summary = summarize_run(records, drift_alerts)

    print("D1 River online learning run complete")
    print(f"Saved CSV : {csv_path}")
    print(f"Saved plot: {plot_path}")

    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()