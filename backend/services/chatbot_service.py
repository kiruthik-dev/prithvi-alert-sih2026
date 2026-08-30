import logging

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self, db_conn):
        self.db_conn = db_conn

    def retrieve_contacts(self):
        """Retrieves emergency contacts from the database."""
        if not self.db_conn:
            return "No verified emergency contacts found in prototype database."
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("SELECT agency, phone, role, district FROM emergency_contacts")
                rows = cur.fetchall()
                if not rows:
                    return "No verified emergency contacts found."
                
                msg = "Verified Emergency Contacts:\n"
                for r in rows:
                    msg += f"- {r['agency']} ({r['district']}): {r['phone']} [{r['role']}]\n"
                return msg.strip()
        except Exception as e:
            logger.error(f"Chatbot contacts retrieval error: {e}")
            return "Error retrieving emergency contacts. Please contact local authorities."

    def retrieve_nearest_risk(self, lat, lon):
        """Retrieves risk data for the nearest zone based on location."""
        if not self.db_conn:
            return "I don't have current verified risk information (Database offline)."
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("""
                    SELECT name, risk_score, risk_level, rainfall_24h, soil_moisture
                    FROM risk_zones
                    ORDER BY ST_Distance(boundary::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) ASC
                    LIMIT 1
                """, (lon, lat))
                row = cur.fetchone()
                if not row:
                    return "I don't have verified risk information for your location."
                
                return (f"Your location is currently near the {row['name']} risk zone. "
                        f"The current prototype risk score is {row['risk_score']} ({row['risk_level']} risk). "
                        f"Current environmental factors include {row['rainfall_24h']}mm rainfall and {row['soil_moisture']}% soil moisture. "
                        f"Please follow local authority instructions.")
        except Exception as e:
            logger.error(f"Chatbot risk retrieval error: {e}")
            return "Error retrieving risk data."

    def determine_intent(self, query):
        """Deterministic Intent Matching based on keywords."""
        query = query.lower()
        if any(keyword in query for keyword in ["safe", "risk", "status", "danger"]):
            return "RISK_STATUS"
        elif any(keyword in query for keyword in ["road", "blocked", "blockage"]):
            return "ROAD_STATUS"
        elif any(keyword in query for keyword in ["what should i do", "help", "instructions", "guidance"]):
            return "SAFETY_GUIDANCE"
        elif any(keyword in query for keyword in ["report", "crack", "landslide near me", "see a landslide"]):
            return "REPORT_HAZARD"
        elif any(keyword in query for keyword in ["hospital", "contact", "police", "number"]):
            return "EMERGENCY_CONTACTS"
        else:
            return "UNKNOWN"

    def process_query(self, query, lat=None, lon=None):
        """Processes the chat query and routes it to the correct retrieval logic."""
        intent = self.determine_intent(query)
        
        response = ""
        action = None

        if intent == "RISK_STATUS":
            if lat is not None and lon is not None:
                response = self.retrieve_nearest_risk(lat, lon)
            else:
                response = "Please enable location access or select your location on the map to get local risk status."

        elif intent == "ROAD_STATUS":
            response = "I don't have current verified road status information for that route. Please check with local traffic authorities."

        elif intent == "SAFETY_GUIDANCE":
            response = ("During a landslide warning:\n"
                        "1. Stay alert and awake.\n"
                        "2. Listen to local news stations.\n"
                        "3. Avoid river valleys and low-lying areas.\n"
                        "4. If you notice structural cracks or moving earth, evacuate immediately.\n"
                        "Always follow instructions from local disaster-management authorities.")

        elif intent == "REPORT_HAZARD":
            response = "If you observe signs of a landslide, please report it to authorities."
            action = "REPORT_HAZARD"

        elif intent == "EMERGENCY_CONTACTS":
            response = self.retrieve_contacts()

        else:
            response = ("I am PrithviAssist, an AI-assisted disaster information bot. "
                        "I can provide current risk status, safety guidance, and emergency contacts. "
                        "How can I help you?")
            
        return {
            "message": response,
            "action": action,
            "note": "AI-Assisted Disaster Information (Retrieval Mode). Never overrides official authorities."
        }
