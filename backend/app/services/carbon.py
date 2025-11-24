from typing import Dict, Tuple, Optional
from app.services.ecosystem import get_ecosystem_info, classify_ecosystem

# Legacy default (kept for backward compatibility)
IPCC_TIER1_DEFAULT_TCO2_HA_YR = 3.0


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
    ecosystem_type, ecosystem_params = get_ecosystem_info(land_cover_class)
    
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
    adj_factor = max(0.0, 1.0 - fire_risk - drought_risk - trend_loss)
    risk_adjusted_co2 = co2_20yr * adj_factor

    return (
        {
            "carbon_biomass": carbon_biomass_tc,
            "soc_total": soc_tC,  # store in tC
            "annual_co2": annual_co2,  # tCO2e/yr
            "co2_20yr": co2_20yr,      # tCO2e over 20 years
            "risk_adjusted_co2": risk_adjusted_co2,
            "ecosystem_type": ecosystem_type,  # Ecosystem classification
        },
        {
            "fire_risk": fire_risk,
            "drought_risk": drought_risk,
            "trend_loss": trend_loss,
            "adj_factor": adj_factor,
            "sequestration_rate": annual_rate_tco2_ha_yr,  # Rate used (tCO2e/ha/yr)
        },
    )
