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


    def test_contact_and_delivery_summary_column_regression(self):
        # This would have caught the 'unique_received' vs 'received_unique'
        # KeyError that occurred after the first successful P1 simulation.
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "p1"
            create_synthetic(prefix)

            gen_path = Path(str(prefix) + "_generated.csv")
            with gen_path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames)
                generated_rows = list(reader)
            for seq in range(6000, 6010):
                r = generated_rows[seq]
                r["associated_at_generation"] = "1"
                r["attempted_socket_send"] = "1"
                r["send_return"] = "1000"
                r["drop_reason"] = ""
            with gen_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(generated_rows)

            # 10 accepted by the socket; 8 uniquely received; 2 not observed.
            with Path(str(prefix) + "_received.csv").open(
                "a", encoding="utf-8", newline=""
            ) as f:
                writer = csv.writer(f)
                for seq in range(6000, 6008):
                    t_gen = 10.0 + seq / 100.0
                    writer.writerow([
                        seq, f"{t_gen:.9f}", f"{t_gen + 0.001:.9f}",
                        "0.001000000", 1, 0, 1
                    ])

            # Complete association state transition around generation times.
            assoc_at = 69.999
            deassoc_at = 70.100
            x_at_assoc = 5.0 * (assoc_at - 70.0)
            ap_mac = "00:00:00:00:00:01"
            with Path(str(prefix) + "_association.csv").open(
                "a", encoding="utf-8", newline=""
            ) as f:
                writer = csv.writer(f)
                writer.writerow([assoc_at, "assoc", ap_mac, x_at_assoc,
                                 math.hypot(x_at_assoc, 1.5)])
                writer.writerow([deassoc_at, "deassoc", ap_mac, 0, 1.5])

            summary_path = Path(str(prefix) + "_summary.csv")
            with summary_path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                summary_fields = list(reader.fieldnames)
                summary = next(reader)
            summary.update({
                "drop_no_association": "11990",
                "socket_accepted": "10",
                "received_unique": "8",
                "received_on_time": "8",
                "not_observed_after_socket_accept": "2",
                "assoc_events": "1",
                "deassoc_events": "1",
                "associated_duration_s": "0.101",
            })
            with summary_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=summary_fields)
                writer.writeheader()
                writer.writerow(summary)

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p1.py"),
                 "--prefix", str(prefix), "--require-contact"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("8 unique received", result.stdout)
            self.assertIn("PASS: P1 CSV accounting", result.stdout)
            self.assertTrue(Path(str(prefix) + "_analysis.json").exists())


if __name__ == "__main__":
    unittest.main()
