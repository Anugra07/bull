from typing import Dict, Tuple, Optional
from app.services.ecosystem import get_ecosystem_info, get_ecosystem_parameters

# Legacy default (kept for backward compatibility)
IPCC_TIER1_DEFAULT_TCO2_HA_YR = 3.0

# Global model variables
GEDI_MODEL = None
SOC_MODEL = None
MODELS_LOADED = False
VALID_ECOSYSTEMS = {
    "Forest",
    "Mangrove",
    "Cropland",
    "Grassland",
    "Wetland",
    "Shrubland",
    "Plantation",
    "Degraded",
    "Other",
}

def load_models():
    """Refresh runtime inference models and expose a coarse readiness flag."""
    global GEDI_MODEL, SOC_MODEL, MODELS_LOADED
    try:
        from app.services.inference import get_inference_engine

        engine = get_inference_engine()
        engine.reload()
        status = engine.status().get("models", {})
        GEDI_MODEL = engine.gedi_model
        SOC_MODEL = engine.soc_model
        MODELS_LOADED = any([
            bool(status.get("gedi_bias", {}).get("ready")),
            bool(status.get("soc_downscaling", {}).get("ready")),
            bool(status.get("stocking_index", {}).get("ready")),
        ])
    except Exception as e:
        MODELS_LOADED = False
        print(f"Error loading models: {e}")

def apply_ml_corrections(metrics: Dict[str, float]) -> Dict[str, float]:
    """
    Apply ML models to correct Biomass and SOC estimates.
    Returns updated metrics dictionary.
    """
    try:
        from app.services.inference import get_inference_engine

        inference = get_inference_engine().predict(metrics)
        updated_metrics = dict(inference.get("metrics", metrics))
        updated_metrics["biomass_source"] = inference.get("biomass_source")
        updated_metrics["soc_source"] = inference.get("soc_source")
        updated_metrics["model_version_biomass"] = inference.get("model_version_biomass")
        updated_metrics["model_version_soc"] = inference.get("model_version_soc")
        updated_metrics["ml_models_used"] = bool(inference.get("ml_models_used"))
        updated_metrics["prediction_interval_biomass"] = inference.get("biomass_interval")
        updated_metrics["prediction_interval_soc"] = inference.get("soc_interval")
        return updated_metrics
    except Exception as e:
        print(f"ML Correction Error: {e}")
        fallback = metrics.copy()
        fallback["ml_models_used"] = False
        return fallback


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
    
    # Get ecosystem type from land cover, with optional ML override.
    ecosystem_type, ecosystem_params = get_ecosystem_info(land_cover_class)
    override_ecosystem = metrics.get("ecosystem_type")
    if isinstance(override_ecosystem, str) and override_ecosystem in VALID_ECOSYSTEMS:
        ecosystem_type = override_ecosystem
        ecosystem_params = get_ecosystem_parameters(ecosystem_type)
    
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
    apply_ml: bool = True,
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
    
    # Apply ML corrections unless caller has already applied inference.
    if apply_ml:
        metrics = apply_ml_corrections(metrics)
    
    # Get ecosystem classification from land cover
    land_cover_class = int(metrics.get("land_cover", 0))
    
    # Extract latitude for climate-specific sequestration rates
    # Use elevation as proxy if available, otherwise default to 0 (tropical)
    # Better: extract from geometry centroid if available
    latitude = float(metrics.get("latitude", 0.0))
    rainfall = float(metrics.get("rainfall", 0.0))
    
    ecosystem_type, ecosystem_params = get_ecosystem_info(land_cover_class, latitude, rainfall)
    override_ecosystem = metrics.get("ecosystem_type")
    if isinstance(override_ecosystem, str) and override_ecosystem in VALID_ECOSYSTEMS:
        ecosystem_type = override_ecosystem
        ecosystem_params = get_ecosystem_parameters(ecosystem_type, latitude, rainfall)
    
    # Use ecosystem-specific parameters if not explicitly provided
    if annual_rate_tco2_ha_yr is None:
        annual_rate_tco2_ha_yr = ecosystem_params["sequestration_rate"]
    if fire_risk is None:
        fire_risk = ecosystem_params["fire_risk"]
    if drought_risk is None:
        drought_risk = ecosystem_params["drought_risk"]
    if trend_loss is None:
        trend_loss = ecosystem_params["trend_loss"]
    
    # Extract biomass components
    # NEW: Use total biomass (AGB + BGB) for accurate carbon accounting
    biomass_agb = float(metrics.get("biomass_aboveground", metrics.get("biomass", 0.0)))
    biomass_bgb = float(metrics.get("biomass_belowground", 0.0))
    biomass_total = float(metrics.get("biomass_total", biomass_agb))  # Fallback to AGB if total not available
    
    soc_pct = float(metrics.get("soc", 0.0))
    bulk_density_raw = float(metrics.get("bulk_density", 0.0))

    # Biomass carbon (tC/ha) - using 0.47 as IPCC carbon fraction of biomass
    # IMPORTANT: Now using TOTAL biomass (AGB + BGB) for accurate carbon stock
    carbon_biomass_agb_tc = biomass_agb * 0.47  # Above-ground carbon (tC/ha)
    carbon_biomass_bgb_tc = biomass_bgb * 0.47  # Below-ground carbon (tC/ha)
    carbon_biomass_tc = biomass_total * 0.47    # Total biomass carbon (tC/ha)

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
        # Missing biomass definition in legacy code, fixing context
        # assuming current_biomass variable reused or re-extract
        # To be safe, use biomass_total
        if biomass_total > 150 and soc_tC_per_ha > 50:
            baseline_condition = "Excellent"
        elif biomass_total > 75:
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

    # Calculate Total Carbon Stock (Biomass + SOC)
    carbon_biomass_total = carbon_biomass_tc * area_ha  # Total biomass carbon (tC)
    total_carbon_stock = carbon_biomass_total + soc_tC  # Total Carbon (Biomass + SOC)

    return (
        {
            "carbon_biomass": carbon_biomass_tc,  # Total biomass carbon (tC/ha) - NOW INCLUDES BGB
            "carbon_biomass_agb": carbon_biomass_agb_tc,  # NEW: Above-ground only (tC/ha)
            "carbon_biomass_bgb": carbon_biomass_bgb_tc,  # NEW: Below-ground only (tC/ha)
            "carbon_biomass_total": carbon_biomass_total,  # NEW: Total Biomass Carbon (tC)
            "soc_total": soc_tC,  # store in tC
            "total_carbon_stock": total_carbon_stock,      # NEW: Total Carbon Stock (tC)
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
            "ml_models_used": bool(metrics.get("ml_models_used", False)),
        },
    )
