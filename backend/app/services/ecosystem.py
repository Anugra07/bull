"""
Ecosystem classification and parameters based on ESA WorldCover land cover classes.
Drives: biomass formulas, sequestration rates, risk models, and baseline estimates.
"""
from typing import Dict, Tuple

# ESA WorldCover v200/2021 Land Cover Classes
# Reference: https://worldcover2021.esa.int/
WORLDCOVER_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen"
}

# Ecosystem types based on WorldCover classes
ECOSYSTEM_TYPES = {
    "Forest": [10, 95],  # Tree cover, Mangroves
    "Cropland": [40],
    "Grassland": [30],
    "Wetland": [90, 95, 80],  # Herbaceous wetland, Mangroves, Permanent water bodies
    "Shrubland": [20],
    "Plantation": [10],  # Tree cover - plantations are a subset but treated as forest
    "Degraded": [60],  # Bare / sparse vegetation
    "Other": [50, 70, 100]  # Built-up, Snow/ice, Moss
}

# Ecosystem-specific annual CO2 sequestration rates (tCO2e/ha/yr)
# Based on IPCC Tier 1 defaults and literature estimates
# Sources: IPCC Guidelines, regional sequestration studies

# Climate-specific forest sequestration rates (IPCC-based, adjusted for forest types)
# Boreal (|lat| > 55°): 1.5-4.4 tCO2e/ha/yr (using midpoint 3.0)
# Temperate (23.5° < |lat| <= 55°): 5.5-16.5 tCO2e/ha/yr (using midpoint 11.0)
# Tropical DRY (|lat| <= 23.5°): 3.5-6.0 tCO2e/ha/yr (using 5.0 for dry deciduous)
# Tropical RAINFOREST (|lat| <= 23.5° & Rainfall > 1500mm): 15-20 tCO2e/ha/yr (using 17.5)

def get_forest_sequestration_rate(latitude: float, rainfall: float = 0.0) -> float:
    """
    Get climate-specific forest sequestration rate based on latitude and rainfall.
    
    Args:
        latitude: Latitude in degrees (-90 to 90)
        rainfall: Annual rainfall in mm (optional, for tropical forest classification)
    
    Returns:
        Annual CO2 sequestration rate in tCO2e/ha/yr
    
    Note:
        Tropical rate varies: 5.0 for dry forests, 17.5 for rainforests (>1500mm rainfall).
    """
    abs_lat = abs(latitude)
    
    if abs_lat > 55:  # Boreal
        return 3.0
    elif abs_lat > 23.5:  # Temperate
        return 11.0
    else:  # Tropical
        # Distinguish between Dry Forest and Rainforest based on rainfall
        # Threshold: 1400mm/yr (captures most tropical rainforests including Amazon)
        # Amazon rainforest: typically 1500-3000mm, but transitional zones can be 1400-1500mm
        if rainfall > 1400:
            return 17.5  # Tropical Rainforest (IPCC: 14-29, using conservative 17.5)
        else:
            return 5.0  # Tropical Dry Forest (IPCC: 3.5-6.0)

# Base ecosystem sequestration rates (non-forest)
ECOSYSTEM_SEQUESTRATION_RATES = {
    "Forest": 11.0,  # Default temperate (will be overridden by climate function)
    "Mangrove": 10.0,  # Mangroves (User/Research: 8-12)
    "Cropland": 0.8,  # Agricultural soils (User: 0.5-1)
    "Grassland": 1.5,  # Managed grasslands (IPCC: ~1.3)
    "Wetland": 4.0,  # Wetlands/Peatlands (User: varies, Research: 2-5+)
    "Shrubland": 2.0,  # Shrublands (User: 1-3)
    "Plantation": 6.0,  # Managed plantations
    "Degraded": 0.3,  # Degraded land
    "Other": 0.0  # No significant sequestration
}

