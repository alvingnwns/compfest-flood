# Flood Remote-Sensing Pipeline

Status: **BLOCKED — EARTH ENGINE AUTHENTICATION REQUIRED**.

C1 real OSM preparation is complete. C2–C9 were intentionally not executed because the installed Earth Engine Python API 1.7.38 could not initialize without credentials. No Sentinel-1 acquisitions, flood masks, thresholds, road labels, or real model artifacts were fabricated.

Required user action:

```powershell
earthengine authenticate
earthengine set_project YOUR_GOOGLE_CLOUD_PROJECT
```

The Google Cloud project must be registered for Earth Engine access and available to the authenticated account. Credentials created by this command live outside the repository and must never be committed. After authentication, verify with:

```powershell
python -c "import ee; ee.Initialize(project='YOUR_GOOGLE_CLOUD_PROJECT'); print('Earth Engine ready')"
```

Planned—but not yet claimed—workflow is `COPERNICUS/S1_GRD` acquisition audit → orbit/polarization-consistent dry baseline → literature-supported change detection → permanent-water and quality masks → OSM road-buffer overlay → positive/negative/unknown labels → scientific feasibility gate. March 04–05 2025 must remain holdout where technically possible.
