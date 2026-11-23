#!/usr/bin/env python3
"""No-ns-3 regression fixtures for P2 FIFO conservation and event order."""
import csv
import math
import subprocess
import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path, headers, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        w = csv.writer(file)
        w.writerow(headers)
        w.writerows(rows)


def make_fifo_without_contact(prefix, broken_order=False, with_sends=False):
    """Every message is queued, eventually expires, and no MAC association occurs."""
    generated = []
    movement = []
    for i in range(12000):
        t = 10.0 + i / 100.0
        x = 5.0 * (t - 70) if t < 70 else 0 if t < 80 else 5.0 * (t - 80)
        generated.append([i, f"{t:.9f}", f"{x:.9f}",
                          f"{math.hypot(x, 1.5):.9f}",
                          int(with_sends and 47 <= t < 50), 0, "", "enqueued"])
    write(str(prefix) + "_generated.csv",
          ["seq", "t_gen_s", "bus_x_m", "distance_ap_m",
           "associated_at_generation", "attempted_socket_send",
           "send_return", "drop_reason"], generated)

    for i in range(801):
        t = i * 0.25
        x = 5.0 * (t - 70) if t < 70 else 0 if t < 80 else 5.0 * (t - 80)
        velocity = 0 if 70 <= t < 80 else 5
        movement.append([f"{t:.9f}", f"{x:.9f}", velocity,
                         f"{math.hypot(x, 1.5):.9f}",
                         int(with_sends and 47 <= t < 50), -70])
    write(str(prefix) + "_mobility.csv",
          ["t_s", "bus_x_m", "bus_velocity_mps", "distance_ap_m",
           "associated", "pr_model_dbm"], movement)
    assoc = []
    if with_sends:
        assoc = [[47, "assoc", "00:00:00:00:00:01", -115,
                  math.hypot(-115, 1.5)],
                 [50, "deassoc", "00:00:00:00:00:01", -100,
                  math.hypot(-100, 1.5)]]
    write(str(prefix) + "_association.csv",
          ["t_s", "event", "ap_mac", "bus_x_m", "distance_ap_m"], assoc)
    rec = []
    sent = []
    if with_sends:
        for seq in range(10):
            gen = 10 + seq / 100
            t_send = 47 + seq * .002
            sent.append([seq, f"{gen:.9f}", f"{t_send:.9f}",
                         f"{t_send-gen:.9f}", 1000, "fifo"])
            if seq < 8:
                t_rx = t_send + .003
                rec.append([seq, f"{gen:.9f}", f"{t_rx:.9f}",
                            f"{t_rx-gen:.9f}", 1, 0, 1])
    write(str(prefix) + "_received.csv",
          ["seq", "t_gen_s", "t_rx_s", "delay_s", "on_time",
           "duplicate", "associated_at_reception"], rec)
    write(str(prefix) + "_sent.csv",
          ["seq", "t_gen_s", "t_socket_s", "age_at_send_s",
           "send_return", "policy"], sent)

    events = []
    for seq in range(12000):
        t = round(10.0 + seq / 100.0, 9)
        events.append((t, 0, seq, "enqueued"))
        if not with_sends or seq >= 10:
            events.append((round(t + 60.0, 9), 2, seq, "expired"))
    if with_sends:
        for seq in range(10):
            events.append((round(47.0 + seq * .002, 9), 1, seq,
                           "send_accepted"))
    events.sort()
    queue = deque()
    event_rows = []
    peak = 0
    for t, _, seq, action in events:
        if action == "enqueued":
            queue.append(seq)
        else:
            if not queue or queue[0] != seq:
                raise AssertionError("Synthetic test events out of FIFO order")
            queue.popleft()
        peak = max(peak, len(queue) * 1000)
        age = (t - (10.0 + seq / 100.0)) if action != "enqueued" else 0.
        event_rows.append([f"{t:.9f}", seq, action, len(queue), len(queue)*1000,
                           int(with_sends and 47 <= t < 50),
                           f"{age:.9f}", 1000 if action == "send_accepted" else ""])
    if broken_order:
        event_rows[1][1] = 123456
    write(str(prefix) + "_buffer.csv",
          ["t_s", "seq", "event", "queued_messages", "queued_bytes",
           "associated", "age_s", "send_return"], event_rows)
    if queue:
        raise AssertionError("Fixture must end with empty FIFO")

    summary = [
        "speed_mps", "stop_s", "ap_x_m", "seed", "run", "generated",
        "drop_no_association", "socket_rejected", "socket_accepted",
        "received_unique", "received_on_time", "received_late",
        "duplicate_rx", "malformed_rx", "not_observed_after_socket_accept",
        "associated_duration_s", "assoc_events", "deassoc_events", "policy",
        "buffer_enqueued", "buffer_overflow", "buffer_expired",
        "buffer_sent_attempts", "buffer_remaining", "buffer_peak_bytes",
        "buffer_limit_bytes", "pacing_ms", "path_loss_exponent", "tx_dbm",
        "wifi_standard", "frequency_hz"
    ]
    values = [5, 10, 0, 1, 1, 12000, 0, 0, 10 if with_sends else 0,
              8 if with_sends else 0, 8 if with_sends else 0, 0, 0, 0,
              2 if with_sends else 0, 3 if with_sends else 0,
              1 if with_sends else 0, 1 if with_sends else 0,
              "fifo", 12000, 0, 11990 if with_sends else 12000,
              10 if with_sends else 0, 0, peak, 12000000, 2, 3, 20,
              "802.11g", 2412000000]
    write(str(prefix) + "_summary.csv", summary, [values])


class P2ValidationTests(unittest.TestCase):
    def test_expiring_fifo_without_contact_is_accounted_for(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "fifo"
            make_fifo_without_contact(prefix)
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p2.py"),
                 "--prefix", str(prefix)], text=True, capture_output=True
            )
            self.assertEqual(process.returncode, 0,
                             process.stderr + process.stdout)
            self.assertIn("PASS P2 fifo", process.stdout)
            self.assertTrue(Path(str(prefix) + "_analysis.json").is_file())

    def test_associated_fifo_sends_and_receives_with_two_unobserved(self):
        # Positive delivery path: 10 sent from FIFO, 8 actually received,
        # and 2 accepted but not observed. Replays FIFO order and pacing.
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "fifo"
            make_fifo_without_contact(prefix, with_sends=True)
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p2.py"),
                 "--prefix", str(prefix), "--require-contact"],
                text=True, capture_output=True,
            )
            self.assertEqual(process.returncode, 0,
                             process.stderr + process.stdout)
            self.assertIn("AP unique received=8", process.stdout)
            self.assertIn("accepted-not-observed=2", process.stdout)

    def test_corrupted_fifo_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "fifo"
            make_fifo_without_contact(prefix, broken_order=True)
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p2.py"),
                 "--prefix", str(prefix)], text=True, capture_output=True
            )
            self.assertNotEqual(process.returncode, 0)

    def test_contact_required_for_positive_pilot(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "fifo"
            make_fifo_without_contact(prefix)
            process = subprocess.run(
                [sys.executable, str(ROOT / "scripts/review_p2.py"),
                 "--prefix", str(prefix), "--require-contact"],
                text=True, capture_output=True
            )
            self.assertNotEqual(process.returncode, 0)


if __name__ == "__main__":
    unittest.main()
