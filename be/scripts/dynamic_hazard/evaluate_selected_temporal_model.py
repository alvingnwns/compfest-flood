from __future__ import annotations

import argparse
import json
from pathlib import Path

from dynamic_hazard.common import (
    DEFAULT_ARTIFACT_DIR,
    MANIFEST_PATH,
    evaluate_probabilities,
    file_sha256,
    load_frozen_model,
    load_split,
    save_json,
)


def evaluate_frozen_test(output_dir: Path = DEFAULT_ARTIFACT_DIR) -> dict:
    selection_path = output_dir / "model_selection.json"
    result_path = output_dir / "test_evaluation.json"
    if result_path.exists():
        raise RuntimeError("Frozen test evaluation already exists; repeated test inspection is prohibited.")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    artifact_path = output_dir / selection["selectedArtifact"]
    if file_sha256(artifact_path) != selection["selectedArtifactSha256"]:
        raise RuntimeError("Selected artifact hash does not match the frozen selection record.")
    if file_sha256(MANIFEST_PATH) != selection["trainingManifestSha256"]:
        raise RuntimeError("Dataset manifest changed after model selection.")
    model = load_frozen_model(artifact_path)
    test = load_split("test", allow_test=True)
    probability = model.predict_proba(test)
    result = {
        "experimentVersion": selection["experimentVersion"],
        "evaluationSplit": "test-2020",
        "testAccessPolicy": "Loaded once after frozen model selection; no post-test tuning is permitted.",
        "selectedModel": selection["selectedModel"]["model"],
        "representation": selection["selectedModel"]["representation"],
        "threshold": model.threshold,
        "artifactSha256": selection["selectedArtifactSha256"],
        "metrics": evaluate_probabilities(test.y, probability, model.threshold),
    }
    save_json(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the frozen temporal-hazard model on test exactly once.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    args = parser.parse_args()
    print(json.dumps(evaluate_frozen_test(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