# Ecosystem-specific default risk factors
# Fire risk, drought risk, trend loss vary by ecosystem type
ECOSYSTEM_DEFAULT_RISKS = {
    "Forest": {
        "fire_risk": 0.08,
        "drought_risk": 0.04,
        "trend_loss": 0.02
    },
    "Mangrove": {
        "fire_risk": 0.01,  # Very low fire risk
        "drought_risk": 0.05,  # Moderate salinity/drought risk
        "trend_loss": 0.03  # Coastal development/erosion
    },
    "Cropland": {
        "fire_risk": 0.02,
        "drought_risk": 0.06,
        "trend_loss": 0.03
    },
    "Grassland": {
        "fire_risk": 0.05,
        "drought_risk": 0.05,
        "trend_loss": 0.02
    },
    "Wetland": {
        "fire_risk": 0.01,
        "drought_risk": 0.08,
        "trend_loss": 0.04
    },
    "Shrubland": {
        "fire_risk": 0.06,
        "drought_risk": 0.05,
        "trend_loss": 0.02
    },
    "Plantation": {
        "fire_risk": 0.07,
        "drought_risk": 0.03,
        "trend_loss": 0.01
    },
    "Degraded": {
        "fire_risk": 0.03,
        "drought_risk": 0.07,
        "trend_loss": 0.05
    },
    "Other": {
        "fire_risk": 0.01,
        "drought_risk": 0.01,
        "trend_loss": 0.01
    }
}


def classify_ecosystem(land_cover_class: int) -> str:
    """
    Classify ecosystem type based on ESA WorldCover land cover class.
    
    Args:
        land_cover_class: ESA WorldCover class code (10, 20, 30, etc.)
    
    Returns:
        Ecosystem type string: "Forest", "Mangrove", "Cropland", "Grassland", "Wetland", 
                               "Shrubland", "Plantation", "Degraded", or "Other"
    """
    for ecosystem_type, classes in ECOSYSTEM_TYPES.items():
        if land_cover_class in classes:
            # Special handling: Mangroves (95)
            if land_cover_class == 95:
                return "Mangrove"
            if ecosystem_type != "Other":  # Don't return "Other" unless no match
                return ecosystem_type
    
    return "Other"


def get_ecosystem_parameters(ecosystem_type: str, latitude: float = 0.0, rainfall: float = 0.0) -> Dict:
    """
    Get ecosystem-specific parameters for carbon calculations.
    
    Args:
        ecosystem_type: Ecosystem classification string
        latitude: Latitude in degrees (for climate-specific forest rates)
        rainfall: Annual rainfall in mm (for forest type distinction)
    
    Returns:
        Dictionary with:
        - sequestration_rate: Annual CO2 sequestration rate (tCO2e/ha/yr)
        - fire_risk: Default fire risk factor
        - drought_risk: Default drought risk factor
        - trend_loss: Default trend loss factor
    """
    # Use climate-specific rate for forests
    if ecosystem_type == "Forest":
        seq_rate = get_forest_sequestration_rate(latitude, rainfall)
    else:
        seq_rate = ECOSYSTEM_SEQUESTRATION_RATES.get(
            ecosystem_type, ECOSYSTEM_SEQUESTRATION_RATES["Other"]
        )
    
    return {
        "sequestration_rate": seq_rate,
        **ECOSYSTEM_DEFAULT_RISKS.get(
            ecosystem_type, ECOSYSTEM_DEFAULT_RISKS["Other"]
        )
    }


def get_ecosystem_info(land_cover_class: int, latitude: float = 0.0, rainfall: float = 0.0) -> Tuple[str, Dict]:
    """
    Get complete ecosystem information including classification and parameters.
    
    Args:
        land_cover_class: ESA WorldCover class code
        latitude: Latitude in degrees (for climate-specific rates)
        rainfall: Annual rainfall in mm
    
    Returns:
        Tuple of (ecosystem_type, parameters_dict)
    """
    ecosystem_type = classify_ecosystem(land_cover_class)
    parameters = get_ecosystem_parameters(ecosystem_type, latitude, rainfall)
    
    return ecosystem_type, parameters


