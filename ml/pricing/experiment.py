import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

FEATURE_NAMES = ["previous merchant price", "demand index", "inventory", "seasonal index", "simulated competitor price", "unit cost"]
TRAIN_ROWS = 320
TOTAL_ROWS = 400


def run(seed=42):
    rng = np.random.default_rng(seed)
    timeline = np.arange(TOTAL_ROWS)
    season = np.sin(timeline / 18)
    demand = rng.uniform(0.15, 0.95, TOTAL_ROWS)
    inventory = rng.integers(8, 80, TOTAL_ROWS)
    cost = rng.integers(3000, 4500, TOTAL_ROWS)
    competitor = 9100 + 900 * season + rng.normal(0, 700, TOTAL_ROWS)
    previous = competitor + rng.normal(0, 640, TOTAL_ROWS)
    willingness = 7500 + 4600 * demand + 0.29 * competitor + 560 * season + rng.normal(0, 320, TOTAL_ROWS)
    features = np.column_stack((previous, demand, inventory, season, competitor, cost))
    candidates = np.arange(5000, 12001, 250)

    def profits(prices, index):
        predicted_units = np.minimum(inventory[index], np.maximum(0, 55 * (1 - prices / willingness[index])))
        return (prices - cost[index]) * predicted_units

    targets = np.array([candidates[np.argmax(profits(candidates, index))] for index in timeline])
    training, testing = features[:TRAIN_ROWS], features[TRAIN_ROWS:]
    models = {
        "Ridge regression": Ridge(alpha=1),
        "Random forest": RandomForestRegressor(n_estimators=100, min_samples_leaf=4, random_state=seed, n_jobs=1),
    }
    predictions = {"Historical merchant price": testing[:, 0]}
    for name, model in models.items():
        model.fit(training, targets[:TRAIN_ROWS])
        predictions[name] = model.predict(testing)
    observed = targets[TRAIN_ROWS:]
    results = {}
    for name, prices in predictions.items():
        prices = np.clip(prices, candidates[0], candidates[-1])
        mse = mean_squared_error(observed, prices)
        results[name] = {
            "mae": round(mean_absolute_error(observed, prices), 4), "mse": round(mse, 4),
            "rmse": round(mse**0.5, 4), "r2": round(r2_score(observed, prices), 6),
            "mean_simulated_profit": round(float(np.mean([profits(price, index) for index, price in enumerate(prices, TRAIN_ROWS)])), 4),
        }
    report = {
        "features": FEATURE_NAMES, "train_rows": TRAIN_ROWS, "test_rows": TOTAL_ROWS - TRAIN_ROWS,
        "split": "First 320 simulated time steps for training, final 80 for evaluation",
        "models": results,
        "ridge": {
            "intercept": float(models["Ridge regression"].intercept_),
            "coefficients": models["Ridge regression"].coef_.tolist(),
            "minimum": int(candidates[0]), "maximum": int(candidates[-1]),
        },
    }
    return report, models
