#!/usr/bin/env python3
"""B10: quantify whether onboard FIFO makes better use of AP contact.

Uses already-generated P2 summary/association/received CSV files.
No ns-3 rerun. Goodput = unique useful application payload bits received
per second of MAC association, NOT 802.11 PHY channel occupation.
"""
import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

from paired_statistics_p2 import interval

PAYLOAD_BYTES = 1000
TOTAL_MESSAGES = 12000
DEADLINE_S = 60.0
SIM_END_S = 200.0


def load_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV without columns: {path}")
        data = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in data):
        raise ValueError(f"Malformed CSV: {path}")
    return data


def one_summary(prefix):
    rows = load_rows(Path(str(prefix) + "_summary.csv"))
    if len(rows) != 1:
        raise ValueError(f"Expected one summary row for {prefix}")
    return rows[0]


def percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    p = (len(values) - 1) * q
    lower = int(p)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (p - lower) * (values[upper] - values[lower])


def association_duration(events):
    """MAC association intervals, not inferred coverage from RSS or distance."""
    start = None
    total = 0.0
    previous = -1.0
    for row in events:
        t = float(row["t_s"])
        if t < previous or t < 0 or t > SIM_END_S:
            raise ValueError("Invalid association timeline")
        previous = t
        if row["event"] == "assoc" and start is None:
            start = t
        elif row["event"] == "deassoc" and start is not None:
            total += t - start
            start = None
        else:
            raise ValueError("Invalid association transition")
    if start is not None:
        total += SIM_END_S - start
    return total


def inspect_run(prefix):
    summary = one_summary(prefix)
    assoc = load_rows(Path(str(prefix) + "_association.csv"))
    received = load_rows(Path(str(prefix) + "_received.csv"))
    assoc_s = association_duration(assoc)
    if not math.isclose(assoc_s, float(summary["associated_duration_s"]),
                        rel_tol=0, abs_tol=1e-5):
        raise ValueError(f"Association duration inconsistent: {prefix}")
    if int(summary["generated"]) != TOTAL_MESSAGES:
        raise ValueError(f"Unexpected generation count: {prefix}")

    received_ids = set()
    delays = []
    on_time = 0
    duplicates = 0
    times = []
    last_rx_s = -1
    for row in received:
        mid = int(row["seq"])
        timestamp = float(row["t_rx_s"])
        t_gen = float(row["t_gen_s"])
        delay = float(row["delay_s"])
        if timestamp < last_rx_s or timestamp > SIM_END_S or delay < 0:
            raise ValueError(f"Invalid reception time: {prefix} ID={mid}")
        last_rx_s = timestamp
        if not math.isclose(timestamp - t_gen, delay, rel_tol=0, abs_tol=1e-6):
            raise ValueError(f"Delay mismatch: {prefix} ID={mid}")
        if int(row["on_time"]) != int(delay <= DEADLINE_S):
            raise ValueError(f"Deadline flag mismatch: {prefix} ID={mid}")
        dup = mid in received_ids
        if int(row["duplicate"]) != int(dup):
            raise ValueError(f"Duplicate flag mismatch: {prefix} ID={mid}")
        if dup:
            duplicates += 1
            continue
        received_ids.add(mid)
        delays.append(delay)
        times.append(timestamp)
        on_time += int(delay <= DEADLINE_S)

    if len(received_ids) != int(summary["received_unique"]):
        raise ValueError(f"Received unique count mismatch: {prefix}")
    if on_time != int(summary["received_on_time"]):
        raise ValueError(f"Received on-time count mismatch: {prefix}")
    if duplicates != int(summary["duplicate_rx"]):
        raise ValueError(f"Received duplicate count mismatch: {prefix}")
    if len(received_ids) < int(summary["received_late"]):
        raise ValueError(f"Invalid late count: {prefix}")
    if len(received_ids) - on_time != int(summary["received_late"]):
        raise ValueError(f"Received late count mismatch: {prefix}")
    if assoc_s <= 0 and received_ids:
        raise ValueError(f"Data delivered with zero association: {prefix}")

    data = {
        "speed_mps": int(float(summary["speed_mps"])),
        "stop_s": int(float(summary["stop_s"])),
        "ap_x_m": float(summary["ap_x_m"]),
        "seed": int(summary["seed"]),
        "run": int(summary["run"]),
        "policy": summary["policy"],
        "n_generated": TOTAL_MESSAGES,
        "n_unique_delivered": len(received_ids),
        "n_on_time": on_time,
        "on_time_delivery_pct": 100 * on_time / TOTAL_MESSAGES,
        "useful_rx_MB": len(received_ids) * PAYLOAD_BYTES / 1e6,
        "on_time_rx_MB": on_time * PAYLOAD_BYTES / 1e6,
        "association_s": assoc_s,
        "contact_goodput_mbps": (
            8 * len(received_ids) * PAYLOAD_BYTES / assoc_s / 1e6
            if assoc_s > 0 else 0.0
        ),
        "on_time_contact_goodput_mbps": (
            8 * on_time * PAYLOAD_BYTES / assoc_s / 1e6
            if assoc_s > 0 else 0.0
        ),
        "rx_first_s": min(times) if times else "",
        "rx_last_s": max(times) if times else "",
        "rx_first_to_last_span_s": (
            max(times) - min(times) if len(times) > 1 else 0.0
        ),
        "latency_mean_s": statistics.mean(delays) if delays else "",
        "latency_median_s": percentile(delays, .5) if delays else "",
        "latency_p95_s": percentile(delays, .95) if delays else "",
        "latency_max_s": max(delays) if delays else "",
        "buffer_peak_bytes": int(summary["buffer_peak_bytes"]),
        "buffer_overflow": int(summary["buffer_overflow"]),
        "buffer_expired": int(summary["buffer_expired"]),
        "accepted_unobserved": int(summary["not_observed_after_socket_accept"]),
    }
    # Association event rows are compared by timestamp and event, not the
    # AP MAC string. Compare same physical scenario for both policies.
    signature = [(row["event"], float(row["t_s"])) for row in assoc]
    return data, signature


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No records for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean_numeric(rows, key):
    values = [float(row[key]) for row in rows if row[key] != ""]
    return statistics.mean(values) if values else ""


