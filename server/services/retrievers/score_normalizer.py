from typing import List


class ScoreNormalizer:
    """
    Reusable per-query Min-Max score normalization utility.
    """

    @staticmethod
    def min_max_normalize(scores: List[float]) -> List[float]:
        """
        Performs per-query Min-Max normalization over a list of scores.
        normalized = (score - min_score) / (max_score - min_score)

        Edge cases:
        - empty list -> []
        - single element > 0 -> [1.0]
        - single element <= 0 -> [0.0]
        - max_score == min_score > 0 -> [1.0, ...]
        - max_score == min_score <= 0 -> [0.0, ...]
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            val = 1.0 if max_score > 0.0 else 0.0
            return [val for _ in scores]

        denom = max_score - min_score
        return [round((s - min_score) / denom, 4) for s in scores]

    @staticmethod
    def normalize_single(score: float, min_score: float, max_score: float) -> float:
        """
        Normalizes a single score given the min and max scores of its candidate pool.
        """
        if max_score == min_score:
            return 1.0 if max_score > 0.0 else 0.0
        return round(max(0.0, min(1.0, (score - min_score) / (max_score - min_score))), 4)
