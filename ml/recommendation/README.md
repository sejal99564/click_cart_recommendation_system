# Recommendation experiment

Run `python -m ml.run_experiments` from the project root. The synthetic generator samples twelve distinct products from a 60-item catalog for each of 120 users. User interests are sampled from six product categories. The first nine observations per user train the models and the final three are excluded until evaluation. Previously interacted items are excluded from ranked candidates.

The experiment compares popularity, category similarity, collaborative item cosine, and an equal-weight hybrid. Ranking evaluation reports Precision@5, Recall@5, F1@5, NDCG@5, MAP@5, catalog coverage, and pairwise category diversity. The live dashboard uses real account preferences and aggregated collection signals with a minimum cohort of three; its rankings are independent of the synthetic model artifact.
