CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS risk_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    district VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    risk_score FLOAT DEFAULT 0.0,
    risk_level VARCHAR(50) DEFAULT 'LOW',
    rainfall_24h FLOAT DEFAULT 0.0,
    soil_moisture FLOAT DEFAULT 0.0,
    slope_angle FLOAT DEFAULT 0.0,
    historical_factor FLOAT DEFAULT 0.5,
    boundary GEOMETRY(Polygon, 4326)
);

CREATE INDEX idx_risk_zones_boundary ON risk_zones USING GIST (boundary);

-- Seed Data (Tawang, Aizawl, Gangtok)
INSERT INTO risk_zones (name, district, state, risk_score, risk_level, rainfall_24h, soil_moisture, slope_angle, historical_factor, boundary)
VALUES 
(
    'Tawang Sector A', 'Tawang', 'Arunachal Pradesh', 15.0, 'LOW', 10.0, 30.0, 25.0, 0.5,
    ST_GeomFromText('POLYGON((91.85 27.55, 91.87 27.55, 91.87 27.57, 91.85 27.57, 91.85 27.55))', 4326)
),
(
    'Aizawl North', 'Aizawl', 'Mizoram', 25.0, 'MODERATE', 50.0, 50.0, 35.0, 0.75,
    ST_GeomFromText('POLYGON((92.70 23.75, 92.73 23.75, 92.73 23.78, 92.70 23.78, 92.70 23.75))', 4326)
),
(
    'Gangtok Central', 'East Sikkim', 'Sikkim', 45.0, 'HIGH', 120.0, 70.0, 40.0, 1.0,
    ST_GeomFromText('POLYGON((88.60 27.32, 88.62 27.32, 88.62 27.35, 88.60 27.35, 88.60 27.32))', 4326)
);

-- Public Warning System Tables
CREATE TABLE IF NOT EXISTS citizen_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    language VARCHAR(50) DEFAULT 'en',
    phone VARCHAR(20),
    preferences JSONB DEFAULT '{"sms": true, "push": false, "in_app": true}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_locations (
    user_id UUID PRIMARY KEY REFERENCES citizen_profiles(id) ON DELETE CASCADE,
    location GEOMETRY(Point, 4326),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_locations_geom ON user_locations USING GIST (location);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES citizen_profiles(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES risk_zones(id) ON DELETE SET NULL,
    risk_level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(50) DEFAULT 'IN_APP',
    status VARCHAR(50) DEFAULT 'QUEUED',
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- Chatbot & Disaster Assistance Tables
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agency VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    role VARCHAR(255) NOT NULL,
    district VARCHAR(255)
);

-- Seed Dummy Emergency Contacts
INSERT INTO emergency_contacts (agency, phone, role, district)
VALUES 
    ('Sikkim State Disaster Management', '1070', 'State Control Room', 'East Sikkim'),
    ('Gangtok Local Police', '100', 'Emergency Response', 'East Sikkim'),
    ('Mizoram Disaster Response', '1070', 'State Control Room', 'Aizawl'),
    ('Arunachal Pradesh Relief', '1070', 'State Control Room', 'Tawang');
