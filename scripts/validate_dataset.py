"""
PrithviAlert - Dataset Validation & Status Report
===================================================
Validates BOTH raw and processed data directories.

Checks:
  RAW DATA STATUS
    - Which source directories are present
    - Record counts in each raw file

  PROCESSED DATA STATUS
    - training_dataset.csv existence and row count
    - landslide_event (ML target) presence
    - Latitude / longitude range validity
    - Missing target values
    - Duplicate canonical_event_id values
    - Numeric feature range validity
    - data_source / data_quality consistency
    - Missing value percentages per feature
    - Feature distributions (mean, std, min, max, percentiles)
    - Split sizes

Outputs:
  data/processed/validation_report.json
  data/processed/validation_report.md  (human-readable)

Usage:
  python scripts/validate_dataset.py
"""

import json
import logging
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("prithvialert.validate")

ROOT = Path(__file__).parent.parent
RAW  = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Expected raw sources — (directory_name, expected_filename)
# ---------------------------------------------------------------------------
RAW_SOURCES = {
    "isro_atlas":  ("isro_atlas",  "isro_atlas_ner.csv",          "required"),
    "nasa_coolr":  ("nasa_coolr",  "nasa_glc_ner.csv",            "required"),
    "gpm_imerg":   ("gpm_imerg",   "gpm_rainfall_features.csv",   "optional"),
    "dem":         ("dem",         "terrain_features.csv",        "optional"),
    "soilgrids":   ("soilgrids",   "soilgrids_features.csv",      "optional"),
    "sentinel2":   ("sentinel2",   "sentinel2_vegetation.csv",    "optional"),
    "sentinel1":   ("sentinel1",   "sentinel1_deformation.csv",   "optional"),
}

# Processed datasets to validate
PROCESSED_DATASETS = [
    "training_dataset", "train", "val", "test",
    "ner_dataset", "ner_train", "ner_val", "ner_test",
]

# Numeric features to check distributions
NUMERIC_FEATURES = [
    "rainfall_1h", "rainfall_6h", "rainfall_12h", "rainfall_24h",
    "rainfall_48h", "rainfall_7d", "rainfall_intensity",
    "soil_moisture", "soil_ph", "soil_organic_carbon",
    "elevation", "slope", "aspect", "curvature", "terrain_ruggedness",
    "ndvi", "ground_displacement",
    "historical_landslide_frequency", "historical_landslide_distance",
    "population_exposure", "infrastructure_exposure",
    "distance_to_road", "distance_to_river",
]

# Hard validity ranges — values outside are flagged as invalid
VALIDITY_RULES = {
    "latitude":         (-90, 90),
    "longitude":        (-180, 180),
    "rainfall_1h":      (0, 500),
    "rainfall_24h":     (0, 2000),
    "ndvi":             (-1.0, 1.0),
    "slope":            (0, 90),
    "elevation":        (-500, 9000),
    "soil_ph":          (0, 14),
    "soil_moisture":    (0, 100),
}


# ===========================================================================
# RAW DATA VALIDATION
# ===========================================================================
def validate_raw() -> dict:
    """
    Scan data/raw/ directories and report what is available.
    """
    result = {
        "raw_dir": str(RAW),
        "sources": {},
        "found_required": [],
        "missing_required": [],
        "found_optional": [],
        "missing_optional": [],
    }

    for key, (dir_name, filename, requirement) in RAW_SOURCES.items():
        dir_path  = RAW / dir_name
        file_path = dir_path / filename

        entry = {
            "directory":   str(dir_path),
            "file":        str(file_path),
            "dir_exists":  dir_path.exists(),
            "file_exists": file_path.exists(),
            "requirement": requirement,
            "record_count": None,
            "columns":     None,
            "status":      None,
        }

        if file_path.exists():
            try:
                df = pd.read_csv(file_path, nrows=5)
                # Get total line count efficiently
                with open(file_path, "r", encoding="utf-8") as fh:
                    n_lines = sum(1 for _ in fh) - 1  # subtract header
                entry["record_count"] = n_lines
                entry["columns"]      = list(df.columns)
                entry["status"]       = "FOUND"
                if requirement == "required":
                    result["found_required"].append(key)
                else:
                    result["found_optional"].append(key)
            except Exception as e:
                entry["status"] = f"ERROR: {e}"
        else:
            entry["status"] = "MISSING"
            if requirement == "required":
                result["missing_required"].append(key)
            else:
                result["missing_optional"].append(key)

        result["sources"][key] = entry

    return result


