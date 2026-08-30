"""
PrithviAlert - Dataset Status Report
======================================
Compares all three dataset states across the pipeline:

  SYNTHETIC_DEMO  - data/processed/training_dataset.csv
  MIXED_DEMO      - (future state - currently same as SYNTHETIC_DEMO)
  REAL_ONLY       - data/processed/training_dataset_real.csv

Outputs:
  data/processed/dataset_status_report.md   (human-readable)
  data/processed/dataset_status_report.json (machine-readable)

Usage:
  python scripts/dataset_status_report.py
"""

import json
import logging
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("prithvialert.status_report")

ROOT = Path(__file__).parent.parent
PROC = ROOT / "data" / "raw" / "real"
OUT  = ROOT / "data" / "processed"

DATASET_PATHS = {
    "SYNTHETIC_DEMO": OUT / "training_dataset.csv",
    "REAL_ONLY":      OUT / "training_dataset_real.csv",
}

NUMERIC_FEATURES = [
    "rainfall_24h", "rainfall_48h", "rainfall_7d",
    "elevation", "slope", "aspect",
    "soil_ph", "soil_organic_carbon",
    "ndvi", "ground_displacement",
    "historical_landslide_frequency", "historical_landslide_distance",
]


# ---------------------------------------------------------------------------
# Dataset profiler
# ---------------------------------------------------------------------------
def profile_dataset(name: str, path: Path) -> dict:
    profile = {
        "mode":    name,
        "path":    str(path),
        "exists":  path.exists(),
        "status":  "NOT_CREATED",
        "rows":    0,
        "features": 0,
        "real_rows": 0,
        "synthetic_rows": 0,
        "positive_events": 0,
        "negative_samples": 0,
        "missing_features": [],
        "sources": {},
        "quality_breakdown": {},
        "feature_coverage": {},
        "temporal_range": {},
        "validation": {},
        "notes": [],
    }

    if not path.exists():
        profile["notes"].append(f"File not found: {path}")
        return profile

    try:
        df = pd.read_csv(path, parse_dates=["date"] if "date" in pd.read_csv(path, nrows=1).columns else [])
    except Exception as e:
        profile["status"] = "READ_ERROR"
        profile["notes"].append(str(e))
        return profile

    if df.empty:
        profile["status"] = "EMPTY"
        profile["notes"].append(
            "Dataset is intentionally empty (REAL_ONLY: no confirmed real events yet)"
        )
        return profile

    profile["status"]   = "AVAILABLE"
    profile["rows"]     = len(df)
    profile["features"] = len(df.columns)

    # Real vs synthetic breakdown
    if "data_quality" in df.columns:
        qual_counts = df["data_quality"].value_counts().to_dict()
        profile["quality_breakdown"] = {str(k): int(v) for k, v in qual_counts.items()}
        profile["real_rows"]      = int(df["data_quality"].isin(["real", "reanalysis", "measured"]).sum())
        profile["synthetic_rows"] = int(df["data_quality"].isin(["simulated", "synthetic"]).sum())
    else:
        profile["notes"].append("data_quality column missing")

    # Class balance
    if "landslide_event" in df.columns:
        profile["positive_events"]  = int(df["landslide_event"].sum())
        profile["negative_samples"] = int((df["landslide_event"] == 0).sum())
    else:
        profile["notes"].append("landslide_event target column missing")

    # Source breakdown
    if "data_source" in df.columns:
        profile["sources"] = {str(k): int(v) for k, v in df["data_source"].value_counts().items()}

    # Feature coverage (non-null %)
    for feat in NUMERIC_FEATURES:
        if feat in df.columns:
            pct = round(100.0 * df[feat].notna().sum() / len(df), 1)
            profile["feature_coverage"][feat] = pct
        else:
            profile["missing_features"].append(feat)

    # Temporal range
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if len(dates):
            profile["temporal_range"] = {
                "min": str(dates.min().date()),
                "max": str(dates.max().date()),
                "years": sorted(dates.dt.year.unique().tolist()),
            }

    # Split sizes
    if "split" in df.columns:
        profile["splits"] = {str(k): int(v) for k, v in df["split"].value_counts().items()}

    # Basic validation
    dup_ids = 0
    if "canonical_event_id" in df.columns:
        dup_ids = int(df["canonical_event_id"].duplicated().sum())
    miss_target = int(df["landslide_event"].isna().sum()) if "landslide_event" in df.columns else "N/A"

    profile["validation"] = {
        "duplicate_event_ids": dup_ids,
        "missing_target":      miss_target,
        "duplicate_rows":      int(df.duplicated().sum()),
        "leakage_check":       "PASS" if not any(
            x in c.lower()
            for c in df.columns
            for x in ["post", "after", "future", "outcome"]
        ) else "WARN",
    }

    return profile


