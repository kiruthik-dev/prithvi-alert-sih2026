# PrithviAlert — Dataset Validation Report

**Generated**: 2026-08-30

> PROTOTYPE: Models trained on this data are NOT scientifically validated for operational use.


---
## RAW DATA STATUS

Raw data directory: `C:\SIH2026 Project\prithvi-alert-sih\data\raw`

| Source | Requirement | File | Records | Status |
|---|---|---|---|---|
| isro_atlas | required | `isro_atlas_ner.csv` | 1200 | FOUND |
| nasa_coolr | required | `nasa_glc_ner.csv` | 800 | FOUND |
| gpm_imerg | optional | `gpm_rainfall_features.csv` | 2000 | FOUND |
| dem | optional | `terrain_features.csv` | None | MISSING |
| soilgrids | optional | `soilgrids_features.csv` | None | MISSING |
| sentinel2 | optional | `sentinel2_vegetation.csv` | None | MISSING |
| sentinel1 | optional | `sentinel1_deformation.csv` | None | MISSING |

**Required sources**: ✅ All present

**Optional missing**: dem, soilgrids, sentinel2, sentinel1


---
## PROCESSED DATA STATUS

| Dataset | Records | Positive | Negative | Invalid | Duplicate IDs |
|---|---|---|---|---|---|
| training_dataset | 4990 | 1996 | 2994 | 0 | 0 |
| train | 4303 | 1705 | 2598 | 0 | 0 |
| val | 459 | 198 | 261 | 0 | 0 |
| test | 228 | 93 | 135 | 0 | 0 |

### Full Dataset — Records by State

| State | Records |
|---|---|
| NER | 2994 |
| Arunachal Pradesh | 358 |
| Assam | 331 |
| Nagaland | 242 |
| Meghalaya | 236 |
| Manipur | 228 |
| Mizoram | 223 |
| Sikkim | 217 |
| Tripura | 161 |

### Full Dataset — Records by Source

| Source | Records |
|---|---|
| negative_sample_synthetic | 2994 |
| isro_atlas_synthetic | 1198 |
| nasa_coolr_synthetic | 798 |

### Missing Values (columns with > 0% missing)

| Feature | Missing Count | Missing % |
|---|---|---|
| elevation | 4990 | 100.0% |
| slope | 4990 | 100.0% |
| aspect | 4990 | 100.0% |
| curvature | 4990 | 100.0% |
| terrain_ruggedness | 4990 | 100.0% |
| soil_moisture | 4990 | 100.0% |
| soil_texture | 4990 | 100.0% |
| soil_ph | 4990 | 100.0% |
| soil_organic_carbon | 4990 | 100.0% |
| ndvi | 4990 | 100.0% |
| land_cover | 4990 | 100.0% |
| ground_displacement | 4990 | 100.0% |
| district | 2994 | 60.0% |

### Validity Issues

No validity issues detected.

### Feature Distributions

| Feature | Mean | Std | Min | P50 | Max | Missing% |
|---|---|---|---|---|---|---|
| rainfall_24h | 54.9857 | 64.5352 | 0.03 | 32.57 | 350.0 | 0.0% |

### Assumptions & Limitations

- All current inventory data is **synthetic/simulated** (labelled `data_quality=simulated`)

- Temporal split: TRAIN ≤ 2019, VAL 2020–2021, TEST ≥ 2022

- Models trained on this data are **research prototypes only**