# ===========================================================================
# PROCESSED DATA VALIDATION
# ===========================================================================
def load_processed_datasets() -> dict:
    datasets = {}
    for name in PROCESSED_DATASETS:
        p = PROC / f"{name}.csv"
        if p.exists():
            try:
                datasets[name] = pd.read_csv(p, parse_dates=["date"])
            except Exception as e:
                log.warning(f"Could not read {p}: {e}")
    return datasets


def missing_value_report(df: pd.DataFrame) -> dict:
    total = len(df)
    missing = {}
    for col in df.columns:
        n_miss = int(df[col].isna().sum())
        missing[col] = {
            "count": n_miss,
            "pct":   round(100.0 * n_miss / total, 2) if total > 0 else 0,
        }
    return missing


def validity_checks(df: pd.DataFrame) -> dict:
    issues = {}
    for col, (lo, hi) in VALIDITY_RULES.items():
        if col not in df.columns:
            continue
        col_numeric = pd.to_numeric(df[col], errors="coerce")
        n_invalid = int(((col_numeric < lo) | (col_numeric > hi)).sum())
        if n_invalid > 0:
            issues[col] = {"invalid_count": n_invalid, "expected_range": [lo, hi]}
    return issues


def check_missing_target(df: pd.DataFrame) -> dict:
    if "landslide_event" not in df.columns:
        return {"present": False, "missing_count": len(df), "note": "Column absent"}
    n_missing = int(df["landslide_event"].isna().sum())
    return {
        "present":       True,
        "missing_count": n_missing,
        "valid":         n_missing == 0,
    }


def duplicate_event_id_check(df: pd.DataFrame) -> dict:
    if "canonical_event_id" not in df.columns:
        return {"checked": False, "note": "canonical_event_id column not present"}
    n_dupes = int(df["canonical_event_id"].duplicated().sum())
    return {"checked": True, "duplicate_event_ids": n_dupes, "valid": n_dupes == 0}


def source_quality_consistency(df: pd.DataFrame) -> dict:
    """
    Verify that data_source and data_quality columns are present and non-null.
    """
    issues = []
    for col in ["data_source", "data_quality"]:
        if col not in df.columns:
            issues.append(f"Column '{col}' missing entirely")
        else:
            n_null = int(df[col].isna().sum())
            if n_null > 0:
                issues.append(f"'{col}' has {n_null} null values")
    return {"issues": issues, "valid": len(issues) == 0}


def duplicate_row_check(df: pd.DataFrame) -> dict:
    key_cols = [c for c in ["latitude", "longitude", "date", "landslide_event"] if c in df.columns]
    n_dupes  = int(df.duplicated(subset=key_cols).sum())
    return {"duplicate_rows": n_dupes, "key_cols": key_cols}


def class_balance(df: pd.DataFrame) -> dict:
    if "landslide_event" not in df.columns:
        return {}
    n_pos = int(df["landslide_event"].sum())
    n_neg = int((df["landslide_event"] == 0).sum())
    return {
        "positive":      n_pos,
        "negative":      n_neg,
        "ratio_pos_neg": round(n_pos / n_neg, 3) if n_neg > 0 else None,
    }


def records_by_state(df: pd.DataFrame) -> dict:
    if "state" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["state"].value_counts().items()}


def records_by_year(df: pd.DataFrame) -> dict:
    if "date" not in df.columns:
        return {}
    return {
        str(int(k)): int(v)
        for k, v in df["date"].dt.year.value_counts().sort_index().items()
        if pd.notna(k)
    }


def records_by_source(df: pd.DataFrame) -> dict:
    if "data_source" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["data_source"].value_counts().items()}