def summarize(per_run):
    grouped = defaultdict(list)
    for row in per_run:
        key = (row["speed_mps"], row["stop_s"], row["ap_x_m"],
               row["policy"])
        grouped[key].append(row)
    scenarios = []
    for key, rows in sorted(grouped.items()):
        speed, stop, ap_x, policy = key
        scenarios.append({
            "speed_mps": speed,
            "stop_s": stop,
            "ap_x_m": ap_x,
            "policy": policy,
            "n_runs": len(rows),
            "delivery_pct_mean": mean_numeric(rows, "on_time_delivery_pct"),
            "goodput_mbps_mean": mean_numeric(rows, "contact_goodput_mbps"),
            "on_time_goodput_mbps_mean": mean_numeric(
                rows, "on_time_contact_goodput_mbps"
            ),
            "association_s_mean": mean_numeric(rows, "association_s"),
            "rx_span_s_mean": mean_numeric(rows, "rx_first_to_last_span_s"),
            "latency_mean_s_mean": mean_numeric(rows, "latency_mean_s"),
            "latency_median_s_mean": mean_numeric(rows, "latency_median_s"),
            "latency_p95_s_mean": mean_numeric(rows, "latency_p95_s"),
            "latency_max_s_mean": mean_numeric(rows, "latency_max_s"),
            "buffer_peak_bytes_mean": mean_numeric(rows, "buffer_peak_bytes"),
            "buffer_overflow_mean": mean_numeric(rows, "buffer_overflow"),
            "buffer_expired_mean": mean_numeric(rows, "buffer_expired"),
        })
    return scenarios


