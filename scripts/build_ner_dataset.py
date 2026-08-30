"""
PrithviAlert — NER Dataset Builder
=====================================
Filters, resamples, and enriches the full dataset for a
North East Region (NER)-focused training experiment.

Outputs:
  data/processed/ner_train.csv
  data/processed/ner_val.csv
  data/processed/ner_test.csv

Usage:
  python scripts/build_ner_dataset.py
"""

import json
import logging
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("prithvialert.ner")

ROOT = Path(__file__).parent.parent
PROC = ROOT / "data" / "processed"

NER_STATES = [
    "Arunachal Pradesh","Assam","Manipur","Meghalaya",
    "Mizoram","Nagaland","Sikkim","Tripura",
]

# NER bounding box for fallback spatial filter
NER_BBOX = dict(lat_min=21.9, lat_max=29.5, lon_min=88.0, lon_max=97.5)

# Priority states (higher resampling weight)
PRIORITY_STATES = {
    "Sikkim": 2.0,
    "Arunachal Pradesh": 1.8,
    "Mizoram": 1.6,
    "Meghalaya": 1.5,
    "Nagaland": 1.4,
    "Manipur": 1.4,
    "Assam": 1.2,
    "Tripura": 1.2,
}


def filter_ner(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep records in NER by:
    1. State name match
    2. Bounding box fallback for records with missing state
    """
    state_match = df["state"].isin(NER_STATES)
    bbox_match  = (
        df["latitude"].between(NER_BBOX["lat_min"], NER_BBOX["lat_max"]) &
        df["longitude"].between(NER_BBOX["lon_min"], NER_BBOX["lon_max"])
    )
    ner_mask = state_match | bbox_match
    ner_df = df[ner_mask].copy()
    log.info(f"NER filter: {ner_mask.sum()} / {len(df)} records kept (state: {state_match.sum()}, bbox-only: {(bbox_match & ~state_match).sum()})")
    return ner_df


def add_state_weights(df: pd.DataFrame) -> pd.DataFrame:
    df["sampling_weight"] = df["state"].map(PRIORITY_STATES).fillna(1.0)
    return df


def report_ner_stats(df: pd.DataFrame):
    log.info("=== NER Dataset Statistics ===")
    log.info(f"Total records: {len(df)}")
    log.info(f"Positive events: {int(df['landslide_event'].sum())}")
    log.info(f"Negative samples: {int((df['landslide_event'] == 0).sum())}")

    by_state = df.groupby("state").agg(
        total=("landslide_event","count"),
        positives=("landslide_event","sum"),
    ).sort_values("total", ascending=False)
    log.info(f"\nBy state:\n{by_state.to_string()}")


def main():
    full_path = PROC / "training_dataset.csv"
    if not full_path.exists():
        raise RuntimeError("training_dataset.csv not found. Run prepare_training_data.py first.")

    df = pd.read_csv(full_path, parse_dates=["date"])
    log.info(f"Loaded {len(df)} records from full training dataset")

    ner = filter_ner(df)
    ner = add_state_weights(ner)

    report_ner_stats(ner)

    # Temporal split (same boundaries as global)
    train = ner[ner["date"].dt.year <= 2019].copy()
    val   = ner[(ner["date"].dt.year >= 2020) & (ner["date"].dt.year <= 2021)].copy()
    test  = ner[ner["date"].dt.year >= 2022].copy()

    train["split"] = "train"
    val["split"]   = "validation"
    test["split"]  = "test"

    ner_all_path   = PROC / "ner_dataset.csv"
    train_path     = PROC / "ner_train.csv"
    val_path       = PROC / "ner_val.csv"
    test_path      = PROC / "ner_test.csv"

    ner.to_csv(ner_all_path, index=False)
    train.to_csv(train_path, index=False)
    val.to_csv(val_path, index=False)
    test.to_csv(test_path, index=False)

    ner_report = {
        "dataset": "NER",
        "states": NER_STATES,
        "split_method": "temporal",
        "train_years": "≤ 2019",
        "val_years": "2020–2021",
        "test_years": "≥ 2022",
        "ner_total": len(ner),
        "ner_train": len(train),
        "ner_val": len(val),
        "ner_test": len(test),
        "ner_positive": int(ner["landslide_event"].sum()),
        "ner_negative": int((ner["landslide_event"] == 0).sum()),
        "priority_weights": PRIORITY_STATES,
        "generated": str(date.today()),
    }
    with open(PROC / "ner_report.json", "w") as f:
        json.dump(ner_report, f, indent=2)

    log.info(f"NER dataset: {len(ner)} records → {ner_all_path}")
    log.info(f"NER TRAIN: {len(train)} | VAL: {len(val)} | TEST: {len(test)}")


if __name__ == "__main__":
    main()
