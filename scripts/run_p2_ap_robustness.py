#!/usr/bin/env python3
"""AP-relocation robustness pilots without modifying the 120-run baseline.

One new run at v=15 m/s, stop=0/30 and AP x=-30/+30 produces
2 stops x 2 AP offsets x 2 policies = 8 new ns-3 simulations.
Identical seed/run, movement and packet generation are checked within each
new FIFO/immediate policy pair; the AP=0 baseline is read, not rerun.
"""
import argparse
import csv
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFSETS = (-30, 30)
STOPS = (0, 30)
POLICIES = ("immediate", "fifo")


def rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        data = list(csv.DictReader(f))
    if len(data) != 1:
        raise ValueError(f"Expected one row: {path}")
    return data[0]


def prefix_for(speed, stop, run, policy, ap_x):
    result = ROOT / "out" / "p2" / f"v{speed}_stop{stop}_run{run}_{policy}"
    if ap_x == -30:
        result = Path(str(result) + "_apxm30")
    elif ap_x == 30:
        result = Path(str(result) + "_apxp30")
    elif ap_x != 0:
        raise ValueError("Invalid AP displacement")
    return result


def check_existing(prefix, speed, stop, run, policy, ap_x):
    try:
        s = rows(Path(str(prefix) + "_summary.csv"))
        return (
            float(s["speed_mps"]) == speed
            and float(s["stop_s"]) == stop
            and float(s["ap_x_m"]) == ap_x
            and s["policy"] == policy
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["generated"]) == 12000
            and int(s["buffer_limit_bytes"]) == 4000000
            and float(s["pacing_ms"]) == 2.0
            and s["wifi_standard"] == "802.11g"
            and int(s["frequency_hz"]) == 2412000000
            and Path(str(prefix) + "_analysis.json").is_file()
        )
    except (OSError, ValueError, KeyError):
        return False


def command(*args):
    print("\n$", " ".join(map(str, args)), flush=True)
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ns3_dir", type=Path)
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    ns3_dir = args.ns3_dir.resolve()
    if not (ns3_dir / "ns3").is_file() or not (ns3_dir / "scratch").is_dir():
        parser.error(f"Not an ns-3 source tree: {ns3_dir}")
    if args.start_run < 1 or args.end_run < args.start_run:
        parser.error("Run interval must be positive and increasing")

    report = []
    new_count, reused = 0, 0
    for run in range(args.start_run, args.end_run + 1):
        for stop in STOPS:
            baseline = {}
            for policy in POLICIES:
                prefix = prefix_for(15, stop, run, policy, 0)
                if not check_existing(prefix, 15, stop, run, policy, 0):
                    raise ValueError(
                        f"Validated AP=0 baseline is missing: {prefix}. "
                        "Do not silently replace the baseline."
                    )
                command(sys.executable, "scripts/review_p2.py",
                        "--prefix", prefix, "--require-contact")
                baseline[policy] = rows(Path(str(prefix) + "_summary.csv"))

            for ap_x in OFFSETS:
                shifted = {}
                prefixes = {}
                for policy in POLICIES:
                    prefix = prefix_for(15, stop, run, policy, ap_x)
                    prefixes[policy] = prefix
                    if args.skip_existing and check_existing(
                        prefix, 15, stop, run, policy, ap_x
                    ):
                        command(sys.executable, "scripts/review_p2.py",
                                "--prefix", prefix, "--require-contact")
                        reused += 1
                    else:
                        command("bash", "scripts/run_p2.sh", ns3_dir,
                                policy, 15, stop, run, 2, ap_x)
                        new_count += 1
                    shifted[policy] = rows(Path(str(prefix) + "_summary.csv"))
                comparison_file = ROOT / "out" / "p2" / (
                    f"v15_stop{stop}_run{run}_apx"
                    f"{'m30' if ap_x < 0 else 'p30'}_pair_analysis.json"
                )
                command(
                    sys.executable, "scripts/compare_p2.py",
                    "--immediate-prefix", prefixes["immediate"],
                    "--fifo-prefix", prefixes["fifo"],
                    "--output-json", comparison_file
                )
                for policy in POLICIES:
                    b = baseline[policy]
                    s = shifted[policy]
                    report.append({
                        "speed_mps": 15,
                        "stop_s": stop,
                        "run": run,
                        "ap_x_m": ap_x,
                        "policy": policy,
                        "baseline_ap0_on_time": int(b["received_on_time"]),
                        "shifted_ap_on_time": int(s["received_on_time"]),
                        "ap_shift_delivery_change_messages": (
                            int(s["received_on_time"]) - int(b["received_on_time"])
                        ),
                        "shifted_association_s": float(s["associated_duration_s"]),
                        "shifted_overflow": int(s["buffer_overflow"]),
                        "shifted_expired": int(s["buffer_expired"]),
                    })
                print(f"AP {ap_x:+} m, stop={stop}s, run={run}: "
                      f"FIFO gain="
                      f"{int(shifted['fifo']['received_on_time'])-int(shifted['immediate']['received_on_time']):+d}"
                      " delivered messages")

    dest = ROOT / "out" / "p2" / (
        f"ap_robustness_runs{args.start_run}-{args.end_run}.csv"
    )
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(report[0]))
        writer.writeheader()
        writer.writerows(report)
    print(f"\nRobustness: {new_count} new, {reused} reused. Summary: {dest}")
    print("These runs change only AP x-coordinate, not MAC/PHY/pacing/channel.")
    print("AP relocation is a geometric sensitivity test, not fading/shadowing.")


if __name__ == "__main__":
    main()
