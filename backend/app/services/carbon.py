from typing import Dict, Tuple, Optional
from app.services.ecosystem import get_ecosystem_info, classify_ecosystem

# Legacy default (kept for backward compatibility)
IPCC_TIER1_DEFAULT_TCO2_HA_YR = 3.0


def calculate_baseline_carbon(
    metrics: Dict[str, float],
    area_m2: float,
    land_cover_class: int,
) -> Dict[str, float]:
    """
    Calculate baseline (business-as-usual) carbon stock for MRV compliance.
    Uses trend data to determine appropriate baseline scenario.
    
    Baseline represents what would happen WITHOUT the project intervention.
    This is required for demonstrating additionality in carbon offset projects.
    
    Returns:
        Dict with baseline_biomass_carbon, baseline_soc_total, baseline_annual_co2,
        baseline_co2_20yr, and baseline_scenario
    """
    trend_class = str(metrics.get("trend_classification", "Unknown"))
    ndvi_trend = float(metrics.get("ndvi_trend", 0.0))
    fire_recent_burn = bool(metrics.get("fire_recent_burn", False))
    rainfall_anomaly_percent = float(metrics.get("rainfall_anomaly_percent", 0.0))
    
    # Get ecosystem type from land cover
    _, ecosystem_params = get_ecosystem_info(land_cover_class)
    
    # Determine baseline scenario and degradation factors
    # These represent "business-as-usual" without project intervention
    
    if "Degrading" in trend_class or ndvi_trend < -0.02:
        # Scenario: Continued degradation
        baseline_biomass_factor = 0.6  # 60% of current biomass (degraded)
        baseline_soc_factor = 0.7      # 70% of current SOC (soil degradation)
        baseline_seq_rate = 0.0        # No sequestration in degraded state
        scenario_description = "Continued Degradation"
        
    elif "Fire-Impacted" in trend_class or fire_recent_burn:
        # Scenario: Post-fire degraded state
        baseline_biomass_factor = 0.4  # 40% of current (fire impact)
        baseline_soc_factor = 0.8      # 80% of current (less soil impact)
        baseline_seq_rate = 0.5        # Minimal natural recovery (tCO2e/ha/yr)
        scenario_description = "Post-Fire Degraded State"
        
    elif "Drought" in trend_class or rainfall_anomaly_percent < -20:
        # Scenario: Drought-stressed degraded state
        baseline_biomass_factor = 0.7  # 70% of current
        baseline_soc_factor = 0.75     # 75% of current
        baseline_seq_rate = 0.8        # Reduced sequestration (tCO2e/ha/yr)
        scenario_description = "Drought-Stressed Degradation"
        
    elif "Improving" in trend_class or "Regenerating" in trend_class:
        # Scenario: Natural regeneration (conservative baseline)
        # This is conservative - assumes some natural recovery without project
        baseline_biomass_factor = 0.85  # 85% of current (natural improvement)
        baseline_soc_factor = 0.9       # 90% of current
        baseline_seq_rate = ecosystem_params["sequestration_rate"] * 0.5  # Half the rate
        scenario_description = "Natural Regeneration (Conservative)"
        
    else:  # Stable or Unknown
        # Scenario: Status quo maintained with slight degradation
        baseline_biomass_factor = 0.95  # 95% of current (slight degradation over time)
        baseline_soc_factor = 0.95      # 95% of current
        baseline_seq_rate = ecosystem_params["sequestration_rate"] * 0.3  # Minimal sequestration
        scenario_description = "Status Quo Maintenance"
    
    # Calculate baseline carbon stocks
    current_biomass = float(metrics.get("biomass", 0.0))
    current_soc_tc_ha = float(metrics.get("soc", 0.0))
    area_ha = area_m2 / 10000.0
    
    # Baseline biomass carbon (tC/ha)
    baseline_biomass_tc = current_biomass * baseline_biomass_factor * 0.47
    
    # Baseline SOC (tC total for entire area)
    baseline_soc_tc = current_soc_tc_ha * baseline_soc_factor * area_ha
    
    # Baseline annual CO2 sequestration (tCO2e/yr)
    baseline_annual_co2 = baseline_seq_rate * area_ha
    
    # Baseline 20-year CO2 (tCO2e)
    baseline_co2_20yr = baseline_annual_co2 * 20.0
    
    return {
        "baseline_biomass_carbon": baseline_biomass_tc,
        "baseline_soc_total": baseline_soc_tc,
        "baseline_annual_co2": baseline_annual_co2,
        "baseline_co2_20yr": baseline_co2_20yr,
        "baseline_scenario": scenario_description,
    }


