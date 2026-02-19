"""
CarbonAnalyzerV2.1 — ML-enhanced carbon analysis with Verra-calibrated SI models.

Combines:
  1. GEDI Bias Correction (Phase 1)
  2. SOC Downscaling (Phase 1)
  3. Ecosystem-specific Stocking Index → Biomass models (Phase 2, Verra-calibrated)

The SI models are preferred when the ecosystem matches a calibrated model,
falling back to the general GEDI bias correction model otherwise.
"""

import os
from pathlib import Path
import joblib
import pandas as pd
from typing import Dict, Any, Optional


class CarbonAnalyzerV2_1:
    """
    ML-enhanced carbon analyzer with Verra-calibrated Stocking Index models.
    
    Prediction priority:
      1. Verra-calibrated SI model (if ecosystem match) → confidence 85
      2. GEDI bias correction model (general) → confidence 75
      3. Raw GEE biomass (no ML) → confidence 60
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            backend_dir = Path(__file__).resolve().parents[2]
            model_dir = str(backend_dir / 'ml' / 'models')
        
        self.model_dir = model_dir
        self.gedi_model = None
        self.soc_model = None
        self.si_models = {}  # ecosystem → {model, features, cv_rmse}
        self.loaded = False
        
        self._load_models()
    
    def _load_models(self):
        """Load all available models."""
        # Phase 1: GEDI Bias Correction
        gedi_path = os.path.join(self.model_dir, 'gedi_bias_v1.pkl')
        if os.path.exists(gedi_path):
            try:
                self.gedi_model = joblib.load(gedi_path)
                print(f"✓ Loaded GEDI bias model")
            except Exception as e:
                print(f"⚠ Could not load GEDI model: {e}")
        
        # Phase 1: SOC Downscaling
        soc_path = os.path.join(self.model_dir, 'soc_downscaling_xgb_v1.pkl')
        if os.path.exists(soc_path):
            try:
                self.soc_model = joblib.load(soc_path)
                print(f"✓ Loaded SOC model")
            except Exception as e:
                print(f"⚠ Could not load SOC model: {e}")
        
        # Phase 2: SI Calibration (ecosystem-specific)
        si_path = os.path.join(self.model_dir, 'stocking_index_calibrated_v1.pkl')
        if os.path.exists(si_path):
            try:
                self.si_models = joblib.load(si_path)
                ecosystems = list(self.si_models.keys())
                print(f"✓ Loaded SI models for: {ecosystems}")
            except Exception as e:
                print(f"⚠ Could not load SI models: {e}")
        
        self.loaded = True
    
    def classify_ecosystem(self, features: Dict[str, Any]) -> str:
        """
        Classify ecosystem from features.
        Uses land_cover class + latitude + NDVI heuristics.
        """
        land_cover = features.get('land_cover', 0)
        latitude = abs(features.get('latitude', 0))
        ndvi = features.get('ndvi', features.get('ndvi_mean', 0))
        
        # ESA WorldCover class mapping
        if land_cover == 10:  # Tree cover
            if latitude < 23.5:
                return 'tropical_forest'
            else:
                return 'temperate_forest'
        elif land_cover == 20:  # Shrubland
            return 'grassland'
        elif land_cover == 30:  # Grassland
            return 'grassland'
        elif land_cover == 95:  # Mangroves
            return 'mangrove'
        elif land_cover == 40:  # Cropland
            if ndvi and ndvi > 0.5:
                return 'plantation'  # Likely agroforestry
            return 'grassland'
        else:
            if ndvi and ndvi > 0.6:
                return 'tropical_forest' if latitude < 23.5 else 'temperate_forest'
            return 'grassland'

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _build_feature_frame(
        self,
        model: Any,
        numeric_values: Dict[str, float],
        ecosystem_label: str,
        climate_label: str,
    ) -> Optional[pd.DataFrame]:
        if model is None or not hasattr(model, "feature_names_in_"):
            return None

        feature_names = [str(x) for x in list(model.feature_names_in_)]
        row = {name: 0.0 for name in feature_names}

        for name, value in numeric_values.items():
            if name in row:
                row[name] = self._to_float(value)

        for name in feature_names:
            if name.startswith("ecosystem_"):
                category = name.replace("ecosystem_", "", 1)
                row[name] = 1.0 if category.lower() == ecosystem_label.lower() else 0.0
            if name.startswith("climate_zone_"):
                category = name.replace("climate_zone_", "", 1)
                row[name] = 1.0 if category.lower() == climate_label.lower() else 0.0

        return pd.DataFrame([row], columns=feature_names)
    
    def predict_biomass(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict biomass using the best available model.
        
        Returns:
            {mean, source, confidence, rmse_estimate}
        """
        ecosystem = self.classify_ecosystem(features)
        
        # Priority 1: Verra-calibrated SI model
        if ecosystem in self.si_models:
            si_entry = self.si_models[ecosystem]
            model = si_entry['model']
            model_features = si_entry['features']
            
            # Build feature vector
            X = pd.DataFrame([{
                f: features.get(f, features.get(f'_{f}', 0))
                for f in model_features
            }])
            
            biomass = float(model.predict(X)[0])
            
            return {
                'mean': max(0.0, biomass),
                'source': f'Verra_calibrated_SI_{ecosystem}',
                'confidence': 85,
                'rmse_estimate': si_entry.get('cv_rmse', 30.0),
                'ecosystem': ecosystem,
            }
        
        # Priority 2: GEDI bias correction (general model)
        if self.gedi_model:
            try:
                latitude = abs(self._to_float(features.get('latitude'), 0.0))
                climate = "Tropical" if latitude < 23.5 else "Temperate"
                ecosystem_label = {
                    "tropical_forest": "Forest",
                    "temperate_forest": "Forest",
                    "mangrove": "Forest",
                    "plantation": "Forest",
                    "grassland": "Grassland",
                }.get(ecosystem, "Forest")

                numeric = {
                    "gedi_agbd_raw": self._to_float(features.get('gedi_agbd_raw', features.get('biomass')), 0.0),
                    "ndvi_mean": self._to_float(features.get('ndvi_mean', features.get('ndvi')), 0.0),
                    "evi_mean": self._to_float(features.get('evi_mean', features.get('evi')), 0.0),
                    "elevation": self._to_float(features.get('elevation'), 0.0),
                    "slope": self._to_float(features.get('slope'), 0.0),
                    "rainfall_annual": self._to_float(features.get('rainfall_annual', features.get('rainfall')), 0.0),
                    "latitude": self._to_float(features.get('latitude'), 0.0),
                }

                X = self._build_feature_frame(self.gedi_model, numeric, ecosystem_label, climate)
                if X is None:
                    raise ValueError("GEDI model feature schema unavailable")

                pred = float(self.gedi_model.predict(X)[0])
                return {
                    'mean': max(0.0, pred),
                    'source': 'ML_corrected_GEDI',
                    'confidence': 75,
                    'rmse_estimate': 35.0,
                    'ecosystem': ecosystem,
                }
            except Exception:
                pass
        
        # Priority 3: Raw GEE value
        raw = features.get('biomass', features.get('biomass_aboveground', 0))
        return {
            'mean': max(0.0, float(raw)),
            'source': 'raw_GEE',
            'confidence': 60,
            'rmse_estimate': 50.0,
            'ecosystem': ecosystem,
        }
    
    def predict_soc(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict SOC using the SOC downscaling model."""
        if self.soc_model:
            try:
                latitude = abs(self._to_float(features.get('latitude'), 0.0))
                climate = "Tropical" if latitude < 23.5 else "Temperate"
                ecosystem_label = "Forest"
                if int(self._to_float(features.get("land_cover"), 0)) in (30, 90):
                    ecosystem_label = "Grassland"
                elif int(self._to_float(features.get("land_cover"), 0)) == 40:
                    ecosystem_label = "Cropland"

                numeric = {
                    "ndvi_mean": self._to_float(features.get("ndvi_mean", features.get("ndvi")), 0.0),
                    "evi_mean": self._to_float(features.get("evi_mean", features.get("evi")), 0.0),
                    "elevation": self._to_float(features.get("elevation"), 0.0),
                    "slope": self._to_float(features.get("slope"), 0.0),
                    "aspect": self._to_float(features.get("aspect"), 0.0),
                    "rainfall_annual": self._to_float(features.get("rainfall_annual", features.get("rainfall")), 0.0),
                    "latitude": self._to_float(features.get("latitude"), 0.0),
                    "longitude": self._to_float(features.get("longitude"), 0.0),
                }

                X = self._build_feature_frame(self.soc_model, numeric, ecosystem_label, climate)
                if X is None:
                    raise ValueError("SOC model feature schema unavailable")

                pred = float(self.soc_model.predict(X)[0])
                return {
                    'mean': max(0.0, pred),
                    'source': 'ML_downscaled_SOC',
                    'confidence': 75,
                }
            except Exception:
                pass
        
        return {
            'mean': float(features.get('soc', 0)),
            'source': 'raw_GEE_SOC',
            'confidence': 60,
        }
    
    def analyze_polygon(self, features: Dict[str, Any], area_m2: float = 10000.0) -> Dict[str, Any]:
        """
        Full ML-enhanced carbon analysis for a polygon.
        
        Args:
            features: Dict from GEE extraction (gee.py analyze_polygon output)
            area_m2: Polygon area in square meters
            
        Returns:
            Complete carbon analysis with source attribution and confidence
        """
        area_ha = area_m2 / 10000.0
        
        # Biomass prediction
        biomass = self.predict_biomass(features)
        agb = biomass['mean']
        bgb = agb * 0.24  # IPCC default root:shoot ratio
        total_biomass = agb + bgb
        
        # Carbon from biomass
        carbon_agb = agb * 0.47
        carbon_bgb = bgb * 0.47
        carbon_biomass = total_biomass * 0.47
        
        # SOC prediction
        soc = self.predict_soc(features)
        soc_tc_ha = soc['mean']
        soc_total = soc_tc_ha * area_ha
        
        # Total carbon stock
        total_carbon = (carbon_biomass * area_ha) + soc_total
        
        return {
            'biomass_agb': biomass,
            'biomass_bgb': {'mean': bgb, 'source': 'IPCC_root_shoot'},
            'carbon_biomass_tc_ha': carbon_biomass,
            'carbon_agb_tc_ha': carbon_agb,
            'carbon_bgb_tc_ha': carbon_bgb,
            'soc': soc,
            'soc_total_tc': soc_total,
            'total_carbon_stock_tc': total_carbon,
            'area_ha': area_ha,
            'models_loaded': {
                'gedi_bias': self.gedi_model is not None,
                'soc_downscaling': self.soc_model is not None,
                'si_calibrated': list(self.si_models.keys()),
            },
        }


# Module-level singleton for use in FastAPI
_analyzer: Optional[CarbonAnalyzerV2_1] = None

def get_analyzer() -> CarbonAnalyzerV2_1:
    """Get or create the singleton CarbonAnalyzerV2.1 instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = CarbonAnalyzerV2_1()
    return _analyzer
