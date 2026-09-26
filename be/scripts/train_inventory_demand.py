from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

NUMERIC = [
    "demand_cups_t",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7",
    "rolling_std_14",
]
FEATURES = ["product_id", *NUMERIC]
TARGETS = ["target_d1", "target_d2", "target_d3"]


def train(source: Path, output: Path) -> dict:
    frame = pd.read_csv(source)
    missing = set(["date", "split", *FEATURES, *TARGETS]) - set(frame)
    if missing:
        raise ValueError(f"Missing dataset columns: {sorted(missing)}")
    if frame.duplicated(["date", "product_id"]).any():
        raise ValueError("Duplicate date/product_id")
    if not {"train", "validation", "test"}.issubset(set(frame["split"])):
        raise ValueError("Temporal train/validation/test splits required")
    frame["date"] = pd.to_datetime(frame["date"])
    splits = {name: frame.loc[frame["split"] == name].copy() for name in ("train", "validation", "test")}
    if not (
        splits["train"]["date"].max() < splits["validation"]["date"].min()
        and splits["validation"]["date"].max() < splits["test"]["date"].min()
    ):
        raise ValueError("Splits are not temporally ordered")
    output.mkdir(parents=True, exist_ok=True)
    metrics: dict = {}
    for horizon, target in enumerate(TARGETS, start=1):
        preprocess = ColumnTransformer(
            [
                ("product", OneHotEncoder(handle_unknown="ignore"), ["product_id"]),
                ("numeric", SimpleImputer(strategy="median", add_indicator=False), NUMERIC),
            ]
        )
        model = Pipeline(
            [
                ("preprocess", preprocess),
                (
                    "regressor",
                    XGBRegressor(
                        n_estimators=160,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        objective="reg:squarederror",
                        n_jobs=2,
                        random_state=42,
                    ),
                ),
            ]
        )
        model.fit(splits["train"][FEATURES], splits["train"][target])
        joblib.dump(model, output / f"d{horizon}.joblib")
        metrics[f"d{horizon}"] = {}
        for split_name in ("validation", "test"):
            subset = splits[split_name]
            actual = subset[target].to_numpy()
            prediction = np.maximum(0, model.predict(subset[FEATURES]))
            # Known-at-t persistence baseline, identical on every horizon.
            baseline = subset["demand_cups_t"].to_numpy()
            metrics[f"d{horizon}"][split_name] = {
                "xgboostMae": round(float(mean_absolute_error(actual, prediction)), 4),
                "persistenceMae": round(float(mean_absolute_error(actual, baseline)), 4),
                "rows": len(subset),
            }
    training_profile = splits["train"].groupby("product_id")["demand_cups_t"].mean()
    demo_history = (
        frame.sort_values("date")
        .groupby("product_id", group_keys=False)
        .tail(7)[["product_id", "date", "demand_cups_t"]]
    )
    manifest = {
        "version": "juice-xgb-direct-v1",
        "trainedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "datasetPath": source.as_posix(),
        "datasetSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "generatorVersions": sorted(frame["generator_version"].dropna().astype(str).unique().tolist()),
        "dataCutoff": splits["train"]["date"].max().strftime("%Y-%m-%d"),
        "features": FEATURES,
        "targets": TARGETS,
        "splitRows": {name: len(value) for name, value in splits.items()},
        "splitDates": {
            name: {"min": value["date"].min().strftime("%Y-%m-%d"), "max": value["date"].max().strftime("%Y-%m-%d")}
            for name, value in splits.items()
        },
        "excludedSplits": sorted(set(frame["split"].astype(str)) - {"train", "validation", "test"}),
        "metrics": metrics,
        "syntheticData": bool(frame.get("is_synthetic", pd.Series([True])).astype(str).str.lower().eq("true").all()),
        "fallbackProfile": {key: round(float(value), 4) for key, value in training_profile.items()},
        "demoHistory": [
            {"productId": row.product_id, "date": row.date.strftime("%Y-%m-%d"), "demand": int(row.demand_cups_t)}
            for row in demo_history.itertuples(index=False)
        ],
        "libraries": {"scikitLearn": sklearn.__version__, "xgboost": xgboost.__version__},
        "notes": (
            "Each direct-horizon pipeline fits preprocessing only on train. "
            "Targets and metadata are excluded from features. "
            "Fallback profile uses train demand only."
        ),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "feature_contract.json").write_text(
        json.dumps(
            {"features": FEATURES, "targets": TARGETS, "rollingIncludesDayT": True, "lag1Means": "t-1"},
            indent=2,
        ),
        encoding="utf-8",
    )
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts" / "inventory")
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output), indent=2))
