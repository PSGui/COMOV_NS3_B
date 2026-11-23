#!/usr/bin/env python3
"""Compare matched P2 immediate vs FIFO pilot summaries.

The two simulation runs MUST use the same physical configuration, RNG seed/run,
speed, stop duration, application traffic and observation interval.
"""
import argparse
import csv
import math
from pathlib import Path


def read_summary(prefix):
    filename = Path(str(prefix) + "_summary.csv")
    with filename.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one summary row in {filename}")
    return rows[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--immediate-prefix", type=Path, required=True)
    parser.add_argument("--fifo-prefix", type=Path, required=True)
    args = parser.parse_args()

    imm = read_summary(args.immediate_prefix)
    fifo = read_summary(args.fifo_prefix)
    if imm["policy"] != "immediate" or fifo["policy"] != "fifo":
        raise ValueError("Wrong policy in input summaries")

    matching = ["speed_mps", "stop_s", "ap_x_m", "seed", "run", "generated",
                "path_loss_exponent", "tx_dbm", "wifi_standard", "frequency_hz"]
    for key in matching:
        if key not in imm or key not in fifo:
            raise ValueError(f"Missing pairing field {key}")
        if imm[key] != fifo[key] and not (
            key not in ("wifi_standard",) and
            math.isclose(float(imm[key]), float(fifo[key]), rel_tol=0, abs_tol=1e-9)
        ):
            raise ValueError(f"Unmatched experiment at {key}: {imm[key]} vs {fifo[key]}")

    count = int(imm["generated"])
    if count != 12000:
        raise ValueError("Unexpected generation window/traffic count")
    rows = [
        ("Generated", "generated"),
        ("Dropped while not associated", "drop_no_association"),
        ("FIFO overflow drop-newest", "buffer_overflow"),
        ("FIFO expired before socket", "buffer_expired"),
        ("Accepted by socket", "socket_accepted"),
        ("Unique received", "received_unique"),
        ("Received within 60 seconds", "received_on_time"),
        ("Accepted but not observed", "not_observed_after_socket_accept"),
        ("Peak FIFO bytes", "buffer_peak_bytes"),
    ]
    print("Metric                                immediate       fifo        delta")
    for label, field in rows:
        i = int(imm[field])
        f = int(fifo[field])
        print(f"{label:<36} {i:>9} {f:>10} {f-i:>+12}")

    imm_pct = 100 * int(imm["received_on_time"]) / count
    fifo_pct = 100 * int(fifo["received_on_time"]) / count
    print(f"\nOn-time delivery / generated: immediate={imm_pct:.3f}%, "
          f"fifo={fifo_pct:.3f}%, improvement={fifo_pct - imm_pct:+.3f} percentage points")
    print(f"Matched RNG seed/run: {imm['seed']}/{imm['run']}")
    print("This single matched pair is NOT a confidence interval or statistical result.")
    print("Socket acceptance, PHY delivery and application deadline remain distinct.")


if __name__ == "__main__":
    main()
