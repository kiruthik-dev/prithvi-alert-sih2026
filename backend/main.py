from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
import json
import math
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add ml folder to path so we can import predict module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ml')))
from predict import predict_risk
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from services.notification_service import NotificationService
from services.chatbot_service import ChatbotService

app = FastAPI(title="PrithviAlert MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/prithvialert")

# ---------------------------------------------------------------------------
# FALLBACK DATA — used ONLY when PostgreSQL is unreachable.
# Clearly labelled with "source": "fallback" so it is never confused with
# live PostgreSQL data in logs, API responses, or any downstream consumer.
# ---------------------------------------------------------------------------
FALLBACK_ZONES = [
    {
        "id": "fallback-uuid-1",
        "name": "Tawang Sector A",
        "district": "Tawang",
        "state": "Arunachal Pradesh",
        "risk_score": 15.0,
        "risk_level": "LOW",
        "rainfall_24h": 10.0,
        "soil_moisture": 30.0,
        "slope_angle": 25.0,
        "historical_factor": 0.5,
        "latitude": 27.56,
        "longitude": 91.86,
        "source": "fallback",
    },
    {
        "id": "fallback-uuid-2",
        "name": "Aizawl North",
        "district": "Aizawl",
        "state": "Mizoram",
        "risk_score": 25.0,
        "risk_level": "MODERATE",
        "rainfall_24h": 50.0,
        "soil_moisture": 50.0,
        "slope_angle": 35.0,
        "historical_factor": 0.75,
        "latitude": 23.765,
        "longitude": 92.715,
        "source": "fallback",
    },
    {
        "id": "fallback-uuid-3",
        "name": "Gangtok Central",
        "district": "East Sikkim",
        "state": "Sikkim",
        "risk_score": 45.0,
        "risk_level": "HIGH",
        "rainfall_24h": 120.0,
        "soil_moisture": 70.0,
        "slope_angle": 40.0,
        "historical_factor": 1.0,
        "latitude": 27.335,
        "longitude": 88.61,
        "source": "fallback",
    },
]

class DemoTriggerRequest(BaseModel):
    scenario: str  # NORMAL, HEAVY_RAIN, CRITICAL

class CitizenRegister(BaseModel):
    name: str
    phone: str
    language: str = "en"

class CitizenLocation(BaseModel):
    user_id: str
    lat: float
    lon: float

class AcknowledgeAlert(BaseModel):
    notification_id: str

class ChatRequest(BaseModel):
    query: str
    lat: float = None
    lon: float = None

def reset_fallback_zones():
    # Helper to reset fallback data
    global FALLBACK_ZONES
    FALLBACK_ZONES[0].update({"risk_score": 15.0, "risk_level": "LOW", "rainfall_24h": 10.0})
    FALLBACK_ZONES[1].update({"risk_score": 25.0, "risk_level": "MODERATE", "rainfall_24h": 50.0})
    FALLBACK_ZONES[2].update({"risk_score": 45.0, "risk_level": "HIGH", "rainfall_24h": 120.0})

