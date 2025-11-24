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
ECOSYSTEM_SEQUESTRATION_RATES = {
    "Forest": 4.5,  # Tropical/subtropical forests: 3-6 tCO2e/ha/yr
    "Cropland": 0.5,  # Agricultural soils: 0.2-1.0 tCO2e/ha/yr (conservation agriculture)
    "Grassland": 0.8,  # Managed grasslands: 0.3-1.5 tCO2e/ha/yr
    "Wetland": 2.5,  # Wetlands: 1-5 tCO2e/ha/yr (highly variable)
    "Shrubland": 1.2,  # Shrublands: 0.5-2.0 tCO2e/ha/yr
    "Plantation": 5.0,  # Managed plantations: 4-7 tCO2e/ha/yr (higher than natural forests)
    "Degraded": 0.2,  # Degraded land: 0.1-0.5 tCO2e/ha/yr (restoration potential)
    "Other": 0.0  # No significant sequestration for built-up, snow/ice, etc.
}

# Ecosystem-specific default risk factors
# Fire risk, drought risk, trend loss vary by ecosystem type
ECOSYSTEM_DEFAULT_RISKS = {
    "Forest": {
        "fire_risk": 0.08,  # Higher fire risk in forests
        "drought_risk": 0.04,  # Moderate drought sensitivity
        "trend_loss": 0.02  # Deforestation/degradation trend
    },
    "Cropland": {
        "fire_risk": 0.02,  # Lower fire risk
        "drought_risk": 0.06,  # Higher drought risk (agricultural dependency)
        "trend_loss": 0.03  # Land conversion/erosion
    },
    "Grassland": {
        "fire_risk": 0.05,  # Moderate fire risk
        "drought_risk": 0.05,  # Moderate drought sensitivity
        "trend_loss": 0.02  # Overgrazing/land conversion
    },
    "Wetland": {
        "fire_risk": 0.01,  # Very low fire risk
        "drought_risk": 0.08,  # High drought risk (water dependency)
        "trend_loss": 0.04  # Drainage/drying trends
    },
    "Shrubland": {
        "fire_risk": 0.06,  # Moderate-high fire risk
        "drought_risk": 0.05,  # Moderate drought tolerance
        "trend_loss": 0.02  # Degradation/desertification
    },
    "Plantation": {
        "fire_risk": 0.07,  # Higher fire risk (managed, uniform)
        "drought_risk": 0.03,  # Lower drought risk (often irrigated/selected species)
        "trend_loss": 0.01  # Lower trend loss (managed systems)
    },
    "Degraded": {
        "fire_risk": 0.03,  # Low fire risk (sparse vegetation)
        "drought_risk": 0.07,  # High drought sensitivity
        "trend_loss": 0.05  # High degradation trend
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
        Ecosystem type string: "Forest", "Cropland", "Grassland", "Wetland", 
                               "Shrubland", "Plantation", "Degraded", or "Other"
    """
    for ecosystem_type, classes in ECOSYSTEM_TYPES.items():
        if land_cover_class in classes:
            # Special handling: Mangroves (95) could be both Forest and Wetland
            # Prioritize Wetland for mangroves
            if land_cover_class == 95:
                return "Wetland"
            if ecosystem_type != "Other":  # Don't return "Other" unless no match
                return ecosystem_type
    
    return "Other"


def get_ecosystem_parameters(ecosystem_type: str) -> Dict:
    """
    Get ecosystem-specific parameters for carbon calculations.
    
    Args:
        ecosystem_type: Ecosystem classification string
    
    Returns:
        Dictionary with:
        - sequestration_rate: Annual CO2 sequestration rate (tCO2e/ha/yr)
        - fire_risk: Default fire risk factor
        - drought_risk: Default drought risk factor
        - trend_loss: Default trend loss factor
    """
    return {
        "sequestration_rate": ECOSYSTEM_SEQUESTRATION_RATES.get(
            ecosystem_type, ECOSYSTEM_SEQUESTRATION_RATES["Other"]
        ),
        **ECOSYSTEM_DEFAULT_RISKS.get(
            ecosystem_type, ECOSYSTEM_DEFAULT_RISKS["Other"]
        )
    }


def get_ecosystem_info(land_cover_class: int) -> Tuple[str, Dict]:
    """
    Get complete ecosystem information including classification and parameters.
    
    Args:
        land_cover_class: ESA WorldCover class code
    
    Returns:
        Tuple of (ecosystem_type, parameters_dict)
    """
    ecosystem_type = classify_ecosystem(land_cover_class)
    parameters = get_ecosystem_parameters(ecosystem_type)
    
    return ecosystem_type, parameters

