# PRITHVIALERT - Speaker Notes

*(These notes are designed for a 5-minute presentation. Speak clearly, pause for emphasis, and avoid rushing.)*

## Slide 1: Title
**What to say:**
"Good morning Judges. We are here to present PrithviAlert, an AI-powered early warning and landslide risk monitoring system for the North Eastern Region, solving problem statement SIH26001. Our mission is simple: Predict Earlier, Warn Faster, and Respond Smarter."

## Slide 2: The Problem
**What to say:**
"The North Eastern Region is highly vulnerable to devastating landslides. While environmental data like rainfall and soil moisture exists, it is deeply fragmented. Authorities lack a unified, location-specific decision-support system, which leads to delayed emergency responses and isolated communities."

## Slide 3: The Solution
**What to say:**
"Our solution is a closed-loop disaster intelligence platform. PrithviAlert automatically fuses live weather, terrain data, satellite telemetry, and citizen reports into a unified AI Risk Engine. This engine generates a dynamic GIS digital risk twin, instantly alerting authorities and helping them prioritize emergency responses."

## Slide 4: System Architecture
**What to say:**
"Here is how it works under the hood. Raw environmental data is pulled through an ETL pipeline and fed into our Machine Learning models. The resulting risk scores are stored in a PostGIS spatial database, which drives our real-time GIS dashboard and pushes live WebSocket alerts to field officers and citizens."

## Slide 5: AI / ML
**What to say:**
"At the core is our ensemble model combining XGBoost and Random Forest. It doesn't just look at rainfall; it considers soil moisture, steepness, and historical susceptibility to predict the probability of a landslide event. *(Pause)* Note that the current prototype evaluates this pipeline using synthetic demonstration data; operational deployment will involve regional calibration with verified historical observations."

## Slide 6: GIS Digital Risk Twin
**What to say:**
"This translates into our GIS Digital Risk Twin. Authorities don’t just get a spreadsheet of numbers—they see exactly which zones, roads, and villages are under threat on a live interactive heatmap."

## Slide 7: Real-Time Early Warning
**What to say:**
"When conditions worsen—say, a heavy rainstorm hits—the map updates dynamically. If a user or field officer with our app approaches a 'Very High' risk zone, our PostGIS backend instantly calculates their proximity and pushes a critical alert to their device via WebSocket, completely bypassing the delays of traditional SMS."

## Slide 8: Citizen + Field Intelligence
**What to say:**
"We also put the human in the loop. Citizens and field officers can submit GPS-tagged photo reports of early hazard signs, like road cracks or minor rockfalls. The AI flags the risk, but the human validates it, ensuring authorities make informed final decisions."

## Slide 9: Emergency Prioritization
**What to say:**
"Most importantly, PrithviAlert doesn't just say *where* the risk is. It multiplies the AI risk score by population exposure and infrastructure impact to generate an Emergency Priority score. It tells disaster response teams exactly where they need to look first."

## Slide 10: Impact + Roadmap
**What to say:**
"Today, we have built a fully integrated, Dockerized, SIH demo-ready prototype. Our roadmap toward operational deployment includes integrating live IMD weather APIs, ISRO satellite feeds, and verified NER historical datasets for regional calibration. PrithviAlert turns fragmented signals into actionable early warning. Thank you."
