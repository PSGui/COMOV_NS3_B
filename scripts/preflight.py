#!/usr/bin/env python3
"""B10: independent analytical preflight; DOES NOT run ns-3."""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "params/reference.json").read_text(encoding="utf-8"))
OUT = ROOT / "out/preflight"
C = 299_792_458.0


def fspl(f_hz, distance_m):
    if distance_m <= 0:
        raise ValueError("distance must be positive")
    return 20 * math.log10(4 * math.pi * distance_m * f_hz / C)


def log_distance_loss(f_hz, distance_m, exponent, d0=1.0):
    # Analytic reference only; inspect exact ns-3 implementation for d<d0.
    if distance_m < d0:
        return fspl(f_hz, d0)
    return fspl(f_hz, d0) + 10 * exponent * math.log10(distance_m / d0)


def distance_to_ap(x_bus_m, x_ap_m, vertical_separation_m):
    return math.hypot(x_bus_m - x_ap_m, vertical_separation_m)


def x_position(time_s, speed_mps, stop_s, stop_at_s):
    if time_s < stop_at_s:
        return speed_mps * (time_s - stop_at_s)
    if time_s < stop_at_s + stop_s:
        return 0.0
    return speed_mps * (time_s - stop_at_s - stop_s)


def write_csv(filename, rows):
    if not rows:
        raise ValueError("no rows to write")
    with (OUT / filename).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    app = CFG["application"]
    sim = CFG["simulation"]
    geo = CFG["scenario"]
    wifi = CFG["wifi"]
    OUT.mkdir(parents=True, exist_ok=True)
    rate = app["generation_rate_packets_per_s"]
    payload = app["packet_payload_bytes"]
    duration = app["generation_end_s"] - app["generation_start_s"]
    generated = round(rate * duration)
    assert abs(generated - rate * duration) < 1e-10
    assert app["buffer_max_bytes"] % payload == 0
    assert sim["drain_end_s"] >= app["generation_end_s"] + app["deadline_s"]
    for stop in geo["stop_durations_s"]:
        assert geo["stop_start_s"] >= app["generation_start_s"]
        assert geo["stop_start_s"] + stop <= app["generation_end_s"]

    print("B10 | ANALYTIC PREFLIGHT ONLY — no ns-3 results")
    print(f"Generation: {rate:.0f} packets/s × {payload} bytes = {rate * payload * 8 / 1e6:.3f} Mbit/s")
    print(f"Window: {duration:g} s -> {generated} messages, {generated * payload / 1e6:g} MB")
    print(f"Buffer: {app['buffer_max_bytes'] / 1e6:g} MB, "
          f"{app['buffer_max_bytes'] / (rate * payload):g} s without service")
    print("PHY rate is NOT application goodput.")

    matrix = []
    for speed in geo["approach_speeds_mps"]:
        for stop in geo["stop_durations_s"]:
            for policy in app["policies"]:
                idx = len(matrix) + 1
                matrix.append(dict(
                    config_id=f"B10-{idx:02d}",
                    speed_mps=speed,
                    stop_s=stop,
                    policy=policy,
                    generation_start_s=app["generation_start_s"],
                    generation_end_s=app["generation_end_s"],
                    stop_start_s=geo["stop_start_s"],
                    observation_end_s=sim["drain_end_s"],
                    initial_runs=sim["initial_runs_per_configuration"],
                ))
    assert len(matrix) == 12
    write_csv("matrix.csv", matrix)
    print(f"Matrix: {len(matrix)} configurations, "
          f"{len(matrix) * sim['initial_runs_per_configuration']} initial runs")

    example_distances = (1, 5, 10, 20, 50, 100, 200)
    link_rows = []
    for standard, freq in ((wifi["reference_standard"], wifi["reference_frequency_hz"]),
                           (wifi["comparison_standard"], wifi["comparison_frequency_hz"])):
        print(f"{standard}: FSPL(1m) = {fspl(freq, 1):.3f} dB")
        for d in example_distances:
            loss = log_distance_loss(freq, d, wifi["path_loss_exponent"],
                                     wifi["reference_distance_m"])
            received = (wifi["tx_power_dbm"] + wifi["tx_antenna_gain_dbi"] +
                        wifi["rx_antenna_gain_dbi"] - wifi["tx_system_loss_db"] -
                        wifi["rx_system_loss_db"] - loss)
            link_rows.append(dict(standard=standard, frequency_hz=freq, distance_m=d,
                                  path_loss_db=round(loss, 5),
                                  received_power_dbm=round(received, 5),
                                  note="analytic hypothetical, no PER/sensitivity test"))
    write_csv("theory.csv", link_rows)
    contact_rows = []
    for horizontal_radius in CFG["analysis"]["illustrative_radius_m"]:
        for speed in geo["approach_speeds_mps"]:
            for stop in geo["stop_durations_s"]:
                contact_rows.append(dict(assumed_horizontal_radius_m=horizontal_radius,
                                         speed_mps=speed, stop_s=stop,
                                         geometric_contact_s=round(2 * horizontal_radius / speed + stop, 5),
                                         note="hypothetical radius, NOT simulated coverage"))
    write_csv("contact_examples.csv", contact_rows)
    print(f"Wrote: {OUT.relative_to(ROOT)}/matrix.csv, theory.csv, contact_examples.csv")


if __name__ == "__main__":
    main()
