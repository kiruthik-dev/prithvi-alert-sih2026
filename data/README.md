# PrithviAlert — Data Directory

## Overview

This directory contains all data assets for the PrithviAlert landslide early-warning ML pipeline.
The pipeline targets the **North East Region (NER)** of India.

> **PROTOTYPE NOTICE**: This is a research prototype. Models trained on this data are NOT
> scientifically validated for operational early-warning use.

---

## Directory Structure

```
data/
├── raw/                    # Original downloaded source files (never modified)
│   ├── isro_atlas/         # ISRO/NRSC Landslide Atlas records
│   ├── nasa_coolr/         # NASA COOLR / Global Landslide Catalog
│   ├── gpm_imerg/          # NASA GPM IMERG rainfall
│   ├── soilgrids/          # ISRIC SoilGrids soil properties
│   ├── sentinel1/          # Copernicus Sentinel-1 SAR deformation
│   ├── sentinel2/          # Copernicus Sentinel-2 NDVI/land-cover
│   └── dem/                # SRTM DEM terrain data
├── interim/                # Per-source cleaned, standardized files
├── processed/              # Final fused training datasets
└── README.md               # This file
```

---

## Data Sources

### 1. ISRO/NRSC Landslide Atlas of India
- **Description**: Indian landslide inventory covering 1998–2022
- **Access**: No public machine-readable API. Records are extracted from published reports.
- **License**: Government of India Open Data License (GODL) where applicable
- **NER Focus**: Arunachal Pradesh, Sikkim, Mizoram, Manipur, Meghalaya, Nagaland, Assam, Tripura
- **Fallback**: Synthetic NER inventory with realistic coordinates, dates, event types
- **Fallback label**: `data_source=isro_atlas_synthetic`, `data_quality=simulated`

### 2. NASA COOLR / Global Landslide Catalog (GLC)
- **Description**: Report-based global landslide observations
- **Access**: Public CSV — https://pmm.nasa.gov/data-access/downloads/gpm
- **License**: NASA Open Data
- **Fields**: event_id, event_date, latitude, longitude, trigger, source_name, source_link
- **Fallback label**: `data_source=nasa_coolr_synthetic`, `data_quality=simulated`

### 3. NASA GPM IMERG
- **Description**: Global Precipitation Measurement - IMERG daily rainfall
- **Access**: NASA Earthdata (requires free account login — not automatable headlessly)
- **License**: NASA Open Data
- **Features**: rainfall_1h, rainfall_6h, rainfall_12h, rainfall_24h, rainfall_48h, rainfall_7d, rainfall_intensity
- **Fallback**: Synthetic monsoon-pattern rainfall generator (Indian monsoon climatology)
- **Fallback label**: `data_source=gpm_synthetic`, `data_quality=simulated`

### 4. ISRIC SoilGrids
- **Description**: Global gridded soil information at 250m resolution
- **Access**: Public REST API (https://rest.isric.org) — no authentication required
- **License**: CC BY 4.0
- **Features**: soil_moisture, soil_texture, soil_ph, soil_organic_carbon
- **Real download**: Attempted for NER bounding box (22°N–30°N, 88°E–98°E)
- **Fallback label**: `data_source=soilgrids_synthetic`, `data_quality=simulated`

### 5. Copernicus Sentinel-1
- **Description**: SAR-derived ground deformation indicators
- **Access**: ESA Copernicus Data Space (requires registration)
- **License**: Copernicus Open Access
- **Features**: ground_displacement (mm/year from InSAR)
- **Fallback**: Synthetic deformation stub with realistic ranges for NER geology
- **Fallback label**: `data_source=sentinel1_synthetic`, `data_quality=simulated`

### 6. Copernicus Sentinel-2
- **Description**: Multispectral optical imagery for NDVI/land-cover
- **Access**: ESA Copernicus Data Space (requires registration)
- **License**: Copernicus Open Access
- **Features**: ndvi, land_cover
- **Fallback**: Synthetic NDVI/land-cover stub based on NER vegetation profiles
- **Fallback label**: `data_source=sentinel2_synthetic`, `data_quality=simulated`

### 7. SRTM DEM / Terrain
- **Description**: Shuttle Radar Topography Mission 1-arc-second DEM
- **Access**: USGS/NASA public — https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/
- **License**: Public Domain
- **Features**: elevation, slope, aspect, curvature, terrain_ruggedness
- **Real download**: Attempted via public SRTM tiles for NER
- **Fallback label**: `data_source=dem_synthetic`, `data_quality=simulated`

---

## Master Feature Schema

| Column | Type | Source | Description |
|---|---|---|---|
| latitude | float | all | WGS84 latitude (Y) |
| longitude | float | all | WGS84 longitude (X) |
| date | date | landslide | Event or observation date |
| state | str | admin | Indian state name |
| district | str | admin | District name |
| rainfall_1h | float | GPM | 1-hour accumulated rainfall (mm) |
| rainfall_6h | float | GPM | 6-hour accumulated rainfall (mm) |
| rainfall_12h | float | GPM | 12-hour accumulated rainfall (mm) |
| rainfall_24h | float | GPM | 24-hour accumulated rainfall (mm) |
| rainfall_48h | float | GPM | 48-hour accumulated rainfall (mm) |
| rainfall_7d | float | GPM | 7-day accumulated rainfall (mm) |
| rainfall_intensity | float | GPM | Peak intensity (mm/hr) |
| soil_moisture | float | SoilGrids | Volumetric water content (%) |
| soil_texture | str | SoilGrids | USDA texture class |
| soil_ph | float | SoilGrids | pH (H2O) |
| soil_organic_carbon | float | SoilGrids | SOC (g/kg) |
| elevation | float | DEM/SRTM | Elevation (m) |
| slope | float | DEM/SRTM | Slope (degrees) |
| aspect | float | DEM/SRTM | Aspect (degrees) |
| curvature | float | DEM/SRTM | Profile curvature |
| terrain_ruggedness | float | DEM/SRTM | TRI (Riley et al. 1999) |
| ndvi | float | Sentinel-2 | NDVI (-1 to 1) |
| land_cover | str | Sentinel-2 | Land cover class |
| distance_to_road | float | OSM | Distance to nearest road (km) |
| distance_to_river | float | OSM | Distance to nearest river (km) |
| historical_landslide_frequency | int | ISRO/COOLR | # events within 10km in past 10yr |
| historical_landslide_distance | float | ISRO/COOLR | Distance to nearest historical event (km) |
| ground_displacement | float | Sentinel-1 | LOS displacement (mm/year) |
| population_exposure | float | WorldPop | Population within 5km |
| infrastructure_exposure | float | OSM | Road length within 5km (km) |
| landslide_event | int | label | 1=landslide, 0=non-event |
| event_id | str | source | Canonical event identifier |
| data_source | str | pipeline | Source dataset name |
| data_quality | str | pipeline | 'real', 'processed', 'simulated' |

---

## Assumptions & Limitations

1. **Synthetic data dominates this version** due to API access restrictions. Real SoilGrids and DEM tiles are attempted.
2. **Negative samples** are generated from spatial-temporal contexts 20–100 km from confirmed events and ≥30 days offset from the event date.
3. **Temporal split** is used: train ≤ 2019, val = 2020–2021, test = 2022+.
4. **No future leakage**: all features represent conditions available at prediction time.
5. **NER focus**: ~70% of records are within the 8 NER states.
6. **Deduplication**: events within 5 km and 7 days of each other with the same trigger are merged.

---

## Processing Version

`pipeline_version: 0.1.0-prototype`
`generated: see dataset_manifest.json`
