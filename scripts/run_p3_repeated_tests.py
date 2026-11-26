#!/usr/bin/env python3
"""B10 P3: repeat all three critical experiments using 10 paired ns-3 runs.

Every physical run keeps v=15 m/s, stop=0 s, seed=1, 12000 messages.
The 8 configs/run are:
 reference immediate/FIFO; fading Nakagami m=5 dynamic ARP immediate/FIFO;
 contention 2 Mbit/s immediate/FIFO; FIFO pacing=3ms; FIFO capacity=2MB.
80 simulations at runs 1..10, reusing validated existing outputs.
The P2 120-run matrix is NEVER overwritten or modified.
"""
import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

from paired_statistics_p2 import interval

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "p3"
P2 = ROOT / "out" / "p2"
GENERATED = 12000
PAYLOAD_BYTES = 1000

# Stable IDs for each exact intervention; all variants keep same PHY/trajectory.
CASES = (
    ("ref_immediate", "reference", "immediate", 2, 4000000, 1),
    ("ref_fifo", "reference", "fifo", 2, 4000000, 1),
    ("fading_m5_immediate", "fading", "immediate", 2, 4000000, 5),
    ("fading_m5_fifo", "fading", "fifo", 2, 4000000, 5),
    ("contention_immediate", "contention", "immediate", 2, 4000000, 1),
    ("contention_fifo", "contention", "fifo", 2, 4000000, 1),
    ("ref_fifo_pace3", "reference", "fifo", 3, 4000000, 1),
    ("ref_fifo_buf2mb", "reference", "fifo", 2, 2000000, 1),
)

# Policy comparisons; always preserve a common run number.
POLICY_PAIRS = (
    ("baseline_fifo_vs_immediate", "ref_immediate", "ref_fifo"),
    ("fading_m5_fifo_vs_immediate", "fading_m5_immediate", "fading_m5_fifo"),
    ("contention_fifo_vs_immediate", "contention_immediate", "contention_fifo"),
    ("pace3_fifo_vs_immediate", "ref_immediate", "ref_fifo_pace3"),
    ("buffer2mb_fifo_vs_immediate", "ref_immediate", "ref_fifo_buf2mb"),
)
# Effects of changing ONE experimental dimension, paired against its control.
SENSITIVITIES = (
    ("fading_m5_effect_on_fifo_gain",
     "baseline_fifo_vs_immediate", "fading_m5_fifo_vs_immediate"),
    ("contention_effect_on_fifo_gain",
     "baseline_fifo_vs_immediate", "contention_fifo_vs_immediate"),
    ("pacing3_effect_on_fifo_delivery", "ref_fifo", "ref_fifo_pace3"),
    ("buffer2mb_effect_on_fifo_delivery", "ref_fifo", "ref_fifo_buf2mb"),
)


def prefix_for(case, run):
    key, scenario, policy, pacing, capacity, fading_m = case
    root = OUT / (
        f"p3_{scenario}_v15_stop0_run{run}_{policy}_"
        f"pace{pacing}_buf{capacity}"
    )
    if fading_m != 1:
        root = Path(str(root) + f"_m{fading_m}")
    return root


def get_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def one_summary(prefix):
    file = Path(str(prefix) + "_summary.csv")
    rows = get_csv(file)
    if len(rows) != 1:
        raise ValueError(f"Expected one summary row: {file}")
    return rows[0]


def valid_existing(case, run):
    key, scenario, policy, pacing, capacity, fading_m = case
    prefix = prefix_for(case, run)
    try:
        s = one_summary(prefix)
        return (
            s["scenario"] == scenario and s["policy"] == policy
            and float(s["speed_mps"]) == 15
            and float(s["stop_s"]) == 0
            and float(s["ap_x_m"]) == 0
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["generated"]) == GENERATED
            and float(s["pacing_ms"]) == pacing
            and int(s["buffer_limit_bytes"]) == capacity
            and float(s.get("fading_m", "1")) == fading_m
            and int(s.get("static_arp", "0")) == 0
            and int(s["background_rate_bps"]) == (
                2000000 if scenario == "contention" else 0
            )
            and all(Path(str(prefix) + "_" + suffix).is_file()
                    for suffix in (
                        "summary.csv", "generated.csv", "sent.csv",
                        "received.csv", "association.csv",
                        "association_raw.csv", "buffer.csv", "mobility.csv",
                        "analysis.json",
                    ))
            and (scenario != "fading" or all(
                len(list(prefix.parent.glob(
                    prefix.name + "_pcap_" + radio + "*.pcap"
                ))) == 1 for radio in ("ap", "bus")
            ))
        )
    except (OSError, KeyError, ValueError):
        return False


def execute(*command):
    print("\n$", " ".join(map(str, command)), flush=True)
    subprocess.run([str(s) for s in command], cwd=ROOT, check=True)


