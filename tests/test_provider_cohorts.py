import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_provider_cohorts import compare, load_groups, summarise


class CohortChecks(unittest.TestCase):
    def test_portfolio_reference(self):
        actual = compare(ROOT / "data/processed")
        for key, n, months, r in [
            ("all_departments", 180, 5174, -0.573520766401),
            ("type1", 121, 3507, 0.037780788609),
            ("matched_all", 121, 3507, 0.158819623637),
            ("matched_type1", 121, 3507, 0.037780788609),
        ]:
            self.assertEqual((actual[key]["provider_count"], actual[key]["provider_months"]), (n, months))
            self.assertAlmostEqual(actual[key]["correlation_mean_monthly_attendance_vs_weighted_performance"], r, places=9)

    def test_names_weights_ties_and_zero_months(self):
        groups = {"B": [("01", "old", 1, 1), ("02", "new", 9, 0)],
                  "A": [("01", "A", 4, 0), ("02", "A", 6, 2)],
                  "C": [("01", "C", 0, 0), ("02", "C", 2, 0)]}
        rows = summarise(groups, 2)["top_10"]
        self.assertEqual([r["org_code"] for r in rows], ["A", "B"])
        self.assertEqual((rows[1]["name"], rows[1]["performance"]), ("new", 90))
        self.assertEqual(summarise(groups, 2, {("B", "01")})["provider_count"], 0)

    def test_rejects_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.csv"
            for counts in [[(3, 4)], [(3, -1)], [(3, 1), (3, 1)]]:
                with path.open("w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Org Code", "Month", "Org name", "volume", "over4"])
                    for volume, over4 in counts:
                        writer.writerow(["A", "2024-04", "Example", volume, over4])
                with self.assertRaises(ValueError):
                    load_groups(path, "volume", "over4")
