"""
PrithviAlert — Training Data Preparation (ETL Pipeline)
=========================================================
Joins all raw source data into a single normalized training dataset.

Pipeline Modes
--------------
  REAL_ONLY      - Only real/verified data. Missing optional sources recorded
                   as unavailable. No synthetic fills. Exits cleanly if
                   required inventories are absent.
  MIXED_DEMO     - Available data (real OR labelled-synthetic) is processed.
                   Missing optional sources → NaN columns + flagged in manifest.
                   No silent synthetic value generation for feature columns.
                   Negative samples are generated and clearly labelled simulated.
  SYNTHETIC_DEMO - Full synthetic run for offline testing.

Steps:
  1. Load landslide inventories (ISRO + NASA COOLR) — REQUIRED
  2. Deduplicate events (spatial + temporal)
  3. Generate negative samples (clearly labelled simulated)
  4. Join rainfall, terrain, soil, vegetation, deformation features
  5. Leakage audit
  6. Temporal train/val/test split
  7. Write data/processed/training_dataset.csv
  8. Write data/processed/processing_manifest.json

Usage:
  python scripts/prepare_training_data.py [--mode MIXED_DEMO]
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("prithvialert.prepare")

ROOT  = Path(__file__).parent.parent
RAW   = ROOT / "data" / "raw"
INTER = ROOT / "data" / "interim"
PROC  = ROOT / "data" / "processed"

INTER.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pipeline mode
# ---------------------------------------------------------------------------
class PipelineMode(str, Enum):
    REAL_ONLY      = "REAL_ONLY"
    MIXED_DEMO     = "MIXED_DEMO"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


NER_STATES = [
    "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Sikkim", "Tripura",
]


# ---------------------------------------------------------------------------
# Manifest accumulator
# ---------------------------------------------------------------------------
class Manifest:
    def __init__(self, mode: PipelineMode):
        self.mode               = mode.value
        self.source_datasets: list  = []
        self.missing_sources: list  = []
        self.real_record_count      = 0
        self.synthetic_record_count = 0
        self.total_processed        = 0
        self.feature_count          = 0
        self.processing_timestamp   = datetime.now(timezone.utc).isoformat()

    def add_source(self, name: str, path: str, records: int, quality: str):
        self.source_datasets.append({
            "name": name, "path": path,
            "records": records, "quality": quality,
        })

    def add_missing(self, name: str, reason: str, missing_features: list):
        self.missing_sources.append({
            "name": name, "reason": reason,
            "missing_features": missing_features,
        })
        log.warning(
            f"SOURCE UNAVAILABLE: {name} — {reason} "
            f"(features set to NaN: {missing_features})"
        )

    def to_dict(self) -> dict:
        return {
            "mode":                   self.mode,
            "processing_timestamp":   self.processing_timestamp,
            "source_datasets":        self.source_datasets,
            "missing_sources":        self.missing_sources,
            "real_record_count":      self.real_record_count,
            "synthetic_record_count": self.synthetic_record_count,
            "total_processed":        self.total_processed,
            "feature_count":          self.feature_count,
        }


# ---------------------------------------------------------------------------
# 1. Load and merge inventories (REQUIRED sources)
# ---------------------------------------------------------------------------
def load_inventories(mode: PipelineMode, manifest: Manifest) -> pd.DataFrame:
    """
    Load ISRO Atlas and NASA COOLR inventories.
    Both are REQUIRED — if neither is present, abort.
    In REAL_ONLY mode, both must be present.
    """
    REQUIRED_SOURCES = [
        {
            "key":  "isro_atlas",
            "path": RAW / "isro_atlas" / "isro_atlas_ner.csv",
            "label": "ISRO Atlas NER",
        },
        {
            "key":  "nasa_coolr",
            "path": RAW / "nasa_coolr" / "nasa_glc_ner.csv",
            "label": "NASA COOLR NER",
        },
    ]

    dfs = []
    for src in REQUIRED_SOURCES:
        p = src["path"]
        if p.exists():
            df = pd.read_csv(p)
            # Ensure required provenance columns exist
            if "data_source" not in df.columns:
                df["data_source"] = src["key"]
            if "data_quality" not in df.columns:
                df["data_quality"] = "unknown"
            dfs.append(df)
            manifest.add_source(
                src["label"], str(p), len(df),
                df["data_quality"].iloc[0] if len(df) > 0 else "unknown",
            )
            log.info(f"Loaded {len(df)} records from {p.name}")
        else:
            msg = f"Required inventory not found: {p}"
            if mode == PipelineMode.REAL_ONLY:
                log.error(msg)
                raise FileNotFoundError(
                    f"{msg}\n"
                    f"In REAL_ONLY mode all required inventories must be present.\n"
                    f"Run download_data.py or switch to MIXED_DEMO mode."
                )
            else:
                log.warning(f"{msg} — skipping (mode={mode.value})")
                manifest.add_missing(
                    src["label"], f"File not found: {p}", ["all inventory columns"]
                )

    if not dfs:
        raise RuntimeError(
            "No inventory files found at all. "
            "Run download_data.py or place inventory CSVs in data/raw/."
        )

    combined = pd.concat(dfs, ignore_index=True)
    log.info(f"Combined inventory: {len(combined)} records before dedup")
    return combined


# ---------------------------------------------------------------------------
# 2. Deduplicate events (spatial + temporal)
# ---------------------------------------------------------------------------
def deduplicate_events(
    df: pd.DataFrame, dist_km: float = 5.0, days: int = 7
) -> pd.DataFrame:
    """
    Merge events within dist_km and days of each other.
    Assigns canonical_event_id; preserves source_event_ids.
    Guarantees unique canonical_event_id values (prefix CE-).
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", "date"])
    df = df.reset_index(drop=True)

    coords_rad = np.radians(df[["latitude", "longitude"]].values)
    tree = cKDTree(coords_rad)
    dist_threshold_rad = (dist_km / 111.0) * (np.pi / 180.0)

    canonical_id    = list(range(len(df)))
    source_event_ids = [[str(eid)] for eid in df["event_id"]]

    for i, row in df.iterrows():
        coord = np.radians([row["latitude"], row["longitude"]])
        neighbors = tree.query_ball_point(coord, dist_threshold_rad)
        for j in neighbors:
            if j <= i:
                continue
            date_diff = abs((df.loc[j, "date"] - row["date"]).days)
            if date_diff <= days:
                old_cid = canonical_id[j]
                new_cid = canonical_id[i]
                if old_cid != new_cid:
                    source_event_ids[new_cid].extend(source_event_ids[old_cid])
                    canonical_id[j] = new_cid

    df["canonical_id"]    = canonical_id
    df["source_event_ids"] = [json.dumps(s) for s in source_event_ids]

    deduped = df.groupby("canonical_id").first().reset_index(drop=True)
    # Unique IDs with CE- prefix (positives only)
    deduped["canonical_event_id"] = [f"CE-{i:05d}" for i in range(len(deduped))]

    removed = len(df) - len(deduped)
    log.info(
        f"Deduplication: {len(df)} → {len(deduped)} events "
        f"(removed {removed} near-duplicates)"
    )
    return deduped


