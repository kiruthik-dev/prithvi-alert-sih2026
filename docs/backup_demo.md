# PRITHVIALERT - Backup Demo Instructions

**CRITICAL:** Do not rely entirely on the live Docker environment during the SIH presentation. Network drops, port conflicts, or laptop crashes can ruin a live demo. You must prepare a backup video and screenshots.

## 1. Prepare the Backup Screen Recording
*Perform this step immediately on your actual presentation laptop, before the event.*

**Recording Setup:**
1. Screen Resolution: 1920x1080 (1080p).
2. Browser Size: Maximized, hiding the bookmarks bar.
3. Open Tabs: `http://localhost:5173` (Dashboard) and `http://localhost:8000/docs` (Swagger UI, optional for technical Q&A).
4. Recording Tool: OBS Studio, Loom, or Windows Game Bar / Mac QuickTime.

**Recording Sequence (Target: 3-4 minutes):**
1. **Start** on the Dashboard with the **NORMAL** state selected. Pause for 5 seconds so the viewer can read the map.
2. Click **HEAVY RAIN**. Wait 5 seconds. Slowly move the mouse to hover over the changing heatmap.
3. Click **SLOPE INSTABILITY**. Wait 5 seconds. Click on the highest risk zone (now red) to open the details panel.
4. Click **CRITICAL**. Wait for the banner alert to appear.
5. Toggle **Simulate Movement** to ON. Let the simulation run for 10-15 seconds until the **PROXIMITY ALERT** banner triggers.
6. Click **Report Hazard**. Briefly fill out the form (type: Rockfall, severity: High) and click Submit.
7. End the recording on the full map view. 
8. Save this video as `docs/demo_assets/PrithviAlert_Backup_Demo.mp4`.

## 2. Prepare Backup Screenshots
*If video playback fails, you need static images.*

Capture the following full-screen screenshots and save them in `docs/demo_assets/`:
- `01_dashboard_normal.png` (The baseline state)
- `02_dashboard_critical.png` (The state after hitting CRITICAL demo button)
- `03_zone_details.png` (A screenshot with the side-panel or pop-up details visible)
- `04_proximity_alert.png` (A screenshot showing the red WebSocket proximity alert banner)
- `05_citizen_report.png` (A screenshot showing the open reporting form)

## 3. How to Use the Backup During the Pitch
If the live environment crashes during the Q&A or demo segment:
1. Do not panic or try to debug Docker live.
2. Calmly state: *"It seems we are experiencing a network/environment issue. I will switch to our backup recording which demonstrates the exact same live system functionality."*
3. Open `PrithviAlert_Backup_Demo.mp4` and narrate over it live, exactly as you practiced in `docs/demo.md`.
