# PRITHVIALERT: ONE-PAGE SUMMARY

**SIH26001 — AI-Based Early Warning and Landslide Risk Monitoring System in NER**

*PREDICT EARLIER. WARN FASTER. RESPOND SMARTER.*

---

## THE PROBLEM
The North Eastern Region (NER) is highly vulnerable to landslides triggered by heavy rainfall and unstable terrain. While environmental data exists, it is highly fragmented. Authorities lack a centralized, location-specific decision support system that translates complex weather and terrain signals into actionable early warnings, leaving remote communities isolated and vulnerable.

## THE SOLUTION
**PrithviAlert** is a functional AI-GIS prototype designed to provide probabilistic landslide-risk decision support. It acts as a digital risk twin, seamlessly fusing heterogeneous hazard signals—such as weather, soil conditions, terrain, and satellite data—into a single, dynamic risk engine.

## ARCHITECTURE & PIPELINE
- **Data Ingestion:** A modular ETL pipeline designed to integrate live weather, DEM, and soil feeds.
- **AI Risk Engine:** An ensemble machine learning model (XGBoost + Random Forest) that predicts probabilistic landslide-risk estimates and risk categories (LOW to CRITICAL).
- **GIS Digital Twin:** A PostGIS-backed interactive map visualizing active risk zones, heatmaps, and exposed infrastructure.
- **Delivery:** A real-time web dashboard capable of pushing proximity alerts via WebSocket.

## KEY FEATURES
1. **Dynamic AI Risk Assessment:** Continuously evaluates environmental state against terrain susceptibility to generate a risk score, rather than looking at rainfall in isolation.
2. **Real-time GIS Visualization:** Overlays risk predictions directly onto critical infrastructure (roads, villages).
3. **Proximity Alerting:** Uses advanced PostGIS spatial queries (`ST_Contains`, `ST_DWithin`) to warn simulated user locations if they enter or approach a high-risk zone dynamically.
4. **Citizen & Field Intelligence:** Allows on-the-ground personnel to submit GPS-tagged visual reports of hazard conditions (e.g., cracks, blockages), enforcing a human-in-the-loop verification process.
5. **Emergency Prioritization:** Calculates a response priority score by multiplying the AI risk factor by population exposure and connectivity impact.
6. **Offline Capability:** Built for progressive web app (PWA) operation, allowing local caching of the risk map and offline report collection for low-network environments.

## IMPACT & STATUS
**Current Prototype Status:** The system is a fully integrated, Dockerized prototype demonstrating the complete ML pipeline, GIS dashboard, demo scenario engine, and real-time alerts. *(Note: The current prototype utilizes a provenance-labelled synthetic demonstration dataset to validate the architecture without data leakage).*

**Future Roadmap for Operational Deployment:**
- Integration of verified NER historical datasets (GSI).
- Integration of real-time weather APIs (IMD) and satellite telemetry (ISRO/Copernicus).
- Strict regional spatial/temporal calibration and cross-validation.
- Deployment of hyper-local IoT moisture sensors.
- Scaling into a comprehensive, NER-wide disaster intelligence platform.

> **Final Note on Operational Use:** PrithviAlert provides advanced decision support. Final emergency action and evacuation orders remain strictly with authorized disaster management personnel.
