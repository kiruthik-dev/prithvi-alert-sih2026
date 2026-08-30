import pickle
import numpy as np
import pandas as pd
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper to get the correct path regardless of where the script is run from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load models and preprocessor
with open(os.path.join(BASE_DIR, 'models/xgboost_model.pkl'), 'rb') as f:
    xgb_model = pickle.load(f)

with open(os.path.join(BASE_DIR, 'models/rf_model.pkl'), 'rb') as f:
    rf_model = pickle.load(f)

with open(os.path.join(BASE_DIR, 'data/interim/preprocessor.pkl'), 'rb') as f:
    preprocessor = pickle.load(f)

with open(os.path.join(BASE_DIR, 'data/interim/feature_cols.pkl'), 'rb') as f:
    feature_cols = pickle.load(f)

logger.info("Models loaded successfully")

def calculate_risk_level(risk_score):
    if risk_score >= 81:
        return "CRITICAL"
    elif risk_score >= 61:
        return "VERY HIGH"
    elif risk_score >= 41:
        return "HIGH"
    elif risk_score >= 21:
        return "MODERATE"
    return "LOW"

def predict_risk(features_dict):
    """
    Predict landslide risk probability and calculate a risk score.
    Returns: dict with risk_score, risk_level, and model agreement (confidence).
    """
    try:
        # Construct DataFrame to pass to sklearn ColumnTransformer
        df_input = pd.DataFrame([features_dict])
        
        # Ensure all expected columns exist and cast to numeric
        for col in feature_cols:
            if col not in df_input.columns:
                df_input[col] = np.nan
            else:
                df_input[col] = pd.to_numeric(df_input[col], errors='coerce')
                
        # Transform using the saved pipeline
        feature_scaled = preprocessor.transform(df_input)
        
        # Get probability of class 1 (landslide)
        prob_xgb = xgb_model.predict_proba(feature_scaled)[0][1]
        prob_rf = rf_model.predict_proba(feature_scaled)[0][1]
        
        # Ensemble Probability
        ensemble_prob = (prob_xgb + prob_rf) / 2.0
        
        # Risk Score is just probability mapped to 0-100
        risk_score = ensemble_prob * 100
        
        # Confidence logic: if models agree closely, confidence is higher
        prob_std = np.std([prob_xgb, prob_rf])
        # simple heuristic: 1 - standard deviation (clamped to 0.5-1.0 range)
        calculated_confidence = max(0.5, 1.0 - (prob_std * 2))
        
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": calculate_risk_level(risk_score),
            "confidence": round(calculated_confidence, 2),
            "model_ensemble": ["XGBoost Classifier", "Random Forest Classifier"],
            "ensemble_probability": ensemble_prob
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise

if __name__ == '__main__':
    # Test prediction
    test_features = {
        'rainfall_24h': 145,
        'soil_moisture': 82,
        'slope': 38,
        'elevation': 2500,
        'ground_displacement': 5,
        'land_cover': 'forest'
    }
    
    res = predict_risk(test_features)
    logger.info(f"Test prediction: {res}")
