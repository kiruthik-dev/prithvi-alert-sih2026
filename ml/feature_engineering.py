"""
PrithviAlert — Feature Engineering
=====================================
Defines the feature set, transformations, and encoding used in model training.

All transformations are defined here so they can be applied consistently
across train/val/test and at inference time.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

log = logging.getLogger("prithvialert.features")

# ---------------------------------------------------------------------------
# Feature groups
# ---------------------------------------------------------------------------
RAINFALL_FEATURES = [
    "rainfall_1h", "rainfall_6h", "rainfall_12h", "rainfall_24h",
    "rainfall_48h", "rainfall_7d", "rainfall_intensity",
]

TERRAIN_FEATURES = [
    "elevation", "slope", "aspect", "curvature", "terrain_ruggedness",
]

SOIL_FEATURES = [
    "soil_moisture", "soil_ph", "soil_organic_carbon",
]

VEGETATION_FEATURES = [
    "ndvi",
]

DEFORMATION_FEATURES = [
    "ground_displacement",
]

HISTORICAL_FEATURES = [
    "historical_landslide_frequency", "historical_landslide_distance",
]

EXPOSURE_FEATURES = [
    "population_exposure", "infrastructure_exposure",
    "distance_to_road", "distance_to_river",
]

CATEGORICAL_FEATURES = [
    "soil_texture", "land_cover",
]

# Ordered by importance for model training
ALL_NUMERIC_FEATURES = (
    RAINFALL_FEATURES + TERRAIN_FEATURES + SOIL_FEATURES +
    VEGETATION_FEATURES + DEFORMATION_FEATURES + HISTORICAL_FEATURES +
    EXPOSURE_FEATURES
)

TARGET = "landslide_event"

# Numeric fill values (median-fill strategy — avoids mean-shift on skewed data)
FILL_STRATEGY = {
    "rainfall_1h": 0.0,
    "rainfall_6h": 0.0,
    "rainfall_12h": 0.0,
    "rainfall_24h": 0.0,
    "rainfall_48h": 0.0,
    "rainfall_7d": 0.0,
    "rainfall_intensity": 0.0,
    "elevation": 500.0,
    "slope": 20.0,
    "aspect": 180.0,
    "curvature": 0.0,
    "terrain_ruggedness": 50.0,
    "soil_moisture": 50.0,
    "soil_ph": 5.5,
    "soil_organic_carbon": 20.0,
    "ndvi": 0.4,
    "ground_displacement": 5.0,
    "historical_landslide_frequency": 0,
    "historical_landslide_distance": 50.0,
    "population_exposure": 500.0,
    "infrastructure_exposure": 5.0,
    "distance_to_road": 3.0,
    "distance_to_river": 2.0,
}


# ---------------------------------------------------------------------------
# Engineered features
# ---------------------------------------------------------------------------
def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that are physically motivated."""
    df = df.copy()

    # Antecedent moisture index (weighted sum of prior rainfall windows)
    if "rainfall_7d" in df.columns and "rainfall_24h" in df.columns:
        df["antecedent_moisture_index"] = (
            0.4 * df["rainfall_24h"].fillna(0) +
            0.3 * df["rainfall_48h"].fillna(0) +
            0.3 * df["rainfall_7d"].fillna(0)
        )

    # Slope × rainfall interaction (high slope + high rain = higher risk)
    if "slope" in df.columns and "rainfall_24h" in df.columns:
        df["slope_rain_interaction"] = (
            df["slope"].fillna(20) * np.log1p(df["rainfall_24h"].fillna(0))
        )

    # NDVI deficit (1 - NDVI as bare soil proxy)
    if "ndvi" in df.columns:
        df["ndvi_deficit"] = 1.0 - df["ndvi"].fillna(0.4)

    # Log-transformed distance to historical events
    if "historical_landslide_distance" in df.columns:
        df["log_hist_distance"] = np.log1p(df["historical_landslide_distance"].fillna(50))

    # Terrain instability index (slope / (1 + terrain_ruggedness) proxy)
    if "slope" in df.columns and "terrain_ruggedness" in df.columns:
        df["terrain_instability"] = df["slope"].fillna(20) / (1 + df["terrain_ruggedness"].fillna(50))

    return df


ENGINEERED_FEATURES = [
    "antecedent_moisture_index",
    "slope_rain_interaction",
    "ndvi_deficit",
    "log_hist_distance",
    "terrain_instability",
]


def encode_categoricals(df: pd.DataFrame, fit: bool = True,
                         encoders: dict = None) -> tuple:
    """
    Label-encode categorical features.
    Returns (encoded_df, encoders_dict)
    """
    df = df.copy()
    if encoders is None:
        encoders = {}

    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            continue
        df[col] = df[col].fillna("unknown").astype(str)
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
        else:
            le = encoders.get(col)
            if le:
                known = set(le.classes_)
                df[col] = df[col].apply(lambda x: x if x in known else "unknown")
                df[col] = le.transform(df[col])
            else:
                df[col] = 0

    return df, encoders


def get_feature_matrix(df: pd.DataFrame, fit: bool = True,
                        encoders: dict = None) -> tuple:
    """
    Build the full feature matrix X and label vector y.

    1. Add engineered features
    2. Fill missing values
    3. Encode categoricals
    4. Return X (DataFrame), y (Series), encoders
    """
    df = add_engineered_features(df)

    all_features = ALL_NUMERIC_FEATURES + ENGINEERED_FEATURES + CATEGORICAL_FEATURES
    available_features = [f for f in all_features if f in df.columns]

    # Fill missing values
    for col in available_features:
        if col in df.columns:
            fill_val = FILL_STRATEGY.get(col, df[col].median() if df[col].dtype != object else "unknown")
            df[col] = df[col].fillna(fill_val)

    df, encoders = encode_categoricals(df, fit=fit, encoders=encoders)

    X = df[available_features]
    y = df[TARGET] if TARGET in df.columns else None

    log.info(f"Feature matrix: {X.shape[0]} rows × {X.shape[1]} features")
    return X, y, encoders, available_features