def validate_reference(run, results):
    # This is non-negotiable: P3 control must reproduce the P2 results.
    for policy in ("immediate", "fifo"):
        original = one_summary(P2 / f"v15_stop0_run{run}_{policy}")
        current = results[f"ref_{policy}"]
        for field in (
            "generated", "received_unique", "received_on_time",
            "received_late", "socket_accepted", "socket_rejected",
            "buffer_overflow", "buffer_expired", "buffer_peak_bytes",
            "assoc_events", "deassoc_events",
        ):
            if int(original[field]) != int(current[field]):
                raise ValueError(
                    f"Run {run}: P3 reference differs from P2, {policy}, "
                    f"{field}: {original[field]} vs {current[field]}"
                )
        if not math.isclose(
            float(original["associated_duration_s"]),
            float(current["associated_duration_s"]),
            rel_tol=0, abs_tol=1e-6,
        ):
            raise ValueError(
                f"Run {run}: P3 reference association differs from P2, "
                f"policy={policy}"
            )


def percentile(values, proportion):
    if not values:
        return ""
    vals = sorted(values)
    position = (len(vals) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(vals) - 1)
    return vals[lower] + (position - lower) * (vals[upper] - vals[lower])


def observed_metrics(case, run):
    key, scenario, policy, pacing, capacity, fading_m = case
    prefix = prefix_for(case, run)
    s = one_summary(prefix)
    received = get_csv(Path(str(prefix) + "_received.csv"))
    unique = [r for r in received if int(r["duplicate"]) == 0]
    delays = [float(r["delay_s"]) for r in unique]
    if len(unique) != int(s["received_unique"]):
        raise ValueError(f"Run {run}, {key}: received count does not match summary")
    in_time = sum(int(r["on_time"]) for r in unique)
    if in_time != int(s["received_on_time"]):
        raise ValueError(f"Run {run}, {key}: on-time count does not match summary")
    assoc_s = float(s["associated_duration_s"])
    if assoc_s <= 0 and unique:
        raise ValueError(f"Run {run}, {key}: received UDP with zero associated seconds")
    goodput = 8 * PAYLOAD_BYTES * in_time / (1e6 * assoc_s) if assoc_s > 0 else ""
    return {
        "case": key,
        "run": run,
        "policy": policy,
        "scenario": scenario,
        "fading_m": fading_m,
        "pacing_ms": pacing,
        "buffer_bytes": capacity,
        "generated": GENERATED,
        "unique_received": len(unique),
        "received_on_time": in_time,
        "delivery_pct": in_time / GENERATED * 100,
        "association_s": assoc_s,
        "contact_goodput_mbps": goodput,
        "contact_success": int(in_time > 0),
        "assoc_events": int(s["assoc_events"]),
        "deassoc_events": int(s["deassoc_events"]),
        "ignored_deassoc_callbacks": int(s.get("ignored_deassoc_callbacks", "0")),
        "socket_accepted": int(s["socket_accepted"]),
        "accepted_unobserved": int(s["not_observed_after_socket_accept"]),
        "overflow": int(s["buffer_overflow"]),
        "expired": int(s["buffer_expired"]),
        "peak_bytes": int(s["buffer_peak_bytes"]),
        "background_rx_packets": int(s["background_rx_packets"]),
        "latency_mean_s_received_only": statistics.mean(delays) if delays else "",
        "latency_p95_s_received_only": percentile(delays, .95),
    }


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"Cannot write empty dataset: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def estimate(values):
    if not values:
        return ("", "", "")
    mean = statistics.mean(values)
    lower, upper = interval(values)
    return (mean, lower if lower is not None else "",
            upper if upper is not None else "")


def paired_results(grouped, runs):
    pair_rows = []
    per_run_deltas = {}
    for pair_name, control, treatment in POLICY_PAIRS:
        delta_pp = []
        delta_packets = []
        delta_goodput = []
        for run in runs:
            a = grouped[(run, control)]
            b = grouped[(run, treatment)]
            dp = b["delivery_pct"] - a["delivery_pct"]
            delta_pp.append(dp)
            delta_packets.append(
                b["received_on_time"] - a["received_on_time"]
            )
            if a["contact_goodput_mbps"] != "" and b["contact_goodput_mbps"] != "":
                delta_goodput.append(
                    b["contact_goodput_mbps"] - a["contact_goodput_mbps"]
                )
            per_run_deltas[(run, pair_name)] = dp
        mean_pp, low_pp, high_pp = estimate(delta_pp)
        mean_goodput, lo_g, hi_g = estimate(delta_goodput)
        pair_rows.append({
            "comparison": pair_name,
            "n_pairs": len(delta_pp),
            "control": control,
            "treatment": treatment,
            "control_mean_delivery_pct": statistics.mean(
                grouped[(run, control)]["delivery_pct"] for run in runs
            ),
            "treatment_mean_delivery_pct": statistics.mean(
                grouped[(run, treatment)]["delivery_pct"] for run in runs
            ),
            "mean_extra_packets": statistics.mean(delta_packets),
            "mean_gain_pp": mean_pp,
            "gain_pp_ci95_low": low_pp,
            "gain_pp_ci95_high": high_pp,
            "n_pairs_with_goodput_defined": len(delta_goodput),
            "mean_goodput_gain_mbps": mean_goodput,
            "goodput_gain_ci95_low_mbps": lo_g,
            "goodput_gain_ci95_high_mbps": hi_g,
            "control_successful_runs": sum(
                grouped[(run, control)]["contact_success"] for run in runs
            ),
            "treatment_successful_runs": sum(
                grouped[(run, treatment)]["contact_success"] for run in runs
            ),
        })
    return pair_rows, per_run_deltas


