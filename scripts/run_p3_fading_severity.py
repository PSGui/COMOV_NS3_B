#!/usr/bin/env python3
"""B10 P3 fading severity experiment: isolate MAC association establishment.

At Nakagami m=1, the AP sends success association responses repeatedly, but
never recognizes the STA (association response acknowledgments likely fail).
Run m=3 and m=5, BOTH policies with dynamic ARP and pre-populated ARP,
using seed=1/run=1. These are exploratory pilots, not 95% CI estimates.

The source P2 and original P3 samples are not modified; all filenames contain
_m3 / _m5, and static-ARP runs have _staticarp_macdiag_mX suffixes.
"""
import argparse
import csv
import hashlib
import math
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "p3"


def prefix_for(m, policy, run, static_arp):
    base = f"p3_fading_v15_stop0_run{run}_{policy}_pace2_buf4000000"
    if static_arp:
        base += "_staticarp_macdiag"
    return OUT / f"{base}_m{m}"


def one_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    if len(records) != 1:
        raise ValueError(f"Expected one summary row: {path}")
    return records[0]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(*command):
    print("$ " + " ".join(map(str, command)), flush=True)
    subprocess.run([str(s) for s in command], cwd=ROOT, check=True)


def required(prefix, suffix):
    file = Path(str(prefix) + "_" + suffix)
    if not file.is_file():
        raise FileNotFoundError(f"Missing evidence {file}")
    return file


def pcap(prefix, radio):
    matches = list(prefix.parent.glob(prefix.name + "_pcap_" + radio + "*.pcap"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one {radio} PCAP: {prefix}, got {matches}")
    return matches[0]


def valid(prefix, run, m, policy, static_arp):
    try:
        s = one_csv(required(prefix, "summary.csv"))
        required(prefix, "analysis.json")
        required(prefix, "association_raw.csv")
        pcap(prefix, "ap")
        pcap(prefix, "bus")
        if static_arp:
            required(prefix, "mac_path.csv")
            required(prefix, "mac_path_summary.csv")
        return (
            s["scenario"] == "fading"
            and s["policy"] == policy
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["generated"]) == 12000
            and int(s["static_arp"]) == int(static_arp)
            and float(s["fading_m"]) == m
            and int(s["buffer_limit_bytes"]) == 4000000
            and float(s["pacing_ms"]) == 2
        )
    except (OSError, ValueError, KeyError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ns3_dir", type=Path)
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    ns3 = args.ns3_dir.resolve()
    if args.run < 1:
        parser.error("--run must be positive")
    if not (ns3 / "ns3").is_file() or not (ns3 / "scratch").is_dir():
        parser.error(f"not ns-3: {ns3}")

    evidence = []
    summary = []
    for m in (3, 5):
        for static_arp in (False, True):
            for policy in ("immediate", "fifo"):
                prefix = prefix_for(m, policy, args.run, static_arp)
                if args.skip_existing and valid(
                        prefix, args.run, m, policy, static_arp):
                    execute(sys.executable, "scripts/review_p3.py",
                            "--prefix", prefix)
                else:
                    execute("bash", "scripts/run_p3.sh", ns3,
                            "fading", policy, 15, 0, args.run, 2, 4000000,
                            int(static_arp), int(static_arp), m)
                if not valid(prefix, args.run, m, policy, static_arp):
                    raise ValueError(f"P3 fading m={m} output invalid: {prefix}")
                s = one_csv(required(prefix, "summary.csv"))
                association = float(s["associated_duration_s"])
                mac = (
                    one_csv(required(prefix, "mac_path_summary.csv"))
                    if static_arp else {}
                )
                rec = int(s["received_on_time"])
                summary.append({
                    "fading_m": m,
                    "static_arp": int(static_arp),
                    "run": args.run,
                    "policy": policy,
                    "delivered_on_time": rec,
                    "delivery_pct": 100 * rec / 12000,
                    "assoc_s": association,
                    "goodput_contact_mbps": (
                        .008 * rec / association if association else 0
                    ),
                    "socket_accepted": int(s["socket_accepted"]),
                    "accepted_not_delivered": int(
                        s["not_observed_after_socket_accept"]
                    ),
                    "assoc_events": int(s["assoc_events"]),
                    "deassoc_events": int(s["deassoc_events"]),
                    "ignored_deassoc_callbacks": int(
                        s["ignored_deassoc_callbacks"]
                    ),
                    "ap_mac_rx": (int(mac["ap_mac_rx"]) if mac else ""),
                    "ap_mac_rx_drop": (
                        int(mac["ap_mac_rx_drop"]) if mac else ""
                    ),
                    "ap_ipv4_rx": (
                        int(mac["ap_ipv4_rx"]) if mac else ""
                    ),
                    "ap_udp_received": (
                        int(mac["ap_udp_received"]) if mac else ""
                    ),
                })
                for suffix in (
                        "summary.csv", "association.csv",
                        "association_raw.csv", "received.csv",
                        "analysis.json", "mobility.csv", "sent.csv",
                        "generated.csv", "buffer.csv"):
                    evidence.append(required(prefix, suffix))
                for radio in ("ap", "bus"):
                    evidence.append(pcap(prefix, radio))
                if static_arp:
                    evidence += [
                        required(prefix, "mac_path.csv"),
                        required(prefix, "mac_path_summary.csv"),
                    ]
                print(
                    f"m={m} arp={'static' if static_arp else 'dynamic'} "
                    f"{policy}: received={rec}/12000, association={association:.3f}s, "
                    f"AP MAC RX={mac.get('ap_mac_rx', 'not recorded')}"
                )
    result_path = OUT / f"p3_fading_severity_run{args.run}.csv"
    with result_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    evidence.append(result_path)
    output = OUT / f"p3_fading_severity_run{args.run}_complete.zip"
    checksum_lines = ["SHA256  PATH"]
    for file in evidence:
        checksum_lines.append(f"{sha256(file)}  {file.relative_to(ROOT)}")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for file in evidence:
            archive.write(file, file.relative_to(ROOT))
        archive.writestr("P3_FADING_SEVERITY_SHA256_MANIFEST.txt",
                         "\n".join(checksum_lines) + "\n")
    print(f"\nUPLOAD ONLY: {output}")
    print("The 8 cases are PILOTS, not confidence intervals. Severe fading m=1"
          " remains documented separately and is not overwritten.")
    print("If MAC AP fails to confirm association, zero UDP is a link-access"
          " failure, not an isolated comparison of FIFO versus immediate.")


if __name__ == "__main__":
    main()