def compute_carbon(
    metrics: Dict[str, float],
    area_m2: float,
    fire_risk: Optional[float] = None,
    drought_risk: Optional[float] = None,
    trend_loss: Optional[float] = None,
    annual_rate_tco2_ha_yr: Optional[float] = None,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Compute biomass carbon, SOC total, annual CO2, 20-year CO2, and risk-adjusted CO2.
    Returns: (computed_values, risks)
    - computed_values contains keys: carbon_biomass, soc_total, annual_co2, co2_20yr, risk_adjusted_co2, ecosystem_type
    - risks contains risk components used

    Ecosystem-specific parameters:
    - Sequestration rates, fire risk, drought risk, and trend loss are determined
      from land cover classification (ESA WorldCover) if not explicitly provided.
    
    Assumptions:
    - metrics['biomass'] assumed in t/ha (from GEDI AGB or allometric equations).
    - metrics['soc'] is percent; metrics['bulk_density'] in g/cm3.
      SOC_total (kgC) = (soc%/100) * bulk_density(kg/m3) * depth(m) * area(m2)
      Convert kgC to tCO2e by * (44/12) / 1000.
    """
    # Get ecosystem classification from land cover
    land_cover_class = int(metrics.get("land_cover", 0))
    
    # Extract latitude for climate-specific sequestration rates
    # Use elevation as proxy if available, otherwise default to 0 (tropical)
    # Better: extract from geometry centroid if available
    latitude = float(metrics.get("latitude", 0.0))
    
    _, ecosystem_params = get_ecosystem_info(land_cover_class, latitude)
    
    # Use ecosystem-specific parameters if not explicitly provided
    if annual_rate_tco2_ha_yr is None:
        annual_rate_tco2_ha_yr = ecosystem_params["sequestration_rate"]
    if fire_risk is None:
        fire_risk = ecosystem_params["fire_risk"]
    if drought_risk is None:
        drought_risk = ecosystem_params["drought_risk"]
    if trend_loss is None:
        trend_loss = ecosystem_params["trend_loss"]
    
    biomass = float(metrics.get("biomass", 0.0))
    soc_pct = float(metrics.get("soc", 0.0))
    bulk_density_raw = float(metrics.get("bulk_density", 0.0))

    # Biomass carbon (tC/ha) - using 0.47 as carbon fraction of biomass
    carbon_biomass_tc = biomass * 0.47  # tC/ha

    # SOC total across polygon
    # Pre-calculated in GEE analysis based on selected depth
    soc_tC_per_ha = float(metrics.get("soc", 0.0))
    
    # Convert per-ha to total for the area
    area_ha = area_m2 / 10000.0
    soc_tC = soc_tC_per_ha * area_ha

    # Annual CO2 sequestration (tCO2e) - ecosystem-specific rate
    area_ha = area_m2 / 10000.0
    annual_co2 = annual_rate_tco2_ha_yr * area_ha
    co2_20yr = annual_co2 * 20.0

    # Risk adjustment using ecosystem-specific risk factors
    # ENHANCED: Adjust risks based on time-series trend data if available
    ndvi_trend = float(metrics.get("ndvi_trend", 0.0))
    fire_burn_percent = float(metrics.get("fire_burn_percent", 0.0))
    fire_recent_burn = bool(metrics.get("fire_recent_burn", False))
    rainfall_anomaly_percent = float(metrics.get("rainfall_anomaly_percent", 0.0))
    
    # Adjust fire risk based on historical data
    if fire_recent_burn:
        fire_risk = min(fire_risk + 0.05, 0.95)  # Increase by 5% if recent burn
    if fire_burn_percent > 10:
        fire_risk = min(fire_risk + 0.03, 0.95)  # Increase by 3% if >10% burned
    
    # Adjust drought risk based on rainfall anomaly
    if rainfall_anomaly_percent < -20:
        drought_risk = min(drought_risk + 0.04, 0.95)  # Increase by 4% if severe drought
    
    # Adjust trend loss based on NDVI trend
    if ndvi_trend < -0.02:  # Degrading trend
        trend_loss = min(trend_loss + 0.03, 0.95)  # Increase by 3%
    elif ndvi_trend > 0.02:  # Improving trend
        trend_loss = max(trend_loss - 0.02, 0.0)  # Decrease by 2%
    
    # Calculate overall adjustment factor
    adj_factor = max(0.0, 1.0 - fire_risk - drought_risk - trend_loss)
    risk_adjusted_co2 = co2_20yr * adj_factor
    
    # Determine baseline condition
    baseline_condition = "Unknown"
    trend_class = str(metrics.get("trend_classification", "Unknown"))
    
    if trend_class in ["Degrading", "Fire-Impacted", "Drought-Stressed"]:
        baseline_condition = "Degraded"
    elif trend_class == "Stable":
        if biomass > 150 and soc_tC_per_ha > 50:
            baseline_condition = "Excellent"
        elif biomass > 75:
            baseline_condition = "Good"
        else:
            baseline_condition = "Stable"
    elif "Improving" in trend_class or "Regenerating" in trend_class:
        baseline_condition = "Improving"
    elif "Recovering" in trend_class:
        baseline_condition = "Recovering"

    
    # BASELINE CARBON STOCK CALCULATION (MRV Compliance)
    # Calculate what would happen WITHOUT the project (business-as-usual)
    baseline_values = calculate_baseline_carbon(metrics, area_m2, land_cover_class)
    
    # PROJECT Carbon values are what we calculated above (WITH the project)
    project_annual_co2 = annual_co2
    project_co2_20yr = co2_20yr
    
    # ADDITIONALITY = Project - Baseline (Carbon Credits)
    additionality_annual_co2 = project_annual_co2 - baseline_values["baseline_annual_co2"]
    additionality_20yr = project_co2_20yr - baseline_values["baseline_co2_20yr"]
    
    # Ensure additionality is non-negative (conservative approach)
    additionality_annual_co2 = max(0.0, additionality_annual_co2)
    additionality_20yr = max(0.0, additionality_20yr)

    return (
        {
            "carbon_biomass": carbon_biomass_tc,
            "soc_total": soc_tC,  # store in tC
            "annual_co2": annual_co2,  # tCO2e/yr (kept for backward compatibility)
            "co2_20yr": co2_20yr,      # tCO2e over 20 years (kept for backward compatibility)
            "risk_adjusted_co2": risk_adjusted_co2,
            "ecosystem_type": ecosystem_type,  # Ecosystem classification
            "baseline_condition": baseline_condition,  # Overall baseline assessment
            # BASELINE Carbon Stock (MRV)
            "baseline_biomass_carbon": baseline_values["baseline_biomass_carbon"],
            "baseline_soc_total": baseline_values["baseline_soc_total"],
            "baseline_annual_co2": baseline_values["baseline_annual_co2"],
            "baseline_co2_20yr": baseline_values["baseline_co2_20yr"],
            "baseline_scenario": baseline_values["baseline_scenario"],
            # PROJECT Carbon Stock (clarified names)
            "project_annual_co2": project_annual_co2,
            "project_co2_20yr": project_co2_20yr,
            # ADDITIONALITY (Carbon Credits)
            "additionality_annual_co2": additionality_annual_co2,
            "additionality_20yr": additionality_20yr,
        },
        {
            "fire_risk": fire_risk,
            "drought_risk": drought_risk,
            "trend_loss": trend_loss,
            "adj_factor": adj_factor,
            "sequestration_rate": annual_rate_tco2_ha_yr,  # Rate used (tCO2e/ha/yr)
        },
    )
