#!/usr/bin/env python3
"""P3-specific validation: full P2 accounting plus raw association callbacks.

Transient fading can cause DeAssoc callbacks with no currently open association
interval. Preserve and check these callbacks rather than silently deleting them.
A zero-UDP result is flagged as anomalous, NOT called a valid scientific gain.
"""
import argparse
import json
from pathlib import Path

from review_p2 import rows_from, validate as validate_p2


def validate(prefix):
    validate_p2(prefix, require_contact=False)
    summary = rows_from(prefix, "summary")[0]
    raw = rows_from(prefix, "association_raw")
    transitions = rows_from(prefix, "association")
    active = False
    accepted = []
    ignored_assoc = 0
    ignored_deassoc = 0
    previous_t = -1.0
    for cb in raw:
        t = float(cb["t_s"])
        if t < previous_t or not (0 <= t <= 200):
            raise ValueError(f"Raw P3 association callback out of order at {t}")
        previous_t = t
        if int(cb["already_open"]) != int(active):
            raise ValueError(f"Incorrect recorded open state in raw callbacks at {t}")
        if int(cb["sta_is_associated"]) not in (0, 1):
            raise ValueError("Invalid STA IsAssociated indicator")
        if cb["callback"] == "assoc_cb":
            if active:
                ignored_assoc += 1
            else:
                active = True
                accepted.append(("assoc", t))
        elif cb["callback"] == "deassoc_cb":
            if active:
                active = False
                accepted.append(("deassoc", t))
            else:
                ignored_deassoc += 1
        else:
            raise ValueError(f"Unexpected raw callback: {cb['callback']}")

    if len(accepted) != len(transitions):
        raise ValueError("Raw callbacks do not match legitimate association transitions")
    for (event, t), row in zip(accepted, transitions):
        if row["event"] != event or abs(float(row["t_s"]) - t) > 1e-6:
            raise ValueError("Association transitions fail raw callback reconciliation")
    if len([v for v in accepted if v[0] == "assoc"]) != int(summary["assoc_events"]):
        raise ValueError("Summary association events inconsistent with callbacks")
    if len([v for v in accepted if v[0] == "deassoc"]) != int(summary["deassoc_events"]):
        raise ValueError("Summary deassociation events inconsistent with callbacks")
    if ignored_assoc != int(summary["ignored_assoc_callbacks"]) or (
        ignored_deassoc != int(summary["ignored_deassoc_callbacks"])
    ):
        raise ValueError("Ignored callback counts inconsistent with summary")

    warnings = []
    if int(summary["assoc_events"]) and not int(summary["received_unique"]):
        warnings.append(
            "CRITICAL: STA associated but AP received zero bus UDP datagrams; "
            "PHY/MAC/ARP cause UNDETERMINED. Examine AP/bus PCAP."
        )
    if ignored_deassoc or ignored_assoc:
        warnings.append(
            f"Extra callbacks: {ignored_assoc} assoc, {ignored_deassoc} deassoc; "
            "full evidence in association_raw.csv."
        )
    output = Path(str(prefix) + "_analysis.json")
    data = json.loads(output.read_text(encoding="utf-8"))
    data["p3_diagnostics"] = {
        "scenario": summary["scenario"],
        "raw_assoc_callbacks": len(raw),
        "ignored_assoc_callbacks": ignored_assoc,
        "ignored_deassoc_callbacks": ignored_deassoc,
        "scientific_quality_flags": warnings,
        "scientifically_interpretable": not bool(warnings),
    }
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"P3 callback audit PASS: {len(accepted)} transitions, "
          f"{ignored_deassoc} additional DeAssoc callbacks.")
    for warning in warnings:
        print("P3 DIAGNOSTIC:", warning)
    print("P3 scientific quality clear." if not warnings
          else "P3 data preserved for diagnosis; do NOT draw conclusions yet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    validate(args.prefix)