# ---------------------------------------------------------------------------
# Load real acquisition log for context
# ---------------------------------------------------------------------------
def load_real_acq_log() -> dict:
    log_path = ROOT / "data" / "raw" / "real" / "real_acquisition_log.json"
    if not log_path.exists():
        return {}
    with open(log_path) as f:
        return json.load(f)


def load_real_status() -> dict:
    path = OUT / "real_dataset_status.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------
def generate_report_md(profiles: dict, acq_log: dict, real_status: dict) -> str:
    md = []
    md.append("# PrithviAlert - Dataset Status Report")
    md.append(f"\n**Generated**: {date.today()}  ")
    md.append(
        "> This report compares SYNTHETIC_DEMO, MIXED_DEMO, and REAL_ONLY "
        "dataset states across the PrithviAlert pipeline."
    )
    md.append(
        "\n> [!IMPORTANT]  \n"
        "> ML model training must NOT begin until REAL_ONLY contains "
        "confirmed real landslide events."
    )

    # --- Pipeline Overview ---
    md.append("\n---\n## Pipeline Mode Overview\n")
    md.append("| Mode | Purpose | Current State |")
    md.append("|---|---|---|")

    syn_p = profiles.get("SYNTHETIC_DEMO", {})
    real_p = profiles.get("REAL_ONLY", {})

    md.append(
        f"| **SYNTHETIC_DEMO** | Baseline dev/test. All values are clearly-labelled "
        f"synthetic. | {syn_p.get('rows', 0)} rows — {syn_p.get('status', 'N/A')} |"
    )
    md.append(
        f"| **MIXED_DEMO** | Combines any available real data with synthetic fill "
        f"(labelled). | Future state (not yet built separately) |"
    )
    md.append(
        f"| **REAL_ONLY** | Only genuine observations. No synthetic fill. "
        f"ML training target. | {real_p.get('rows', 0)} real rows — {real_p.get('status', 'N/A')} |"
    )

    # --- Dataset Comparison Table ---
    md.append("\n---\n## Dataset Comparison\n")
    md.append("| Metric | SYNTHETIC_DEMO | REAL_ONLY |")
    md.append("|---|---|---|")

    def fmt(p, key, default="N/A"):
        v = p.get(key, default)
        return str(v) if v is not None else "N/A"

    metrics = [
        ("Status",           "status"),
        ("Total rows",       "rows"),
        ("Real rows",        "real_rows"),
        ("Synthetic rows",   "synthetic_rows"),
        ("Positive events",  "positive_events"),
        ("Negative samples", "negative_samples"),
        ("Feature count",    "features"),
    ]
    for label, key in metrics:
        md.append(f"| {label} | {fmt(syn_p, key)} | {fmt(real_p, key)} |")

    # --- Real Data Sources ---
    md.append("\n---\n## Real Data Sources Status\n")
    sources = acq_log.get("sources", [])
    if sources:
        md.append("| Source | Status | Records | Data Quality | Notes |")
        md.append("|---|---|---|---|---|")
        for src in sources:
            status_icon = {
                "ACQUIRED":    "[OK]",
                "PARTIAL":     "[PARTIAL]",
                "UNAVAILABLE": "[UNAVAILABLE]",
                "SKIPPED":     "[SKIPPED]",
                "ERROR":       "[ERROR]",
            }.get(src.get("status", ""), "[?]")
            notes_short = src.get("notes", "")[:80].replace("|", "/") + ("..." if len(src.get("notes", "")) > 80 else "")
            md.append(
                f"| {src.get('name', '')} | {status_icon} {src.get('status', '')} "
                f"| {src.get('records', 0)} "
                f"| {src.get('data_quality', 'N/A')} "
                f"| {notes_short} |"
            )
    else:
        md.append(
            "> [!WARNING]  \n"
            "> Real acquisition log not found. "
            "Run: `python scripts/acquire_real_data.py`"
        )

    # --- Feature Coverage ---
    md.append("\n---\n## Feature Coverage Comparison\n")
    md.append("| Feature | SYNTHETIC_DEMO coverage | REAL_ONLY coverage |")
    md.append("|---|---|---|")
    all_feats = sorted(set(
        list(syn_p.get("feature_coverage", {}).keys())
        + list(real_p.get("feature_coverage", {}).keys())
    ))
    for feat in all_feats:
        syn_cov  = syn_p.get("feature_coverage", {}).get(feat, "MISSING")
        real_cov = real_p.get("feature_coverage", {}).get(feat, "MISSING")
        syn_str  = f"{syn_cov}%" if isinstance(syn_cov, (int, float)) else str(syn_cov)
        real_str = f"{real_cov}%" if isinstance(real_cov, (int, float)) else str(real_cov)
        md.append(f"| {feat} | {syn_str} | {real_str} |")

    # --- Missing Sources for REAL_ONLY ---
    md.append("\n---\n## REAL_ONLY Missing Sources\n")
    real_missing = real_status.get("missing_features", [])
    if real_missing:
        for mf in real_missing:
            md.append(f"- {mf}")
    else:
        md.append("(Run `build_real_dataset.py` first)")

    # --- Manual Download Instructions ---
    md.append("\n---\n## How to Obtain Real Inventory Data\n")
    md.append(
        "The REAL_ONLY pipeline is blocked on the **landslide inventory**. "
        "Both COOLR and ISRO are currently unavailable programmatically."
    )
    md.append("\n### Option A — NASA COOLR (Recommended)")
    md.append(
        "1. Go to https://gpm.nasa.gov/landslides/data.html\n"
        "2. Download the **Global Landslide Catalog (GLC)** CSV\n"
        "3. Filter to NER bounding box (lat 21.9–29.5, lon 88.0–97.5)\n"
        "4. Save as `data/raw/real/real_inventory.csv`\n"
        "5. Required columns: `event_id, latitude, longitude, date, event_type, trigger, severity, state`\n"
        "6. Add columns: `data_source=nasa_coolr_real, data_quality=real, license=NASA Open Data`"
    )
    md.append("\n### Option B — ISRO/NRSC Landslide Atlas")
    md.append(
        "1. Contact NRSC: nrsc-disastermanagement@gov.in\n"
        "2. Request the NER event-level CSV from the 2023 Landslide Atlas\n"
        "3. Save as `data/raw/real/real_inventory.csv` with provenance columns"
    )

    # --- ML Training Gate ---
    md.append("\n---\n## ML Training Gate\n")
    real_ready = real_p.get("rows", 0) > 0 and real_p.get("status") == "AVAILABLE"
    md.append(
        f"**REAL_ONLY dataset ready for ML training: {'YES' if real_ready else 'NO'}**\n"
    )
    if not real_ready:
        md.append(
            "> [!CAUTION]  \n"
            "> Do NOT train Random Forest or XGBoost until REAL_ONLY contains "
            "confirmed real landslide events. Training on synthetic data only "
            "will produce misleading performance metrics."
        )
    else:
        md.append(
            "> [!IMPORTANT]  \n"
            "> Even with real data, validate that model performance is not "
            "inflated by data leakage or spatial autocorrelation before "
            "claiming scientific validity."
        )

    # --- Provenance Reminder ---
    md.append("\n---\n## Data Provenance Policy\n")
    md.append(
        "All datasets in this pipeline carry the following mandatory provenance columns:\n\n"
        "| Column | Purpose |\n|---|---|\n"
        "| `data_source` | Source identifier (e.g., `open_meteo_era5`) |\n"
        "| `data_quality` | Quality label: `real`, `reanalysis`, `simulated`, `masked` |\n"
        "| `source_url` | URL of the original data source |\n"
        "| `source_version` | Version or release date of the source |\n"
        "| `acquisition_date` | Date this pipeline fetched the data |\n"
        "| `license` | License of the source data |\n"
    )

    return "\n".join(md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("PrithviAlert Dataset Status Report")
    log.info("=" * 60)

    profiles   = {}
    for mode, path in DATASET_PATHS.items():
        log.info(f"Profiling: {mode} ({path.name})")
        profiles[mode] = profile_dataset(mode, path)

    acq_log    = load_real_acq_log()
    real_status = load_real_status()

    # --- Console output ---
    print("\n" + "=" * 60)
    print("DATASET STATUS REPORT")
    print("=" * 60)

    for mode, p in profiles.items():
        print(f"\n  [{mode}]")
        print(f"    Status:           {p.get('status', 'N/A')}")
        print(f"    Total rows:       {p.get('rows', 0)}")
        print(f"    Real rows:        {p.get('real_rows', 0)}")
        print(f"    Synthetic rows:   {p.get('synthetic_rows', 0)}")
        print(f"    Positive events:  {p.get('positive_events', 0)}")
        print(f"    Negative samples: {p.get('negative_samples', 0)}")
        print(f"    Features:         {p.get('features', 0)}")
        if p.get("notes"):
            for n in p["notes"]:
                print(f"    NOTE: {n}")

    print("\n  [REAL DATA SOURCES]")
    sources = acq_log.get("sources", [])
    if sources:
        for src in sources:
            print(f"    {src['status']:12s} {src['name']}")
            print(f"               Records: {src['records']}  Quality: {src['data_quality']}")
    else:
        print("    No acquisition log found. Run: python scripts/acquire_real_data.py")

    acq_summary = acq_log.get("summary", {})
    print("\n  [REAL ACQUISITION SUMMARY]")
    print(f"    Real landslide events:  {acq_summary.get('real_inventory_events', 'N/A')}")
    print(f"    Real rainfall records:  {acq_summary.get('real_rainfall_records', 'N/A')}")
    print(f"    Real soil records:      {acq_summary.get('real_soil_records', 'N/A')}")
    print(f"    Sources ACQUIRED:       {acq_summary.get('sources_acquired', 'N/A')}")
    print(f"    Sources UNAVAILABLE:    {acq_summary.get('sources_unavailable', 'N/A')}")

    real_p = profiles.get("REAL_ONLY", {})
    ml_ready = real_p.get("rows", 0) > 0 and real_p.get("status") == "AVAILABLE"
    print(f"\n  ML TRAINING GATE:     {'[OPEN] REAL_ONLY ready' if ml_ready else '[CLOSED] Awaiting real inventory'}")
    print("=" * 60)

    # --- Write reports ---
    report = {
        "generated":   str(date.today()),
        "profiles":    profiles,
        "real_acquisition_summary": acq_summary,
        "ml_training_gate": {
            "ready":  ml_ready,
            "reason": "REAL_ONLY dataset has confirmed real events" if ml_ready
                      else "REAL_ONLY inventory = 0. Awaiting real landslide catalog.",
        },
    }

    json_path = OUT / "dataset_status_report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    log.info(f"Status report JSON: {json_path}")

    md_path = OUT / "dataset_status_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_report_md(profiles, acq_log, real_status))
    log.info(f"Status report Markdown: {md_path}")


if __name__ == "__main__":
    main()
