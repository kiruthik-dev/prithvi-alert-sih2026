import numpy as np
import pickle
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, 
    confusion_matrix, average_precision_score
)
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load test data
X_test = np.load('data/interim/X_test.npy')
y_test = np.load('data/interim/y_test.npy')

# Load models
with open('models/xgboost_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

with open('models/rf_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

# Predictions
y_pred_xgb = xgb_model.predict(X_test)
y_prob_xgb = xgb_model.predict_proba(X_test)[:, 1]

y_pred_rf = rf_model.predict(X_test)
y_prob_rf = rf_model.predict_proba(X_test)[:, 1]

# ============================================
# EVALUATION METRICS
# ============================================

def evaluate_model(y_true, y_pred, y_prob, model_name):
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluation: {model_name}")
    logger.info(f"{'='*60}")
    
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # Only calculate AUC if both classes exist in test set
    if len(np.unique(y_true)) > 1:
        roc_auc = roc_auc_score(y_true, y_prob)
        pr_auc = average_precision_score(y_true, y_prob)
    else:
        roc_auc = 0.0
        pr_auc = 0.0
        
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0,0,0,0)
    
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    logger.info(f"Precision:         {precision:.4f}")
    logger.info(f"Recall:            {recall:.4f}")
    logger.info(f"F1 Score:          {f1:.4f}")
    logger.info(f"ROC-AUC:           {roc_auc:.4f}")
    logger.info(f"PR-AUC:            {pr_auc:.4f}")
    logger.info(f"False Neg Rate:    {fnr:.4f}")
    logger.info(f"Confusion Matrix:\n{cm}")
    
    return {
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'roc_auc': float(roc_auc),
        'pr_auc': float(pr_auc),
        'fnr': float(fnr),
        'confusion_matrix': cm.tolist()
    }

xgb_metrics = evaluate_model(y_test, y_pred_xgb, y_prob_xgb, "XGBoost")
rf_metrics = evaluate_model(y_test, y_pred_rf, y_prob_rf, "Random Forest")

# ============================================
# COMPARISON
# ============================================
logger.info(f"\n{'='*60}")
logger.info("MODEL COMPARISON")
logger.info(f"{'='*60}")
logger.info(f"XGBoost F1: {xgb_metrics['f1']:.4f}")
logger.info(f"RF F1:      {rf_metrics['f1']:.4f}")
logger.info(f"Winner:     {'XGBoost' if xgb_metrics['f1'] > rf_metrics['f1'] else 'Random Forest'}")

# ============================================
# SAVE RESULTS
# ============================================
results = {
    'xgboost': xgb_metrics,
    'random_forest': rf_metrics,
    'test_size': len(y_test),
    'timestamp': pd.Timestamp.now(tz='UTC').isoformat()
}

with open('models/evaluation_results.json', 'w') as f:
    json.dump(results, f, indent=2)

logger.info("\nEvaluation results saved to models/evaluation_results.json")
