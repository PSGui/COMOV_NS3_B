#!/usr/bin/env python3
"""Fail early if 802.11g has regressed to a 5 GHz-only OFDM data mode.

A cheap static guard, NOT a substitute for compiling/running ns-3.48.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p0 = (root / "src/b10-p0-propagation.cc").read_text(encoding="utf-8")
p1 = (root / "src/b10-p1-mobility-udp.cc").read_text(encoding="utf-8")
checks = [
    ("P0 11g/11a band-dependent selector",
     '(standard == "11g") ? "ErpOfdmRate6Mbps" : "OfdmRate6Mbps"' in p0),
    ("P1 IEEE 802.11g ERP data mode",
     '"DataMode", StringValue("ErpOfdmRate6Mbps")' in p1),
    ("P1 IEEE 802.11g ERP control mode",
     '"ControlMode", StringValue("ErpOfdmRate6Mbps")' in p1),
    ("P1 no legacy OFDM mode",
     '"DataMode", StringValue("OfdmRate6Mbps")' not in p1),
]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
if not all(ok for _, ok in checks):
    raise SystemExit(1)
print("Band/mode source checks pass. Runtime validation still required.")
