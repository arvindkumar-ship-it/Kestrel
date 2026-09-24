import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestJob:
    """Batch anomaly scorer over per-actor feature vectors. Real IsolationForest — not a
    stub — run periodically (Celery beat) over a window of accumulated feature rows."""

    def __init__(self, contamination: float = 0.05) -> None:
        self.contamination = contamination

    def score(self, feature_matrix: list[list[float]]) -> list[float]:
        if len(feature_matrix) < 10:
            return [0.0] * len(feature_matrix)
        x = np.array(feature_matrix)
        model = IsolationForest(contamination=self.contamination, random_state=42)
        model.fit(x)
        raw = model.score_samples(x)  # higher = more normal
        risk = -raw
        lo, hi = risk.min(), risk.max()
        if hi - lo < 1e-9:
            return [0.0] * len(feature_matrix)
        return list((risk - lo) / (hi - lo))
