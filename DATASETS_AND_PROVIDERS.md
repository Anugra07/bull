# Datasets and Providers Documentation

This document provides a detailed overview of the datasets and data providers used in the **Bull - Carbon Offset Land Analyzer**. The system leverages a multi-source fusion approach, combining optical imagery, LIDAR, radar, and climate data to provide accurate carbon estimation and risk assessment.

## 1. Primary Data Providers

The platform relies on the following major scientific organizations and data providers:

| Provider | Role | Key Datasets |
| :--- | :--- | :--- |
| **Google Earth Engine (GEE)** | **Compute & Data Platform** | Hosts and processes PB-scale geospatial datasets |
| **NASA** (USA) | **LIDAR & Fire Data** | GEDI (Biomass/Height), MODIS (Fire), SRTM (Elevation) |
| **ESA** (Europe) | **Optical & Radar** | Sentinel-2 (Vegetation), WorldCover (Land Cover), CCI (Biomass) |
| **Copernicus** (EU) | **Program** | Sentinel Mission (High-resolution optical imagery) |
| **UCSB / CHG** | **Climate Data** | CHIRPS (Rainfall/Precipitation) |
| **OpenLandMap** | **Soil Data** | Soil Organic Carbon, Bulk Density |
| **Woods Hole (WHRC)** | **Historical Baseline** | Pantropical Biomass (Legacy comparison) |

---

## 2. Detailed Dataset Breakdown

### 2.1. Biomass & Structure (LIDAR)

These datasets are critical for calculating Above-Ground Biomass (AGB) and Canopy Height.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **GEDI L4A Monthly AGBD** | `LARSE/GEDI/GEDI04_A_002_MONTHLY` | ~25m (footprint) | Monthly | **Primary Source** for Biomass. Includes bias correction. |
| **GEDI L4A Annual AGBD** | `LARSE/GEDI/GEDI04_A_002` | ~25m (footprint) | Annual | **Secondary Source** if monthly data is missing. |
| **GEDI L2A Canopy Height** | `LARSE/GEDI/GEDI02_A_002_MONTHLY` | ~25m (footprint) | Monthly | **Primary Source** for Canopy Height (`rh98`). Used for allometric fallbacks. |
| **ESA CCI Biomass** | `ESA/CCI/BIOMASS/v4` | 100m | Annual | **Fallback** (Global) if GEDI coverage is zero. |
| **WHRC Pantropical** | `WHRC/biomass/tropical` | 30m | Static (c. 2000) | **Tertiary Fallback** (Tropics only). |

**Note on GEDI**: We apply ecosystem-specific bias corrections (+10% to +35%) to GEDI L4A data based on recent research (Taylor & Francis, 2023) indicating systematic underestimation in dense forests.

### 2.2. Vegetation & Optical Imagery

Used for vegetation indices (NDVI, EVI), phenology, and time-series trend analysis.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Sentinel-2 MSA/SR** | `COPERNICUS/S2_SR_HARMONIZED` | 10m / 20m | ~5 days | **Vegetation health** (NDVI, EVI), trend analysis, and QA/QC. |
| **ESA WorldCover** | `ESA/WorldCover/v200/2021` | 10m | Annual (2021) | **Land Cover Classification**. Determines ecosystem type and risk factors. |

**Processing**:
- **Cloud Masking**: Uses the Scene Classification Layer (SCL) to mask clouds, shadows, and cirrus.
- **Composites**: Seasonal composites (Dry/Wet) are generated to minimize cloud cover impact.

### 2.3. Soil (Geochemistry)

Used to calculate Soil Organic Carbon (SOC) stock.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **OpenLandMap SOC** | `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02` | 250m | Static (Interpolated) | **Soil Organic Carbon** content (g/kg) at 6 standard depths. |
| **OpenLandMap Bulk Density** | `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02` | 250m | Static (Interpolated) | **Bulk Density** (kg/m³) at 6 depths. Essential for converting SOC to t/ha. |

### 2.4. Climate & Weather

Used for drought risk assessment, rainfall anomalies, and climate zone determination.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **CHIRPS Daily** | `UCSB-CHG/CHIRPS/DAILY` | 5.5km (0.05°) | Daily | **Rainfall Analysis**. Calculates annual mean and long-term anomalies. |

### 2.5. Terrain & Topography

Used into risk models and for correcting satellite observations.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **NASADEM / SRTM** | `USGS/SRTMGL1_003` | 30m | Static | **Elevation and Slope**. |

### 2.6. Fire & Disturbance

Used to detect degradation and risk.

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **MODIS Burned Area** | `MODIS/006/MCD64A1` | 500m | Monthly | **Fire Detection**. Identifies burn scars and calculates burned area %. |

---

## 3. Data Integration Strategy

### 3.1. Implementation Hierarchy (Biomass)

To ensure maximum coverage and accuracy, we use a waterfall "fallback" logic for biomass estimation:

1.  **GEDI L4A Monthly** (Highest Precision, Limited Coverage)
    *   *If valid shots exist inside polygon -> Use Mean AGBD + Bias Correction*
2.  **GEDI L4A Annual** (High Precision, Better Coverage)
    *   *If monthly missing -> Use Annual AGBD + Bias Correction*
3.  **ESA CCI Biomass** (Medium Precision, Global Coverage)
    *   *If GEDI missing -> Use ESA CCI (2020)*
4.  **Allometric Equations** (Estimation)
    *   *If all direct biomass data missing -> Calculate from GEDI Canopy Height + Ecosystem Type*
5.  **Zero/No Data**
    *   *If no canopy height available -> Return 0 (requires manual review)*

### 3.2. Data Processing Pipeline

1.  **Ingestion**: Receives a GeoJSON polygon.
2.  **Geometry Analysis**: Computes centroid to determine **Latitude/Climate Zone**.
3.  **Land Cover Classification**:
    *   Queries `ESA WorldCover`.
    *   Applies **Intelligent Snapping**: If standard classification fails or is ambiguous (e.g., misclassified tropical forest), uses latitude and NDVI context to correct the class.
4.  **Carbon Stock Calculation**:
    *   **Above-Ground**: GEDI/Fallback + Bias Correction.
    *   **Below-Ground**: Applies IPCC Root-to-Shoot ratios based on Ecosystem and Climate Zone.
    *   **Soil**: Integrates OpenLandMap SOC layers (typically 0-30cm).
5.  **Risk & Trend Analysis**:
    *   Computes 5-year NDVI trend slope.
    *   Checks for MODIS fire scars (>25ha or >10% area).
    *   Compares 5-year Rainfall vs 25-year baseline (Anomaly %).
6.  **QC & Scoring**:
    *   Calculates a **Data Confidence Score (0-100)** based on:
        *   Pixel count quality
        *   Cloud coverage %
        *   Presence of GEDI shots
        *   Signal noise (StdDev)
        *   Source tier (GEDI = high, Allometric = low)

## 4. References

*   **Sentinel-2**: [Copernicus Guide](https://sentinel.esa.int/web/sentinel/missions/sentinel-2)
*   **GEDI**: [NASA GEDI Mission](https://gedi.umd.edu/)
*   **ESA WorldCover**: [ESA WorldCover Product](https://esa-worldcover.org/en)
*   **OpenLandMap**: [OpenGeoHub](https://openlandmap.org/)
*   **CHIRPS**: [UCSB Climate Hazards Group](https://www.chc.ucsb.edu/data/chirps)
