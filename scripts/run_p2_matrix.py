#!/usr/bin/env python3
"""Run paired B10 P2 experiment matrix on the group's installed ns-3.48.

One RNG run means 2 speeds x 3 stops x 2 policies = 12 simulations.
Use --skip-existing only to reuse cases whose summary matches all arguments
and have already passed review_p2.py, not to bypass verification.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEEDS = (5, 15)
STOPS = (0, 10, 30)
POLICIES = ("immediate", "fifo")


def existing_is_compatible(prefix, speed, stop, run):
    summary = Path(str(prefix) + "_summary.csv")
    analysis = Path(str(prefix) + "_analysis.json")
    if not summary.is_file() or not analysis.is_file():
        return False
    try:
        with summary.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1:
            return False
        row = rows[0]
        return (int(float(row["speed_mps"])) == speed and
                int(float(row["stop_s"])) == stop and
                int(row["run"]) == run and
                int(row["seed"]) == 1 and
                int(row["generated"]) == 12000 and
                row["policy"] == str(prefix).split("_")[-1] and
                int(row["buffer_limit_bytes"]) == 4000000 and
                float(row["pacing_ms"]) == 2.0 and
                row["wifi_standard"] == "802.11g" and
                int(row["frequency_hz"]) == 2412000000)
    except (ValueError, KeyError, OSError):
        return False


def execute(*args):
    print("\n$", " ".join(str(arg) for arg in args), flush=True)
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ns3_dir", type=Path,
                        help="Path from repository root to ns-3 source directory")
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true",
                        help="Reuse cases with matching summary and completed review JSON")
    args = parser.parse_args()
    if args.start_run < 1 or args.end_run < args.start_run:
        parser.error("run range must be >=1 and increasing")
    ns3_dir = args.ns3_dir.resolve()
    if not (ns3_dir / "ns3").is_file() or not (ns3_dir / "scratch").is_dir():
        parser.error(f"not an ns-3 source tree: {ns3_dir}")

    n_executed = 0
    n_reused = 0
    for run in range(args.start_run, args.end_run + 1):
        for speed in SPEEDS:
            for stop in STOPS:
                prefixes = {}
                for policy in POLICIES:
                    prefix = ROOT / "out" / "p2" / (
                        f"v{speed}_stop{stop}_run{run}_{policy}")
                    prefixes[policy] = prefix
                    if args.skip_existing and existing_is_compatible(
                        prefix, speed, stop, run
                    ):
                        print(f"Re-validating previous CSV: {prefix.name}", flush=True)
                        execute(sys.executable, "scripts/review_p2.py",
                                "--prefix", prefix, "--require-contact")
                        n_reused += 1
                    else:
                        execute("bash", "scripts/run_p2.sh", ns3_dir,
                                policy, speed, stop, run, 2)
                        n_executed += 1
                execute(
                    sys.executable, "scripts/compare_p2.py",
                    "--immediate-prefix", prefixes["immediate"],
                    "--fifo-prefix", prefixes["fifo"],
                    "--output-json", ROOT / "out" / "p2" /
                    f"v{speed}_stop{stop}_run{run}_pair_analysis.json",
                )
    print(f"\nMatrix completed: {n_executed} newly executed, {n_reused} reused; "
          f"{len(SPEEDS)*len(STOPS)*(args.end_run-args.start_run+1)} pairs.")
    print("Do not calculate IC95% from only one run per scenario.")


if __name__ == "__main__":
    main()