def feature_distributions(df: pd.DataFrame) -> dict:
    stats = {}
    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            stats[col] = {"count": 0, "all_missing": True}
            continue
        stats[col] = {
            "count":       int(s.count()),
            "mean":        round(float(s.mean()), 4),
            "std":         round(float(s.std()), 4),
            "min":         round(float(s.min()), 4),
            "p25":         round(float(s.quantile(0.25)), 4),
            "p50":         round(float(s.median()), 4),
            "p75":         round(float(s.quantile(0.75)), 4),
            "max":         round(float(s.max()), 4),
            "missing_pct": round(100.0 * df[col].isna().sum() / len(df), 2),
        }
    return stats


def validate_one_processed(name: str, df: pd.DataFrame) -> dict:
    log.info(f"  Validating: {name} ({len(df)} records)")
    target_check   = check_missing_target(df)
    event_id_check = duplicate_event_id_check(df)
    sq_check       = source_quality_consistency(df)

    # Count invalid records (rows failing any validity rule)
    all_invalid_rows = set()
    val_issues = validity_checks(df)
    for col, info in val_issues.items():
        if col in df.columns:
            col_numeric = pd.to_numeric(df[col], errors="coerce")
            lo, hi = VALIDITY_RULES[col]
            bad_idx = df.index[(col_numeric < lo) | (col_numeric > hi)].tolist()
            all_invalid_rows.update(bad_idx)

    return {
        "total_records":          len(df),
        "columns":                len(df.columns),
        "class_balance":          class_balance(df),
        "by_state":               records_by_state(df),
        "by_year":                records_by_year(df),
        "by_source":              records_by_source(df),
        "missing_values":         missing_value_report(df),
        "validity_issues":        val_issues,
        "invalid_record_count":   len(all_invalid_rows),
        "target_check":           target_check,
        "event_id_duplicates":    event_id_check,
        "source_quality_check":   sq_check,
        "duplicate_rows":         duplicate_row_check(df),
        "feature_distributions":  feature_distributions(df),
    }


