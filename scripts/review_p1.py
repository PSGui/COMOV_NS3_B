#!/usr/bin/env python3
"""Independent P1 CSV validation. Does not infer radio losses from missing UDP."""

import argparse
import csv
import json
import math
from pathlib import Path


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header: {path}")
        rows = list(reader)
    for row_no, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV (wrong number of columns) in {path}:{row_no}")
    return rows


def expected_x(t_s, v, stop_s):
    if t_s < 70.0:
        return v * (t_s - 70.0)
    if t_s < 70.0 + stop_s:
        return 0.0
    return v * (t_s - 70.0 - stop_s)


def check_close(actual, expected, tolerance, explanation):
    if not math.isclose(actual, expected, rel_tol=0, abs_tol=tolerance):
        raise ValueError(f"{explanation}: expected={expected}, got={actual}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--require-contact", action="store_true",
                        help="Pilot smoke test: fail if no association or no UDP reception")
    args = parser.parse_args()
    prefix = str(args.prefix)
    generated = load_csv(Path(prefix + "_generated.csv"))
    received = load_csv(Path(prefix + "_received.csv"))
    associations = load_csv(Path(prefix + "_association.csv"))
    mobility = load_csv(Path(prefix + "_mobility.csv"))
    summary_rows = load_csv(Path(prefix + "_summary.csv"))
    if len(summary_rows) != 1:
        raise ValueError("Expected exactly one P1 summary row")
    summary = summary_rows[0]
    speed = float(summary["speed_mps"])
    stop_s = float(summary["stop_s"])
    ap_x = float(summary["ap_x_m"])
    accepted = int(summary["socket_accepted"])
    dropped = int(summary["drop_no_association"])
    rejected = int(summary["socket_rejected"])

    if len(generated) != 12000:
        raise ValueError(f"Expected 12,000 generated records, got {len(generated)}")
    seen_seq = set()
    decisions = {"no_association": 0, "socket_rejected": 0, "accepted": 0}
    accepted_ids = set()
    for seq, row in enumerate(generated):
        message_id = int(row["seq"])
        if message_id != seq or message_id in seen_seq:
            raise ValueError(f"Non-sequential or duplicate message ID at seq {seq}")
        seen_seq.add(message_id)
        t = float(row["t_gen_s"])
        check_close(t, 10.0 + seq / 100, 1e-7, f"generation time for seq={seq}")
        check_close(float(row["bus_x_m"]), expected_x(t, speed, stop_s),
                    1e-5, f"generation position for seq={seq}")
        d = math.hypot(float(row["bus_x_m"]) - ap_x, 1.5)
        check_close(float(row["distance_ap_m"]), d, 1e-5,
                    f"generation 3D distance for seq={seq}")
        assoc = int(row["associated_at_generation"])
        attempted = int(row["attempted_socket_send"])
        reason = row["drop_reason"]
        if assoc not in (0, 1) or attempted not in (0, 1):
            raise ValueError(f"Invalid association/send flags: seq {seq}")
        if not assoc:
            if attempted or reason != "no_association" or row["send_return"]:
                raise ValueError(f"Bad no-association drop status: seq={seq}")
            decisions["no_association"] += 1
        elif reason == "socket_rejected":
            if not attempted or not row["send_return"]:
                raise ValueError(f"Socket-rejected row missing attempt/result: seq={seq}")
            decisions["socket_rejected"] += 1
        else:
            if reason or not attempted or row["send_return"] != "1000":
                raise ValueError(f"Invalid socket-accepted row: seq={seq}")
            decisions["accepted"] += 1
            accepted_ids.add(seq)

    if decisions["no_association"] != dropped or decisions["accepted"] != accepted:
        raise ValueError(f"Summary disagrees with generated dispositions: {decisions}")
    if decisions["socket_rejected"] != rejected:
        raise ValueError("Summary socket_rejected mismatch")

    delivered = set()
    dupes = 0
    on_time = 0
    late = 0
    previous_time = -1.0
    for row in received:
        seq = int(row["seq"])
        if seq not in seen_seq or seq not in accepted_ids:
            raise ValueError(f"Received unknown or non-accepted seq={seq}")
        t_gen = float(row["t_gen_s"])
        t_rx = float(row["t_rx_s"])
        d = float(row["delay_s"])
        check_close(t_gen, 10.0 + seq / 100, 1e-7, f"received gen time seq={seq}")
        check_close(t_rx - t_gen, d, 1e-6, f"delay seq={seq}")
        if t_rx < t_gen or t_rx > 200.000001 or t_rx < previous_time:
            raise ValueError(f"Invalid or unsorted reception time seq={seq}")
        previous_time = t_rx
        duplicate = seq in delivered
        if int(row["duplicate"]) != int(duplicate):
            raise ValueError(f"Duplicate flag mismatch seq={seq}")
        if duplicate:
            dupes += 1
            continue
        delivered.add(seq)
        if d <= 60:
            on_time += 1
        else:
            late += 1
        if int(row["on_time"]) != int(d <= 60):
            raise ValueError(f"Deadline flag mismatch seq={seq}")

    checks = {
        "generated": len(generated),
        "drop_no_association": decisions["no_association"],
        "socket_rejected": decisions["socket_rejected"],
        "socket_accepted": decisions["accepted"],
        "unique_received": len(delivered),
        "received_on_time": on_time,
        "received_late": late,
        "duplicate_rx": dupes,
        "not_observed_after_socket_accept": len(accepted_ids - delivered),
    }
    for key, observed in checks.items():
        if int(summary[key]) != observed:
            raise ValueError(f"Summary {key} mismatch: {summary[key]} != {observed}")

    if len(mobility) != 801:
        raise ValueError(f"Expected 801 mobility samples, got {len(mobility)}")
    for i, row in enumerate(mobility):
        t = float(row["t_s"])
        check_close(t, i / 4.0, 1e-7, f"mobility sample time {i}")
        x = expected_x(t, speed, stop_s)
        check_close(float(row["bus_x_m"]), x, 1e-5, f"mobility position t={t}")
        check_close(float(row["distance_ap_m"]), math.hypot(x - ap_x, 1.5),
                    1e-5, f"3D distance t={t}")
        if int(row["associated"]) not in (0, 1):
            raise ValueError(f"Invalid association flag in mobility sample t={t}")

    event_state = False
    last_event = -1.0
    for row in associations:
        t = float(row["t_s"])
        if t < last_event or t < 0 or t > 200:
            raise ValueError("Association events not chronological")
        last_event = t
        check_close(float(row["bus_x_m"]), expected_x(t, speed, stop_s),
                    1e-5, f"event position at {t}")
        if row["event"] == "assoc":
            if event_state:
                raise ValueError("Repeated assoc without deassoc")
            event_state = True
        elif row["event"] == "deassoc":
            if not event_state:
                raise ValueError("DeAssoc without preceding Assoc")
            event_state = False
        else:
            raise ValueError(f"Unknown association event: {row['event']}")

    assoc_count = sum(row["event"] == "assoc" for row in associations)
    deassoc_count = sum(row["event"] == "deassoc" for row in associations)
    if assoc_count != int(summary["assoc_events"]) or deassoc_count != int(summary["deassoc_events"]):
        raise ValueError("Association counters in summary do not match events")

    pct = 100 * on_time / len(generated)
    report = {
        "status": "validated_csv_accounting",
        "scenario": {"speed_mps": speed, "stop_s": stop_s, "ap_x_m": ap_x},
        "counters": checks,
        "on_time_delivery_generated_denominator_pct": round(pct, 6),
        "associated_seconds": float(summary["associated_duration_s"]),
        "association_events": assoc_count,
        "deassociation_events": deassoc_count,
        "measurement_window_s": [10, 130],
        "observation_end_s": 200,
        "warning": "socket acceptance is not PHY delivery; messages not observed "
                   "after accepted send are NOT necessarily radio losses",
    }
    output = Path(prefix + "_analysis.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"P1 validated: 12000 generated; {len(delivered)} unique received;"
          f" {on_time} <=60s; on-time delivery {pct:.3f}% of generated")
    print(f"Drop while unassociated={dropped}; socket rejected={rejected};"
          f" accepted-but-not-observed={len(accepted_ids-delivered)}")
    print(f"Association events={assoc_count}, deassociation events={deassoc_count}")
    print(f"Analysis: {output}")
    if args.require_contact and (assoc_count == 0 or not delivered):
        raise SystemExit("P1 pilot failed contact smoke test: no association or no delivered UDP")
    print("PASS: P1 CSV accounting and trajectory. PHY/network causes still unproven.")


if __name__ == "__main__":
    main()
