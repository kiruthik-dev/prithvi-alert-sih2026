"""
PrithviAlert - REAL_ONLY Dataset Builder
=========================================
Builds data/processed/training_dataset_real.csv from genuinely acquired data.

Rules:
  - ONLY uses data from data/raw/real/ (output of acquire_real_data.py)
  - In REAL_ONLY mode: missing features remain NaN - NO synthetic fill
  - If real inventory = 0: writes an empty dataset with a clear status file
  - All provenance columns (data_source, data_quality, source_url,
    source_version, acquisition_date, license) are carried through
  - Temporal split applied only when data is available
  - Validates all coordinates and feature ranges before writing

Usage:
  python scripts/build_real_dataset.py

Output:
  data/processed/training_dataset_real.csv
  data/processed/real_dataset_manifest.json
  data/processed/real_dataset_status.json
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("prithvialert.build_real")

ROOT  = Path(__file__).parent.parent
RAW   = ROOT / "data" / "raw"
REAL  = RAW / "real"
PROC  = ROOT / "data" / "processed"

PROC.mkdir(parents=True, exist_ok=True)

NER_BBOX = {"lat_min": 21.9, "lat_max": 29.5, "lon_min": 88.0, "lon_max": 97.5}

VALIDITY_RULES = {
    "latitude":    (NER_BBOX["lat_min"] - 2, NER_BBOX["lat_max"] + 2),
    "longitude":   (NER_BBOX["lon_min"] - 2, NER_BBOX["lon_max"] + 2),
    "rainfall_24h": (0, 2000),
    "rainfall_7d":  (0, 20000),
    "soil_ph":     (0, 14),
    "era5_elevation_m": (-500, 9000),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def file_checksum(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_coordinates(df: pd.DataFrame) -> dict:
    """Check lat/lon range validity."""
    issues = {}
    for col, (lo, hi) in VALIDITY_RULES.items():
        if col in df.columns:
            n_invalid = int(((df[col] < lo) | (df[col] > hi)).sum())
            if n_invalid > 0:
                issues[col] = {"invalid_count": n_invalid, "range": [lo, hi]}
    return issues


def validate_temporal(df: pd.DataFrame) -> dict:
    """Check date validity and temporal range."""
    result = {"invalid_dates": 0, "year_range": None}
    if "date" not in df.columns:
        return result
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    n_bad = int(df["date"].isna().sum())
    result["invalid_dates"] = n_bad
    valid = df["date"].dropna()
    if len(valid) > 0:
        result["year_range"] = [int(valid.dt.year.min()), int(valid.dt.year.max())]
    return result


def check_leakage_columns(df: pd.DataFrame) -> list:
    """Flag any column names suggesting post-event data."""
    suspicious = [
        c for c in df.columns
        if any(x in c.lower() for x in ["post", "after", "future", "outcome", "result"])
    ]
    return suspicious


# ---------------------------------------------------------------------------
# Load real acquisition log
# ---------------------------------------------------------------------------
def load_acquisition_log() -> dict:
    log_path = REAL / "real_acquisition_log.json"
    if not log_path.exists():
        return {}
    with open(log_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Load real data files
# ---------------------------------------------------------------------------
def load_real_inventory() -> pd.DataFrame:
    """Load real landslide inventory from data/raw/real/."""
    path = REAL / "real_inventory.csv"
    if not path.exists():
        log.warning("Real inventory: data/raw/real/real_inventory.csv not found — 0 real events")
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    log.info(f"Real inventory: {len(df)} events loaded")
    return df


def load_real_rainfall() -> pd.DataFrame:
    """Load Open-Meteo ERA5 rainfall from data/raw/real/."""
    path = REAL / "openmeteo_rainfall.csv"
    if not path.exists():
        log.warning("ERA5 Rainfall: data/raw/real/openmeteo_rainfall.csv not found")
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    log.info(f"ERA5 Rainfall: {len(df)} records loaded")
    return df


def load_real_soil() -> pd.DataFrame:
    """Load SoilGrids data from data/raw/real/."""
    path = REAL / "soilgrids_real.csv"
    if not path.exists():
        log.warning("SoilGrids: data/raw/real/soilgrids_real.csv not found")
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Only use rows where data is actually real (not masked)
    real_rows = df[df["data_quality"] == "real"].copy()
    log.info(
        f"SoilGrids: {len(real_rows)} real rows loaded "
        f"({len(df) - len(real_rows)} masked/skipped)"
    )
    return real_rows


# ---------------------------------------------------------------------------
# Build real dataset
# ---------------------------------------------------------------------------
def build_real_dataset():
    log.info("=" * 60)
    log.info("PrithviAlert - Building REAL_ONLY Training Dataset")
    log.info("=" * 60)

    acq_log     = load_acquisition_log()
    inventory   = load_real_inventory()
    rainfall    = load_real_rainfall()
    soil        = load_real_soil()

    status = {
        "build_timestamp":       datetime.now(timezone.utc).isoformat(),
        "mode":                  "REAL_ONLY",
        "real_inventory_events": len(inventory),
        "real_rainfall_records": len(rainfall),
        "real_soil_records":     len(soil),
        "dataset_ready":         False,
        "missing_features":      [],
        "notes":                 [],
        "validation":            {},
    }

    # -------------------------------------------------------------------------
    # Case 1: No real inventory — dataset is empty (correctly)
    # -------------------------------------------------------------------------
    if inventory.empty:
        log.warning(
            "REAL_ONLY: Zero real landslide events found. "
            "The REAL_ONLY dataset cannot be built without a real inventory. "
            "Required: NASA COOLR or ISRO Atlas event data with confirmed coordinates."
        )
        status["notes"].append(
            "Real inventory = 0. REAL_ONLY dataset is intentionally empty. "
            "Do NOT train ML model on this dataset. "
            "Required action: obtain NASA COOLR CSV from "
            "https://gpm.nasa.gov/landslides/data.html and place in "
            "data/raw/real/real_inventory.csv"
        )
        status["missing_features"] = [
            "ALL — real landslide inventory unavailable",
        ]

        # Write empty dataset with correct schema
        empty_schema = [
            "canonical_event_id", "event_id", "latitude", "longitude", "date",
            "state", "district", "event_type", "trigger", "severity",
            "data_source", "data_quality", "source_url", "source_version",
            "acquisition_date", "license",
            "rainfall_24h", "rainfall_48h", "rainfall_7d", "antecedent_7d",
            "era5_elevation_m",
            "soil_ph", "soil_organic_carbon", "clay_pct", "silt_pct",
            "elevation", "slope", "aspect",
            "ndvi", "land_cover", "ground_displacement",
            "historical_landslide_frequency", "historical_landslide_distance",
            "landslide_event", "split",
        ]
        empty_df = pd.DataFrame(columns=empty_schema)
        out_path = PROC / "training_dataset_real.csv"
        empty_df.to_csv(out_path, index=False)
        log.info(f"Empty REAL_ONLY dataset written: {out_path}")
        status["output_file"] = str(out_path)
        status["total_rows"]  = 0
        status["total_features"] = len(empty_schema)

        # Even with empty inventory, if we have ERA5 rainfall we can write it
        # for reference as a point dataset (not a training dataset)
        if not rainfall.empty:
            ref_path = PROC / "era5_rainfall_reference.csv"
            rainfall.to_csv(ref_path, index=False)
            log.info(
                f"ERA5 rainfall reference saved: {ref_path} "
                f"({len(rainfall)} records — spatial samples, not event-aligned)"
            )
            status["notes"].append(
                f"ERA5 reanalysis rainfall saved separately as reference: "
                f"era5_rainfall_reference.csv ({len(rainfall)} records). "
                f"These are real ERA5 values at synthetic event coordinates. "
                f"NOT suitable as a training target — no confirmed real events."
            )

        _save_status(status)
        return empty_df

    # -------------------------------------------------------------------------
    # Case 2: Real inventory exists — build dataset
    # -------------------------------------------------------------------------
    log.info(f"Building REAL_ONLY dataset from {len(inventory)} real events...")
    df = inventory.copy()
    df["landslide_event"] = 1
    df["canonical_event_id"] = [f"REAL-CE-{i:05d}" for i in range(len(df))]

    # Track missing feature groups
    missing_features = []

    # --- Join ERA5 Rainfall ---
    if not rainfall.empty:
        rain_cols = [
            "rainfall_24h", "rainfall_48h", "rainfall_7d",
            "antecedent_7d", "era5_elevation_m",
        ]
        rain_join = rainfall[["event_id"] + rain_cols].copy()
        df = df.merge(rain_join, on="event_id", how="left")
        n_joined = df["rainfall_24h"].notna().sum()
        log.info(f"ERA5 rainfall joined: {n_joined}/{len(df)} events matched")
    else:
        for col in ["rainfall_24h", "rainfall_48h", "rainfall_7d", "antecedent_7d", "era5_elevation_m"]:
            df[col] = np.nan
        missing_features.append("rainfall (ERA5 not acquired)")

    # --- Join Soil Data ---
    if not soil.empty:
        soil_join = soil[["latitude", "longitude", "soil_ph", "soil_organic_carbon", "clay_pct", "silt_pct"]].copy()
        # Nearest-join by lat/lon (coarse)
        from scipy.spatial import cKDTree
        soil_coords = soil_join[["latitude", "longitude"]].values
        df_coords   = df[["latitude", "longitude"]].values
        tree = cKDTree(soil_coords)
        _, idx = tree.query(df_coords, k=1)
        for col in ["soil_ph", "soil_organic_carbon", "clay_pct", "silt_pct"]:
            df[col] = soil_join[col].iloc[idx].values
        n_joined = df["soil_ph"].notna().sum()
        log.info(f"SoilGrids joined: {n_joined}/{len(df)} events with real soil data")
    else:
        for col in ["soil_ph", "soil_organic_carbon", "clay_pct", "silt_pct"]:
            df[col] = np.nan
        missing_features.append("soil (SoilGrids not acquired)")

    # --- Terrain (no real source available — NaN, not synthetic) ---
    for col in ["elevation", "slope", "aspect", "curvature", "terrain_ruggedness"]:
        df[col] = np.nan
    missing_features.append("terrain/DEM (OpenTopography API key required)")

    # --- Satellite (not available) ---
    df["ndvi"]               = np.nan
    df["land_cover"]         = np.nan
    df["ground_displacement"] = np.nan
    missing_features.extend([
        "ndvi/land_cover (Sentinel-2 auth required)",
        "ground_displacement (Sentinel-1 auth required)",
    ])

    # --- Historical frequency (derived from real inventory itself) ---
    from scipy.spatial import cKDTree
    pos_coords = df[["latitude", "longitude"]].values
    if len(pos_coords) > 1:
        tree = cKDTree(pos_coords)
        threshold = 10.0 / 111.0
        counts = tree.query_ball_point(pos_coords, threshold)
        df["historical_landslide_frequency"] = [max(0, len(c) - 1) for c in counts]
        dists, _ = tree.query(pos_coords, k=min(2, len(pos_coords)))
        if dists.ndim > 1:
            df["historical_landslide_distance"] = np.round(dists[:, -1] * 111.0, 3)
        else:
            df["historical_landslide_distance"] = 999.9
    else:
        df["historical_landslide_frequency"] = 0
        df["historical_landslide_distance"]  = 999.9

    # -------------------------------------------------------------------------
    # Leakage audit
    # -------------------------------------------------------------------------
    suspicious = check_leakage_columns(df)
    if suspicious:
        log.warning(f"LEAKAGE AUDIT: Suspicious columns: {suspicious}")
    else:
        log.info("LEAKAGE AUDIT: No post-event columns detected")

    # -------------------------------------------------------------------------
    # Coordinate validation
    # -------------------------------------------------------------------------
    coord_issues = validate_coordinates(df)
    temporal_issues = validate_temporal(df)

    if coord_issues:
        log.warning(f"Coordinate issues: {coord_issues}")
    if temporal_issues.get("invalid_dates", 0) > 0:
        log.warning(f"Invalid dates: {temporal_issues['invalid_dates']}")
        df = df[pd.to_datetime(df["date"], errors="coerce").notna()].copy()

    # -------------------------------------------------------------------------
    # Temporal split (if enough data)
    # -------------------------------------------------------------------------
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    train = df[df["date"].dt.year <= 2019].copy()
    val   = df[(df["date"].dt.year >= 2020) & (df["date"].dt.year <= 2021)].copy()
    test  = df[df["date"].dt.year >= 2022].copy()

    train["split"] = "train"
    val["split"]   = "validation"
    test["split"]  = "test"
    df = pd.concat([train, val, test], ignore_index=True)

    log.info(
        f"Temporal split: TRAIN={len(train)}, VAL={len(val)}, TEST={len(test)}"
    )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------
    out_path = PROC / "training_dataset_real.csv"
    df.to_csv(out_path, index=False)
    log.info(f"REAL_ONLY dataset saved: {out_path} ({len(df)} rows, {len(df.columns)} features)")

    # Save split files
    train.to_csv(PROC / "real_train.csv", index=False)
    val.to_csv(PROC / "real_val.csv",     index=False)
    test.to_csv(PROC / "real_test.csv",   index=False)

    # -------------------------------------------------------------------------
    # Final manifest
    # -------------------------------------------------------------------------
    status.update({
        "dataset_ready":    True,
        "total_rows":       len(df),
        "total_features":   len(df.columns),
        "real_rows":        len(df),
        "synthetic_rows":   0,
        "train_rows":       len(train),
        "val_rows":         len(val),
        "test_rows":        len(test),
        "missing_features": missing_features,
        "output_file":      str(out_path),
        "checksum":         file_checksum(out_path),
        "validation": {
            "coordinate_issues": coord_issues,
            "temporal_issues":   temporal_issues,
            "leakage_audit":     suspicious,
        },
    })

    _save_status(status)
    log.info("=" * 60)
    log.info("REAL_ONLY Build Complete")
    log.info(f"  Total real rows:    {len(df)}")
    log.info(f"  Total features:     {len(df.columns)}")
    log.info(f"  Missing features:   {len(missing_features)}")
    for mf in missing_features:
        log.info(f"    - {mf}")
    log.info("=" * 60)
    return df


def _save_status(status: dict):
    status_path = PROC / "real_dataset_status.json"
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2, default=str)
    log.info(f"Real dataset status saved: {status_path}")

    manifest_path = PROC / "real_dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(status, f, indent=2, default=str)


if __name__ == "__main__":
    build_real_dataset()
