#!/usr/bin/env python3
"""Unit regression checks for P3 10-run paired design, no ns-3 needed."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p3_repeated_tests import (  # noqa: E402
    CASES, POLICY_PAIRS, SENSITIVITIES, prefix_for, estimate,
    paired_results, sensitivity_results, valid_existing,
)


class RepeatedP3Tests(unittest.TestCase):
    def test_exactly_eight_distinct_controlled_configs(self):
        self.assertEqual(len(CASES), 8)
        self.assertEqual(len({case[0] for case in CASES}), 8)
        self.assertEqual(len({str(prefix_for(case, 3)) for case in CASES}), 8)
        for key, scenario, policy, pace, capacity, m in CASES:
            self.assertIn(scenario, ("reference", "fading", "contention"))
            self.assertIn(policy, ("immediate", "fifo"))
            self.assertEqual(m, 5 if scenario == "fading" else 1)
            self.assertEqual(pace, 3 if key == "ref_fifo_pace3" else 2)
            self.assertEqual(capacity, 2000000 if key == "ref_fifo_buf2mb" else 4000000)
            path = str(prefix_for((key, scenario, policy, pace, capacity, m), 3))
            self.assertIn("_m5", path) if scenario == "fading" else self.assertNotIn("_m5", path)
            self.assertNotIn("staticarp", path)
        self.assertFalse(any(valid_existing(case, 233) for case in CASES))

    def test_paired_statistics_and_difference_of_differences(self):
        cases = {
            "ref_immediate": 1000, "ref_fifo": 5000,
            "fading_m5_immediate": 900, "fading_m5_fifo": 4300,
            "contention_immediate": 900, "contention_fifo": 4000,
            "ref_fifo_pace3": 4500, "ref_fifo_buf2mb": 3000,
        }
        grouped = {}
        for run in (1, 2, 3):
            for name, count in cases.items():
                grouped[(run, name)] = {
                    "delivery_pct": count / 12000 * 100,
                    "received_on_time": count,
                    "contact_goodput_mbps": count * .008 / 16,
                    "contact_success": 1,
                }
        pairs, deltas = paired_results(grouped, (1, 2, 3))
        self.assertEqual(len(pairs), 5)
        self.assertEqual(len(deltas), 15)
        self.assertEqual(len(SENSITIVITIES), 4)
        effects = {r["sensitivity"]: r for r in
                   sensitivity_results(grouped, deltas, (1, 2, 3))}
        self.assertAlmostEqual(effects["fading_m5_effect_on_fifo_gain"]
                               ["change_mean_pp"], -5)
        self.assertAlmostEqual(effects["contention_effect_on_fifo_gain"]
                               ["change_mean_pp"], -7.5)
        self.assertAlmostEqual(effects["pacing3_effect_on_fifo_delivery"]
                               ["change_mean_pp"], -500 / 12000 * 100)
        self.assertAlmostEqual(effects["buffer2mb_effect_on_fifo_delivery"]
                               ["change_mean_pp"], -2000 / 12000 * 100)
        self.assertAlmostEqual(
            next(row for row in pairs if row["comparison"] ==
                 "fading_m5_fifo_vs_immediate")["mean_extra_packets"], 3400)
        self.assertEqual(estimate([5, 5, 5]), (5, 5, 5))

    def test_undefined_goodput_not_replaced_with_zero(self):
        grouped = {}
        for run in (1, 2, 3):
            for key, _, _, _, _, _ in CASES:
                delivery = 10 if key.endswith("fifo") else 0
                grouped[(run, key)] = {
                    "delivery_pct": delivery / 12000 * 100,
                    "received_on_time": delivery,
                    "contact_goodput_mbps": "" if key.startswith("fading") else .05,
                    "contact_success": int(delivery > 0),
                }
        pairs, _ = paired_results(grouped, (1, 2, 3))
        fading = next(x for x in pairs
                      if x["comparison"] == "fading_m5_fifo_vs_immediate")
        self.assertEqual(fading["n_pairs_with_goodput_defined"], 0)
        self.assertEqual(fading["mean_goodput_gain_mbps"], "")


if __name__ == "__main__":
    unittest.main()
