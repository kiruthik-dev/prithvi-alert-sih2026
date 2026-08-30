# PRITHVIALERT - 5-Minute Live Demo Script

**0:00–0:20 | Introduction**
*(Speaker stands by the presentation screen/laptop)*
"PrithviAlert turns environmental signals and field intelligence into location-specific landslide-risk decision support."

**0:20–0:50 | Dashboard Overview**
*(Operator navigates the main dashboard)*
- Point out the GIS map.
- Show the risk zones (polygons).
- Explain the risk levels (Low to Critical).
- Point out the active alerts panel on the side.

**0:50–1:10 | Normal State**
*(Operator clicks the NORMAL demo trigger)*
- Show that the dashboard reflects LOW risk across zones.
- Highlight the baseline environmental values in the sidebar.

**1:10–1:40 | Heavy Rain Scenario**
*(Operator clicks the HEAVY RAIN demo trigger)*
- Show the rainfall value change dramatically.
- Show the risk level increase on the map (color shift).
- Point out the heatmap change.
- **Say:** "The system continuously combines environmental signals rather than looking at rainfall in isolation."

**1:40–2:05 | Slope Instability**
*(Operator clicks the SLOPE INSTABILITY demo trigger)*
- Show the risk escalating to VERY HIGH.
- Click on a specific zone to reveal details.
- Point out the compounding environmental factors (e.g., steep slope + saturated soil).

**2:05–2:30 | Critical Alert**
*(Operator clicks the CRITICAL demo trigger)*
- Show the CRITICAL alert banner pop up on the dashboard.
- Highlight the affected infrastructure (roads, villages within the zone).
- Point out the priority response recommendation.

**2:30–3:00 | GPS Proximity Simulation**
*(Operator toggles "Simulate Movement" on the dashboard)*
- Show the simulated user location moving near a high-risk zone.
- Demonstrate the system performing a live PostGIS `ST_DWithin` check.
- Show the live **PROXIMITY ALERT** appearing dynamically via WebSocket.

**3:00–3:35 | Citizen / Field Intelligence**
*(Operator navigates to the Citizen Report form)*
- Submit a mock report:
  - GPS coordinates
  - Photo upload
  - Hazard type (e.g., "rockfall")
  - Severity
- Show the report appear live on the GIS map.

**3:35–4:00 | Human-in-the-Loop Validation**
*(Operator clicks on the new field report)*
- Show AI/image analysis (if available) identifying the hazard.
- **Explain:** "Visual analysis serves as supplementary evidence. AI generates the risk, but human authorities make the final operational decisions."

**4:00–4:30 | Emergency Prioritization**
*(Operator navigates to the Prioritization / Analytics view)*
- **Explain:** "Risk + Exposure + Connectivity = Response Priority."
- Show how the system ranks zones not just by risk score, but by how many people and critical roads are affected.

**4:30–5:00 | Conclusion & Roadmap**
*(Operator returns to the main map view)*
- **Say:** "Today this is a fully integrated prototype. The next step toward operational deployment is calibration using verified regional historical observations and live data feeds. Thank you."
