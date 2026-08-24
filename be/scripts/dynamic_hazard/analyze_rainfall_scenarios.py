from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import kruskal, spearmanr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from dynamic_hazard.common import (
    DEFAULT_ARTIFACT_DIR,
    SEED,
    TemporalSplit,
    file_sha256,
    load_frozen_model,
    load_selection_splits,
    save_json,
)

PHASE2_DIR = DEFAULT_ARTIFACT_DIR
DEFAULT_OUTPUT_DIR = PHASE2_DIR.parent / "phase3a"
STATION_COUNT = 3
SCORE_SEMANTICS = "uncalibrated relative temporal hazard score"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _linear_slope(values: np.ndarray) -> np.ndarray:
    time = np.arange(values.shape[1], dtype=np.float64)
    centered = time - time.mean()
    return np.sum((values - values.mean(axis=1, keepdims=True)) * centered[None, :], axis=1) / np.sum(centered**2)


def derive_pattern_features(split: TemporalSplit) -> tuple[np.ndarray, list[str]]:
    station = split.X[:, :, :STATION_COUNT]
    names: list[str] = []
    columns: list[np.ndarray] = []
    channel_names = [str(value) for value in split.stations[:STATION_COUNT]]
    operations = {
        "mean30": lambda value: value.mean(axis=1),
        "max30": lambda value: value.max(axis=1),
        "min30": lambda value: value.min(axis=1),
        "std30": lambda value: value.std(axis=1),
        "recent5Mean": lambda value: value[:, -5:].mean(axis=1),
        "recent10Mean": lambda value: value[:, -10:].mean(axis=1),
        "first10Mean": lambda value: value[:, :10].mean(axis=1),
        "last10Mean": lambda value: value[:, -10:].mean(axis=1),
        "positiveFraction": lambda value: (value > 0).mean(axis=1),
        "negativeFraction": lambda value: (value < 0).mean(axis=1),
        "linearSlope": _linear_slope,
    }
    for channel_index, channel_name in enumerate(channel_names):
        values = station[:, :, channel_index]
        for operation_name, operation in operations.items():
            names.append(f"{channel_name}:{operation_name}")
            columns.append(operation(values))
    per_step_mean = station.mean(axis=2)
    per_step_station_std = station.std(axis=2)
    names.extend(
        [
            "crossStation:overallMean",
            "crossStation:recent5Mean",
            "crossStation:recent10Mean",
            "crossStation:meanDisagreement",
            "crossStation:maxDisagreement",
        ]
    )
    columns.extend(
        [
            per_step_mean.mean(axis=1),
            per_step_mean[:, -5:].mean(axis=1),
            per_step_mean[:, -10:].mean(axis=1),
            per_step_station_std.mean(axis=1),
            per_step_station_std.max(axis=1),
        ]
    )
    return np.column_stack(columns).astype(np.float64), names


def _score_summary(scores: np.ndarray, targets: np.ndarray) -> dict[str, Any]:
    q1, median, q3 = np.quantile(scores, [0.25, 0.5, 0.75])
    return {
        "sampleCount": int(len(scores)),
        "hazardScoreMinimum": float(np.min(scores)),
        "hazardScoreQ1": float(q1),
        "hazardScoreMedian": float(median),
        "hazardScoreQ3": float(q3),
        "hazardScoreIqr": float(q3 - q1),
        "hazardScoreMaximum": float(np.max(scores)),
        "targetRate": float(np.mean(targets)),
    }


