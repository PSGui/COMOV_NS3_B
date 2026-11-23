#!/usr/bin/env python3
"""Synthetic tests for CSV accounting, without needing ns-3.

These do not validate PHY/MAC or prove the actual P1 run; they test that
review_p1.py accepts a valid no-contact run and rejects malformed logs.
"""
import csv
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create_synthetic(prefix):
    speed, stop = 5.0, 10.0
    columns = {
        "_generated.csv": [
            "seq", "t_gen_s", "bus_x_m", "distance_ap_m",
            "associated_at_generation", "attempted_socket_send",
            "send_return", "drop_reason",
        ],
        "_received.csv": [
            "seq", "t_gen_s", "t_rx_s", "delay_s",
            "on_time", "duplicate", "associated_at_reception",
        ],
        "_association.csv": [
            "t_s", "event", "ap_mac", "bus_x_m", "distance_ap_m",
        ],
        "_mobility.csv": [
            "t_s", "bus_x_m", "bus_velocity_mps",
            "distance_ap_m", "associated", "pr_model_dbm",
        ],
        "_summary.csv": [
            "speed_mps", "stop_s", "ap_x_m", "seed", "run", "generated",
            "drop_no_association", "socket_rejected", "socket_accepted",
            "received_unique", "received_on_time", "received_late",
            "duplicate_rx", "malformed_rx",
            "not_observed_after_socket_accept", "associated_duration_s",
            "assoc_events", "deassoc_events", "policy",
        ],
    }
    for suffix, header in columns.items():
        with Path(str(prefix) + suffix).open("w", encoding="utf-8", newline="") as out:
            csv.writer(out).writerow(header)

    def x_at(t):
        if t < 70:
            return speed * (t - 70)
        if t < 80:
            return 0.
        return speed * (t - 80)

    with Path(str(prefix) + "_generated.csv").open("a", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        for i in range(12000):
            t = 10.0 + i / 100.0
            x = x_at(t)
            writer.writerow([i, f"{t:.9f}", f"{x:.9f}",
                             f"{math.hypot(x, 1.5):.9f}", 0, 0,
                             "", "no_association"])
    with Path(str(prefix) + "_mobility.csv").open("a", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        for i in range(801):
            t = i / 4
            x = x_at(t)
            velocity = 0 if 70 <= t < 80 else 5
            writer.writerow([f"{t:.9f}", f"{x:.9f}", velocity,
                             f"{math.hypot(x, 1.5):.9f}", 0, 0])
    with Path(str(prefix) + "_summary.csv").open("a", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow([5, 10, 0, 1, 1, 12000, 12000, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 0,
                         "immediate_drop_if_unassociated"])


class P1ValidatorTests(unittest.TestCase):
    def test_valid_no_contact_run_is_not_a_simulator_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "p1"
            create_synthetic(prefix)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p1.py"), "--prefix", str(prefix)],
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(Path(str(prefix) + "_analysis.json").exists())

    def test_pilot_can_require_observed_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "p1"
            create_synthetic(prefix)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p1.py"), "--prefix", str(prefix),
                 "--require-contact"], capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)

    def test_rejects_wrong_message_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "p1"
            create_synthetic(prefix)
            with Path(str(prefix) + "_generated.csv").open("a", encoding="utf-8") as out:
                out.write("12000,130.000000000,250,250,0,0,,no_association\n")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p1.py"), "--prefix", str(prefix)],
                capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