# ===========================================================================
# Markdown report
# ===========================================================================
def generate_md_report(report: dict) -> str:
    md = []
    md.append("# PrithviAlert — Dataset Validation Report\n")
    md.append(f"**Generated**: {report['generated']}\n")
    md.append(
        "> PROTOTYPE: Models trained on this data are NOT scientifically "
        "validated for operational use.\n"
    )

    # --- RAW DATA STATUS ---
    md.append("\n---\n## RAW DATA STATUS\n")
    raw = report.get("raw_data", {})
    md.append(f"Raw data directory: `{raw.get('raw_dir', 'N/A')}`\n")
    md.append("| Source | Requirement | File | Records | Status |")
    md.append("|---|---|---|---|---|")
    for key, info in raw.get("sources", {}).items():
        records = info.get("record_count", "—")
        md.append(
            f"| {key} | {info['requirement']} | "
            f"`{Path(info['file']).name}` | {records} | {info['status']} |"
        )

    required_ok = len(raw.get("missing_required", [])) == 0
    md.append(f"\n**Required sources**: {'✅ All present' if required_ok else '❌ MISSING: ' + ', '.join(raw.get('missing_required', []))}")
    md.append(f"\n**Optional missing**: {', '.join(raw.get('missing_optional', [])) or 'None'}\n")

    # --- PROCESSED DATA STATUS ---
    md.append("\n---\n## PROCESSED DATA STATUS\n")
    proc = report.get("processed_data", {})
    if not proc.get("available"):
        md.append(
            "> ⚠️ **No processed datasets found.**  \n"
            "> Run `python scripts/prepare_training_data.py` to create them.\n"
        )
    else:
        md.append("| Dataset | Records | Positive | Negative | Invalid | Duplicate IDs |")
        md.append("|---|---|---|---|---|---|")
        for name, stats in proc.get("datasets", {}).items():
            cb     = stats.get("class_balance", {})
            pos    = cb.get("positive", "—")
            neg    = cb.get("negative", "—")
            inv    = stats.get("invalid_record_count", 0)
            eid_d  = stats.get("event_id_duplicates", {}).get("duplicate_event_ids", "—")
            md.append(f"| {name} | {stats['total_records']} | {pos} | {neg} | {inv} | {eid_d} |")

        main = proc.get("datasets", {}).get("training_dataset", {})
        if main:
            md.append("\n### Full Dataset — Records by State\n")
            md.append("| State | Records |")
            md.append("|---|---|")
            for state, count in sorted(
                main.get("by_state", {}).items(), key=lambda x: -x[1]
            ):
                md.append(f"| {state} | {count} |")

            md.append("\n### Full Dataset — Records by Source\n")
            md.append("| Source | Records |")
            md.append("|---|---|")
            for src, count in sorted(
                main.get("by_source", {}).items(), key=lambda x: -x[1]
            ):
                md.append(f"| {src} | {count} |")

            md.append("\n### Missing Values (columns with > 0% missing)\n")
            md.append("| Feature | Missing Count | Missing % |")
            md.append("|---|---|---|")
            flagged = [
                (c, v)
                for c, v in main.get("missing_values", {}).items()
                if v["pct"] > 0
            ]
            flagged.sort(key=lambda x: -x[1]["pct"])
            for col, v in flagged[:30]:
                md.append(f"| {col} | {v['count']} | {v['pct']}% |")

            md.append("\n### Validity Issues\n")
            issues = main.get("validity_issues", {})
            if issues:
                for col, v in issues.items():
                    md.append(
                        f"- **{col}**: {v['invalid_count']} values "
                        f"outside {v['expected_range']}"
                    )
            else:
                md.append("No validity issues detected.")

            md.append("\n### Feature Distributions\n")
            md.append("| Feature | Mean | Std | Min | P50 | Max | Missing% |")
            md.append("|---|---|---|---|---|---|---|")
            dists = main.get("feature_distributions", {})
            for feat in [
                "rainfall_24h", "slope", "elevation",
                "ndvi", "soil_moisture", "ground_displacement",
            ]:
                if feat in dists and not dists[feat].get("all_missing"):
                    d = dists[feat]
                    md.append(
                        f"| {feat} | {d['mean']} | {d['std']} | "
                        f"{d['min']} | {d['p50']} | {d['max']} | {d['missing_pct']}% |"
                    )

        md.append("\n### Assumptions & Limitations\n")
        md.append(
            "- All current inventory data is **synthetic/simulated** "
            "(labelled `data_quality=simulated`)\n"
        )
        md.append("- Temporal split: TRAIN ≤ 2019, VAL 2020–2021, TEST ≥ 2022\n")
        md.append("- Models trained on this data are **research prototypes only**\n")

    return "\n".join(md)


