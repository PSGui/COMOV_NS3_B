#!/usr/bin/env python3
"""P3 investigation: where do fading+static-ARP UDP frames stop?

Run two additional *passively instrumented* fading simulations (immediate/FIFO),
without overwriting previously uploaded P3 or P2 results.
The AP MAC, IPv4 and application paths are counted independently and sampled
every 250ms together with AP's own association state for the moving STA.
Package everything into one evidence ZIP with SHA256 manifest.
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


def prefix(policy, run, diag=False):
    return OUT / (
        f"p3_fading_v15_stop0_run{run}_{policy}_pace2_buf4000000_staticarp"
        + ("_macdiag" if diag else "")
    )


def read_one(path):
    with path.open(encoding="utf-8", newline="") as stream:
        values = list(csv.DictReader(stream))
    if len(values) != 1:
        raise ValueError(f"Expected one summary row: {path}")
    return values[0]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def required(prefix_path, suffix):
    file = Path(str(prefix_path) + "_" + suffix)
    if not file.is_file():
        raise FileNotFoundError(f"Missing evidence: {file}")
    return file


def pcap(prefix_path, radio):
    matches = list(prefix_path.parent.glob(
        prefix_path.name + "_pcap_" + radio + "*.pcap"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected AP/bus PCAP for {prefix_path}: {matches}")
    return matches[0]


def valid_diag(prefix_path, run, policy):
    try:
        s = read_one(required(prefix_path, "summary.csv"))
        m = read_one(required(prefix_path, "mac_path_summary.csv"))
        required(prefix_path, "mac_path.csv")
        required(prefix_path, "analysis.json")
        required(prefix_path, "association_raw.csv")
        pcap(prefix_path, "ap")
        pcap(prefix_path, "bus")
        return (
            s["scenario"] == "fading" and s["policy"] == policy
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["static_arp"]) == 1
            and int(s["generated"]) == 12000
            and int(m["run"]) == run and m["policy"] == policy
        )
    except (OSError, KeyError, ValueError):
        return False


def execute(*command):
    print("$ " + " ".join(map(str, command)), flush=True)
    subprocess.run([str(s) for s in command], cwd=ROOT, check=True)


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
        parser.error(f"not an ns-3 source tree: {ns3}")

    evidence = []
    summary = []
    for policy in ("immediate", "fifo"):
        original = prefix(policy, args.run)
        measured = prefix(policy, args.run, diag=True)
        existing = read_one(required(original, "summary.csv"))
        if args.skip_existing and valid_diag(measured, args.run, policy):
            execute(sys.executable, "scripts/review_p3.py",
                    "--prefix", measured)
        else:
            execute("bash", "scripts/run_p3.sh", ns3, "fading", policy,
                    15, 0, args.run, 2, 4000000, 1, 1)
        if not valid_diag(measured, args.run, policy):
            raise ValueError(f"MAC-path diagnostic output incomplete: {measured}")
        new_summary = read_one(required(measured, "summary.csv"))
        mac = read_one(required(measured, "mac_path_summary.csv"))
        with required(measured, "mac_path.csv").open(
                encoding="utf-8", newline="") as stream:
            points = list(csv.DictReader(stream))
        if len(points) != 801:
            raise ValueError(f"Expected 801 MAC-path trajectory samples: {measured}")
        sta_assoc_points = sum(int(r["sta_associated"]) for r in points)
        ap_assoc_points = sum(int(r["ap_recognizes_bus"]) for r in points)
        both_assoc_points = sum(int(r["sta_associated"]) and
                                int(r["ap_recognizes_bus"]) for r in points)

        changes = {}
        for field in ("received_on_time", "socket_accepted",
                      "assoc_events", "deassoc_events",
                      "associated_duration_s", "buffer_overflow",
                      "buffer_expired"):
            a = float(existing[field])
            b = float(new_summary[field])
            changes[field] = (
                math.isclose(a, b, rel_tol=0, abs_tol=1e-6) if
                field == "associated_duration_s" else a == b
            )
        row = {
            "run": args.run,
            "policy": policy,
            "static_arp_reference_received": int(existing["received_on_time"]),
            "diagnostic_received": int(new_summary["received_on_time"]),
            "static_arp_reference_assoc_s": float(existing["associated_duration_s"]),
            "diagnostic_assoc_s": float(new_summary["associated_duration_s"]),
            "ap_mac_rx": int(mac["ap_mac_rx"]),
            "ap_mac_promisc_rx": int(mac["ap_mac_promisc_rx"]),
            "ap_mac_rx_drop": int(mac["ap_mac_rx_drop"]),
            "bus_mac_tx": int(mac["bus_mac_tx"]),
            "ap_ipv4_rx": int(mac["ap_ipv4_rx"]),
            "ap_udp_received": int(mac["ap_udp_received"]),
            "sta_assoc_samples": sta_assoc_points,
            "ap_assoc_samples": ap_assoc_points,
            "both_assoc_samples": both_assoc_points,
            "passive_instrumentation_reproduced_original": int(all(changes.values())),
            "nonmatching_fields": ";".join(k for k, same in changes.items() if not same),
        }
        summary.append(row)
        for version in (original, measured):
            # Include prior control (without added instrumentation) and new
            # instrumented evidence to enable independent comparison.
            for suffix in ("summary.csv", "association.csv",
                           "association_raw.csv", "received.csv",
                           "analysis.json"):
                evidence.append(required(version, suffix))
            for radio in ("ap", "bus"):
                evidence.append(pcap(version, radio))
        for suffix in ("mac_path.csv", "mac_path_summary.csv"):
            evidence.append(required(measured, suffix))
        print(f"{policy}: AP MAC Rx={row['ap_mac_rx']}, MAC RxDrop="
              f"{row['ap_mac_rx_drop']}, IPv4 Rx={row['ap_ipv4_rx']}, "
              f"UDP delivered={row['ap_udp_received']}, "
              f"AP assoc samples={row['ap_assoc_samples']}/801, "
              f"STA assoc samples={row['sta_assoc_samples']}/801")

    out_csv = OUT / f"p3_fading_mac_path_run{args.run}.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    evidence.append(out_csv)
    output = OUT / f"p3_fading_mac_path_run{args.run}_complete.zip"
    checksum_lines = ["SHA256  PATH"]
    for file in evidence:
        checksum_lines.append(f"{sha256(file)}  {file.relative_to(ROOT)}")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for file in evidence:
            archive.write(file, file.relative_to(ROOT))
        archive.writestr("P3_MAC_PATH_SHA256_MANIFEST.txt",
                         "\n".join(checksum_lines) + "\n")
    print(f"\nUPLOAD ONLY: {output}")
    if any(not int(row["passive_instrumentation_reproduced_original"])
           for row in summary):
        print("WARNING: Instrumented run did not reproduce prior static ARP "
              "counters; inspect nonmatching_fields BEFORE scientific claims.")
    print("PCAP frames alone do not prove packet acceptance at AP MAC/IPv4.")


if __name__ == "__main__":
    main()
