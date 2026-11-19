import json
from math import log2
from pathlib import Path

import pytest

from ml.pricing.experiment import run as pricing
from ml.recommendation.experiment import run as recommendation
from ml.recommendation.metrics import ranking_metrics


def test_ranking_metrics_for_known_top_three():
    metrics = ranking_metrics([4, 2, 5], {2, 4, 9}, 3)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(2 / 3)
    assert metrics["map"] == pytest.approx(2 / 3)
    assert metrics["ndcg"] == pytest.approx((1 + 1 / log2(3)) / (1.5 + 1 / log2(3)))


def test_committed_report_reproduces_from_seed():
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "frontend/public/experiment-results.json").read_text(encoding="utf-8"))
    recommend_results, _ = recommendation(report["seed"])
    pricing_results, _ = pricing(report["seed"])
    ridge = pricing_results.pop("ridge")
    published_ridge = report["pricing"].pop("ridge")
    assert ridge["intercept"] == pytest.approx(published_ridge["intercept"])
    assert ridge["coefficients"] == pytest.approx(published_ridge["coefficients"])
    assert recommend_results == report["recommendation"]
    assert pricing_results == report["pricing"]

def test_runs_preserve_previous_reports_and_model_artifacts(tmp_path, monkeypatch):
    import sys

    from ml.run_experiments import main

    report_path = tmp_path / "public" / "experiment-results.json"
    artifacts_path = tmp_path / "models"
    for seed in (42, 43):
        monkeypatch.setattr(sys, "argv", ["run_experiments", "--output", str(report_path),
                                          "--artifacts", str(artifacts_path), "--seed", str(seed)])
        main()
    reports = [json.loads(path.read_text(encoding="utf-8"))
               for path in report_path.with_name("experiment-runs").glob("*.json")]
    assert {report["seed"] for report in reports} == {42, 43}
    assert json.loads(report_path.read_text(encoding="utf-8"))["seed"] == 43
    for report in reports:
        run = artifacts_path / report["run_id"]
        assert (run / "pricing-v1.joblib").is_file()
        assert (run / "recommendation-v1.npz").is_file()
