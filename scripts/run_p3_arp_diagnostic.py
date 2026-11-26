#!/usr/bin/env python3
"""B10 P3 fading ARP-resolution control, automated and isolated.

The failing dynamic-ARP fading pair (run=1) had MAC association but zero UDP.
PCAP shows repeated ARP requests, no ARP replies and no IP DATA. These two
ADDITIONAL simulations pre-populate neighbor caches to isolate ARP resolution
from the Wi-Fi fading channel. DO NOT merge results into the P2 baseline.
"""
import argparse
import csv
import hashlib
import json
import struct
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "p3"


def prefix_for(policy, run, static_arp):
    return OUT / (
        f"p3_fading_v15_stop0_run{run}_{policy}_pace2_buf4000000"
        + ("_staticarp" if static_arp else "")
    )


def parse_summary(prefix):
    file = Path(str(prefix) + "_summary.csv")
    with file.open(encoding="utf-8", newline="") as stream:
        values = list(csv.DictReader(stream))
    if len(values) != 1:
        raise ValueError(f"Invalid summary {file}")
    return values[0]


def pcap_counts(path):
    """Count captured 802.11 frame types and LLC ARP/IP using DLT 105.

    The PCAP records can contain both Tx and successfully-sniffed Rx.
    Counts are not automatically unique deliveries or PHY error counters.
    """
    raw = path.read_bytes()
    if len(raw) < 24 or raw[:4] != b"\xd4\xc3\xb2\xa1":
        raise ValueError(f"Expected little-endian microsecond PCAP: {path}")
    if struct.unpack_from("<I", raw, 20)[0] != 105:
        raise ValueError(f"Expected DLT_IEEE802_11=105: {path}")
    found = Counter()
    cursor = 24
    while cursor < len(raw):
        if cursor + 16 > len(raw):
            raise ValueError(f"Truncated PCAP record: {path}")
        _, _, captured, _ = struct.unpack_from("<IIII", raw, cursor)
        cursor += 16
        frame = raw[cursor:cursor + captured]
        cursor += captured
        if len(frame) != captured or len(frame) < 2:
            raise ValueError(f"Malformed PCAP frame: {path}")
        control = struct.unpack_from("<H", frame)[0]
        kind = (control >> 2) & 3
        sub = (control >> 4) & 15
        found["frames"] += 1
        found[f"type_{kind}_sub_{sub}"] += 1
        if kind == 2 and len(frame) >= 32 and frame[24:27] == b"\xaa\xaa\x03":
            ether_type = int.from_bytes(frame[30:32], "big")
            if ether_type == 0x806 and len(frame) >= 40:
                opcode = int.from_bytes(frame[38:40], "big")
                found["arp_request" if opcode == 1 else
                      "arp_reply" if opcode == 2 else "arp_other"] += 1
            if ether_type == 0x800:
                found["ipv4_data"] += 1
    return dict(found)


def capture_path(prefix, radio):
    matching = list(prefix.parent.glob(prefix.name + f"_pcap_{radio}*.pcap"))
    if len(matching) != 1:
        raise FileNotFoundError(f"Expected one PCAP for {prefix} / {radio}: {matching}")
    return matching[0]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(*command):
    print("$ " + " ".join(map(str, command)), flush=True)
    subprocess.run([str(s) for s in command], cwd=ROOT, check=True)


