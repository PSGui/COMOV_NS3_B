#!/usr/bin/env python3
"""Validate P2 message accounting, FIFO order, expiry and trajectory.

Only uses CSV outputs: the validator cannot determine the physical cause of
datagrams accepted by the socket but not observed at the AP.
"""
import argparse
import csv
import json
import math
from collections import deque
from pathlib import Path

N_GENERATED = 12000
PAYLOAD_BYTES = 1000
DEADLINE_S = 60.0


def rows_from(prefix, suffix):
    path = Path(str(prefix) + "_" + suffix + ".csv")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Missing header: {path}")
        rows = list(reader)
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV: {path}:{line}")
    return rows


def near(x, y, tol=1e-6):
    return math.isclose(x, y, rel_tol=0, abs_tol=tol)


def bus_x(t, speed, stop):
    if t < 70:
        return speed * (t - 70)
    if t < 70 + stop:
        return 0.0
    return speed * (t - 70 - stop)


def validate(prefix, require_contact):
    summary_rows = rows_from(prefix, "summary")
    if len(summary_rows) != 1:
        raise ValueError("Exactly one summary row expected")
    s = summary_rows[0]
    policy = s["policy"]
    if policy not in ("immediate", "fifo"):
        raise ValueError("Unexpected policy in summary")
    speed = float(s["speed_mps"])
    stop = float(s["stop_s"])
    ap_x = float(s["ap_x_m"])
    limit = int(s["buffer_limit_bytes"])
    pacing = float(s["pacing_ms"])
    generated = rows_from(prefix, "generated")
    received = rows_from(prefix, "received")
    assoc = rows_from(prefix, "association")
    movement = rows_from(prefix, "mobility")
    attempts = rows_from(prefix, "sent")
    events = rows_from(prefix, "buffer")

    if len(generated) != N_GENERATED:
        raise ValueError(f"Expected {N_GENERATED} generated messages")
    generated_by_seq = {}
    accepted_enqueue = set()
    overflow_ids = set()
    dropped_no_assoc = set()
    immediate_attempted = set()
    for seq, record in enumerate(generated):
        mid = int(record["seq"])
        if mid != seq:
            raise ValueError(f"Bad or out-of-order generated ID: {mid}, expected {seq}")
        gen_time = float(record["t_gen_s"])
        expected_time = 10.0 + seq / 100.0
        if not near(gen_time, expected_time, 1e-7):
            raise ValueError(f"Generation time wrong: {seq}")
        x = bus_x(gen_time, speed, stop)
        if not near(float(record["bus_x_m"]), x, 1e-5) or not near(
            float(record["distance_ap_m"]), math.hypot(x - ap_x, 1.5), 1e-5
        ):
            raise ValueError(f"Generation location wrong: {seq}")
        associated = int(record["associated_at_generation"])
        attempted = int(record["attempted_socket_send"])
        if associated not in (0, 1) or attempted not in (0, 1):
            raise ValueError(f"Bad association/attempt indicator: {seq}")
        reason = record["drop_reason"]
        if policy == "fifo":
            if attempted or record["send_return"]:
                raise ValueError(f"FIFO sent at generation, expected enqueue: {seq}")
            if reason == "enqueued":
                accepted_enqueue.add(mid)
            elif reason == "buffer_full":
                overflow_ids.add(mid)
            else:
                raise ValueError(f"Unknown FIFO disposition for {seq}: {reason}")
        else:
            if not associated:
                if attempted or reason != "no_association" or record["send_return"]:
                    raise ValueError(f"Invalid unassociated disposition: {seq}")
                dropped_no_assoc.add(mid)
            else:
                if not attempted or reason not in ("", "socket_rejected"):
                    raise ValueError(f"Invalid immediate socket disposition: {seq}")
                immediate_attempted.add(mid)
        generated_by_seq[mid] = gen_time

    # Association traces: verify real ordered MAC state transitions.
    associated = False
    association_count = 0
    deassociation_count = 0
    associated_seconds = 0.0
    last_assoc_s = 0.0
    event_time = -1.0
    for record in assoc:
        t = float(record["t_s"])
        if t < event_time or t < 0 or t > 200:
            raise ValueError("Association events not ordered")
        event_time = t
        if not near(float(record["bus_x_m"]), bus_x(t, speed, stop), 1e-5):
            raise ValueError("Association event position incorrect")
        if not near(float(record["distance_ap_m"]),
                    math.hypot(float(record["bus_x_m"]) - ap_x, 1.5), 1e-5):
            raise ValueError("Association event distance incorrect")
        if record["event"] == "assoc" and not associated:
            associated = True
            last_assoc_s = t
            association_count += 1
        elif record["event"] == "deassoc" and associated:
            associated = False
            associated_seconds += t - last_assoc_s
            deassociation_count += 1
        else:
            raise ValueError("Invalid repeated/out-of-order association event")
    if associated:
        associated_seconds += 200.0 - last_assoc_s
    if not near(associated_seconds, float(s["associated_duration_s"]), 1e-4):
        raise ValueError("Associated duration disagrees with trace")
    if association_count != int(s["assoc_events"]) or deassociation_count != int(
        s["deassoc_events"]
    ):
        raise ValueError("Association event counts disagree with summary")

    if len(movement) != 801:
        raise ValueError("Expected 801 mobility samples")
    for i, record in enumerate(movement):
        t = i * .25
        if not near(float(record["t_s"]), t, 1e-7):
            raise ValueError("Incorrect mobility sampling")
        x = bus_x(t, speed, stop)
        if not near(float(record["bus_x_m"]), x, 1e-5) or not near(
            float(record["distance_ap_m"]), math.hypot(x - ap_x, 1.5), 1e-5
        ):
            raise ValueError(f"Incorrect bus position at {t}")
        if int(record["associated"]) not in (0, 1):
            raise ValueError("Invalid association state in mobility data")

    # Trace of actual calls to UDP socket, distinct from generation.
    accepted_socket = set()
    rejected_socket = set()
    attempt_time_by_seq = {}
    previous_attempt = -1.0
    for row in attempts:
        mid = int(row["seq"])
        if mid not in generated_by_seq or mid in attempt_time_by_seq:
            raise ValueError(f"Invalid/duplicated socket attempt ID {mid}")
        t_gen = float(row["t_gen_s"])
        t_send = float(row["t_socket_s"])
        age = float(row["age_at_send_s"])
        returned = int(row["send_return"])
        if t_send + 1e-7 < t_gen or t_send + 1e-7 < previous_attempt:
            raise ValueError("Socket attempts not time ordered")
        if not near(t_gen, generated_by_seq[mid], 1e-6) or not near(
            t_send - t_gen, age, 1e-6
        ):
            raise ValueError(f"Socket attempt timestamp inconsistent: {mid}")
        previous_attempt = t_send
        if policy != row["policy"]:
            raise ValueError("Policy mismatch in sent CSV")
        if policy == "immediate" and not near(t_send, t_gen, 1e-6):
            raise ValueError(f"Immediate policy buffered message ID {mid}")
        if policy == "fifo" and age >= DEADLINE_S + 1e-6:
            raise ValueError(f"FIFO submitted an expired datagram {mid}")
        if returned == PAYLOAD_BYTES:
            accepted_socket.add(mid)
        else:
            rejected_socket.add(mid)
        attempt_time_by_seq[mid] = t_send

    if policy == "immediate":
        if len(events) or len(accepted_enqueue) or len(overflow_ids):
            raise ValueError("Unexpected FIFO logs under immediate policy")
        if set(attempt_time_by_seq) != immediate_attempted:
            raise ValueError("Immediate generation/send mismatch")
        for rec in generated:
            if int(rec["attempted_socket_send"]):
                mid = int(rec["seq"])
                if int(rec["send_return"]) != (PAYLOAD_BYTES if mid in accepted_socket
                                               else int(rec["send_return"])):
                    raise ValueError("Immediate send result mismatch")
                if mid in accepted_socket and rec["drop_reason"]:
                    raise ValueError("Accepted socket send marked dropped")
                if mid in rejected_socket and rec["drop_reason"] != "socket_rejected":
                    raise ValueError("Rejected socket send not marked")
        max_queue_bytes = 0
        expired_ids = set()
        buffered_attempted = set()
    else:
        # Replay FIFO events in original CSV order, including same-timestamp
        # events. Verify that every send removes the oldest queued message.
        fifo = deque()
        enqueue_seen = set()
        overflow_seen = set()
        expired_ids = set()
        buffered_attempted = set()
        max_queue_bytes = 0
        previous_event = -1.0
        last_socket_event = -1.0
        for row in events:
            t = float(row["t_s"])
            mid = int(row["seq"])
            action = row["event"]
            age = float(row["age_s"])
            if t + 1e-7 < previous_event:
                raise ValueError("FIFO events not chronological")
            previous_event = t
            if action == "enqueued":
                if mid not in accepted_enqueue or mid in enqueue_seen:
                    raise ValueError(f"Unknown/duplicate buffer enqueue {mid}")
                if len(fifo) * PAYLOAD_BYTES + PAYLOAD_BYTES > limit:
                    raise ValueError("Buffer enqueue exceeded configured limit")
                fifo.append(mid)
                enqueue_seen.add(mid)
                if not near(t, generated_by_seq[mid], 1e-6):
                    raise ValueError(f"Enqueue time differs from generation: {mid}")
            elif action == "drop_newest":
                if mid not in overflow_ids or mid in overflow_seen:
                    raise ValueError(f"Unknown/duplicate overflow {mid}")
                if len(fifo) * PAYLOAD_BYTES + PAYLOAD_BYTES <= limit:
                    raise ValueError(f"Overflow without full FIFO at {mid}")
                overflow_seen.add(mid)
            elif action in ("expired", "send_accepted", "send_rejected"):
                if not fifo or fifo[0] != mid:
                    raise ValueError(f"FIFO ordering violation at {mid} ({action})")
                fifo.popleft()
                if action == "expired":
                    if age < DEADLINE_S - 1e-6 or mid in attempt_time_by_seq:
                        raise ValueError(f"Incorrect expiration {mid}")
                    expired_ids.add(mid)
                else:
                    if int(row["associated"]) != 1 or mid not in attempt_time_by_seq:
                        raise ValueError(f"Buffered send not associated: {mid}")
                    if not near(t, attempt_time_by_seq[mid], 1e-6):
                        raise ValueError(f"Sent time differs from FIFO log: {mid}")
                    if (action == "send_accepted") != (mid in accepted_socket):
                        raise ValueError(f"Socket result differs from FIFO event: {mid}")
                    if not row["send_return"]:
                        raise ValueError(f"Missing socket return code: {mid}")
                    buffered_attempted.add(mid)
                    if last_socket_event >= 0 and t > last_socket_event:
                        # Gaps can be longer when the FIFO empties.
                        if t - last_socket_event + 1e-7 < pacing / 1000.0:
                            raise ValueError("FIFO sends faster than configured pacing")
                    last_socket_event = t
            else:
                raise ValueError(f"Unexpected FIFO event: {action}")
            if len(fifo) != int(row["queued_messages"]) or (
                len(fifo) * PAYLOAD_BYTES != int(row["queued_bytes"])
            ):
                raise ValueError(f"Recorded FIFO occupancy mismatch at {t}: {action}")
            max_queue_bytes = max(max_queue_bytes, len(fifo) * PAYLOAD_BYTES)
        if enqueue_seen != accepted_enqueue or overflow_seen != overflow_ids:
            raise ValueError("Missing FIFO enqueue or overflow events")
        if buffered_attempted != set(attempt_time_by_seq):
            raise ValueError("FIFO sent.csv disagrees with buffer events")
        if int(s["buffer_remaining"]) != len(fifo):
            raise ValueError("Summary pending messages differ from FIFO replay")

    # Receiver records cannot be substituted with socket acceptance.
    delivered = set()
    received_late = 0
    received_on_time = 0
    duplicate_count = 0
    last_reception = -1.0
    for row in received:
        mid = int(row["seq"])
        if mid not in accepted_socket:
            raise ValueError(f"Received packet not accepted by sender socket: {mid}")
        tg = float(row["t_gen_s"])
        tr = float(row["t_rx_s"])
        delay = float(row["delay_s"])
        if tr < tg or tr < last_reception or tr > 200.00001:
            raise ValueError("Nonchronological or negative receiver timestamps")
        last_reception = tr
        if not near(tg, generated_by_seq[mid], 1e-6) or not near(
            tr - tg, delay, 1e-6
        ):
            raise ValueError(f"Incorrect received delay: {mid}")
        duplicate = mid in delivered
        if int(row["duplicate"]) != int(duplicate):
            raise ValueError("Incorrect duplicate flag")
        if int(row["on_time"]) != int(delay <= DEADLINE_S):
            raise ValueError("Incorrect deadline flag")
        if duplicate:
            duplicate_count += 1
        else:
            delivered.add(mid)
            if delay <= DEADLINE_S:
                received_on_time += 1
            else:
                received_late += 1

    checks = {
        "generated": len(generated),
        "drop_no_association": len(dropped_no_assoc),
        "socket_rejected": len(rejected_socket),
        "socket_accepted": len(accepted_socket),
        "received_unique": len(delivered),
        "received_on_time": received_on_time,
        "received_late": received_late,
        "duplicate_rx": duplicate_count,
        "not_observed_after_socket_accept": len(accepted_socket - delivered),
        "buffer_enqueued": len(accepted_enqueue),
        "buffer_overflow": len(overflow_ids),
        "buffer_expired": len(expired_ids),
        "buffer_sent_attempts": len(buffered_attempted),
        "buffer_peak_bytes": max_queue_bytes,
    }
    for key, observed in checks.items():
        if int(s[key]) != observed:
            raise ValueError(f"Summary {key}={s[key]} but audit found {observed}")
    if int(s["buffer_remaining"]) != (0 if policy == "immediate" else len(fifo)):
        raise ValueError("Buffer remaining summary mismatch")
    if int(s["buffer_limit_bytes"]) != limit or limit % PAYLOAD_BYTES:
        raise ValueError("Unexpected buffer configuration")
    if len(accepted_socket) != len(delivered) + len(accepted_socket - delivered):
        raise ValueError("Socket acceptance reconciliation failed")
    if policy == "fifo":
        if len(generated) != len(accepted_enqueue) + len(overflow_ids):
            raise ValueError("FIFO generation disposition mismatch")
        if len(accepted_enqueue) != (len(expired_ids) + len(buffered_attempted)
                                     + len(fifo)):
            raise ValueError("FIFO conservation mismatch")
        if len(attempt_time_by_seq) != len(accepted_socket) + len(rejected_socket):
            raise ValueError("FIFO socket submission mismatch")
        if int(s["drop_no_association"]) != 0:
            raise ValueError("FIFO must not discard solely for no association")
    else:
        if len(generated) != len(dropped_no_assoc) + len(attempt_time_by_seq):
            raise ValueError("Immediate disposition mismatch")

    if require_contact and (association_count == 0 or not delivered):
        raise ValueError("Pilot require-contact: no association or no AP delivery")

    received_times = [float(v["t_rx_s"]) for v in received
                      if int(v["duplicate"]) == 0]
    missing_ids = sorted(accepted_socket - delivered)
    result = {
        "status": "validated_csv_accounting",
        "policy": policy,
        "speed_mps": speed,
        "stop_s": stop,
        "ap_x_m": ap_x,
        "seed": int(s["seed"]),
        "run": int(s["run"]),
        "pacing_ms": pacing,
        "buffer_limit_bytes": limit,
        "counters": checks,
        "delivered_on_time_pct_all_generated": 100 * received_on_time / len(generated),
        "delivered_pct_socket_accepted": (
            100 * len(delivered) / len(accepted_socket) if accepted_socket else 0
        ),
        "associated_seconds": associated_seconds,
        "association_events": association_count,
        "deassociation_events": deassociation_count,
        "first_rx_s": min(received_times) if received_times else None,
        "last_rx_s": max(received_times) if received_times else None,
        "not_observed_ids_range": ([missing_ids[0], missing_ids[-1]]
                                   if missing_ids else []),
        "warning": "No inference of PHY loss from socket-accepted but unreceived IDs",
    }
    output = Path(str(prefix) + "_analysis.json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(
        f"PASS P2 {policy}: generated={len(generated)}, accepted={len(accepted_socket)}, "
        f"AP unique received={len(delivered)}, <=60s={received_on_time} "
        f"({result['delivered_on_time_pct_all_generated']:.3f}% of generated)"
    )
    print(
        f"Buffer: enqueued={len(accepted_enqueue)} overflow={len(overflow_ids)} "
        f"expired={len(expired_ids)} peak={max_queue_bytes} B; "
        f"accepted-not-observed={len(missing_ids)}"
    )
    print(f"Analysis JSON: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--require-contact", action="store_true")
    args = parser.parse_args()
    validate(args.prefix, args.require_contact)
