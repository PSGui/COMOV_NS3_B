#!/usr/bin/env python3
"""Compare matched P2 immediate vs FIFO pilot summaries.

The two simulation runs MUST use the same physical configuration, RNG seed/run,
speed, stop duration, application traffic and observation interval.
"""
import argparse
import csv
import math
import json
from pathlib import Path


def read_summary(prefix):
    filename = Path(str(prefix) + "_summary.csv")
    with filename.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one summary row in {filename}")
    return rows[0]



def read_log(prefix, kind):
    path = Path(str(prefix) + "_" + kind + ".csv")
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        data = list(reader)
    for line, item in enumerate(data, 2):
        if None in item or any(value is None for value in item.values()):
            raise ValueError(f"Malformed CSV at {path}:{line}")
    return data


def contiguous_ranges(numbers):
    """Return inclusive [first,last,count] intervals, not just min/max."""
    result = []
    for item in sorted(set(numbers)):
        if result and item == result[-1][1] + 1:
            result[-1][1] = item
            result[-1][2] += 1
        else:
            result.append([item, item, 1])
    return result


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (pos - lo) * (ordered[hi] - ordered[lo])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--immediate-prefix", type=Path, required=True)
    parser.add_argument("--fifo-prefix", type=Path, required=True)
    parser.add_argument("--output-json", type=Path,
                        help="Optional structured paired analysis path")
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
            key != "wifi_standard" and math.isclose(
                float(imm[key]), float(fifo[key]), rel_tol=0, abs_tol=1e-9
            )
        ):
            raise ValueError(f"Unmatched experiment at {key}: {imm[key]} vs {fifo[key]}")

    generated_i = read_log(args.immediate_prefix, "generated")
    generated_f = read_log(args.fifo_prefix, "generated")
    assoc_i = read_log(args.immediate_prefix, "association")
    assoc_f = read_log(args.fifo_prefix, "association")
    mobility_i = read_log(args.immediate_prefix, "mobility")
    mobility_f = read_log(args.fifo_prefix, "mobility")
    if assoc_i != assoc_f:
        raise ValueError("Association traces differ between paired policies")
    if len(mobility_i) != len(mobility_f):
        raise ValueError("Mobility sample count differs between paired policies")
    for index, (i, f) in enumerate(zip(mobility_i, mobility_f)):
        for field in ("t_s", "bus_x_m", "bus_velocity_mps",
                      "distance_ap_m", "pr_model_dbm"):
            # Floating output differs by 1e-9 in a few records because the
            # two policies schedule different events at the same simulator
            # time. This is NOT a different trajectory or link budget.
            if not math.isclose(float(i[field]), float(f[field]),
                                rel_tol=0, abs_tol=1e-6):
                raise ValueError(f"Unmatched mobility {field} at row {index}")
        if i["associated"] != f["associated"]:
            raise ValueError(f"Unmatched association sample at row {index}")

    if len(generated_i) != len(generated_f):
        raise ValueError("Different number of generated records between policies")
    for i, f in zip(generated_i, generated_f):
        if i["seq"] != f["seq"]:
            raise ValueError("Different generation sequence IDs")
        for field in ("t_gen_s", "bus_x_m", "distance_ap_m"):
            if not math.isclose(float(i[field]), float(f[field]),
                                rel_tol=0, abs_tol=1e-6):
                raise ValueError(f"Unmatched generation {field}, seq={i['seq']}")

    count = int(imm["generated"])
    if len(generated_i) != count or count != 12000:
        raise ValueError("Unexpected number of generated records")

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
    print("Association and sampled mobility traces: IDENTICAL across policies.")

    received_i = read_log(args.immediate_prefix, "received")
    received_f = read_log(args.fifo_prefix, "received")
    sent_i = read_log(args.immediate_prefix, "sent")
    sent_f = read_log(args.fifo_prefix, "sent")
    buffer_f = read_log(args.fifo_prefix, "buffer")

    first_assoc = next(
        (float(e["t_s"]) for e in assoc_i if e["event"] == "assoc"), None
    )
    if first_assoc is None:
        raise ValueError("Pair diagnostics need a first association event")

    results = {}
    for name, sent, received in [
        ("immediate", sent_i, received_i), ("fifo", sent_f, received_f)
    ]:
        sent_ids = {
            int(row["seq"]) for row in sent
            if int(row["send_return"]) == 1000
        }
        received_ids = {int(row["seq"]) for row in received}
        if not received_ids <= sent_ids:
            raise ValueError(f"Received IDs absent from socket-accepted sends: {name}")
        miss = contiguous_ranges(sent_ids - received_ids)
        latencies = [float(row["delay_s"]) for row in received
                     if row["duplicate"] == "0"]
        recovery = sum(float(row["t_gen_s"]) < first_assoc
                       for row in received if row["duplicate"] == "0")
        results[name] = {
            "socket_accepted": len(sent_ids),
            "unique_received": len(received_ids),
            "missing_socket_accepted_ranges": miss,
            "received_generated_before_first_assoc": recovery,
            "mean_delivery_delay_s": (sum(latencies) / len(latencies)
                                      if latencies else None),
            "median_delivery_delay_s": percentile(latencies, .5),
            "p95_delivery_delay_s": percentile(latencies, .95),
            "max_delivery_delay_s": max(latencies) if latencies else None,
            "first_rx_s": (min(float(row["t_rx_s"]) for row in received)
                           if received else None),
            "last_rx_s": (max(float(row["t_rx_s"]) for row in received)
                          if received else None),
        }
        print(f"\n{name}: received {len(received_ids)}, recovered before"
              f" association={recovery}; missing accepted IDs={miss}")
        print(f"  mean delay={results[name]['mean_delivery_delay_s']:.6f} s,"
              f" p95 delay={results[name]['p95_delivery_delay_s']:.6f} s")

    if not buffer_f:
        raise ValueError("Missing FIFO event log")
    limit_bytes = int(fifo["buffer_limit_bytes"])
    if not (0 <= int(fifo["buffer_peak_bytes"]) <= limit_bytes):
        raise ValueError("Invalid peak buffer occupancy")
    occupancy_peak = max(buffer_f, key=lambda e: int(e["queued_bytes"]))
    empty_after_contact = next(
        (float(e["t_s"]) for e in buffer_f
         if float(e["t_s"]) >= first_assoc and
         int(e["queued_messages"]) == 0 and
         e["event"] in ("send_accepted", "send_rejected")), None
    )
    results["fifo"]["peak_buffer_bytes"] = int(fifo["buffer_peak_bytes"])
    results["fifo"]["peak_buffer_time_s"] = float(occupancy_peak["t_s"])
    results["fifo"]["capacity_fraction"] = (
        int(fifo["buffer_peak_bytes"]) / limit_bytes
    )
    results["fifo"]["first_empty_during_contact_s"] = empty_after_contact
    results["fifo"]["first_empty_elapsed_after_assoc_s"] = (
        empty_after_contact - first_assoc if empty_after_contact is not None else None
    )
    print(f"\nFIFO peak={int(fifo['buffer_peak_bytes'])} B at "
          f"{occupancy_peak['t_s']} s "
          f"({100*results['fifo']['capacity_fraction']:.2f}% capacity)")
    if empty_after_contact is not None:
        print(f"FIFO first emptied while associated at t={empty_after_contact:.6f} s"
              f" ({empty_after_contact-first_assoc:.6f} s after first association)")
    print("These statements describe this paired run, not statistical confidence.")

    report = {
        "matched_pair": True,
        "scenario": {key: imm[key] for key in matching},
        "first_association_s": first_assoc,
        "delivery_rate_immediate_pct": imm_pct,
        "delivery_rate_fifo_pct": fifo_pct,
        "delivery_gain_percentage_points": fifo_pct - imm_pct,
        "additional_on_time_messages": (
            int(fifo["received_on_time"]) - int(imm["received_on_time"])
        ),
        "policies": results,
        "limitations": [
            "One paired run, not an independent-run confidence interval",
            "Socket acceptance is not PHY delivery",
            "Missing socket-accepted packets require MAC/PHY trace for causes",
        ],
    }
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Structured paired analysis: {args.output_json}")


if __name__ == "__main__":
    main()