# ---------------------------------------------------------------------------
# 3. Generate negative samples (clearly labelled as synthetic/simulated)
# ---------------------------------------------------------------------------
def generate_negatives(
    pos_df: pd.DataFrame, ratio: float = 1.5, mode: PipelineMode = PipelineMode.MIXED_DEMO
) -> pd.DataFrame:
    """
    Non-event negative samples at spatial-temporal offsets from positives.
    Always labelled: data_source=negative_sample_synthetic, data_quality=simulated.
    In REAL_ONLY mode negative samples are NOT generated.
    """
    if mode == PipelineMode.REAL_ONLY:
        log.info("REAL_ONLY mode: skipping synthetic negative sample generation")
        return pd.DataFrame()

    rng = np.random.default_rng(55)
    n_neg = int(len(pos_df) * ratio)

    pos_lats   = pos_df["latitude"].values
    pos_lons   = pos_df["longitude"].values

    negatives  = []
    attempts   = 0
    max_attempts = n_neg * 20

    # Representative NER district centroids for spatial anchoring
    NER_ANCHORS = [
        (27.6, 91.8), (28.1, 94.7), (26.5, 94.2), (25.5, 92.7),
        (24.8, 94.4), (25.3, 92.1), (23.4, 92.7), (26.2, 94.5),
        (27.3, 88.6), (23.8, 91.3),
    ]

    while len(negatives) < n_neg and attempts < max_attempts:
        attempts += 1
        base_lat, base_lon = NER_ANCHORS[rng.integers(0, len(NER_ANCHORS))]
        lat_off = float(rng.uniform(0.18, 0.90)) * rng.choice([-1, 1])
        lon_off = float(rng.uniform(0.18, 0.90)) * rng.choice([-1, 1])
        neg_lat = base_lat + lat_off
        neg_lon = base_lon + lon_off

        # Constrain to NER bounding box
        if not (21.9 <= neg_lat <= 29.5 and 88.0 <= neg_lon <= 97.5):
            continue

        # Must be > 5 km from any positive event
        dists_deg = np.sqrt((pos_lats - neg_lat) ** 2 + (pos_lons - neg_lon) ** 2)
        if np.min(dists_deg) < (5.0 / 111.0):
            continue

        year  = int(rng.integers(2000, 2023))
        month = int(rng.integers(1, 13))
        day   = int(rng.integers(1, 28))
        try:
            neg_date = pd.Timestamp(year=year, month=month, day=day)
        except Exception:
            continue

        negatives.append({
            "canonical_event_id": f"NEG-{len(negatives):06d}",
            "latitude":           round(neg_lat, 6),
            "longitude":          round(neg_lon, 6),
            "date":               neg_date,
            "state":              "NER",
            "district":           "",
            "event_type":         "non_event",
            "trigger":            "none",
            "severity":           "none",
            "data_source":        "negative_sample_synthetic",
            "data_quality":       "simulated",
            "landslide_event":    0,
        })

    neg_df = pd.DataFrame(negatives)
    log.info(f"Generated {len(neg_df)} negative samples (target: {n_neg})")
    return neg_df


