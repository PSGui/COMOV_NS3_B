#!/usr/bin/env python3
"""Smoke/regression tests for contact-utilisation analysis (stdlib only)."""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_p2_contact import association_duration, inspect_run, percentile  # noqa: E402
from run_p2_ap_robustness import prefix_for  # noqa: E402


def write_csv(path, columns, data):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(data)


def make_fixture(root):
    for speed in (5, 15):
        for stop in (0, 10, 30):
            for run in (1, 2):
                for policy in ("immediate", "fifo"):
                    prefix = root / f"v{speed}_stop{stop}_run{run}_{policy}"
                    count = 2 if policy == "fifo" else 1
                    headers = ["speed_mps", "stop_s", "ap_x_m", "seed", "run",
                               "generated", "received_unique", "received_on_time",
                               "received_late", "duplicate_rx", "associated_duration_s",
                               "buffer_peak_bytes", "buffer_overflow", "buffer_expired",
                               "not_observed_after_socket_accept"]
                    write_csv(Path(str(prefix) + "_summary.csv"), headers,
                              [[speed, stop, 0, 1, run, 12000, count, count,
                                0, 0, 10, 2000 if policy == "fifo" else 0,
                                0, 0, 0]])
                    write_csv(Path(str(prefix) + "_association.csv"),
                              ["t_s", "event", "ap_mac", "bus_x_m", "distance_ap_m"],
                              [[40, "assoc", "00:00:00:00:00:01", 0, 1],
                               [50, "deassoc", "00:00:00:00:00:01", 0, 1]])
                    delivered = [[0, 40, 40.001, .001, 1, 0, 1]]
                    if count == 2:
                        delivered.append([1, 10, 40.003, 30.003, 1, 0, 1])
                    write_csv(Path(str(prefix) + "_received.csv"),
                              ["seq", "t_gen_s", "t_rx_s", "delay_s",
                               "on_time", "duplicate", "associated_at_reception"],
                              delivered)


class ContactAnalysisTests(unittest.TestCase):
    def test_aggregate_paired_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            make_fixture(root)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/analyze_p2_contact.py"),
                 "--input-dir", str(root), "--output-dir", str(root),
                 "--start-run", "1", "--end-run", "2"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            with (root / "contact_metrics_runs.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                runs = list(csv.DictReader(stream))
            with (root / "contact_metrics_summary.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                summaries = list(csv.DictReader(stream))
            with (root / "contact_metrics_pairs.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                pairs = list(csv.DictReader(stream))
            self.assertEqual(len(runs), 24)
            self.assertEqual(len(summaries), 12)
            self.assertEqual(len(pairs), 6)
            for row in pairs:
                # One extra 1000-B payload / 12000 = 0.008333333 pp.
                self.assertAlmostEqual(float(row["delivery_gain_mean_pp"]), 1/120)
                self.assertAlmostEqual(float(row["on_time_goodput_gain_mean_mbps"]),
                                       .0008)
                self.assertAlmostEqual(float(row["delivery_gain_ci95_low_pp"]),
                                       1/120)
                self.assertAlmostEqual(float(row["delivery_gain_ci95_high_pp"]),
                                       1/120)
            for row in runs:
                self.assertAlmostEqual(float(row["association_s"]), 10.0)

    def test_association_timeline_rejects_bad_state(self):
        with self.assertRaisesRegex(ValueError, "Invalid association transition"):
            association_duration([{"t_s": "1", "event": "deassoc"}])
        self.assertEqual(association_duration([
            {"t_s": "20", "event": "assoc"},
            {"t_s": "25", "event": "deassoc"},
        ]), 5.0)
        self.assertAlmostEqual(percentile([1, 3, 5], .95), 4.8)

    def test_bad_deadline_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            make_fixture(root)
            path = root / "v5_stop0_run1_immediate_received.csv"
            content = path.read_text(encoding="utf-8").replace(
                "40.001,0.001,1", "40.001,0.001,0"
            )
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Deadline flag mismatch"):
                inspect_run(root / "v5_stop0_run1_immediate")

    def test_robustness_suffixes_cannot_replace_baseline(self):
        base = str(prefix_for(15, 30, 1, "fifo", 0))
        neg = str(prefix_for(15, 30, 1, "fifo", -30))
        pos = str(prefix_for(15, 30, 1, "fifo", 30))
        self.assertEqual(len({base, neg, pos}), 3)
        self.assertTrue(neg.endswith("_apxm30"))
        self.assertTrue(pos.endswith("_apxp30"))
        with self.assertRaises(ValueError):
            prefix_for(15, 30, 1, "fifo", 25)


if __name__ == "__main__":
    unittest.main()
