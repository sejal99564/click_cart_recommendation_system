import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import joblib
import numpy as np
import sklearn

from .pricing.experiment import run as price_experiment
from .recommendation.experiment import run as recommend_experiment


def write_report(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Run reproducible synthetic Shopwise AI experiments")
    parser.add_argument("--output", type=Path, default=Path("frontend/public/experiment-results.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("models/artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    seed = args.seed
    if not 0 <= seed <= 2**32 - 1:
        parser.error("--seed must be between 0 and 4294967295")
    recommendation, similarity_models = recommend_experiment(seed)
    pricing, price_models = price_experiment(seed)
    completed = datetime.now(timezone.utc)
    run_id = completed.strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex
    artifacts = args.artifacts / run_id
    artifacts.mkdir(parents=True)
    np.savez_compressed(artifacts / "recommendation-v1.npz", **similarity_models)
    joblib.dump(price_models, artifacts / "pricing-v1.joblib")
    report = {
        "version": "synthetic-v1", "source": "Synthetic Shopwise AI experiments", "seed": seed,
        "run_id": run_id, "completed_at": completed.isoformat(),
        "numpy": np.__version__, "scikit_learn": sklearn.__version__,
        "recommendation": recommendation, "pricing": pricing,
    }
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    archive = args.output.parent / "experiment-runs" / f"{run_id}.json"
    write_report(archive, content)
    write_report(args.output, content)
    print(f"Saved metrics to {args.output}, archived run at {archive}, and saved models to {artifacts}")


if __name__ == "__main__":
    main()
