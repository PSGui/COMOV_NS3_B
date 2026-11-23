#!/usr/bin/env python3
"""Regression tests for paired P2 diagnostics: rounding, ID runs and delays."""
import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_p2 import contiguous_ranges, percentile  # noqa: E402


def make_csv(prefix, suffix, cols, rows):
    with Path(str(prefix) + "_" + suffix + ".csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(cols)
        writer.writerows(rows)


def fixture(directory, difference=0.000000001):
    immediate = Path(directory) / "immediate"
    fifo = Path(directory) / "fifo"
    fields = [
        "speed_mps", "stop_s", "ap_x_m", "seed", "run", "generated",
        "path_loss_exponent", "tx_dbm", "wifi_standard", "frequency_hz",
        "policy", "received_on_time", "received_unique", "socket_accepted",
        "drop_no_association", "buffer_overflow", "buffer_expired",
        "not_observed_after_socket_accept", "buffer_peak_bytes",
        "buffer_limit_bytes",
    ]
    for prefix, policy, offset in [(immediate, "immediate", 0), (fifo, "fifo", difference)]:
        is_fifo = policy == "fifo"
        make_csv(
            prefix, "summary", fields,
            [[5, 10, 0, 1, 1, 12000, 3, 20, "802.11g", 2412000000,
              policy, 3 if is_fifo else 2, 3 if is_fifo else 2,
              4 if is_fifo else 3, 0, 0, 0, 1,
              3000 if is_fifo else 0, 4000000]],
        )
        make_csv(
            prefix, "association",
            ["t_s", "event", "ap_mac", "bus_x_m", "distance_ap_m"],
            [[46.940678770, "assoc", "00:00:00:00:00:01", -115, 115],
             [104.140776386, "deassoc", "00:00:00:00:00:01", 120, 120]],
        )
        make_csv(
            prefix, "mobility",
            ["t_s", "bus_x_m", "bus_velocity_mps", "distance_ap_m",
             "associated", "pr_model_dbm"],
            [[0, -350, 5, 350, 0, -90.1],
             [70, 0, 0, 1.5, 1, -25.3 + offset],
             [80, 0, 5, 1.5, 1, -25.3]],
        )
        make_csv(
            prefix, "generated",
            ["seq", "t_gen_s", "bus_x_m", "distance_ap_m"],
            ((k, f"{10+k/100:.9f}", 0,
              f"{100.0+(offset if k == 3913 else 0):.9f}")
             for k in range(12000)),
        )

        if is_fifo:
            sends = [(0, 1000), (1, 1000), (3695, 1000), (9315, 1000)]
            received = [(0, 10, 46.95, 36.95),
                        (1, 10.01, 46.96, 36.95),
                        (3695, 46.95, 46.97, .02)]
            events = [
                (10, 0, "enqueued", 1, 1000),
                (10.01, 1, "enqueued", 2, 2000),
                (46.95, 3695, "enqueued", 3, 3000),
                (47, 0, "send_accepted", 2, 2000),
                (47.002, 1, "send_accepted", 1, 1000),
                (47.004, 3695, "send_accepted", 0, 0),
            ]
        else:
            sends = [(3695, 1000), (3696, 1000), (9315, 1000)]
            received = [(3695, 46.95, 46.97, .02),
                        (3696, 46.96, 46.98, .02)]
            events = []
        make_csv(prefix, "sent", ["seq", "send_return"], sends)
        make_csv(prefix, "received",
                 ["seq", "t_gen_s", "t_rx_s", "delay_s", "duplicate"],
                 ((seq, tg, tr, delay, 0) for seq, tg, tr, delay in received))
        make_csv(prefix, "buffer", ["t_s", "seq", "event", "queued_messages", "queued_bytes"],
                 events)
    return immediate, fifo


class P2ComparisonTests(unittest.TestCase):
    def test_range_and_percentile_helpers(self):
        self.assertEqual(contiguous_ranges([5, 9316, 4, 3, 9315]),
                         [[3, 5, 3], [9315, 9316, 2]])
        self.assertEqual(percentile([1.0, 3.0, 5.0], .5), 3.0)
        self.assertEqual(percentile([0.0, 10.0], .95), 9.5)

    def test_matched_pair_allows_csv_rounding_one_nanounit(self):
        with tempfile.TemporaryDirectory() as tmp:
            immediate, fifo = fixture(tmp)
            output = Path(tmp) / "pair.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/compare_p2.py"),
                 "--immediate-prefix", str(immediate),
                 "--fifo-prefix", str(fifo),
                 "--output-json", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["policies"]["fifo"]["received_generated_before_first_assoc"], 2)
            self.assertEqual(report["policies"]["fifo"]["missing_socket_accepted_ranges"],
                             [[9315, 9315, 1]])

    def test_materially_different_mobility_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            immediate, fifo = fixture(tmp, difference=1.0)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/compare_p2.py"),
                 "--immediate-prefix", str(immediate),
                 "--fifo-prefix", str(fifo)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
