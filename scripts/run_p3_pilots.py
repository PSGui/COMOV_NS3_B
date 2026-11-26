#!/usr/bin/env python3
"""B10 P3: run 8 stress pilots, preserving all 120 P2 reference simulations.

Experiment A: Nakagami m=1 fading vs a separate two-node control.
Experiment B: a 2 Mbit/s competing uplink STA vs the same control.
Experiment C: FIFO pacing=3ms or capacity=2MB vs the 2ms/4MB FIFO.
Initial physical case: v=15 m/s, stop=0s, run=1.
"""
import argparse
import csv
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("reference", "immediate", 2, 4000000),
    ("reference", "fifo", 2, 4000000),
    ("fading", "immediate", 2, 4000000),
    ("fading", "fifo", 2, 4000000),
    ("contention", "immediate", 2, 4000000),
    ("contention", "fifo", 2, 4000000),
    ("reference", "fifo", 3, 4000000),
    ("reference", "fifo", 2, 2000000),
)


def prefix_for(scenario, policy, speed, stop, run, pacing, capacity):
    return ROOT / "out" / "p3" / (
        f"p3_{scenario}_v{speed}_stop{stop}_run{run}_"
        f"{policy}_pace{pacing}_buf{capacity}"
    )


def load_summary(prefix):
    path = Path(str(prefix) + "_summary.csv")
    with path.open(encoding="utf-8", newline="") as stream:
        values = list(csv.DictReader(stream))
    if len(values) != 1:
        raise ValueError(f"Expected 1 row: {path}")
    return values[0]


def valid_existing(prefix, scenario, policy, speed, stop, run, pace, capacity):
    try:
        s = load_summary(prefix)
        return (
            s["scenario"] == scenario and s["policy"] == policy
            and float(s["speed_mps"]) == speed and float(s["stop_s"]) == stop
            and float(s["ap_x_m"]) == 0.0
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["generated"]) == 12000
            and float(s["pacing_ms"]) == pace
            and int(s["buffer_limit_bytes"]) == capacity
            and (int(s["background_rate_bps"]) == 2000000
                 if scenario == "contention" else
                 int(s["background_rate_bps"]) == 0)
            and Path(str(prefix) + "_analysis.json").is_file()
        )
    except (OSError, ValueError, KeyError):
        return False


def execute(*command):
    print("\n$", " ".join(map(str, command)), flush=True)
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ns3_dir", type=Path)
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--speed", type=int, choices=(5, 15), default=15)
    parser.add_argument("--stop", type=int, choices=(0, 10, 30), default=0)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    if args.run < 1:
        parser.error("--run must be positive")
    ns3 = args.ns3_dir.resolve()
    if not (ns3 / "ns3").is_file() or not (ns3 / "scratch").is_dir():
        parser.error(f"not an ns-3 source tree: {ns3}")

    result = {}
    new_count = 0
    for scenario, policy, pace, capacity in CASES:
        prefix = prefix_for(
            scenario, policy, args.speed, args.stop, args.run, pace, capacity
        )
        if (args.skip_existing and valid_existing(
                prefix, scenario, policy, args.speed, args.stop, args.run,
                pace, capacity)):
            execute(sys.executable, "scripts/review_p2.py", "--prefix", prefix)
        else:
            execute("bash", "scripts/run_p3.sh", ns3, scenario, policy,
                    args.speed, args.stop, args.run, pace, capacity)
            new_count += 1
        s = load_summary(prefix)
        if not valid_existing(prefix, scenario, policy, args.speed, args.stop,
                              args.run, pace, capacity):
            raise ValueError(f"Incorrect scenario outputs: {prefix}")
        if scenario == "contention" and int(s["background_rx_packets"]) == 0:
            raise ValueError("Competing STA traffic NOT observed at AP; invalid contention stress test")
        result[(scenario, policy, pace, capacity)] = s

    # Before studying stress variants, the P3 control MUST reproduce the original
    # P2 results; otherwise physics/implementation changed before the stressor.
    for policy in ("immediate", "fifo"):
        original = ROOT / "out" / "p2" / (
            f"v{args.speed}_stop{args.stop}_run{args.run}_{policy}")
        previous = load_summary(original)
        current = result[("reference", policy, 2, 4000000)]
        for field in ("generated", "received_on_time", "received_unique",
                      "socket_accepted", "buffer_overflow", "buffer_expired"):
            if int(previous[field]) != int(current[field]):
                raise ValueError(f"P3 reference does NOT reproduce P2 for "
                                 f"{policy}, {field}: P2={previous[field]}, "
                                 f"P3={current[field]}")
        if not math.isclose(
            float(previous["associated_duration_s"]),
            float(current["associated_duration_s"]),
            abs_tol=1e-6
        ):
            raise ValueError(f"P3 changed reference Wi-Fi association: {policy}")

    ref = result[("reference", "immediate", 2, 4000000)]
    original_fifo = result[("reference", "fifo", 2, 4000000)]
    records = []
    for scenario, policy, pace, capacity in CASES:
        s = result[(scenario, policy, pace, capacity)]
        association = float(s["associated_duration_s"])
        delivered = int(s["received_on_time"])
        records.append({
            "scenario": scenario,
            "policy": policy,
            "speed_mps": args.speed,
            "stop_s": args.stop,
            "run": args.run,
            "pacing_ms": pace,
            "buffer_bytes": capacity,
            "on_time": delivered,
            "delivery_pct": 100 * delivered / 12000,
            "goodput_contact_mbps": (
                0.008 * delivered / association if association else 0
            ),
            "assoc_s": association,
            "overflows": int(s["buffer_overflow"]),
            "expired": int(s["buffer_expired"]),
            "socket_accepted": int(s["socket_accepted"]),
            "not_observed_after_accept": int(
                s["not_observed_after_socket_accept"]
            ),
            "background_rx_packets": int(s["background_rx_packets"]),
            "delta_on_time_vs_ref_same_policy": (
                delivered - int(
                    result[("reference", policy, 2, 4000000)]["received_on_time"]
                )
            ),
            "delta_on_time_vs_reference_immediate": (
                delivered - int(ref["received_on_time"])
            ),
            "delta_on_time_vs_reference_fifo": (
                delivered - int(original_fifo["received_on_time"])
            ),
        })
    output = ROOT / "out" / "p3" / (
        f"p3_pilots_v{args.speed}_stop{args.stop}_run{args.run}.csv"
    )
    save_csv(output, records)
    print(f"\nP3 PASS: 8 validated configurations, {new_count} new executions.")
    print("P3 reference exactly reproduces baseline P2 delivery and association.")
    print("NOTE: policy differences under fading/contention may change association.")
    for row in records:
        print(f"{row['scenario']:10s} {row['policy']:9s} "
              f"pacing={row['pacing_ms']}ms cap={row['buffer_bytes']//1000000}MB: "
              f"delivery={row['delivery_pct']:.2f}%, "
              f"goodput={row['goodput_contact_mbps']:.3f} Mbit/s, "
              f"overflow={row['overflows']}")
    print(f"CSV to send: {output}")
    print("For interpretation also send the 8 *_summary.csv and "
          "the corresponding 8 *_association.csv, *_received.csv.")


if __name__ == "__main__":
    main()
