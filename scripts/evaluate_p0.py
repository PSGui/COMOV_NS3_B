#!/usr/bin/env python3
"""Independently verify ns-3.48 P0 propagation CSV.

Theoretical values are recalculated from frequency, antenna positions and
log-distance parameters, without reading the C++ theoretical column as truth.
This checks MODEL arithmetic and decoded-frame RSS, not UDP or association.
"""
import argparse
import csv
import math
import sys
from pathlib import Path

C = 299_792_458.0


def expected_received_dbm(f_hz, d_3d, exponent, ref_m=1.0, tx_dbm=20.0):
    if d_3d < ref_m:
        raise ValueError("d_3d below reference distance")
    reference_loss_db = 20 * math.log10(4 * math.pi * f_hz * ref_m / C)
    return tx_dbm - reference_loss_db - 10 * exponent * math.log10(d_3d / ref_m)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--tx-power-dbm", type=float, default=20.0)
    parser.add_argument("--ap-height-m", type=float, default=4.0)
    parser.add_argument("--sta-height-m", type=float, default=2.5)
    parser.add_argument("--model-tolerance-db", type=float, default=0.01)
    parser.add_argument("--phy-tolerance-db", type=float, default=1.5)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != 7:
        raise ValueError(f"expected 7 static positions; got {len(rows)}")
    for index, row in enumerate(rows, start=2):
        # DictReader stores any extra fields under None, and uses None when
        # a trailing column is missing. Neither is valid for the P0 schema.
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"malformed CSV at line {index}: wrong number of fields")

    max_model_error = 0.0
    phy_deltas = []
    phy_rows = 0
    near_has_phy = False

    for row in rows:
        h = float(row["horizontal_m"])
        d = math.hypot(h, args.ap_height_m - args.sta_height_m)
        d_csv = float(row["distance_3d_m"])
        if abs(d - d_csv) > 1e-4:
            raise ValueError(f"incorrect 3D distance for horizontal={h}: {d_csv} vs {d}")

        freq = float(row["frequency_hz"])
        exponent = float(row["path_loss_exponent"])
        expected = expected_received_dbm(freq, d, exponent, tx_dbm=args.tx_power_dbm)
        reported = float(row["ns3_model_pr_dbm"])
        delta = reported - expected
        max_model_error = max(max_model_error, abs(delta))
        frames = int(row["decoded_frames_at_sta"])
        phy_rss = row["phy_rss_mean_dbm"].strip()

        if frames == 0 and phy_rss:
            raise ValueError(f"RSS reported without frames at h={h}")
        if frames > 0 and not phy_rss:
            raise ValueError(f"frames decoded without RSS at h={h}")
        if frames > 0:
            phy_rows += 1
            if h <= 10.0:
                near_has_phy = True
            phy_deltas.append((h, float(phy_rss) - expected, frames))

    print(f"Analysed {len(rows)} positions from {args.input}")
    print(f"Max independent model error: {max_model_error:.6f} dB "
          f"(tolerance {args.model_tolerance_db:.3f} dB)")
    print(f"Positions with decoded PHY frames: {phy_rows}/{len(rows)}")
    for h, delta, frames in phy_deltas:
        print(f"  h={h:g} m: PHY minus theory={delta:+.4f} dB, decoded_frames={frames}")

    if max_model_error > args.model_tolerance_db:
        print("FAIL: propagation-model result disagrees with independent calculation", file=sys.stderr)
        return 1
    if not near_has_phy:
        print("FAIL: no successful decoded Wi-Fi frames at near distances (0/5/10 m)",
              file=sys.stderr)
        return 1
    discrepant = [(h, delta) for h, delta, _ in phy_deltas
                  if abs(delta) > args.phy_tolerance_db]
    if discrepant:
        print(f"WARNING: PHY RSS outside ±{args.phy_tolerance_db:g} dB of propagation-only "
              f"reference at {discrepant}. Check gain, transmit power, PHY trace semantics.")
        # This should be understood, not silently treated as a model failure.
    print("PASS: model vs independent equations and nearby decoded-frame trace.")
    print("NOTE: no frames at long distances is not automatically a simulation error; "
          "association, PDR and usable coverage are not assessed by P0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
