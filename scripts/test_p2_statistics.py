#!/usr/bin/env python3
"""Synthetic tests for 95% paired P2 CI (no ns-3 installation required)."""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create_summaries(folder, mismatched_seed=False):
    columns = [
        "speed_mps", "stop_s", "ap_x_m", "seed", "run", "generated",
        "path_loss_exponent", "tx_dbm", "wifi_standard", "frequency_hz",
        "policy", "received_on_time", "buffer_overflow", "buffer_expired",
        "buffer_peak_bytes", "pacing_ms",
    ]
    for speed in (5, 15):
        for stop in (0, 10, 30):
            for run in (1, 2):
                for policy in ("immediate", "fifo"):
                    prefix = Path(folder) / f"v{speed}_stop{stop}_run{run}_{policy}_summary.csv"
                    accepted = (2000 + run * 10 +
                                (1200 if policy == "fifo" else 0))
                    seed = 2 if mismatched_seed and speed == 5 and stop == 0 and (
                        run == 2 and policy == "fifo"
                    ) else 1
                    values = [speed, stop, 0, seed, run, 12000, 3, 20, "802.11g",
                              2412000000, policy, accepted, 0, 100, 1000, 2]
                    with prefix.open("w", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(columns)
                        writer.writerow(values)


class P2PairedStatsTests(unittest.TestCase):
    def test_constant_paired_gain_gives_zero_ci_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_summaries(tmp)
            dest = Path(tmp) / "stats.csv"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/paired_statistics_p2.py"),
                 "--output-dir", tmp, "--start-run", "1", "--end-run", "2",
                 "--output-csv", dest],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            with dest.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 6)
            for r in rows:
                self.assertEqual(int(r["n_pairs"]), 2)
                self.assertAlmostEqual(float(r["fifo_minus_immediate_mean_pp"]), 10)
                self.assertAlmostEqual(float(r["difference_95ci_low_pp"]), 10)
                self.assertAlmostEqual(float(r["difference_95ci_high_pp"]), 10)

    def test_wrong_seed_in_pair_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_summaries(tmp, mismatched_seed=True)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/paired_statistics_p2.py"),
                 "--output-dir", tmp, "--start-run", "1", "--end-run", "2",
                 "--output-csv", Path(tmp) / "stats.csv"],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_single_run_is_explicitly_pilot_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_summaries(tmp)
            dest = Path(tmp) / "stats.csv"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/paired_statistics_p2.py"),
                 "--output-dir", tmp, "--start-run", "1", "--end-run", "1",
                 "--output-csv", dest],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("pilot-only", result.stdout)
            with dest.open(encoding="utf-8", newline="") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["difference_95ci_low_pp"], "")
            self.assertEqual(row["difference_95ci_high_pp"], "")


if __name__ == "__main__":
    unittest.main()
