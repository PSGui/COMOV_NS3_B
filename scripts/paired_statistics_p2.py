#!/usr/bin/env python3
"""Paired statistics for B10 P2 experiments using stdlib only.

Each pair matches speed, stop, seed, run, channel and 12000 generated messages.
95% Student-t confidence intervals refer to the model's stochastic components
(MAC backoff, etc.), NOT environmental real-world uncertainty.
"""
import argparse
import csv
import math
import statistics
from pathlib import Path

# Two-sided 95% Student-t critical values by integer degrees of freedom.
# Rounded to three decimals; adequate for summary presentation.
T_CRITICAL_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def get_summary(path):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"Expected one summary row: {path}")
    return rows[0]


def interval(samples):
    if len(samples) < 2:
        return None, None
    df = len(samples) - 1
    if df not in T_CRITICAL_95:
        raise ValueError("95% t table supports 2..31 runs; extend the table "
                         "or use scipy.stats.t.ppf for larger samples")
    mean = statistics.mean(samples)
    error = T_CRITICAL_95[df] * statistics.stdev(samples) / math.sqrt(len(samples))
    return mean - error, mean + error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("out/p2"))
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=10)
    parser.add_argument("--output-csv", type=Path,
                        default=Path("out/p2/paired_statistics.csv"))
    args = parser.parse_args()
    if not (1 <= args.start_run <= args.end_run <= args.start_run + 30):
        parser.error("Invalid run range, maximum 31 consecutive paired runs")

    records = []
    for speed in (5, 15):
        for stop in (0, 10, 30):
            deltas_pp = []
            deltas_messages = []
            imm_rates = []
            fifo_rates = []
            fifo_overflow = []
            fifo_expired = []
            fifo_peak = []
            for run in range(args.start_run, args.end_run + 1):
                root = args.output_dir / f"v{speed}_stop{stop}_run{run}"
                imm = get_summary(Path(str(root) + "_immediate_summary.csv"))
                fifo = get_summary(Path(str(root) + "_fifo_summary.csv"))
                if imm["policy"] != "immediate" or fifo["policy"] != "fifo":
                    raise ValueError(f"Wrong policies in pair {root}")
                for key in ("speed_mps", "stop_s", "ap_x_m", "seed", "run",
                            "path_loss_exponent", "tx_dbm",
                            "wifi_standard", "frequency_hz", "generated"):
                    if imm[key] != fifo[key] and not (
                        key != "wifi_standard" and
                        math.isclose(float(imm[key]), float(fifo[key]),
                                     rel_tol=0, abs_tol=1e-9)
                    ):
                        raise ValueError(f"Pair mismatch {key}: {root}")
                if int(imm["run"]) != run or int(imm["seed"]) != 1:
                    raise ValueError(f"Unexpected RNG for {root}")
                if int(float(imm["speed_mps"])) != speed or int(float(
                    imm["stop_s"])) != stop:
                    raise ValueError(f"Scenario mismatch: {root}")
                generated = int(imm["generated"])
                if generated != 12000 or int(fifo["generated"]) != 12000:
                    raise ValueError(f"Wrong generation count in pair {root}")
                if float(fifo["pacing_ms"]) != 2.0:
                    raise ValueError("Reference matrix must use 2 ms FIFO pacing")
                n_i = int(imm["received_on_time"])
                n_f = int(fifo["received_on_time"])
                imm_rates.append(100 * n_i / generated)
                fifo_rates.append(100 * n_f / generated)
                deltas_pp.append(100 * (n_f - n_i) / generated)
                deltas_messages.append(n_f - n_i)
                fifo_overflow.append(int(fifo["buffer_overflow"]))
                fifo_expired.append(int(fifo["buffer_expired"]))
                fifo_peak.append(int(fifo["buffer_peak_bytes"]))

            low, high = interval(deltas_pp)
            record = {
                "speed_mps": speed,
                "stop_s": stop,
                "n_pairs": len(deltas_pp),
                "immediate_delivery_mean_pct": statistics.mean(imm_rates),
                "fifo_delivery_mean_pct": statistics.mean(fifo_rates),
                "fifo_minus_immediate_mean_pp": statistics.mean(deltas_pp),
                "difference_95ci_low_pp": low if low is not None else "",
                "difference_95ci_high_pp": high if high is not None else "",
                "additional_messages_mean": statistics.mean(deltas_messages),
                "fifo_overflow_mean": statistics.mean(fifo_overflow),
                "fifo_expired_mean": statistics.mean(fifo_expired),
                "fifo_peak_bytes_mean": statistics.mean(fifo_peak),
            }
            records.append(record)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    for r in records:
        bounds = (
            f"[{r['difference_95ci_low_pp']:.3f}, {r['difference_95ci_high_pp']:.3f}]"
            if r["n_pairs"] >= 2 else "n/a (one pilot run)"
        )
        print(f"v={r['speed_mps']:2d} m/s, stop={r['stop_s']:2d}s, "
              f"n={r['n_pairs']:2d}: mean delivery gain="
              f"{r['fifo_minus_immediate_mean_pp']:+.3f} pp; 95% CI {bounds}")
    print(f"Saved: {args.output_csv}")
    print("CI reflects only ns-3 stochasticity in the configured model, "
          "not real-world radio uncertainty.")
    if args.start_run == args.end_run:
        print("This is pilot-only output. Do NOT report a 95% CI for one run.")


if __name__ == "__main__":
    main()
