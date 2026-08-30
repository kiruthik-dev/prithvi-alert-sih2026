import logging
import uuid
import datetime

logger = logging.getLogger(__name__)

# Configurable Radii (Prototype)
PROXIMITY_RADII_M = {
    "CRITICAL": 1500.0,
    "VERY HIGH": 1000.0,
    "HIGH": 500.0,
    "MODERATE": 250.0,
    "LOW": 0.0
}

# Cooldown period for identical risk level warnings (e.g., 30 minutes)
COOLDOWN_MINUTES = 30

def generate_warning_message(zone_name, risk_level, risk_score, language="en"):
    """
    Generates localized warning messages based on risk tier and language.
    """
    messages = {
        "en": {
            "CRITICAL": f"CRITICAL LANDSLIDE WARNING: Critical landslide risk (Score: {risk_score}) detected near {zone_name}. Avoid unstable slopes and affected roads. Follow instructions issued by local authorities immediately.",
            "VERY HIGH": f"URGENT WARNING: Very high landslide risk (Score: {risk_score}) detected near {zone_name}. Remain vigilant and prepare to follow official instructions.",
            "HIGH": f"CAUTION: High landslide risk (Score: {risk_score}) detected near {zone_name}. Please stay alert.",
            "MODERATE": f"Monitoring: Moderate risk detected near {zone_name}.",
            "LOW": "Conditions are normal."
        },
        "hi": {
            "CRITICAL": f"गंभीर भूस्खलन चेतावनी: {zone_name} के पास गंभीर जोखिम (स्कोर: {risk_score}) है। अस्थिर ढलानों और सड़कों से बचें। तुरंत स्थानीय अधिकारियों के निर्देशों का पालन करें।",
            "VERY HIGH": f"अत्यावश्यक चेतावनी: {zone_name} के पास बहुत अधिक जोखिम (स्कोर: {risk_score}) है। सतर्क रहें।",
            "HIGH": f"सावधानी: {zone_name} के पास उच्च जोखिम (स्कोर: {risk_score}) है। कृपया सतर्क रहें।",
            "MODERATE": f"निगरानी: {zone_name} के पास मध्यम जोखिम का पता चला है।",
            "LOW": "स्थितियां सामान्य हैं।"
        },
        "as": {
            "CRITICAL": f"গুৰুতৰ ভূমিস্খলনৰ সতৰ্কবাণী: {zone_name} ৰ ওচৰত গুৰুতৰ বিপদ (স্ক'ৰ: {risk_score})। স্থানীয় কৰ্তৃপক্ষৰ নিৰ্দেশনা মানি চলক।",
            "VERY HIGH": f"জৰুৰী সতৰ্কবাণী: {zone_name} ৰ ওচৰত অতি উচ্চ বিপদ (স্ক'ৰ: {risk_score})।",
            "HIGH": f"সাৱধান: {zone_name} ৰ ওচৰত উচ্চ বিপদ (স্ক'ৰ: {risk_score})।",
            "MODERATE": f"নিৰীক্ষণ: {zone_name} ৰ ওচৰত মজলীয়া বিপদ।",
            "LOW": "পৰিস্থিতি স্বাভাৱিক।"
        }
    }
    
    # Fallback to english if language not supported
    lang_dict = messages.get(language, messages["en"])
    return lang_dict.get(risk_level, lang_dict["LOW"])


class NotificationService:
    def __init__(self, db_conn):
        self.db_conn = db_conn

    def simulate_delivery(self, channel, phone, message):
        """Simulates sending a notification (MockSMSProvider, MockPushProvider)"""
        print(f"\n[{datetime.datetime.now().isoformat()}] --- SIMULATED NOTIFICATION ---")
        print(f"CHANNEL: {channel}")
        print(f"TARGET: {phone if phone else 'Unknown Device'}")
        print(f"MESSAGE: {message}")
        print("------------------------------------------\n")
        return "SIMULATED"

    def process_proximity_alert(self, user_id, lat, lon):
        """
        Queries ST_DWithin to find nearby risk zones.
        If user is near a zone (HIGH+), dispatches a warning.
        """
        if not self.db_conn:
            return None

        # Fetch citizen preferences
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("SELECT language, phone, preferences FROM citizen_profiles WHERE id = %s", (user_id,))
                user_row = cur.fetchone()
                if not user_row:
                    return None
                
                lang = user_row.get("language", "en")
                phone = user_row.get("phone", "")
                
                # Check nearest zone
                cur.execute("""
                    SELECT id, name, risk_score, risk_level,
                           ST_Distance(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as dist
                    FROM risk_zones
                    ORDER BY dist ASC LIMIT 1
                """, (lon, lat))
                nearest = cur.fetchone()

                if not nearest:
                    return None

                zone_id = nearest["id"]
                zone_name = nearest["name"]
                risk_level = nearest["risk_level"]
                risk_score = nearest["risk_score"]
                dist_m = nearest["dist"]

                # Check if within radius for that risk level
                threshold = PROXIMITY_RADII_M.get(risk_level, 0.0)
                
                if dist_m <= threshold and risk_level in ["CRITICAL", "VERY HIGH", "HIGH"]:
                    # Deduplication logic (check cooldown)
                    cur.execute("""
                        SELECT created_at FROM notifications
                        WHERE user_id = %s AND zone_id = %s AND risk_level = %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (user_id, zone_id, risk_level))
                    last_alert = cur.fetchone()

                    if last_alert:
                        time_diff = datetime.datetime.utcnow() - last_alert["created_at"].replace(tzinfo=None)
                        if time_diff.total_seconds() < (COOLDOWN_MINUTES * 60):
                            # In cooldown period, do not send duplicate
                            return None

                    # Generate and dispatch
                    message = generate_warning_message(zone_name, risk_level, risk_score, lang)
                    status = self.simulate_delivery("MOCK_SMS", phone, message)

                    cur.execute("""
                        INSERT INTO notifications (user_id, zone_id, risk_level, message, channel, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, message, risk_level, created_at
                    """, (user_id, zone_id, risk_level, message, "MOCK_SMS", status))
                    
                    self.db_conn.commit()
                    new_notification = cur.fetchone()
                    return new_notification

        except Exception as e:
            print(f"NotificationService Error: {e}")
            if self.db_conn:
                self.db_conn.rollback()
        
        return None
