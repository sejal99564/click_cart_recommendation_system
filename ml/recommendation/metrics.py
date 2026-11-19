from math import log2
from statistics import mean


def ranking_metrics(recommended, relevant, k):
    ranked = recommended[:k]
    hits = [int(item in relevant) for item in ranked]
    total = sum(hits)
    precision = total / k
    recall = total / len(relevant) if relevant else 0
    ideal = sum(1 / log2(index + 2) for index in range(min(k, len(relevant))))
    dcg = sum(hit / log2(index + 2) for index, hit in enumerate(hits))
    average_precision = sum(sum(hits[:index + 1]) / (index + 1) for index, hit in enumerate(hits) if hit)
    return {
        "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "ndcg": dcg / ideal if ideal else 0,
        "map": average_precision / min(k, len(relevant)) if relevant else 0,
    }


def summarize(rankings, relevant, item_features, k):
    per_user = [ranking_metrics(ranked, target, k) for ranked, target in zip(rankings, relevant, strict=True)]
    result = {metric: mean(row[metric] for row in per_user) for metric in per_user[0]}
    result["coverage"] = len({item for ranking in rankings for item in ranking[:k]}) / len(item_features)
    result["diversity"] = mean(
        mean(float(item_features[left] != item_features[right])
             for index, left in enumerate(ranking[:k]) for right in ranking[index + 1:k])
        for ranking in rankings
    )
    return {key: round(value, 6) for key, value in result.items()}