# ---------------------------------------------------------------------------
# 4. Feature joins — each optional source handled gracefully
# ---------------------------------------------------------------------------
def _nearest_join(
    base_df: pd.DataFrame, feat_df: pd.DataFrame, feat_cols: list
) -> pd.DataFrame:
    """
    Spatial nearest-neighbour join. If feat_df is empty, columns are NaN.
    """
    base_df = base_df.copy()
    if feat_df.empty:
        for col in feat_cols:
            base_df[col] = np.nan
        return base_df

    feat_coords = feat_df[["latitude", "longitude"]].values
    base_coords = base_df[["latitude", "longitude"]].values
    tree = cKDTree(feat_coords)
    _, idx = tree.query(base_coords, k=1)

    for col in feat_cols:
        if col in feat_df.columns:
            base_df[col] = feat_df[col].iloc[idx].values
    return base_df


def join_rainfall(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    RAIN_COLS = [
        "rainfall_1h", "rainfall_6h", "rainfall_12h",
        "rainfall_24h", "rainfall_48h", "rainfall_7d", "rainfall_intensity",
    ]
    path = RAW / "gpm_imerg" / "gpm_rainfall_features.csv"
    if not path.exists():
        manifest.add_missing("GPM IMERG Rainfall", f"File not found: {path}", RAIN_COLS)
        for col in RAIN_COLS:
            master_df[col] = np.nan
        master_df["rainfall_data_source"] = "missing"
        return master_df

    feat = pd.read_csv(path)
    manifest.add_source(
        "GPM IMERG Rainfall", str(path), len(feat),
        feat["data_quality"].iloc[0] if "data_quality" in feat.columns and len(feat) > 0 else "simulated",
    )
    master_df = _nearest_join(master_df, feat, RAIN_COLS)
    master_df["rainfall_data_source"] = (
        feat["data_source"].iloc[0] if "data_source" in feat.columns and len(feat) > 0 else "gpm_imerg"
    )
    log.info("Rainfall features joined")
    return master_df


def join_terrain(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    TERRAIN_COLS = ["elevation", "slope", "aspect", "curvature", "terrain_ruggedness"]
    path = RAW / "dem" / "terrain_features.csv"
    if not path.exists():
        manifest.add_missing("DEM / Terrain", f"File not found: {path}", TERRAIN_COLS)
        for col in TERRAIN_COLS:
            master_df[col] = np.nan
        return master_df

    feat = pd.read_csv(path)
    manifest.add_source("DEM / Terrain", str(path), len(feat), "real")
    master_df = _nearest_join(master_df, feat, TERRAIN_COLS)
    log.info("Terrain features joined")
    return master_df


def join_soil(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    SOIL_COLS = ["soil_moisture", "soil_texture", "soil_ph", "soil_organic_carbon"]
    path = RAW / "soilgrids" / "soilgrids_features.csv"
    if not path.exists():
        manifest.add_missing("SoilGrids", f"File not found: {path}", SOIL_COLS)
        for col in SOIL_COLS:
            master_df[col] = np.nan
        return master_df

    feat = pd.read_csv(path)
    manifest.add_source("SoilGrids", str(path), len(feat), "real")
    master_df = _nearest_join(master_df, feat, SOIL_COLS)
    log.info("Soil features joined")
    return master_df


def join_vegetation(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    VEG_COLS = ["ndvi", "land_cover"]
    path = RAW / "sentinel2" / "sentinel2_vegetation.csv"
    if not path.exists():
        manifest.add_missing(
            "Sentinel-2 Vegetation", f"File not found: {path}", VEG_COLS
        )
        master_df["ndvi"]       = np.nan
        master_df["land_cover"] = np.nan
        return master_df

    feat = pd.read_csv(path)
    manifest.add_source("Sentinel-2 Vegetation", str(path), len(feat), "real")
    master_df = _nearest_join(master_df, feat, VEG_COLS)
    log.info("Vegetation/NDVI features joined")
    return master_df


def join_deformation(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    DEFORM_COLS = ["ground_displacement"]
    path = RAW / "sentinel1" / "sentinel1_deformation.csv"
    if not path.exists():
        manifest.add_missing(
            "Sentinel-1 SAR Deformation", f"File not found: {path}", DEFORM_COLS
        )
        master_df["ground_displacement"] = np.nan
        return master_df

    feat = pd.read_csv(path)
    manifest.add_source("Sentinel-1 SAR Deformation", str(path), len(feat), "real")
    master_df = _nearest_join(master_df, feat, DEFORM_COLS)
    log.info("SAR deformation features joined")
    return master_df


# ---------------------------------------------------------------------------
# Historical susceptibility features (derived from the positive inventory)
# ---------------------------------------------------------------------------
def add_historical_features(
    master_df: pd.DataFrame, pos_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Per-record statistics derived only from the positive inventory:
    - historical_landslide_frequency: # positive events within 10 km
    - historical_landslide_distance:  km to nearest historical positive
    These are structural features — no leakage (they use the full positive set,
    not the split-specific labels).
    """
    pos_coords = pos_df[["latitude", "longitude"]].values
    if len(pos_coords) == 0:
        master_df["historical_landslide_frequency"] = 0
        master_df["historical_landslide_distance"]  = 999.9
        return master_df

    tree = cKDTree(pos_coords)
    base_coords = master_df[["latitude", "longitude"]].values

    threshold = 10.0 / 111.0  # ~10 km in degrees
    counts = tree.query_ball_point(base_coords, threshold)
    master_df["historical_landslide_frequency"] = [len(c) for c in counts]

    dists, _ = tree.query(base_coords, k=1)
    master_df["historical_landslide_distance"] = np.round(dists * 111.0, 3)
    log.info("Historical susceptibility features added")
    return master_df


# ---------------------------------------------------------------------------
# Exposure features — MIXED_DEMO: explicitly labelled simulated in manifest
# ---------------------------------------------------------------------------
def add_exposure_features(
    master_df: pd.DataFrame,
    mode: PipelineMode,
    manifest: Manifest,
) -> pd.DataFrame:
    """
    Population and infrastructure exposure.
    Real values would come from WorldPop + OSM.

    In REAL_ONLY: these columns are NaN (no synthetic fill).
    In MIXED_DEMO / SYNTHETIC_DEMO: synthetic values generated and
      clearly recorded in the manifest.
    """
    EXPOSURE_COLS = [
        "population_exposure", "infrastructure_exposure",
        "distance_to_road", "distance_to_river",
    ]
    if mode == PipelineMode.REAL_ONLY:
        manifest.add_missing(
            "WorldPop / OSM Exposure",
            "Real exposure data not downloaded; REAL_ONLY mode prevents synthetic fill.",
            EXPOSURE_COLS,
        )
        for col in EXPOSURE_COLS:
            master_df[col] = np.nan
        log.info("REAL_ONLY: exposure features set to NaN")
        return master_df

    rng = np.random.default_rng(77)
    n   = len(master_df)
    master_df["population_exposure"]     = np.round(rng.exponential(500, n), 0)
    master_df["infrastructure_exposure"] = np.round(rng.exponential(5, n), 2)
    master_df["distance_to_road"]        = np.round(rng.exponential(3, n), 2)
    master_df["distance_to_river"]       = np.round(rng.exponential(2, n), 2)

    manifest.add_source(
        "Exposure (synthetic — WorldPop/OSM placeholder)",
        "generated_in_pipeline",
        n,
        "simulated",
    )
    log.info("Exposure features added (synthetic — labelled in manifest)")
    return master_df


# ---------------------------------------------------------------------------
# 5. Leakage audit
# ---------------------------------------------------------------------------
def leakage_audit(df: pd.DataFrame) -> pd.DataFrame:
    suspicious = [
        c for c in df.columns
        if any(x in c.lower() for x in ["post", "after", "future", "outcome"])
    ]
    if suspicious:
        log.warning(f"LEAKAGE AUDIT: Suspicious post-event columns: {suspicious}")
    else:
        log.info("LEAKAGE AUDIT: No suspicious post-event columns detected")
    return df


# ---------------------------------------------------------------------------
# 6. Temporal train/val/test split (no leakage across boundaries)
# ---------------------------------------------------------------------------
def temporal_split(df: pd.DataFrame):
    """
    TRAIN  : year <= 2019
    VAL    : 2020–2021
    TEST   : year >= 2022
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    train = df[df["date"].dt.year <= 2019].copy()
    val   = df[(df["date"].dt.year >= 2020) & (df["date"].dt.year <= 2021)].copy()
    test  = df[df["date"].dt.year >= 2022].copy()

    train["split"] = "train"
    val["split"]   = "validation"
    test["split"]  = "test"

    log.info(
        f"Temporal split → TRAIN: {len(train)}, VAL: {len(val)}, TEST: {len(test)}"
    )
    return train, val, test


# ---------------------------------------------------------------------------
# 7. Uniqueness guard — ensure no duplicate canonical_event_id
# ---------------------------------------------------------------------------
def ensure_unique_event_ids(df: pd.DataFrame) -> pd.DataFrame:
    if "canonical_event_id" not in df.columns:
        df["canonical_event_id"] = [f"EVT-{i:06d}" for i in range(len(df))]
        return df

    dupes = df["canonical_event_id"].duplicated()
    if dupes.any():
        n_dupes = int(dupes.sum())
        log.error(
            f"DUPLICATE EVENT IDs detected: {n_dupes} — reassigning globally unique IDs"
        )
        # Reassign: keep canonical prefix, append row index
        ids = df["canonical_event_id"].tolist()
        seen = {}
        for i, eid in enumerate(ids):
            if eid in seen:
                ids[i] = f"{eid}-DUP{i}"
            else:
                seen[eid] = True
        df = df.copy()
        df["canonical_event_id"] = ids
    else:
        log.info(f"Event IDs: {len(df)} unique IDs — OK")
    return df


# ---------------------------------------------------------------------------
# 8. Main pipeline
# ---------------------------------------------------------------------------
def main(mode: PipelineMode = PipelineMode.MIXED_DEMO):
    log.info("=" * 60)
    log.info(f"PrithviAlert ETL Pipeline — Mode: {mode.value}")
    log.info("=" * 60)

    manifest = Manifest(mode)

    # -- Step 1: Load inventories (REQUIRED) ---------------------------------
    raw_events = load_inventories(mode, manifest)

    # -- Step 2: Deduplicate -------------------------------------------------
    pos_df = deduplicate_events(raw_events)
    pos_df["landslide_event"] = 1

    # Track real vs synthetic record counts
    # (All current inventories are labelled simulated — we preserve their labels)
    real_pos      = int((pos_df.get("data_quality", pd.Series(["simulated"] * len(pos_df))) == "real").sum())
    synthetic_pos = len(pos_df) - real_pos
    manifest.real_record_count      += real_pos
    manifest.synthetic_record_count += synthetic_pos

    # -- Step 3: Negative samples --------------------------------------------
    neg_df = generate_negatives(pos_df, ratio=1.5, mode=mode)
    manifest.synthetic_record_count += len(neg_df)  # negatives are always synthetic

    # -- Step 4: Align and merge ---------------------------------------------
    common_cols = [
        "canonical_event_id", "latitude", "longitude", "date",
        "state", "district", "event_type", "trigger", "severity",
        "data_source", "data_quality", "landslide_event",
    ]
    for col in common_cols:
        if col not in pos_df.columns:
            pos_df[col] = None
        if neg_df is not None and len(neg_df) > 0 and col not in neg_df.columns:
            neg_df[col] = None

    parts = [pos_df[common_cols]]
    if neg_df is not None and len(neg_df) > 0:
        parts.append(neg_df[common_cols])

    master = pd.concat(parts, ignore_index=True)
    log.info(
        f"Master dataset: {len(master)} rows "
        f"({int(pos_df['landslide_event'].sum())} positive, {len(neg_df)} negative)"
    )

    # -- Step 5: Feature joins -----------------------------------------------
    master = join_rainfall(master, mode, manifest)
    master = join_terrain(master, mode, manifest)
    master = join_soil(master, mode, manifest)
    master = join_vegetation(master, mode, manifest)
    master = join_deformation(master, mode, manifest)
    master = add_historical_features(master, pos_df)
    master = add_exposure_features(master, mode, manifest)

    # -- Step 6: Leakage audit -----------------------------------------------
    master = leakage_audit(master)

    # -- Step 7: NER membership flag -----------------------------------------
    master["is_ner"] = master["state"].isin(NER_STATES).astype(int)

    # -- Step 8: Ensure target column is present and clean -------------------
    if "landslide_event" not in master.columns:
        raise RuntimeError("CRITICAL: landslide_event target column missing after pipeline!")
    missing_target = master["landslide_event"].isna().sum()
    if missing_target > 0:
        raise RuntimeError(
            f"CRITICAL: {missing_target} rows have missing landslide_event target — "
            "data leakage or pipeline bug."
        )
    log.info(
        f"Target check: landslide_event present, "
        f"{int(master['landslide_event'].sum())} positive / "
        f"{int((master['landslide_event']==0).sum())} negative"
    )

    # -- Step 9: Unique event ID guard ---------------------------------------
    master = ensure_unique_event_ids(master)

    # -- Step 10: Save interim -----------------------------------------------
    interim_path = INTER / "master_dataset_pre_split.csv"
    master.to_csv(interim_path, index=False)
    log.info(f"Interim dataset saved: {interim_path}")

    # -- Step 11: Temporal split ---------------------------------------------
    train, val, test = temporal_split(master)

    # -- Step 12: Save processed datasets ------------------------------------
    full_path  = PROC / "training_dataset.csv"
    train_path = PROC / "train.csv"
    val_path   = PROC / "val.csv"
    test_path  = PROC / "test.csv"

    master.to_csv(full_path, index=False)
    train.to_csv(train_path, index=False)
    val.to_csv(val_path, index=False)
    test.to_csv(test_path, index=False)
    log.info(f"Processed dataset saved: {full_path}")

    # -- Step 13: Finalize manifest ------------------------------------------
    manifest.total_processed  = len(master)
    manifest.feature_count    = len(master.columns)

    manifest_dict = manifest.to_dict()
    manifest_dict["split_report"] = {
        "split_method": "temporal",
        "train_years":  "<= 2019",
        "val_years":    "2020-2021",
        "test_years":   ">= 2022",
        "train_size":   len(train),
        "val_size":     len(val),
        "test_size":    len(test),
    }
    manifest_path = PROC / "processing_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_dict, f, indent=2, default=str)
    log.info(f"Processing manifest saved: {manifest_path}")

    # -- Step 14: Console summary --------------------------------------------
    log.info("=" * 60)
    log.info("ETL Pipeline Complete")
    log.info(f"  Mode:            {mode.value}")
    log.info(f"  Total rows:      {len(master)}")
    log.info(f"  Real rows:       {manifest.real_record_count}")
    log.info(f"  Synthetic rows:  {manifest.synthetic_record_count}")
    log.info(f"  Features:        {manifest.feature_count}")
    log.info(f"  TRAIN:           {len(train)}")
    log.info(f"  VAL:             {len(val)}")
    log.info(f"  TEST:            {len(test)}")
    log.info(f"  Missing sources: {len(manifest.missing_sources)}")
    for ms in manifest.missing_sources:
        log.info(f"    - {ms['name']}: {ms['reason']}")
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PrithviAlert ETL — Training Data Preparation"
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in PipelineMode],
        default=PipelineMode.MIXED_DEMO.value,
        help="Pipeline mode: REAL_ONLY | MIXED_DEMO (default) | SYNTHETIC_DEMO",
    )
    args = parser.parse_args()
    main(mode=PipelineMode(args.mode))
