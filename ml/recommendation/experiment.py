import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .metrics import summarize

USERS = 120
ITEMS = 60
CATEGORIES = 6
K = 5


def run(seed=42):
    rng = np.random.default_rng(seed)
    categories = np.repeat(np.arange(CATEGORIES), ITEMS // CATEGORIES)
    interactions = np.zeros((USERS, ITEMS), dtype=np.int16)
    held_out = []
    for row in interactions:
        preferred = rng.choice(CATEGORIES, size=2, replace=False)
        weights = np.where(np.isin(categories, preferred), 8.0, 1.0)
        ordered = rng.choice(ITEMS, size=12, replace=False, p=weights / weights.sum())
        row[ordered[:9]] = 1
        held_out.append(set(ordered[9:]))

    popularity = interactions.sum(axis=0) / USERS
    content_similarity = (categories[:, None] == categories[None, :]).astype(float)
    collaborative_similarity = cosine_similarity(interactions.T)
    content_scores = interactions @ content_similarity / 9
    collaborative_scores = interactions @ collaborative_similarity / 9
    scores = {
        "Popularity": np.broadcast_to(popularity, interactions.shape),
        "Content-based": content_scores,
        "Collaborative cosine": collaborative_scores,
        "Hybrid": 0.5 * content_scores + 0.5 * collaborative_scores,
    }
    results = {}
    for name, values in scores.items():
        eligible_scores = np.where(interactions == 1, -np.inf, values)
        ranked = np.argsort(-eligible_scores, kind="stable", axis=1)[:, :K].tolist()
        results[name] = summarize(ranked, held_out, categories.tolist(), K)
    report = {
        "k": K, "users": USERS, "items": ITEMS, "train_events": USERS * 9, "test_events": USERS * 3,
        "split": "First nine synthetic interactions per user for training, final three for evaluation",
        "models": results,
    }
    artifacts = {"content": content_similarity, "collaborative": collaborative_similarity, "popularity": popularity}
    return report, artifacts
