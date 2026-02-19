import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd


class InferenceEngine:
    """Runtime model loader + inference router for biomass and SOC."""

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            backend_dir = Path(__file__).resolve().parents[2]
            model_dir = str(backend_dir / "ml" / "models")
        self.model_dir = model_dir

        self.gedi_model = None
        self.soc_model = None
        self.si_models: Dict[str, Dict[str, Any]] = {}

        self.gedi_info: Dict[str, Any] = {}
        self.soc_info: Dict[str, Any] = {}
        self.si_info: Dict[str, Any] = {}

        self._loaded_at: Optional[str] = None
        self.reload()

    def _load_json(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _build_model_info(
        self,
        key: str,
        model_path: str,
        meta_path: str,
        model_obj: Any,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        meta = self._load_json(meta_path)
        feature_names = []
        if model_obj is not None and hasattr(model_obj, "feature_names_in_"):
            feature_names = [str(x) for x in list(model_obj.feature_names_in_)]
        elif isinstance(meta.get("feature_names"), list):
            feature_names = [str(x) for x in meta.get("feature_names", [])]

        return {
            "key": key,
            "path": model_path,
            "exists": os.path.exists(model_path),
            "ready": model_obj is not None and error is None,
            "error": error,
            "version": meta.get("version", os.path.splitext(os.path.basename(model_path))[0]),
            "trained_at": meta.get("trained_at"),
            "n_samples": meta.get("n_samples"),
            "rmse": meta.get("rmse"),
            "r2": meta.get("r2"),
            "feature_names": feature_names,
            "feature_count": len(feature_names),
            "metadata": meta,
        }

    def reload(self) -> None:
        gedi_path = os.path.join(self.model_dir, "gedi_bias_v1.pkl")
        gedi_meta = os.path.join(self.model_dir, "gedi_bias_v1.meta.json")
        soc_path = os.path.join(self.model_dir, "soc_downscaling_xgb_v1.pkl")
        soc_meta = os.path.join(self.model_dir, "soc_downscaling_xgb_v1.meta.json")
        si_path = os.path.join(self.model_dir, "stocking_index_calibrated_v1.pkl")
        si_meta = os.path.join(self.model_dir, "stocking_index_calibrated_v1.meta.json")

        self.gedi_model = None
        self.soc_model = None
        self.si_models = {}

        gedi_err = None
        try:
            if os.path.exists(gedi_path):
                self.gedi_model = joblib.load(gedi_path)
        except Exception as e:
            gedi_err = str(e)

        soc_err = None
        try:
            if os.path.exists(soc_path):
                self.soc_model = joblib.load(soc_path)
        except Exception as e:
            soc_err = str(e)

        si_err = None
        try:
            if os.path.exists(si_path):
                loaded_si = joblib.load(si_path)
                if isinstance(loaded_si, dict):
                    self.si_models = loaded_si
                else:
                    si_err = "SI artifact is not a dict"
        except Exception as e:
            si_err = str(e)

        self.gedi_info = self._build_model_info("gedi_bias", gedi_path, gedi_meta, self.gedi_model, gedi_err)
        self.soc_info = self._build_model_info("soc_downscaling", soc_path, soc_meta, self.soc_model, soc_err)

        si_meta_data = self._load_json(si_meta)
        self.si_info = {
            "key": "stocking_index",
            "path": si_path,
            "exists": os.path.exists(si_path),
            "ready": len(self.si_models) > 0 and si_err is None,
            "error": si_err,
            "version": si_meta_data.get("version", "stocking_index_calibrated_v1"),
            "trained_at": si_meta_data.get("trained_at"),
            "ecosystems": list(self.si_models.keys()),
            "metadata": si_meta_data,
        }

        self._loaded_at = datetime.now(timezone.utc).isoformat()

    def status(self) -> Dict[str, Any]:
        return {
            "loaded_at": self._loaded_at,
            "model_dir": self.model_dir,
            "models": {
                "gedi_bias": self.gedi_info,
                "soc_downscaling": self.soc_info,
                "stocking_index": self.si_info,
            },
        }

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            value = float(value)
            if np.isnan(value) or np.isinf(value):
                return default
            return value
        except Exception:
            return default

    def _infer_ecosystem_labels(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        land_cover = int(self._to_float(metrics.get("land_cover"), 0))
        latitude = abs(self._to_float(metrics.get("latitude"), 0.0))

        if land_cover == 20:
            ecosystem = "Shrubland"
            si_key = "grassland"
        elif land_cover in (30, 90):
            ecosystem = "Grassland"
            si_key = "grassland"
        elif land_cover == 95:
            ecosystem = "Forest"
            si_key = "mangrove"
        elif land_cover == 40:
            ecosystem = "Cropland"
            si_key = "plantation"
        else:
            ecosystem = "Forest"
            si_key = "tropical_forest" if latitude < 23.5 else "temperate_forest"

        climate = "Tropical" if latitude < 23.5 else "Temperate"
        return {"ecosystem": ecosystem, "climate": climate, "si_key": si_key}

    def _build_feature_frame(
        self,
        feature_names: List[str],
        raw_numeric: Dict[str, float],
        ecosystem: str,
        climate: str,
    ) -> pd.DataFrame:
        row = {name: 0.0 for name in feature_names}

        for name, value in raw_numeric.items():
            if name in row:
                row[name] = self._to_float(value)

        for name in feature_names:
            if name.startswith("ecosystem_"):
                category = name.replace("ecosystem_", "", 1)
                row[name] = 1.0 if category.lower() == ecosystem.lower() else 0.0
            if name.startswith("climate_zone_"):
                category = name.replace("climate_zone_", "", 1)
                row[name] = 1.0 if category.lower() == climate.lower() else 0.0

        return pd.DataFrame([row], columns=feature_names)

    def _rf_interval(self, model: Any, X: pd.DataFrame) -> Optional[Dict[str, float]]:
        if not hasattr(model, "estimators_"):
            return None

        try:
            # Use numpy array for tree-level predictions to avoid sklearn feature-name warnings.
            preds = np.array([float(tree.predict(X.values)[0]) for tree in model.estimators_], dtype=float)
            lower = float(np.percentile(preds, 2.5))
            upper = float(np.percentile(preds, 97.5))
            mean = float(np.mean(preds))
            return {
                "mean": mean,
                "lower_95": lower,
                "upper_95": upper,
                "interval_width": upper - lower,
            }
        except Exception:
            return None

    def _rmse_interval(self, mean_value: float, rmse: Optional[float]) -> Optional[Dict[str, float]]:
        if rmse is None:
            return None
        rmse = self._to_float(rmse, 0.0)
        if rmse <= 0:
            return None

        width = 1.96 * rmse
        lower = max(0.0, mean_value - width)
        upper = mean_value + width
        return {
            "mean": mean_value,
            "lower_95": lower,
            "upper_95": upper,
            "interval_width": upper - lower,
        }

    def _predict_biomass(self, metrics: Dict[str, Any], labels: Dict[str, str]) -> Dict[str, Any]:
        raw_biomass = self._to_float(metrics.get("biomass_aboveground", metrics.get("biomass", 0.0)), 0.0)

        # Try ecosystem-specific SI model first.
        si_key = labels["si_key"]
        if si_key in self.si_models:
            si_entry = self.si_models[si_key]
            model = si_entry.get("model")
            features = si_entry.get("features", [])

            ndvi = self._to_float(metrics.get("ndvi", metrics.get("ndvi_mean")), 0.0)
            si_vector = {
                "ndvi": ndvi,
                "evi": self._to_float(metrics.get("evi", metrics.get("evi_mean")), 0.0),
                "gedi_rh98": self._to_float(metrics.get("gedi_rh98", metrics.get("canopy_height")), 0.0),
                "canopy_cover": self._to_float(metrics.get("canopy_cover"), max(0.0, min(100.0, ndvi * 100.0))),
                "elevation": self._to_float(metrics.get("elevation"), 0.0),
                "slope": self._to_float(metrics.get("slope"), 0.0),
                "rainfall_annual": self._to_float(metrics.get("rainfall_annual", metrics.get("rainfall")), 0.0),
            }

            try:
                X_si = pd.DataFrame([{f: si_vector.get(f, 0.0) for f in features}], columns=features)
                pred = float(model.predict(X_si)[0])
                interval = self._rf_interval(model, X_si)
                return {
                    "value": max(0.0, pred),
                    "source": f"Verra_calibrated_SI_{si_key}",
                    "version": self.si_info.get("version"),
                    "interval": interval,
                    "ml_used": True,
                }
            except Exception:
                pass

        if self.gedi_model is not None and self.gedi_info.get("ready"):
            feature_names = self.gedi_info.get("feature_names", [])
            raw = {
                "gedi_agbd_raw": self._to_float(metrics.get("gedi_agbd_raw", raw_biomass), raw_biomass),
                "ndvi_mean": self._to_float(metrics.get("ndvi_mean", metrics.get("ndvi")), 0.0),
                "evi_mean": self._to_float(metrics.get("evi_mean", metrics.get("evi")), 0.0),
                "elevation": self._to_float(metrics.get("elevation"), 0.0),
                "slope": self._to_float(metrics.get("slope"), 0.0),
                "rainfall_annual": self._to_float(metrics.get("rainfall_annual", metrics.get("rainfall")), 0.0),
                "latitude": self._to_float(metrics.get("latitude"), 0.0),
            }

            try:
                X = self._build_feature_frame(feature_names, raw, labels["ecosystem"], labels["climate"])
                pred = float(self.gedi_model.predict(X)[0])
                interval = self._rf_interval(self.gedi_model, X)
                return {
                    "value": max(0.0, pred),
                    "source": "ML_corrected_GEDI",
                    "version": self.gedi_info.get("version"),
                    "interval": interval,
                    "ml_used": True,
                }
            except Exception:
                pass

        return {
            "value": max(0.0, raw_biomass),
            "source": str(metrics.get("biomass_source", "raw_GEE")),
            "version": "raw",
            "interval": None,
            "ml_used": False,
        }

    def _predict_soc(self, metrics: Dict[str, Any], labels: Dict[str, str]) -> Dict[str, Any]:
        raw_soc = self._to_float(metrics.get("soc", 0.0), 0.0)

        if self.soc_model is not None and self.soc_info.get("ready"):
            feature_names = self.soc_info.get("feature_names", [])
            raw = {
                "ndvi_mean": self._to_float(metrics.get("ndvi_mean", metrics.get("ndvi")), 0.0),
                "evi_mean": self._to_float(metrics.get("evi_mean", metrics.get("evi")), 0.0),
                "elevation": self._to_float(metrics.get("elevation"), 0.0),
                "slope": self._to_float(metrics.get("slope"), 0.0),
                "aspect": self._to_float(metrics.get("aspect"), 0.0),
                "rainfall_annual": self._to_float(metrics.get("rainfall_annual", metrics.get("rainfall")), 0.0),
                "latitude": self._to_float(metrics.get("latitude"), 0.0),
                "longitude": self._to_float(metrics.get("longitude"), 0.0),
            }

            try:
                X = self._build_feature_frame(feature_names, raw, labels["ecosystem"], labels["climate"])
                pred = float(self.soc_model.predict(X)[0])
                interval = self._rmse_interval(pred, self.soc_info.get("rmse"))
                return {
                    "value": max(0.0, pred),
                    "source": "ML_downscaled_SOC",
                    "version": self.soc_info.get("version"),
                    "interval": interval,
                    "ml_used": True,
                }
            except Exception:
                pass

        return {
            "value": raw_soc,
            "source": "raw_GEE_SOC",
            "version": "raw",
            "interval": None,
            "ml_used": False,
        }

    def predict(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        labels = self._infer_ecosystem_labels(metrics)

        biomass_pred = self._predict_biomass(metrics, labels)
        soc_pred = self._predict_soc(metrics, labels)

        root_shoot_ratio = self._to_float(metrics.get("root_shoot_ratio"), 0.24)
        agb = biomass_pred["value"]
        bgb = agb * root_shoot_ratio
        total_biomass = agb + bgb

        updated = dict(metrics)
        updated["biomass"] = agb
        updated["biomass_aboveground"] = agb
        updated["biomass_belowground"] = bgb
        updated["biomass_total"] = total_biomass
        updated["soc"] = soc_pred["value"]
        updated["ecosystem_type"] = labels["ecosystem"]
        updated["ml_models_used"] = bool(biomass_pred["ml_used"] or soc_pred["ml_used"])

        return {
            "metrics": updated,
            "ml_models_used": updated["ml_models_used"],
            "biomass_source": biomass_pred["source"],
            "soc_source": soc_pred["source"],
            "model_version_biomass": biomass_pred["version"],
            "model_version_soc": soc_pred["version"],
            "biomass_interval": biomass_pred.get("interval"),
            "soc_interval": soc_pred.get("interval"),
            "models_ready": {
                "gedi_bias": bool(self.gedi_info.get("ready")),
                "soc_downscaling": bool(self.soc_info.get("ready")),
                "stocking_index": bool(self.si_info.get("ready")),
            },
        }


_ENGINE: Optional[InferenceEngine] = None


def get_inference_engine() -> InferenceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = InferenceEngine()
    return _ENGINE
