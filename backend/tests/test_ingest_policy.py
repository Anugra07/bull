import unittest
from pathlib import Path
import sys

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.ingest_field_data import (  # noqa: E402
    POLICY_TAG,
    build_common_record,
    validate_source_policy,
)


class IngestPolicyTests(unittest.TestCase):
    def test_validate_source_policy_rejects_non_public_source(self) -> None:
        with self.assertRaises(ValueError):
            validate_source_policy("personal-iot")

    def test_build_record_respects_india_only_filter(self) -> None:
        policy = validate_source_policy("gedi-fia")

        india_row = pd.Series({"latitude": 22.5, "longitude": 78.1, "agbd": 120.0})
        outside_row = pd.Series({"latitude": 45.0, "longitude": -120.0, "agbd": 120.0})

        in_record = build_common_record(
            row=india_row,
            source="gedi-fia",
            policy_meta=policy,
            biomass_keys=["agbd"],
            ecosystem_default="Forest",
            india_only=True,
        )
        out_record = build_common_record(
            row=outside_row,
            source="gedi-fia",
            policy_meta=policy,
            biomass_keys=["agbd"],
            ecosystem_default="Forest",
            india_only=True,
        )

        self.assertIsNotNone(in_record)
        self.assertIsNone(out_record)
        self.assertEqual(in_record["features"]["provenance"]["policy"], POLICY_TAG)


if __name__ == "__main__":
    unittest.main()
