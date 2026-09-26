# ARUNA juice demand model report

Artifact version: `juice-xgb-direct-v1`

Dataset: `be/data/new_data/aruna_juice.csv`

Dataset SHA-256: `f6461f8934d5a879c0bdc0fbd07d4dbbac9209139ce03e65637c4f0f9561cac0`

Generator: `aruna-juice-v4.0`

Training cutoff: `2026-05-18`

## Dataset role

The dataset contains 4,015 synthetic product-day rows for 11 juice menus from 2025-09-01 through 2026-08-31. It represents demand characteristics designed around a target juice business and is permitted as the phase training dataset. It is not observed production demand and cannot establish real-world forecast accuracy or business impact.

Synthetic `demand_cups_t` is unconstrained requested demand. Runtime POS history is fulfilled sales and may understate demand during stockouts.

## Feature and split controls

- Direct models: one XGBoost regressor for D+1, D+2, and D+3.
- Product encoding: `OneHotEncoder(handle_unknown="ignore")` inside each persisted pipeline.
- Numeric missing values: median imputation fitted only on `train`.
- Features: `product_id`, `demand_cups_t`, lags 1/2/3/7/14/28, rolling means 7/14/28, and rolling standard deviations 7/14.
- `target_d1`, `target_d2`, `target_d3`, dates, names, split labels, and generator metadata are excluded from features.
- `warmup`, `embargo`, and `inference_only` are excluded from fitting.

| Split | Rows | Date range |
| --- | ---: | --- |
| Train | 2,552 | 2025-09-29 to 2026-05-18 |
| Validation | 528 | 2026-05-22 to 2026-07-08 |
| Test | 528 | 2026-07-12 to 2026-08-28 |

Rolling features include completed day `t`; `lag_1` means `t-1`.

## Results

Metric: mean absolute error in cups per product-day. Persistence predicts the known `demand_cups_t` for every horizon.

| Horizon | Validation XGBoost | Validation persistence | Test XGBoost | Test persistence |
| --- | ---: | ---: | ---: | ---: |
| D+1 | 2.8915 | 3.9299 | 2.9934 | 4.2159 |
| D+2 | 2.9043 | 4.2689 | 3.0130 | 4.3371 |
| D+3 | 2.9102 | 4.0436 | 3.0323 | 4.0303 |

XGBoost has lower MAE than persistence in all six reported comparisons on this synthetic dataset. This result does not validate future performance on real outlet demand.

## Runtime policy

- XGBoost inference requires 29 completed WIB calendar days since the first observed POS sale so lag-28 and rolling features have a valid runtime origin.
- Closed days after the first observed sale may have zero fulfilled sales.
- Before that threshold, the API uses a train-only per-product mean profile and labels it `FALLBACK` with reason `INSUFFICIENT_OBSERVED_SALES_HISTORY`.
- Synthetic history shown during fallback retains its original 2026 dates; it is never relabeled as current observed history.
- Training is offline and never runs inside an API request.

Artifacts are stored in `be/artifacts/inventory/`: `d1.joblib`, `d2.joblib`, `d3.joblib`, `feature_contract.json`, `manifest.json`, and `metrics.json`.
