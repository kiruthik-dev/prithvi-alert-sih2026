import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load dataset
df = pd.read_csv('../data/processed/training_dataset.csv')

logger.info(f"Dataset shape: {df.shape}")
logger.info(f"Columns: {df.columns.tolist()}")

TARGET_COL = 'landslide_event'
GROUP_COL = 'canonical_event_id'

# Ensure target exists and is binary
if TARGET_COL not in df.columns:
    raise ValueError(f"Target column {TARGET_COL} missing from dataset.")

# Select Features
exclude_cols = [TARGET_COL, 'id', 'timestamp', 'date', 'geometry', 'district', 'state', 'location', GROUP_COL, 'risk_score', 'canonical_event_id']

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

# We just use numeric features for XGBoost / RF
FEATURE_COLS = [c for c in numeric_cols if c not in exclude_cols]

logger.info(f"Numeric features ({len(FEATURE_COLS)}): {FEATURE_COLS}")

# Prepare X, y, and groups
X = df[FEATURE_COLS]
y = df[TARGET_COL].astype(int)
groups = df[GROUP_COL]

logger.info(f"Features shape: {X.shape}")
logger.info(f"Target distribution:\n{y.value_counts(normalize=True)}")

# Grouped Train/test split (80/20) to prevent event-based spatial leakage
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=groups))

X_train = X.iloc[train_idx]
y_train = y.iloc[train_idx]
X_test = X.iloc[test_idx]
y_test = y.iloc[test_idx]

logger.info(f"Train set: {X_train.shape[0]} samples, {len(X_train[GROUP_COL].unique()) if GROUP_COL in X_train else '?'} events")
logger.info(f"Test set: {X_test.shape[0]} samples, {len(X_test[GROUP_COL].unique()) if GROUP_COL in X_test else '?'} events")

# Preprocessing Pipeline
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, FEATURE_COLS)
    ])

# Fit on training data ONLY
X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# Save for training
np.save('data/interim/X_train.npy', X_train_processed)
np.save('data/interim/X_test.npy', X_test_processed)
np.save('data/interim/y_train.npy', y_train.values)
np.save('data/interim/y_test.npy', y_test.values)

with open('data/interim/feature_cols.pkl', 'wb') as f:
    pickle.dump(FEATURE_COLS, f)

with open('data/interim/preprocessor.pkl', 'wb') as f:
    pickle.dump(preprocessor, f)

# Save metadata
metadata = {
    "model_version": "1.0",
    "training_timestamp": pd.Timestamp.now(tz='UTC').isoformat(),
    "dataset_version": "synthetic_v1",
    "target": TARGET_COL,
    "feature_count": X_train_processed.shape[1],
    "training_rows": int(X_train.shape[0]),
    "validation_rows": 0,
    "test_rows": int(X_test.shape[0]),
    "source_type": "SYNTHETIC DEMO DATA",
    "model_type": "Classification Ensemble (XGBoost + RF)",
    "preprocessing_version": "1.0"
}
import json
with open('models/model_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

logger.info("Data preparation complete. Preprocessor and arrays saved.")
