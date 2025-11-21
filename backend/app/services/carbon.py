from typing import Dict, Tuple

# Simple IPCC Tier-1-like sequestration rates in tCO2e/ha/yr (very coarse placeholders)
# In a real system, index by ecozone/region/land cover.
IPCC_TIER1_DEFAULT_TCO2_HA_YR = 3.0  # conservative default placeholder


def compute_carbon(
    metrics: Dict[str, float],
    area_m2: float,
    soil_depth_m: float = 0.30,
    fire_risk: float = 0.05,
    drought_risk: float = 0.03,
    trend_loss: float = 0.02,
    annual_rate_tco2_ha_yr: float = IPCC_TIER1_DEFAULT_TCO2_HA_YR,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Compute biomass carbon, SOC total, annual CO2, 20-year CO2, and risk-adjusted CO2.
    Returns: (computed_values, risks)
    - computed_values contains keys: carbon_biomass, soc_total, annual_co2, co2_20yr, risk_adjusted_co2
    - risks contains risk components used

    Assumptions (MVP placeholders):
    - metrics['biomass'] assumed in t/ha (if not, treat as scalar proxy; MVP acceptable).
    - metrics['soc'] is percent; metrics['bulk_density'] in g/cm3 or kg/m3 is uncertain.
      For MVP, assume bulk_density provided in g/cm3; convert to kg/m3 by * 1000.
      SOC_total (kgC) = (soc%/100) * bulk_density(kg/m3) * depth(m) * area(m2)
      Convert kgC to tCO2e by * (44/12) / 1000.
    """
    biomass = float(metrics.get("biomass", 0.0))
    soc_pct = float(metrics.get("soc", 0.0))
    bulk_density_raw = float(metrics.get("bulk_density", 0.0))

    # Biomass carbon (tC/ha proxy -> convert to tCO2e? Requirement stores 'carbon_biomass' directly.)
    carbon_biomass_tc = biomass * 0.47  # tC/ha (proxy)

    # SOC total across polygon
    # Interpret bulk density as g/cm3 and convert to kg/m3
    bulk_density_kg_m3 = bulk_density_raw * 1000.0
    soc_fraction = soc_pct / 100.0
    soc_kgC = soc_fraction * bulk_density_kg_m3 * soil_depth_m * area_m2
    soc_tC = soc_kgC / 1000.0

    # Annual CO2 sequestration (tCO2e) using Tier-1 default per ha per yr
    area_ha = area_m2 / 10000.0
    annual_co2 = annual_rate_tco2_ha_yr * area_ha
    co2_20yr = annual_co2 * 20.0

    # Risk adjustment
    adj_factor = max(0.0, 1.0 - fire_risk - drought_risk - trend_loss)
    risk_adjusted_co2 = co2_20yr * adj_factor

    return (
        {
            "carbon_biomass": carbon_biomass_tc,
            "soc_total": soc_tC,  # store in tC
            "annual_co2": annual_co2,  # tCO2e/yr
            "co2_20yr": co2_20yr,      # tCO2e over 20 years
            "risk_adjusted_co2": risk_adjusted_co2,
        },
        {
            "fire_risk": fire_risk,
            "drought_risk": drought_risk,
            "trend_loss": trend_loss,
            "adj_factor": adj_factor,
        },
    )
