import tempfile
import unittest
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.inference import InferenceEngine  # noqa: E402


class InferenceEngineTests(unittest.TestCase):
    def test_feature_frame_alignment_and_one_hot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = InferenceEngine(model_dir=tmp)
            feature_names = [
                "ndvi_mean",
                "elevation",
                "ecosystem_Forest",
                "ecosystem_Grassland",
                "climate_zone_Tropical",
                "climate_zone_Temperate",
            ]
            raw = {"ndvi_mean": 0.42, "elevation": 777.0, "ignored_extra": 123.0}

            frame = engine._build_feature_frame(
                feature_names=feature_names,
                raw_numeric=raw,
                ecosystem="Forest",
                climate="Tropical",
            )

            self.assertEqual(list(frame.columns), feature_names)
            self.assertAlmostEqual(float(frame.loc[0, "ndvi_mean"]), 0.42, places=6)
            self.assertAlmostEqual(float(frame.loc[0, "elevation"]), 777.0, places=6)
            self.assertEqual(float(frame.loc[0, "ecosystem_Forest"]), 1.0)
            self.assertEqual(float(frame.loc[0, "ecosystem_Grassland"]), 0.0)
            self.assertEqual(float(frame.loc[0, "climate_zone_Tropical"]), 1.0)
            self.assertEqual(float(frame.loc[0, "climate_zone_Temperate"]), 0.0)

    def test_predict_without_models_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = InferenceEngine(model_dir=tmp)
            result = engine.predict(
                {
                    "biomass": 80.0,
                    "soc": 15.0,
                    "root_shoot_ratio": 0.25,
                    "land_cover": 10,  # forest
                    "latitude": 19.0,
                    "ndvi": 0.5,
                    "evi": 0.3,
                }
            )

            self.assertFalse(result["ml_models_used"])
            self.assertEqual(result["biomass_source"], "raw_GEE")
            self.assertEqual(result["soc_source"], "raw_GEE_SOC")
            self.assertAlmostEqual(float(result["metrics"]["biomass_aboveground"]), 80.0, places=6)
            self.assertAlmostEqual(float(result["metrics"]["biomass_belowground"]), 20.0, places=6)
            self.assertAlmostEqual(float(result["metrics"]["biomass_total"]), 100.0, places=6)
            self.assertAlmostEqual(float(result["metrics"]["soc"]), 15.0, places=6)


if __name__ == "__main__":
    unittest.main()