def get_db():
    """
    Dependency that yields a psycopg2 connection, or None if PostgreSQL is
    unavailable. Callers MUST check for None and handle the fallback path
    explicitly — never allow fallback data to be silently treated as live data.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        yield conn
    except Exception as e:
        print(f"[PRITHVIALERT] ⚠  DB connection FAILED — source=fallback — {e}")
        yield None
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "PrithviAlert Backend MVP"}


@app.get("/api/v1/risk-zones")
def get_risk_zones(db=Depends(get_db)):
    # ── FALLBACK PATH ──────────────────────────────────────────────────────
    # Triggered only when get_db() yielded None (PostgreSQL unreachable).
    # Every record is explicitly marked source="fallback".
    # This branch is logged at WARNING level so it is never silent.
    if db is None:
        print("[PRITHVIALERT] ⚠  RETURNING FALLBACK DATA — PostgreSQL unavailable")
        return FALLBACK_ZONES

    # ── POSTGRES PATH ──────────────────────────────────────────────────────
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, district, state, risk_score, risk_level,
                       rainfall_24h, soil_moisture, slope_angle, historical_factor,
                       ST_Y(ST_Centroid(boundary)) AS latitude,
                       ST_X(ST_Centroid(boundary)) AS longitude
                FROM risk_zones
                ORDER BY risk_score DESC
            """)
            rows = cursor.fetchall()

        # Attach source field so callers can distinguish postgres vs fallback
        zones = [dict(row, source="postgres") for row in rows]
        print(f"[PRITHVIALERT] ✓  source=postgres — returned {len(zones)} zone(s)")
        return zones

    except Exception as e:
        # Query-level failure after connection succeeded — return empty, do
        # NOT silently serve fallback as if it were live data.
        print(f"[PRITHVIALERT] ✗  DB query FAILED — source=error — {e}")
        return []


