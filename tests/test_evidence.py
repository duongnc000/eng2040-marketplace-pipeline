"""Focused regression checks for the additive exports and evidence safeguards."""

import os
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from marketplace_pipeline import features, validation
from marketplace_pipeline.common import write_csv
from marketplace_pipeline.config import ROOT
from marketplace_pipeline.monitoring import ResourceMonitor, python_size


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".pipeline_tmp"
        base.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="test_", dir=base)
        self.path = Path(self.directory.name).resolve()
        self.assertTrue(self.path.is_relative_to(base.resolve()))
        self.addCleanup(self.directory.cleanup)

    def test_temp_sampling_and_environment_restoration_on_error(self):
        previous = os.environ.get("TEMP")
        with self.assertRaisesRegex(ValueError, "example"):
            with ResourceMonitor() as monitor:
                (monitor.path / "working.bin").write_bytes(b"x" * 8192)
                time.sleep(.08)
                self.assertGreaterEqual(monitor.peak_temporary, 8192)
                if monitor.read_rss is not None:
                    self.assertGreater(monitor.peak_rss, 0)
                raise ValueError("example")
        self.assertEqual(os.environ.get("TEMP"), previous)
        self.assertFalse(monitor.path.exists())

    def test_python_size_handles_shared_and_circular_references(self):
        shared = [1, 2, 3]
        seen = set()
        self.assertGreater(python_size(shared, seen), 0)
        self.assertEqual(python_size(shared, seen), 0)
        shared.append(shared)
        self.assertGreater(python_size(shared), 0)

    def test_exports_and_validation_detect_reordered_targets_and_missing_audit(self):
        orders = [{
            "order_id": identity, "_label": label,
            "_label_reason": "reliable_completed_delivery" if label is not None else "status_not_delivered",
            "_delay_days": 2 if label is not None else None,
            "_item": {"item_count": 1},
            "_parsed": {"order_approved_at": datetime(2020, 1, 1)},
            "_approval_to_estimate_days": 10, "_purchase_to_approval_hours": 1,
            "_state_clean": "SP", "customer_zip_code_prefix": "01005",
        } for identity, label in (("a", 1), ("b", None))]
        cleaned = [{"order_id": row["order_id"], "item_count": 1,
                    "basket_price_valid_brl": 0, "basket_freight_valid_brl": 0,
                    "basket_price_raw_brl": 0, "basket_freight_raw_brl": 0} for row in orders]
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript("CREATE TABLE orders(order_id TEXT); INSERT INTO orders VALUES('a'),('b');"
                                 "CREATE TABLE order_items(price REAL, freight_value REAL);"
                                 "INSERT INTO order_items VALUES(0,0),(0,0);")
        with patch.object(features, "FEATURE_OUTPUTS", self.path), \
                patch.object(validation, "FEATURE_OUTPUTS", self.path), \
                patch.object(validation, "CLEANING_OUTPUTS", self.path), \
                patch.object(validation, "DOCUMENTATION_OUTPUTS", self.path):
            data = features.build_features(orders)
            self.assertEqual(len(data["all_features"]), 2)
            self.assertEqual(len(data["features"]), 1)
            self.assertEqual(len(data["features"][0]), 53)
            self.assertEqual(data["all_labels"][1]["delivered_after_estimate"], None)
            write_csv(self.path / "order_audit.csv", [{"order_id": "a"}, {"order_id": "b"}])
            context = {"orders": orders, "cleaned": cleaned}
            checks = validation.run_checks(connection, context, data)
            self.assertTrue(all(row["status"] == "PASS" for row in checks), checks)
            write_csv(self.path / "all_labels.csv", list(reversed(data["all_labels"])))
            write_csv(self.path / "order_audit.csv", [{"order_id": "a"}, {"order_id": "a"}])
            checks = validation.run_checks(connection, context, data)
            failures = {row["check"] for row in checks if row["status"] == "FAIL"}
            self.assertIn("all_saved feature/ID/label positions match source orders", failures)
            self.assertIn("every order has exactly one saved audit row", failures)


if __name__ == "__main__":
    unittest.main()
