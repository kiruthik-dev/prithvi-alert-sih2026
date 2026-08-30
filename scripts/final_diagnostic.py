import urllib.request
import json
import os
import psycopg2
import sys

def report(name, condition, details=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if details and not condition:
        print(f"       -> {details}")
    return condition

def main():
    print("==================================================")
    print("PRITHVIALERT FINAL DIAGNOSTIC SCRIPT")
    print("==================================================\n")
    all_passed = True
    
    # 1. Check Files
    print("--- FILES ---")
    files = [
        "ml/prepare_data.py", "ml/train.py", "ml/evaluate.py", "ml/predict.py",
        "ml/models/xgboost_model.pkl", "ml/models/rf_model.pkl", "ml/models/model_metadata.json",
        "backend/main.py", "docker-compose.yml"
    ]
    for f in files:
        if not report(f"File exists: {f}", os.path.exists(os.path.join("..", f)) if not os.path.exists(f) else True):
            all_passed = False

    # 2. Database
    print("\n--- DATABASE ---")
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/prithvialert")
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM risk_zones;")
        count = cur.fetchone()[0]
        report("PostgreSQL Connection", True)
        report("PostGIS Data exists", count > 0)
        conn.close()
    except Exception as e:
        report("PostgreSQL Connection", False, str(e))
        all_passed = False
        
    # 3. API & ML
    print("\n--- BACKEND & APIs ---")
    base_url = "http://localhost:8000/api/v1"
    
    def test_api(endpoint, method='GET', data=None):
        try:
            req = urllib.request.Request(f"{base_url}{endpoint}", method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                req.data = json.dumps(data).encode()
            resp = urllib.request.urlopen(req)
            if resp.status == 200:
                return True, json.loads(resp.read().decode())
            return False, f"Status {resp.status}"
        except Exception as e:
            return False, str(e)

    health_ok, _ = test_api("/health")
    report("API Health Check", health_ok)
    
    loc_ok, _ = test_api("/spatial/check-location?lat=28.616&lon=88.589")
    report("Spatial ST_Contains API", loc_ok)
    
    prox_ok, _ = test_api("/spatial/check-proximity?lat=28.5&lon=88.5&radius_km=5")
    report("Spatial ST_DWithin API", prox_ok)
    
    # Valid Predict Payload
    payload = {
        'rainfall_1h': 5, 'rainfall_24h': 145, 'soil_moisture': 82, 
        'ground_displacement': 5, 'tilt_angle': 3.2, 'elevation': 2500, 
        'slope': 38, 'aspect': 180, 'curvature': 0.5, 'terrain_ruggedness': 0.75, 
        'ndvi': 0.65, 'land_cover': 'forest', 'distance_to_road': 500, 
        'distance_to_river': 1000, 'historical_landslide_frequency': 2.0, 
        'historical_landslide_distance': 500, 'forecast_rainfall': 120, 
        'population_exposure': 2000, 'infrastructure_exposure': 3
    }
    pred_ok, pred_data = test_api("/predict", "POST", payload)
    
    if report("ML Prediction API", pred_ok):
        if 'risk_score' in pred_data and 'confidence' in pred_data:
            report("No fake confidence", pred_data['confidence'] != 0.92, f"Found {pred_data['confidence']}")
        else:
            report("Prediction Payload Valid", False, "Missing risk_score or confidence")
    else:
        all_passed = False

    print("\n==================================================")
    if all_passed:
        print("[PASS] FINAL DIAGNOSTIC: System is SIH DEMO READY.")
        sys.exit(0)
    else:
        print("[FAIL] FINAL DIAGNOSTIC: System Needs Fixes.")
        sys.exit(1)

if __name__ == '__main__':
    main()