@app.post("/api/v1/demo/trigger")
def trigger_demo_scenario(req: DemoTriggerRequest, db=Depends(get_db)):
    """Idempotent trigger to simulate changing conditions."""
    scenario = req.scenario.upper()
    valid_scenarios = ["NORMAL", "HEAVY_RAIN", "CRITICAL"]
    if scenario not in valid_scenarios:
        raise HTTPException(status_code=400, detail="Invalid scenario")

    if db is None:
        # In-memory fallback mutation
        if scenario == "NORMAL":
            reset_fallback_zones()
        elif scenario == "HEAVY_RAIN":
            for z in FALLBACK_ZONES:
                z["rainfall_24h"] += 80.0
                z["risk_score"] = min(99.0, z["risk_score"] + 30.0)
                z["risk_level"] = "HIGH" if z["risk_score"] >= 60 else ("MODERATE" if z["risk_score"] >= 40 else "LOW")
        elif scenario == "CRITICAL":
            for z in FALLBACK_ZONES:
                z["rainfall_24h"] += 200.0
                z["risk_score"] = min(100.0, z["risk_score"] + 60.0)
                z["risk_level"] = "CRITICAL" if z["risk_score"] >= 80 else ("HIGH" if z["risk_score"] >= 60 else "MODERATE")
        return {"status": "success", "scenario": scenario, "source": "fallback"}
    
    # DB mutation
    try:
        with db.cursor() as cursor:
            if scenario == "NORMAL":
                cursor.execute("UPDATE risk_zones SET rainfall_24h = 10.0, risk_score = 15.0, risk_level = 'LOW' WHERE district = 'Tawang'")
                cursor.execute("UPDATE risk_zones SET rainfall_24h = 50.0, risk_score = 25.0, risk_level = 'MODERATE' WHERE district = 'Aizawl'")
                cursor.execute("UPDATE risk_zones SET rainfall_24h = 120.0, risk_score = 45.0, risk_level = 'HIGH' WHERE district = 'East Sikkim'")
            elif scenario == "HEAVY_RAIN":
                cursor.execute("UPDATE risk_zones SET rainfall_24h = rainfall_24h + 80.0, risk_score = LEAST(99.0, risk_score + 30.0)")
                cursor.execute("UPDATE risk_zones SET risk_level = CASE WHEN risk_score >= 60 THEN 'HIGH' WHEN risk_score >= 40 THEN 'MODERATE' ELSE 'LOW' END")
            elif scenario == "CRITICAL":
                cursor.execute("UPDATE risk_zones SET rainfall_24h = rainfall_24h + 200.0, risk_score = LEAST(100.0, risk_score + 60.0)")
                cursor.execute("UPDATE risk_zones SET risk_level = CASE WHEN risk_score >= 80 THEN 'CRITICAL' WHEN risk_score >= 60 THEN 'HIGH' ELSE 'MODERATE' END")
        db.commit()
        return {"status": "success", "scenario": scenario, "source": "postgres"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371e3
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

@app.get("/api/v1/spatial/check-location")
def check_location(lat: float = Query(...), lon: float = Query(...), db=Depends(get_db)):
    if db is None:
        # Fallback (no boundary checking, just simple distance check for demo)
        for z in FALLBACK_ZONES:
            if _haversine(lat, lon, z["latitude"], z["longitude"]) < 5000:
                return {"inside": True, "zone": z, "source": "fallback"}
        return {"inside": False, "zone": None, "source": "fallback"}

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, district, state, risk_score, risk_level,
                       ST_Y(ST_Centroid(boundary)) AS latitude,
                       ST_X(ST_Centroid(boundary)) AS longitude
                FROM risk_zones
                WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
            """, (lon, lat))
            row = cursor.fetchone()
        
        if row:
            return {"inside": True, "zone": dict(row, source="postgres"), "source": "postgres"}
        return {"inside": False, "zone": None, "source": "postgres"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/spatial/check-proximity")
def check_proximity(lat: float = Query(...), lon: float = Query(...), radius_m: float = 5000, db=Depends(get_db)):
    if db is None:
        nearby = []
        for z in FALLBACK_ZONES:
            d = _haversine(lat, lon, z["latitude"], z["longitude"])
            if d <= radius_m:
                nearby.append({"distance_m": d, "zone": z})
        nearby.sort(key=lambda x: x["distance_m"])
        return {"nearby_zones": nearby, "source": "fallback"}

    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, district, state, risk_score, risk_level,
                       ST_Distance(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance_m,
                       ST_Y(ST_Centroid(boundary)) AS latitude,
                       ST_X(ST_Centroid(boundary)) AS longitude
                FROM risk_zones
                WHERE ST_DWithin(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
                ORDER BY distance_m ASC
            """, (lon, lat, lon, lat, radius_m))
            rows = cursor.fetchall()
        
        results = [{"distance_m": row["distance_m"], "zone": dict(row, source="postgres")} for row in rows]
        return {"nearby_zones": results, "source": "postgres"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/citizens/register")
def register_citizen(req: CitizenRegister, db=Depends(get_db)):
    if db is None:
        return {"id": "fallback-user-uuid", "message": "Registered in fallback mode"}
    try:
        with db.cursor() as cur:
            cur.execute("""
                INSERT INTO citizen_profiles (name, phone, language) 
                VALUES (%s, %s, %s) RETURNING id
            """, (req.name, req.phone, req.language))
            user_id = cur.fetchone()["id"]
            db.commit()
            return {"id": user_id, "message": "Registration successful"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/alerts/history")
def get_alert_history(db=Depends(get_db)):
    if db is None:
        return []
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT n.id, n.risk_level, n.message, n.status, n.acknowledged, n.created_at, z.name as zone_name
                FROM notifications n
                LEFT JOIN risk_zones z ON n.zone_id = z.id
                ORDER BY n.created_at DESC
                LIMIT 50
            """)
            return cur.fetchall()
    except Exception as e:
        return []

@app.post("/api/v1/alerts/acknowledge")
def acknowledge_alert(req: AcknowledgeAlert, db=Depends(get_db)):
    if db is None:
        return {"status": "success", "message": "Acknowledged (Fallback)"}
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE notifications SET acknowledged = TRUE WHERE id = %s", (req.notification_id,))
            db.commit()
            return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
def chat_with_assistant(req: ChatRequest, db=Depends(get_db)):
    bot = ChatbotService(db)
    return bot.process_query(req.query, req.lat, req.lon)

@app.websocket("/ws/location")
async def location_websocket(websocket: WebSocket):
    await websocket.accept()
    # For a websocket, we manage the DB connection manually since Depends() isn't well suited for persistent connections across many frames without scoping tricks.
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        use_fallback = False
        notification_svc = NotificationService(conn)
    except:
        use_fallback = True
        notification_svc = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                lat = payload.get("lat")
                lon = payload.get("lon")
                user_id = payload.get("user_id")
            except:
                await websocket.send_json({"error": "Invalid JSON payload"})
                continue
            
            if lat is None or lon is None:
                await websocket.send_json({"error": "Missing lat/lon"})
                continue

            # Process logic
            status = "SAFE"
            alert_zone = None
            dist = None

            if use_fallback:
                nearby = []
                for z in FALLBACK_ZONES:
                    d = _haversine(lat, lon, z["latitude"], z["longitude"])
                    if d <= 5000:
                        nearby.append({"d": d, "z": z})
                nearby.sort(key=lambda x: x["d"])
                if nearby:
                    nearest = nearby[0]["z"]
                    dist = nearby[0]["d"]
                    if nearest["risk_level"] in ["HIGH", "VERY HIGH", "CRITICAL"]:
                        status = "DANGER"
                        alert_zone = nearest["name"]
            else:
                try:
                    with conn.cursor() as cursor:
                        # Upsert user location if user_id is provided
                        if user_id and user_id != "fallback-user-uuid":
                            cursor.execute("""
                                INSERT INTO user_locations (user_id, location, last_updated)
                                VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), CURRENT_TIMESTAMP)
                                ON CONFLICT (user_id) DO UPDATE 
                                SET location = EXCLUDED.location, last_updated = CURRENT_TIMESTAMP
                            """, (user_id, lon, lat))

                        cursor.execute("""
                            SELECT name, risk_level,
                                ST_Distance(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as dist
                            FROM risk_zones
                            WHERE ST_DWithin(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 5000)
                            ORDER BY dist ASC LIMIT 1
                        """, (lon, lat, lon, lat))
                        row = cursor.fetchone()
                        
                        if row:
                            dist = row["dist"]
                            if row["risk_level"] in ["HIGH", "VERY HIGH", "CRITICAL"]:
                                status = "DANGER"
                                alert_zone = row["name"]
                        conn.commit() # commit transaction
                        
                        # Process targeted public warning
                        if user_id and user_id != "fallback-user-uuid" and notification_svc:
                            new_alert = notification_svc.process_proximity_alert(user_id, lat, lon)
                            if new_alert:
                                await websocket.send_json({
                                    "type": "WARNING",
                                    "notification_id": str(new_alert["id"]),
                                    "risk_level": new_alert["risk_level"],
                                    "message": new_alert["message"],
                                    "timestamp": new_alert["created_at"].isoformat()
                                })
                except Exception as e:
                    print(f"WS DB Error: {e}")
                    if conn:
                        conn.rollback()

            response = {
                "type": "PROXIMITY_ALERT",
                "status": status,
                "zone": alert_zone,
                "distance_m": round(dist, 1) if dist is not None else None,
                "source": "fallback" if use_fallback else "postgres"
            }
            await websocket.send_json(response)
    
    except WebSocketDisconnect:
        pass
    finally:
        if conn:
            conn.close()

class PredictionRequest(BaseModel):
    # Allow arbitrary features in the body directly
    class Config:
        extra = 'allow'

@app.post("/api/v1/predict")
async def predict_risk_endpoint(request: PredictionRequest):
    """
    Predict landslide risk from raw environmental features.
    Uses XGBoost & RF classifiers trained on synthetic demonstration dataset.
    """
    try:
        features_dict = request.model_dump()
        
        # predict_risk returns {"risk_score": ..., "risk_level": ..., "confidence": ..., "ensemble_probability": ...}
        prediction_result = predict_risk(features_dict)
        
        # Add metadata
        prediction_result["feature_count"] = len(features_dict)
        prediction_result["note"] = "Prototype risk classification. Predictions use synthetic demonstration data and should be validated against regional historical data."
        
        return prediction_result
        
    except Exception as e:
        print(f"Prediction failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