def paired_differences(per_run, signatures):
    grouped = defaultdict(dict)
    for row in per_run:
        key = (row["speed_mps"], row["stop_s"], row["ap_x_m"], row["run"])
        policy = row["policy"]
        if policy in grouped[key]:
            raise ValueError(f"Duplicate policy for {key}")
        grouped[key][policy] = row
    collected = defaultdict(list)
    for key, policies in grouped.items():
        if set(policies) != {"fifo", "immediate"}:
            raise ValueError(f"Missing paired policy for {key}")
        imm, fifo = policies["immediate"], policies["fifo"]
        if imm["seed"] != fifo["seed"] or imm["association_s"] != fifo["association_s"]:
            raise ValueError(f"Unmatched seed or association duration: {key}")
        a = signatures[(*key, "immediate")]
        b = signatures[(*key, "fifo")]
        if len(a) != len(b) or any(
            x[0] != y[0] or not math.isclose(x[1], y[1], rel_tol=0, abs_tol=1e-6)
            for x, y in zip(a, b)
        ):
            raise ValueError(f"Unmatched association events: {key}")
        collected[key[:3]].append({
            "delivery_gain_pp": fifo["on_time_delivery_pct"] - imm["on_time_delivery_pct"],
            "goodput_gain_mbps": fifo["contact_goodput_mbps"] -
                                  imm["contact_goodput_mbps"],
            "on_time_goodput_gain_mbps": fifo["on_time_contact_goodput_mbps"] -
                                          imm["on_time_contact_goodput_mbps"],
            "mean_latency_difference_s": (
                fifo["latency_mean_s"] - imm["latency_mean_s"]
                if fifo["latency_mean_s"] != "" and imm["latency_mean_s"] != ""
                else ""
            ),
        })
    results = []
    for key, records in sorted(collected.items()):
        diffs = [r["delivery_gain_pp"] for r in records]
        goodputs = [r["on_time_goodput_gain_mbps"] for r in records]
        delta_latency = [r["mean_latency_difference_s"] for r in records
                         if r["mean_latency_difference_s"] != ""]
        ci_delivery = interval(diffs)
        ci_goodput = interval(goodputs)
        results.append({
            "speed_mps": key[0],
            "stop_s": key[1],
            "ap_x_m": key[2],
            "n_pairs": len(records),
            "delivery_gain_mean_pp": statistics.mean(diffs),
            "delivery_gain_ci95_low_pp": ci_delivery[0] if ci_delivery[0] is not None else "",
            "delivery_gain_ci95_high_pp": ci_delivery[1] if ci_delivery[1] is not None else "",
            "on_time_goodput_gain_mean_mbps": statistics.mean(goodputs),
            "on_time_goodput_gain_ci95_low_mbps": (
                ci_goodput[0] if ci_goodput[0] is not None else ""
            ),
            "on_time_goodput_gain_ci95_high_mbps": (
                ci_goodput[1] if ci_goodput[1] is not None else ""
            ),
            "mean_latency_difference_s": (
                statistics.mean(delta_latency) if delta_latency else ""
            ),
        })
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("out/p2"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/p2"))
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=10)
    parser.add_argument("--speeds", nargs="+", type=int, default=[5, 15])
    parser.add_argument("--stops", nargs="+", type=int, default=[0, 10, 30])
    parser.add_argument("--ap-x", type=float, default=0.0)
    args = parser.parse_args()
    if args.start_run < 1 or args.end_run < args.start_run:
        parser.error("Invalid run interval")
    if args.end_run - args.start_run > 30:
        parser.error("Student t table only supports at most 31 runs")
    if args.ap_x != 0:
        parser.error("AP displacement runs are analysed separately")
    per_run = []
    signatures = {}
    for speed in args.speeds:
        for stop in args.stops:
            for run in range(args.start_run, args.end_run + 1):
                for policy in ("immediate", "fifo"):
                    prefix = args.input_dir / (
                        f"v{speed}_stop{stop}_run{run}_{policy}"
                    )
                    record, signature = inspect_run(prefix)
                    if (record["speed_mps"] != speed or record["stop_s"] != stop or
                        record["run"] != run or record["policy"] != policy or
                        record["ap_x_m"] != args.ap_x):
                        raise ValueError(f"Scenario mismatch at {prefix}")
                    per_run.append(record)
                    signatures[(speed, stop, args.ap_x, run, policy)] = signature
    summary = summarize(per_run)
    paired = paired_differences(per_run, signatures)
    write_csv(args.output_dir / "contact_metrics_runs.csv", per_run)
    write_csv(args.output_dir / "contact_metrics_summary.csv", summary)
    write_csv(args.output_dir / "contact_metrics_pairs.csv", paired)
    print(f"PASS: {len(per_run)} run-level records, {len(paired)} physical pairs.")
    print("Goodput = useful UDP application payload delivered per association second.")
    print("This is NOT a measurement of Wi-Fi PHY airtime utilisation.")
    print("P95 in scenario summary = mean of per-run P95 values, not pooled P95.")
    for r in paired:
        print(
            f"v={r['speed_mps']} m/s, stop={r['stop_s']} s: "
            f"FIFO on-time gain={r['delivery_gain_mean_pp']:+.3f} pp; "
            f"goodput gain={r['on_time_goodput_gain_mean_mbps']:+.4f} Mbit/s"
        )


if __name__ == "__main__":
    main()