# ===========================================================================
# Main
# ===========================================================================
def main():
    import sys
    # Ensure UTF-8 output on Windows terminals that default to cp1252
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    log.info("=" * 60)
    log.info("PrithviAlert Dataset Validation")
    log.info("=" * 60)

    report = {
        "generated":        str(date.today()),
        "pipeline_version": "0.1.0-prototype",
    }

    # -------------------------------------------------------------------------
    # RAW DATA STATUS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("RAW DATA STATUS")
    print("=" * 60)

    raw_result = validate_raw()
    report["raw_data"] = raw_result

    for key, info in raw_result["sources"].items():
        status_str = f"{'[FOUND]' if info['status'] == 'FOUND' else '[MISSING]':10s}"
        req_str    = f"({info['requirement']})"
        count_str  = f"  {info['record_count']} records" if info["record_count"] else ""
        print(f"  {status_str} {key:20s} {req_str:12s}{count_str}")

    print()
    if raw_result["missing_required"]:
        print(f"  [FAIL] REQUIRED sources missing: {', '.join(raw_result['missing_required'])}")
    else:
        print("  [OK]   All required raw sources present")

    if raw_result["missing_optional"]:
        print(f"  [WARN] Optional sources unavailable: {', '.join(raw_result['missing_optional'])}")
    else:
        print("  [OK]   All optional raw sources present")

    # -------------------------------------------------------------------------
    # PROCESSED DATA STATUS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PROCESSED DATA STATUS")
    print("=" * 60)

    proc_datasets = load_processed_datasets()

    if not proc_datasets:
        print("  [WARN] No processed datasets found.")
        print("  Run: python scripts/prepare_training_data.py")
        print()
        report["processed_data"] = {"available": False}
    else:
        report["processed_data"] = {"available": True, "datasets": {}}

        for name, df in proc_datasets.items():
            ds_report = validate_one_processed(name, df)
            report["processed_data"]["datasets"][name] = ds_report

        # Print summary for training_dataset
        main_ds = report["processed_data"]["datasets"].get("training_dataset", {})
        if main_ds:
            cb           = main_ds.get("class_balance", {})
            target_chk   = main_ds.get("target_check", {})
            eid_chk      = main_ds.get("event_id_duplicates", {})
            sq_chk       = main_ds.get("source_quality_check", {})
            dupe_rows    = main_ds.get("duplicate_rows", {}).get("duplicate_rows", 0)
            invalid_recs = main_ds.get("invalid_record_count", 0)
            missing_vals = main_ds.get("missing_values", {})
            avg_miss     = (
                np.mean([v["pct"] for v in missing_vals.values()])
                if missing_vals else 0
            )

            # Load manifest if it exists
            manifest_path = PROC / "processing_manifest.json"
            manifest_data = {}
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest_data = json.load(f)

            real_rows      = manifest_data.get("real_record_count", "N/A")
            synth_rows     = manifest_data.get("synthetic_record_count", "N/A")
            missing_srcs   = manifest_data.get("missing_sources", [])
            pipeline_mode  = manifest_data.get("mode", "N/A")

            print(f"  Pipeline mode:       {pipeline_mode}")
            print(f"  Total rows:          {main_ds.get('total_records', 0)}")
            print(f"  Total features:      {main_ds.get('columns', 0)}")
            print(f"  Positive (landslide):{cb.get('positive', 0)}")
            print(f"  Negative (non-event):{cb.get('negative', 0)}")
            print(f"  Pos/Neg ratio:       {cb.get('ratio_pos_neg', 0)}")
            print(f"  Real rows:           {real_rows}")
            print(f"  Synthetic rows:      {synth_rows}")
            print(f"  Missing sources:     {len(missing_srcs)}")
            for ms in missing_srcs:
                print(f"    - {ms['name']}: {ms['reason']}")
            print()
            print("  --- Integrity Checks ---")
            print(
                f"  Target (landslide_event) present: "
                f"{'[OK]' if target_chk.get('present') else '[FAIL]'}"
            )
            print(
                f"  Missing target values: "
                f"{'[OK] 0' if target_chk.get('missing_count', 1) == 0 else '[FAIL] ' + str(target_chk.get('missing_count'))}"
            )
            print(
                f"  Duplicate event IDs: "
                f"{'[OK] 0' if eid_chk.get('duplicate_event_ids', 1) == 0 else '[FAIL] ' + str(eid_chk.get('duplicate_event_ids'))}"
            )
            print(
                f"  Duplicate rows:      "
                f"{'[OK] 0' if dupe_rows == 0 else '[WARN] ' + str(dupe_rows)}"
            )
            print(
                f"  Invalid records:     "
                f"{'[OK] 0' if invalid_recs == 0 else '[WARN] ' + str(invalid_recs)}"
            )
            print(
                f"  Source/quality cols: "
                f"{'[OK] consistent' if sq_chk.get('valid') else '[FAIL] ' + '; '.join(sq_chk.get('issues', []))}"
            )
            print(f"  Avg missing %:       {round(avg_miss, 2)}%")

            # Overall status
            checks_ok = (
                target_chk.get("present")
                and target_chk.get("missing_count", 1) == 0
                and eid_chk.get("duplicate_event_ids", 1) == 0
                and sq_chk.get("valid")
            )
            print()
            print(
                f"  VALIDATION STATUS:   {'[PASSED]' if checks_ok else '[FAILED] (see above)'}"
            )

        # Write JSON report
        PROC.mkdir(parents=True, exist_ok=True)
        json_path = PROC / "validation_report.json"
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        log.info(f"Validation JSON saved: {json_path}")

        # Write Markdown report
        md_path = PROC / "validation_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(generate_md_report(report))
        log.info(f"Validation Markdown saved: {md_path}")

    print("=" * 60)


if __name__ == "__main__":
    main()
