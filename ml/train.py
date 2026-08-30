import numpy as np
import pickle
import logging
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load prepared data
X_train = np.load('data/interim/X_train.npy')
y_train = np.load('data/interim/y_train.npy')

with open('data/interim/feature_cols.pkl', 'rb') as f:
    feature_cols = pickle.load(f)

# The preprocessor output shape may be larger due to OneHotEncoding.
# If we need exact feature names, we can extract from preprocessor, but let's just train.
with open('data/interim/preprocessor.pkl', 'rb') as f:
    preprocessor = pickle.load(f)

# Extract generated feature names from preprocessor for feature importance
try:
    processed_feature_names = preprocessor.get_feature_names_out()
except Exception:
    processed_feature_names = [f"Feature_{i}" for i in range(X_train.shape[1])]

logger.info(f"Training data shape: {X_train.shape}")
logger.info(f"Target shape: {y_train.shape}")

# ============================================
# MODEL 1: XGBoost Classifier
# ============================================
logger.info("Training XGBoost Classifier...")

xgb_model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    use_label_encoder=False,
    eval_metric='logloss'
)

xgb_model.fit(X_train, y_train)

# Save model
with open('models/xgboost_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
logger.info("XGBoost model saved to models/xgboost_model.pkl")

# Feature importance
xgb_importance = pd.DataFrame({
    'feature': processed_feature_names,
    'importance': xgb_model.feature_importances_
}).sort_values('importance', ascending=False)
logger.info(f"\nXGBoost Top Important Features:\n{xgb_importance.head()}")

# ============================================
# MODEL 2: Random Forest Classifier
# ============================================
logger.info("\nTraining Random Forest Classifier...")

rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
    verbose=0
)

rf_model.fit(X_train, y_train)

# Save model
with open('models/rf_model.pkl', 'wb') as f:
    pickle.dump(rf_model, f)
logger.info("Random Forest model saved to models/rf_model.pkl")

# Feature importance
rf_importance = pd.DataFrame({
    'feature': processed_feature_names,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)

# ============================================
# Save Feature Importance
# ============================================
xgb_importance.to_csv('models/xgboost_feature_importance.csv', index=False)
rf_importance.to_csv('models/rf_feature_importance.csv', index=False)

logger.info("Training complete!")
