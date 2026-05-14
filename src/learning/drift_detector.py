"""ADWIN drift detection utilities for D1 online learning.

This module watches the prequential error stream of the topic classifier.
A value of 0 means the prediction was correct and 1 means it was wrong.
ADWIN is then able to detect a statistically significant change in the
recent error rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DriftAlert:
    """Information recorded whenever ADWIN detects a drift alert."""

    index: int
    width: float | None
    error_estimate: float | None


class ADWINDriftDetector:
    """Small wrapper around river.drift.ADWIN.

    Parameters
    ----------
    delta:
        ADWIN confidence parameter. Higher values are more sensitive and may
        detect drift earlier. Lower values are stricter and may reduce false
        positives.

    min_num_instances:
        Number of initial prequential observations ignored by ADWIN so the
        normal model warm-up period is not counted as concept drift.

    Notes
    -----
    We update ADWIN with an error signal, not raw correctness:

    - correct prediction -> 0
    - wrong prediction -> 1

    This makes alerts easier to interpret: a drift warning means the recent
    classification error rate changed significantly.
    """

    def __init__(self, delta: float = 0.01, min_num_instances: int = 250):
        from river import drift

        self.delta = delta
        self.min_num_instances = min_num_instances
        self.detector = drift.ADWIN(delta=delta)
        self.n_seen = 0
        self.alerts: List[DriftAlert] = []

    def update(self, correct: bool, index: Optional[int] = None) -> bool:
        """Update ADWIN and return True if drift is detected."""

        self.n_seen += 1
        stream_index = index if index is not None else self.n_seen
        error_value = 0 if correct else 1

        # Skip early cold-start period.
        # Otherwise ADWIN may treat normal early learning improvement as drift.
        if self.n_seen < self.min_num_instances:
            return False

        self.detector.update(error_value)

        # Newer River versions use drift_detected.
        # Some older versions used change_detected.
        detected = bool(
            getattr(self.detector, "drift_detected", False)
            or getattr(self.detector, "change_detected", False)
        )

        if detected:
            self.alerts.append(
                DriftAlert(
                    index=stream_index,
                    width=self.width,
                    error_estimate=self.error_estimate,
                )
            )

        return detected

    @property
    def error_estimate(self) -> float | None:
        """Current ADWIN mean estimate over the monitored error stream."""

        return getattr(self.detector, "estimation", None)

    @property
    def width(self) -> float | None:
        """Current adaptive window width used by ADWIN."""

        return getattr(self.detector, "width", None)

    def get_alert_indices(self) -> list[int]:
        """Return all detected drift indices."""

        return [alert.index for alert in self.alerts]