def sensitivity_results(grouped, deltas, runs):
    rows = []
    for name, control, treatment in SENSITIVITIES:
        if control in {p[0] for p in POLICY_PAIRS}:
            differences = [
                deltas[(run, treatment)] - deltas[(run, control)]
                for run in runs
            ]
        else:
            differences = [
                grouped[(run, treatment)]["delivery_pct"] -
                grouped[(run, control)]["delivery_pct"]
                for run in runs
            ]
        mean, low, high = estimate(differences)
        rows.append({
            "sensitivity": name,
            "baseline": control,
            "intervention": treatment,
            "n_runs": len(differences),
            "change_mean_pp": mean,
            "change_ci95_low_pp": low,
            "change_ci95_high_pp": high,
            "note": "Negative means fewer on-time deliveries or smaller FIFO gain",
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ns3_dir", type=Path)
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=10)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.start_run <= args.end_run <= args.start_run + 30):
        parser.error("Use 1..31 consecutive runs at most for Student-t table")
    ns3 = args.ns3_dir.resolve()
    if not (ns3 / "ns3").is_file() or not (ns3 / "scratch").is_dir():
        parser.error(f"Not an ns-3 source tree: {ns3}")

    runs = list(range(args.start_run, args.end_run + 1))
    records = []
    new_count = 0
    for run in runs:
        summary_per_case = {}
        for case in CASES:
            key, scenario, policy, pacing, capacity, fading_m = case
            prefix = prefix_for(case, run)
            if args.skip_existing and valid_existing(case, run):
                execute(sys.executable, "scripts/review_p3.py",
                        "--prefix", prefix)
            else:
                execute("bash", "scripts/run_p3.sh", ns3, scenario, policy,
                        15, 0, run, pacing, capacity, 0, 0, fading_m)
                new_count += 1
            if not valid_existing(case, run):
                raise ValueError(f"Missing/mismatched validated P3 run: {prefix}")
            summary_per_case[key] = one_summary(prefix)
            if scenario == "contention" and int(
                summary_per_case[key]["background_rx_packets"]
            ) == 0:
                raise ValueError(
                    f"Run {run}: competing STA not received at AP: {key}"
                )
            records.append(observed_metrics(case, run))
        validate_reference(run, summary_per_case)
        print(f"\nP3 run={run}: P3 reference reproduces P2 exactly. "
              f"All 8 policy/scenario outputs audited.")

    grouped = {(int(r["run"]), r["case"]): r for r in records}
    pair_rows, deltas = paired_results(grouped, runs)
    effect_rows = sensitivity_results(grouped, deltas, runs)

    label = f"runs{args.start_run}-{args.end_run}"
    run_csv = OUT / f"p3_repeated_{label}_runs.csv"
    pair_csv = OUT / f"p3_repeated_{label}_paired.csv"
    effects_csv = OUT / f"p3_repeated_{label}_effects.csv"
    manifest = OUT / f"p3_repeated_{label}_parameters.json"
    write_csv(run_csv, records)
    write_csv(pair_csv, pair_rows)
    write_csv(effects_csv, effect_rows)
    manifest.write_text(json.dumps({
        "aim": "Does onboard FIFO storage improve useful Wi-Fi contact?",
        "speed_mps": 15,
        "stop_s": 0,
        "seed": 1,
        "runs": runs,
        "cases": [dict(
            name=k, scenario=s, policy=p, pacing_ms=pace,
            buffer_bytes=buf, nakagami_m=m, dynamic_arp=True
        ) for k, s, p, pace, buf, m in CASES],
        "note": "Application goodput uses seconds of STA association, "
                "NOT radio PHY airtime; 95% CI is conditional on ns-3 model. "
                "Zero-UDP runs are INCLUDED in delivery rates and flagged. "
                "Undefined goodput with zero association is excluded from "
                "goodput CI, never replaced with zero.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nP3 completed: {8 * len(runs)} validated cases, "
          f"{new_count} new executions.")
    for row in pair_rows:
        print(f"{row['comparison']}: mean gain="
              f"{row['mean_gain_pp']:+.3f} pp "
              f"[{row['gain_pp_ci95_low']}, {row['gain_pp_ci95_high']}]; "
              f"successful runs control/treatment "
              f"{row['control_successful_runs']}/{row['treatment_successful_runs']}")
    print(f"\nCSV to send: {run_csv}, {pair_csv}, {effects_csv}")
    print("Next: python3 scripts/pack_p3_repeated_tests.py "
          f"--start-run {args.start_run} --end-run {args.end_run}")


if __name__ == "__main__":
    main()
