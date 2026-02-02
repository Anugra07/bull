# Ecosystem Classification System

## Overview
The system uses **ESA WorldCover v200/2021** (10m resolution) to classify land cover into ecosystem types, which then drives:
- **Biomass formula choice** (already implemented)
- **Sequestration rate** (now ecosystem-specific)
- **Risk model** (now ecosystem-specific)
- **Baseline estimate**

---

## ESA WorldCover to Ecosystem Mapping

| ESA WorldCover Class | Class Name | Ecosystem Type | Sequestration Rate (tCO2e/ha/yr) |
|---------------------|------------|----------------|----------------------------------|
| **10** | Tree cover | **Forest** | 4.5 |
| **95** | Mangroves | **Wetland** | 2.5 |
| **40** | Cropland | **Cropland** | 0.5 |
| **30** | Grassland | **Grassland** | 0.8 |
| **90** | Herbaceous wetland | **Wetland** | 2.5 |
| **80** | Permanent water bodies | **Wetland** | 2.5 |
| **20** | Shrubland | **Shrubland** | 1.2 |
| **10** | Tree cover (managed) | **Plantation** | 5.0 |
| **60** | Bare / sparse vegetation | **Degraded** | 0.2 |
| **50, 70, 100** | Built-up, Snow/ice, Moss | **Other** | 0.0 |

**Note**: Mangroves (95) are classified as **Wetland** (prioritized over Forest) due to their unique carbon dynamics.

---

## Ecosystem-Specific Sequestration Rates

### Forest
- **Rate**: 4.5 tCO2e/ha/yr
- **Range**: 3-6 tCO2e/ha/yr (tropical/subtropical forests)
- **Sources**: IPCC Guidelines, regional sequestration studies
- **Typical Uses**: Natural forests, woodlands

### Plantation
- **Rate**: 5.0 tCO2e/ha/yr
- **Range**: 4-7 tCO2e/ha/yr
- **Rationale**: Managed plantations often have higher sequestration due to:
  - Optimal species selection
  - Managed planting density
  - Fertilization and irrigation (when applicable)
  - Fast-growing species

### Wetland
- **Rate**: 2.5 tCO2e/ha/yr
- **Range**: 1-5 tCO2e/ha/yr (highly variable)
- **Includes**: Mangroves, herbaceous wetlands, permanent water bodies
- **Note**: Wetlands can be both carbon sinks (sequestration) and sources (methane emissions)

### Shrubland
- **Rate**: 1.2 tCO2e/ha/yr
- **Range**: 0.5-2.0 tCO2e/ha/yr
- **Typical Uses**: Mediterranean scrub, savanna understory

### Grassland
- **Rate**: 0.8 tCO2e/ha/yr
- **Range**: 0.3-1.5 tCO2e/ha/yr
- **Typical Uses**: Managed grasslands, pastures, rangelands

### Cropland
- **Rate**: 0.5 tCO2e/ha/yr
- **Range**: 0.2-1.0 tCO2e/ha/yr
- **Typical Uses**: Conservation agriculture, cover crops, agroforestry
- **Note**: Conventional agriculture often has negative or near-zero sequestration

### Degraded
- **Rate**: 0.2 tCO2e/ha/yr
- **Range**: 0.1-0.5 tCO2e/ha/yr
- **Typical Uses**: Restoration projects, reforestation of degraded land
- **Potential**: Can improve significantly with restoration interventions

### Other
- **Rate**: 0.0 tCO2e/ha/yr
- **Includes**: Built-up areas, snow/ice, moss/lichen
- **Note**: No significant sequestration potential

---

## Ecosystem-Specific Risk Factors

### Fire Risk
- **Highest**: Forest (0.08), Plantation (0.07)
- **Moderate**: Shrubland (0.06), Grassland (0.05)
- **Low**: Cropland (0.02), Degraded (0.03), Wetland (0.01)

### Drought Risk
- **Highest**: Wetland (0.08), Degraded (0.07), Cropland (0.06)
- **Moderate**: Grassland (0.05), Shrubland (0.05)
- **Lower**: Forest (0.04), Plantation (0.03)

### Trend Loss
- **Highest**: Degraded (0.05), Wetland (0.04)
- **Moderate**: Cropland (0.03)
- **Lower**: Forest (0.02), Grassland (0.02), Shrubland (0.02)
- **Lowest**: Plantation (0.01) - managed systems

---

## How It Works

### 1. Land Cover Classification
```python
# ESA WorldCover classification (10m resolution)
land_cover_class = 10  # Example: Tree cover

# Ecosystem classification
ecosystem_type = classify_ecosystem(land_cover_class)
# Returns: "Forest"
```

### 2. Parameter Lookup
```python
# Get ecosystem-specific parameters
params = get_ecosystem_parameters("Forest")
# Returns:
# {
#   "sequestration_rate": 4.5,
#   "fire_risk": 0.08,
#   "drought_risk": 0.04,
#   "trend_loss": 0.02
# }
```

### 3. Carbon Calculation
```python
# Use ecosystem-specific sequestration rate
annual_co2 = sequestration_rate * area_ha  # 4.5 tCO2e/ha/yr for Forest

# Use ecosystem-specific risk factors
adj_factor = 1 - fire_risk - drought_risk - trend_loss
risk_adjusted_co2 = co2_20yr * adj_factor
```

---

## Benefits

1. **Accurate Sequestration Estimates**: Ecosystem-specific rates reflect real-world variations
2. **Realistic Risk Assessment**: Risk factors vary by ecosystem type (wetlands have high drought risk, forests have high fire risk)
3. **Better Carbon Accounting**: Different ecosystems have different carbon dynamics
4. **Restoration Planning**: Degraded land shows potential for improvement
5. **Policy Alignment**: Aligned with IPCC guidelines and regional studies

---

## Future Enhancements

1. **Regional Variation**: Adjust rates based on climate zones (tropical, temperate, boreal)
2. **Forest Age/Stage**: Different rates for young vs. mature forests
3. **Management Practices**: Cropland rates vary by farming practices (organic, conservation, conventional)
4. **Wetland Methane Emissions**: Account for CH4 emissions in wetlands (net carbon impact)
5. **Time-Dependent Rates**: Sequestration rates change as ecosystems mature

---

*Last Updated: Implementation completed*




