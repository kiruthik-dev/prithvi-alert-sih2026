# PRITHVIALERT - Judge Q&A Preparation

**1. Why XGBoost?**
XGBoost is highly robust against missing data, handles non-linear relationships well (e.g., rainfall vs. steep slope), and provides excellent feature importance scoring which helps us understand *why* a risk alert was triggered.

**2. Why Random Forest?**
Random Forest prevents overfitting on highly complex, noisy spatial datasets. It serves as a strong, stable ensemble partner to XGBoost.

**3. Why use two models?**
Ensembling an algorithmic approach (XGBoost) with a bagging approach (Random Forest) creates a more generalized, defensive architecture that reduces the likelihood of false positives in edge cases.

**4. What exactly does the AI predict?**
It predicts a probabilistic landslide-risk estimate based on the current environmental state (rainfall, soil moisture, etc.) and inherent susceptibility (slope, terrain).

**5. Is this deterministic?**
No. It is a probabilistic decision-support tool. It evaluates risk susceptibility, it does not guarantee that a landslide will happen at an exact minute.

**6. Where does your training data come from?**
The current prototype demonstrates the complete ML pipeline using provenance-labelled demonstration data. Operational deployment would require verified regional historical observations.

**7. Is the current dataset real?**
The current dataset is a synthetic demonstration dataset designed specifically to validate the ETL and ML pipeline architectures without data leakage. Real data ingestion is fully supported by the pipeline.

**8. How will you get real NER data?**
Through our modular ETL pipeline, which is built to ingest data from IMD (weather), ISRO/Bhuvan (terrain/satellite), and GSI (historical landslide inventories). 

**9. How do you prevent false alarms?**
By relying on an ensemble model, demanding multi-factor conditions (not just rainfall, but soil saturation and slope), and keeping a "Human-in-the-Loop" verification step via field reports before final operational action is taken.

**10. How do you reduce missed landslides?**
By utilizing localized sensor data (IoT) and citizen reports to catch micro-level ground shifts that broad satellite or weather data might miss.

**11. How do you prevent data leakage?**
We use `GroupShuffleSplit` on canonical spatial event IDs during training. This ensures that temporal slices of the same geographic event don't artificially inflate our validation/test metrics by leaking into the training set.

**12. How does GIS help?**
It transforms raw, tabular AI predictions into a visual, spatial reality. Authorities don't just see a "High Risk" number; they see exactly which road and which village is in the path of the hazard.

**13. Why PostGIS?**
PostGIS allows us to perform lightning-fast, native spatial queries (like point-in-polygon and distance calculations) directly at the database level, which is critical for real-time proximity alerting.

**14. How does offline operation work?**
The system is built to support a PWA (Progressive Web App) architecture where the GIS risk map is cached locally. Field officers can view the last known state and collect reports offline, syncing them when connectivity is restored.

**15. How does low-network operation work?**
We send extremely lightweight GeoJSON payloads and WebSocket text frames rather than heavy raster images.

**16. How does the WebSocket alert work?**
The backend pushes a live event over a bidirectional TCP socket connection instantly when a spatial threshold is crossed, avoiding the latency and battery drain of continuous HTTP polling.

**17. How does ST_Contains work?**
It's a PostGIS function that rapidly mathematically verifies if a specific GPS point (a user) is located entirely within the boundary of a specific polygon (a risk zone).

**18. How does ST_DWithin work?**
It's a PostGIS proximity function that checks if the distance between two geometries (a user and a high-risk zone) is less than a specified threshold radius, triggering early proximity alerts.

**19. How would this scale to all 8 NER states?**
Our architecture is fully containerized (Docker) and horizontally scalable. The spatial database indexes can handle millions of geometries, and the ML pipeline can be regionally federated (trained on specific states).

**20. How would you integrate IMD?**
Via automated cron jobs fetching IMD APIs/FTP servers to pull live gridded rainfall data into our `/data/interim` pipeline for immediate inference.

**21. How would you integrate satellite data?**
Our architecture supports Sentinel-1 (SAR) and Sentinel-2 derived features (like NDVI). Live operational integration requires access to Copernicus or ISRO data nodes and an automated raster-to-vector processing pipeline.

**22. How would you integrate IoT sensors?**
IoT endpoints can push MQTT or HTTP POST payloads directly to our ingestion API, overriding broader satellite metrics with hyper-local truth values for soil moisture and tilt.

**23. How would you protect citizen privacy?**
Citizen reports are strictly tied to geographic coordinates, not PII (Personally Identifiable Information). WebSocket tracking utilizes session-based ephemeral IDs, not permanent user tracking.

**24. Can AI automatically order evacuation?**
No. The system provides decision support. Final emergency action and evacuation orders remain strictly with authorized disaster management personnel.

**25. How would you validate this before deployment?**
Operational deployment requires spatial and temporal cross-validation against verified regional historical observations, followed by a shadow-deployment period to tune sensitivity thresholds.

**26. How often would you retrain the model?**
Annually to account for changing topography and climate patterns, or immediately following a major geological event (like an earthquake) that significantly alters regional susceptibility.

**27. What are the biggest limitations?**
The AI is only as good as the incoming data. Cloud cover can obstruct optical satellites, and dense forests can complicate DEM accuracy. This is why ground-level IoT and citizen reporting are crucial fallback mechanisms.

**28. What makes this different from a simple GIS dashboard?**
A standard GIS dashboard shows what *has happened*. PrithviAlert is a proactive engine that combines historical susceptibility with live triggers to predict what is *likely to happen*, prioritizing response before the disaster occurs.