def validate_existing(prefix, run):
    try:
        s = parse_summary(prefix)
        return (
            s["scenario"] == "fading" and s["policy"] in ("immediate", "fifo")
            and int(s["run"]) == run and int(s["seed"]) == 1
            and int(s["generated"]) == 12000
            and int(s["static_arp"]) == 1
            and int(s["buffer_limit_bytes"]) == 4000000
            and float(s["pacing_ms"]) == 2
            and all(Path(str(prefix) + "_" + suffix).is_file()
                    for suffix in ("summary.csv", "association_raw.csv", "analysis.json"))
            and all(len(list(prefix.parent.glob(prefix.name + f"_pcap_{r}*.pcap"))) == 1
                    for r in ("ap", "bus"))
        )
    except (OSError, KeyError, ValueError):
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
        parser.error(f"not an ns-3 tree: {ns3}")

    evidence = []
    summary_rows = []
    for policy in ("immediate", "fifo"):
        ordinary = prefix_for(policy, args.run, False)
        diagnostic = prefix_for(policy, args.run, True)
        if not Path(str(ordinary) + "_summary.csv").is_file():
            raise FileNotFoundError(f"Missing original failing fading pilot: {ordinary}")
        if args.skip_existing and validate_existing(diagnostic, args.run):
            execute(sys.executable, "scripts/review_p3.py",
                    "--prefix", diagnostic)
        else:
            execute("bash", "scripts/run_p3.sh", ns3, "fading", policy,
                    15, 0, args.run, 2, 4000000, 1)
        if not validate_existing(diagnostic, args.run):
            raise ValueError(f"Static ARP diagnostic output invalid: {diagnostic}")
        previous = parse_summary(ordinary)
        after = parse_summary(diagnostic)
        result = {
            "run": args.run,
            "policy": policy,
            "dynamic_arp_received_on_time": int(previous["received_on_time"]),
            "static_arp_received_on_time": int(after["received_on_time"]),
            "dynamic_arp_socket_accepted": int(previous["socket_accepted"]),
            "static_arp_socket_accepted": int(after["socket_accepted"]),
            "dynamic_arp_assoc_s": float(previous["associated_duration_s"]),
            "static_arp_assoc_s": float(after["associated_duration_s"]),
            "dynamic_arp_ignored_deassoc_callbacks": int(previous["ignored_deassoc_callbacks"]),
            "static_arp_ignored_deassoc_callbacks": int(after["ignored_deassoc_callbacks"]),
        }
        for state, prefix in (("dynamic", ordinary), ("static", diagnostic)):
            for radio in ("ap", "bus"):
                pc = capture_path(prefix, radio)
                counts = pcap_counts(pc)
                for key in ("frames", "arp_request", "arp_reply", "ipv4_data"):
                    result[f"{state}_{radio}_{key}"] = counts.get(key, 0)
                evidence.append(pc)
            for suffix in ("summary.csv", "association.csv",
                           "association_raw.csv", "received.csv",
                           "generated.csv", "sent.csv", "buffer.csv",
                           "mobility.csv", "analysis.json"):
                file = Path(str(prefix) + "_" + suffix)
                if not file.is_file():
                    raise FileNotFoundError(f"Missing diagnostic evidence {file}")
                evidence.append(file)
        summary_rows.append(result)

    summary_path = OUT / f"p3_fading_arp_diagnostic_run{args.run}.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    evidence.append(summary_path)
    zip_path = OUT / f"p3_fading_arp_diagnostic_run{args.run}_complete.zip"
    checksum_lines = ["SHA256  PATH"]
    for file in evidence:
        checksum_lines.append(f"{sha256(file)}  {file.relative_to(ROOT)}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for file in evidence:
            archive.write(file, file.relative_to(ROOT))
        archive.writestr("P3_ARP_SHA256_MANIFEST.txt",
                         "\n".join(checksum_lines) + "\n")
    for row in summary_rows:
        print(f"{row['policy']}: UDP received, normal ARP="
              f"{row['dynamic_arp_received_on_time']}, static ARP="
              f"{row['static_arp_received_on_time']}; "
              f"static AP IPv4 frames={row['static_ap_ipv4_data']}")
    print(f"\nUPLOAD ONLY THIS ZIP: {zip_path}")
    print("Treat this as a DIAGNOSTIC control, not a new scientific baseline.")
    print("If zero UDP persists, the radio problem has NOT been isolated to ARP.")


if __name__ == "__main__":
    main()