def _separation(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    groups = [scores[labels == label] for label in sorted(np.unique(labels))]
    statistic, p_value = kruskal(*groups)
    overall = scores.mean()
    between = sum(len(group) * (group.mean() - overall) ** 2 for group in groups)
    total = float(np.sum((scores - overall) ** 2))
    medians = [float(np.median(group)) for group in groups]
    return {
        "kruskalStatistic": float(statistic),
        "kruskalPValue": float(p_value),
        "betweenGroupVarianceFraction": float(between / total) if total else 0.0,
        "medianRange": float(max(medians) - min(medians)),
    }


def _nearest_member(values: np.ndarray, indices: np.ndarray, center: np.ndarray) -> int:
    distances = np.linalg.norm(values[indices] - center, axis=1)
    return int(indices[int(np.argmin(distances))])


def _representative(
    split: TemporalSplit,
    index: int,
    pattern_values: np.ndarray,
    pattern_names: list[str],
    hazard_scores: np.ndarray,
    membership: str,
) -> dict[str, Any]:
    return {
        "sourceSplit": "train",
        "sourceSampleIndex": index,
        "referenceDate": str(split.dates[index]),
        "membership": membership,
        "temporalHazardScore": float(hazard_scores[index]),
        "scoreSemantics": SCORE_SEMANTICS,
        "descriptiveFeatureSummary": {
            name: float(value) for name, value in zip(pattern_names, pattern_values[index], strict=True)
        },
    }


def _fit_intensity_axis(train_features: np.ndarray, feature_names: list[str]) -> dict[str, Any]:
    core_suffixes = ("mean30", "max30", "std30", "recent5Mean", "recent10Mean", "positiveFraction")
    core_indices = [
        index
        for index, name in enumerate(feature_names)
        if name.startswith("crossStation:") or name.endswith(core_suffixes)
    ]
    scaler = StandardScaler().fit(train_features[:, core_indices])
    scaled = scaler.transform(train_features[:, core_indices])
    pca = PCA(n_components=1, random_state=SEED).fit(scaled)
    score = pca.transform(scaled)[:, 0]
    aggregate_mean_index = feature_names.index("crossStation:overallMean")
    if np.corrcoef(score, train_features[:, aggregate_mean_index])[0, 1] < 0:
        pca.components_ *= -1
        score *= -1
    return {
        "indices": core_indices,
        "featureNames": [feature_names[index] for index in core_indices],
        "scaler": scaler,
        "pca": pca,
        "trainScore": score,
    }


def _apply_intensity_axis(features: np.ndarray, axis: dict[str, Any]) -> np.ndarray:
    scaled = axis["scaler"].transform(features[:, axis["indices"]])
    return axis["pca"].transform(scaled)[:, 0]


def _quantile_groups(train_score: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    boundaries = np.quantile(train_score, [0.25, 0.5, 0.75])
    return np.digitize(values, boundaries, right=True), boundaries


def _group_report(
    labels: np.ndarray,
    scores: np.ndarray,
    targets: np.ndarray,
    prefix: str,
) -> list[dict[str, Any]]:
    return [
        {"id": f"{prefix}{label + 1}", **_score_summary(scores[labels == label], targets[labels == label])}
        for label in sorted(np.unique(labels))
    ]


def _monotonic_report(groups: list[dict[str, Any]]) -> dict[str, Any]:
    medians = [group["hazardScoreMedian"] for group in groups]
    target_rates = [group["targetRate"] for group in groups]
    indices = np.arange(len(groups))
    return {
        "hazardMedianSpearman": float(spearmanr(indices, medians).statistic),
        "targetRateSpearman": float(spearmanr(indices, target_rates).statistic),
        "hazardMediansStrictlyIncreasing": all(left < right for left, right in zip(medians, medians[1:], strict=False)),
        "targetRatesNondecreasing": all(
            left <= right for left, right in zip(target_rates, target_rates[1:], strict=False)
        ),
    }


def _cluster_candidates(train_scaled: np.ndarray) -> tuple[list[dict[str, Any]], KMeans, np.ndarray]:
    candidates = []
    fitted: dict[int, tuple[KMeans, np.ndarray]] = {}
    for clusters in range(2, 6):
        reference = KMeans(n_clusters=clusters, random_state=SEED, n_init=20).fit(train_scaled)
        labels = reference.labels_
        stability = []
        for seed in range(SEED + 1, SEED + 6):
            alternate = KMeans(n_clusters=clusters, random_state=seed, n_init=1).fit_predict(train_scaled)
            stability.append(adjusted_rand_score(labels, alternate))
        sizes = np.bincount(labels, minlength=clusters)
        row = {
            "k": clusters,
            "silhouette": float(silhouette_score(train_scaled, labels)),
            "minimumClusterSize": int(sizes.min()),
            "clusterSizes": sizes.tolist(),
            "meanAdjustedRandStability": float(np.mean(stability)),
            "minimumAdjustedRandStability": float(np.min(stability)),
        }
        candidates.append(row)
        fitted[clusters] = (reference, labels)
    eligible = [
        row for row in candidates if row["minimumClusterSize"] >= 15 and row["meanAdjustedRandStability"] >= 0.8
    ]
    selected = max(eligible or candidates, key=lambda row: row["silhouette"])
    model, labels = fitted[selected["k"]]
    return candidates, model, labels


def _same_month_sensitivity(
    train: TemporalSplit,
    frozen_model: Any,
    original_scores: np.ndarray,
) -> dict[str, Any]:
    groups: dict[bytes, list[int]] = {}
    for index, month in enumerate(train.X[:, :, 3]):
        groups.setdefault(np.ascontiguousarray(month).tobytes(), []).append(index)
    eligible = [indices for indices in groups.values() if len(indices) > 1]
    counterfactual = train.X.copy()
    changed_indices = []
    donor_indices = []
    for indices in eligible:
        donors = indices[1:] + indices[:1]
        for recipient, donor in zip(indices, donors, strict=True):
            counterfactual[recipient, :, :STATION_COUNT] = train.X[donor, :, :STATION_COUNT]
            changed_indices.append(recipient)
            donor_indices.append(donor)
    if not changed_indices:
        return {"constructible": False, "reason": "No repeated exact month representations exist in train."}
    changed = np.asarray(changed_indices)
    counterfactual_split = replace(train, X=counterfactual)
    scores = frozen_model.predict_proba(counterfactual_split)
    difference = np.abs(scores[changed] - original_scores[changed])
    return {
        "constructible": True,
        "method": (
            "Swap complete real station sequences only between train samples with byte-identical month channels; "
            "the resulting 30x4 tensor equals the real donor sample and does not fabricate station values."
        ),
        "eligibleMonthPatternGroups": len(eligible),
        "evaluatedSamples": int(len(changed)),
        "uniqueDonorSamples": int(len(set(donor_indices))),
        "absoluteScoreChangeMedian": float(np.median(difference)),
        "absoluteScoreChangeP75": float(np.quantile(difference, 0.75)),
        "absoluteScoreChangeP90": float(np.quantile(difference, 0.9)),
        "absoluteScoreChangeMaximum": float(np.max(difference)),
        "fractionChangingAtLeast005": float(np.mean(difference >= 0.05)),
        "fractionChangingAtLeast010": float(np.mean(difference >= 0.10)),
    }


def _write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name in sorted(arrays):
            output = io.BytesIO()
            np.lib.format.write_array(output, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, output.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def analyze(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    train, validation = load_selection_splits()
    selection = json.loads((PHASE2_DIR / "model_selection.json").read_text(encoding="utf-8"))
    model_path = PHASE2_DIR / selection["selectedArtifact"]
    if file_sha256(model_path) != selection["selectedArtifactSha256"]:
        raise RuntimeError("Frozen Phase 2 model hash does not match its selection record.")
    frozen = load_frozen_model(model_path)
    train_scores = frozen.predict_proba(train)
    validation_scores = frozen.predict_proba(validation)
    if np.any((train_scores < 0) | (train_scores > 1)) or np.any((validation_scores < 0) | (validation_scores > 1)):
        raise ValueError("Temporal hazard scores must remain numerically within [0, 1].")

    train_features, pattern_names = derive_pattern_features(train)
    validation_features, validation_names = derive_pattern_features(validation)
    if pattern_names != validation_names:
        raise ValueError("Train and validation descriptive feature contracts differ.")

    axis = _fit_intensity_axis(train_features, pattern_names)
    train_intensity = axis["trainScore"]
    validation_intensity = _apply_intensity_axis(validation_features, axis)
    train_quantile, boundaries = _quantile_groups(train_intensity, train_intensity)
    validation_quantile, _ = _quantile_groups(train_intensity, validation_intensity)
    train_quantile_groups = _group_report(train_quantile, train_scores, train.y, "Q")
    validation_quantile_groups = _group_report(validation_quantile, validation_scores, validation.y, "Q")

    pattern_scaler = StandardScaler().fit(train_features)
    train_scaled = pattern_scaler.transform(train_features)
    validation_scaled = pattern_scaler.transform(validation_features)
    clustering_candidates, cluster_model, train_clusters = _cluster_candidates(train_scaled)
    validation_clusters = cluster_model.predict(validation_scaled)
    train_cluster_groups = _group_report(train_clusters, train_scores, train.y, "C")
    validation_cluster_groups = _group_report(validation_clusters, validation_scores, validation.y, "C")

    representatives = []
    representative_sequences = {}
    for label in sorted(np.unique(train_quantile)):
        indices = np.flatnonzero(train_quantile == label)
        index = _nearest_member(train_scaled, indices, np.median(train_scaled[indices], axis=0))
        identifier = f"quantile_Q{label + 1}"
        representatives.append(_representative(train, index, train_features, pattern_names, train_scores, identifier))
        representative_sequences[identifier] = train.X[index]
    for label in sorted(np.unique(train_clusters)):
        indices = np.flatnonzero(train_clusters == label)
        index = _nearest_member(train_scaled, indices, cluster_model.cluster_centers_[label])
        identifier = f"cluster_C{label + 1}"
        representatives.append(_representative(train, index, train_features, pattern_names, train_scores, identifier))
        representative_sequences[identifier] = train.X[index]

    importances = frozen.estimator.feature_importances_
    month_mask = np.asarray([name.endswith(":month") for name in frozen.feature_names])
    month_importance = float(importances[month_mask].sum())
    station_importance = float(importances[~month_mask].sum())
    sensitivity = _same_month_sensitivity(train, frozen, train_scores)
    median_change = sensitivity.get("absoluteScoreChangeMedian", 0.0)
    if station_importance >= 0.75 and median_change >= 0.05:
        rain_dependency = "HIGH"
    elif station_importance >= 0.50 and median_change >= 0.02:
        rain_dependency = "MODERATE"
    else:
        rain_dependency = "LOW"

    quantile_separation_train = _separation(train_quantile, train_scores)
    quantile_separation_validation = _separation(validation_quantile, validation_scores)
    quantile_order_train = _monotonic_report(train_quantile_groups)
    quantile_order_validation = _monotonic_report(validation_quantile_groups)
    validation_stable = (
        quantile_order_validation["hazardMedianSpearman"] >= 0.5
        and quantile_separation_validation["medianRange"] >= 0.05
    )
    train_useful = (
        quantile_separation_train["betweenGroupVarianceFraction"] >= 0.10
        and quantile_separation_train["medianRange"] >= 0.10
    )
    not_month_only = rain_dependency in {"MODERATE", "HIGH"}
    selected_cluster = next(row for row in clustering_candidates if row["k"] == cluster_model.n_clusters)
    reproducible = selected_cluster["meanAdjustedRandStability"] >= 0.8
    if train_useful and validation_stable and not_month_only and reproducible:
        decision = "GO"
    elif train_useful and not_month_only and reproducible:
        decision = "CONDITIONAL GO"
    else:
        decision = "NO-GO"

    report = {
        "analysisVersion": "dynamic-hazard-phase3a-v1",
        "trainOnlyDerived": True,
        "scoreName": "temporalHazardScore",
        "scoreSemantics": SCORE_SEMANTICS,
        "phase2Model": {
            "artifact": str(model_path.relative_to(model_path.parents[4])).replace("\\", "/"),
            "sha256": file_sha256(model_path),
            "retrained": False,
        },
        "dataGovernance": {
            "derivationSplit": "train-2014-2018",
            "validationRole": "post-derivation stability assessment only",
            "testAccessed": False,
            "stationChannels": [str(value) for value in train.stations[:STATION_COUNT]],
            "excludedFromRainfallPatternFeatures": [str(train.stations[3])],
        },
        "descriptiveFeatures": {
            "names": pattern_names,
            "trainShape": list(train_features.shape),
            "limitation": "All statistics describe transformed source features, not physical rainfall units.",
        },
        "quantileMethod": {
            "method": (
                "Train-fitted PCA first component over standardized station-only magnitude, persistence, "
                "variability, and agreement features"
            ),
            "rationale": (
                "PCA supplies data-derived weights without using targets or model scores; component sign is oriented "
                "to positive correlation with train cross-station transformed-feature mean."
            ),
            "explainedVarianceRatio": float(axis["pca"].explained_variance_ratio_[0]),
            "featureNames": axis["featureNames"],
            "componentLoadings": axis["pca"].components_[0].tolist(),
            "trainBoundaries": boundaries.tolist(),
            "trainGroups": train_quantile_groups,
            "validationGroups": validation_quantile_groups,
            "trainSeparation": quantile_separation_train,
            "validationSeparation": quantile_separation_validation,
            "trainOrdering": quantile_order_train,
            "validationOrdering": quantile_order_validation,
        },
        "clusteringMethod": {
            "method": "KMeans on train-fitted standardized station-only descriptive pattern features",
            "candidates": clustering_candidates,
            "selectionRule": "Highest silhouette among K with minimum size >=15 and mean ARI stability >=0.8",
            "selectedK": int(cluster_model.n_clusters),
            "trainGroups": train_cluster_groups,
            "validationGroups": validation_cluster_groups,
            "trainSeparation": _separation(train_clusters, train_scores),
            "validationSeparation": _separation(validation_clusters, validation_scores),
        },
        "representatives": representatives,
        "monthVsRainSignal": {
            "stationFeatureImportanceShare": station_importance,
            "monthFeatureImportanceShare": month_importance,
            "sameMonthRealSequenceSensitivity": sensitivity,
            "RAIN_SIGNAL_DEPENDENCY": rain_dependency,
            "classificationRule": (
                "HIGH requires station importance >=0.75 and median same-month score change >=0.05; MODERATE "
                "requires >=0.50 and >=0.02; otherwise LOW."
            ),
        },
        "consistencyGate": {
            "reproducibleClustering": reproducible,
            "trainScoreSeparationUseful": train_useful,
            "validationOrderingBroadlyStable": validation_stable,
            "notPurelyMonthDriven": not_month_only,
        },
        "decisionGate": decision,
        "limitations": [
            "Temporal channels are transformed/scaled; physical rainfall units and transformations are unavailable.",
            "Binary target ground-truth provenance is undocumented.",
            "Per-timestep dates and exact forecast-horizon alignment cannot be reconstructed.",
            "Temporal hazard scores are uncalibrated relative scores, not literal flood probabilities.",
            "Quantile and cluster semantics are research-only and are not runtime rainfall presets.",
            "Validation contains only 67 samples and 10 positive targets; stability estimates are uncertain.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(output_dir / "scenario_analysis.json", report)
    with (output_dir / "scenario_comparison.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=[
                "method",
                "split",
                "group",
                "sampleCount",
                "hazardScoreMedian",
                "hazardScoreIqr",
                "hazardScoreMinimum",
                "hazardScoreMaximum",
                "targetRate",
            ],
        )
        writer.writeheader()
        for method, train_groups, validation_groups in (
            ("quantile", train_quantile_groups, validation_quantile_groups),
            ("cluster", train_cluster_groups, validation_cluster_groups),
        ):
            for split_name, groups in (("train", train_groups), ("validation", validation_groups)):
                for group in groups:
                    writer.writerow(
                        {
                            "method": method,
                            "split": split_name,
                            "group": group["id"],
                            **{key: group[key] for key in writer.fieldnames[3:]},
                        }
                    )
    representative_sequences["source_sample_indices"] = np.asarray(
        [row["sourceSampleIndex"] for row in representatives], dtype=np.int64
    )
    representative_sequences["reference_dates"] = np.asarray(
        [row["referenceDate"] for row in representatives], dtype="U10"
    )
    _write_deterministic_npz(output_dir / "representative_sequences.npz", representative_sequences)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Research train-derived temporal rainfall-pattern scenarios.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(json.dumps(analyze(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
