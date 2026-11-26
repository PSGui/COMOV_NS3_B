#!/usr/bin/env python3
"""Package complete P3 run-level evidence into one ZIP.

All 80 P3 executions (10 runs x 8 configurations): each full application CSV
and accounting JSON, plus original P2 summary controls. PCAP captures are
included for Nakagami m=5 run 1 and for ANY m=5 run reporting zero UDP
(receivers may be blocked by association or address resolution). A manifest
protects every byte of data. Source ns-3 scratch binaries are not packaged.
"""
import argparse
import hashlib
import zipfile
from pathlib import Path

from run_p3_repeated_tests import CASES, OUT, P2, prefix_for, one_summary, valid_existing

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = (
    "summary.csv", "generated.csv", "received.csv", "sent.csv",
    "association.csv", "association_raw.csv", "buffer.csv",
    "mobility.csv", "analysis.json",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_file(path, files, seen):
    if not path.is_file():
        raise FileNotFoundError(f"Missing evidence {path}")
    if path not in seen:
        seen.add(path)
        files.append(path)


def pcap_file(prefix, radio):
    matches = list(prefix.parent.glob(prefix.name + "_pcap_" + radio + "*.pcap"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one fading PCAP {prefix}, {radio}: {matches}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-run", type=int, default=1)
    parser.add_argument("--end-run", type=int, default=10)
    args = parser.parse_args()
    if not (1 <= args.start_run <= args.end_run <= args.start_run + 30):
        parser.error("Invalid run interval")

    label = f"runs{args.start_run}-{args.end_run}"
    files = []
    seen = set()
    for name in (
        f"p3_repeated_{label}_runs.csv",
        f"p3_repeated_{label}_paired.csv",
        f"p3_repeated_{label}_effects.csv",
        f"p3_repeated_{label}_parameters.json",
    ):
        add_file(OUT / name, files, seen)

    zero_delivery_fading_runs = []
    for run in range(args.start_run, args.end_run + 1):
        for case in CASES:
            key, scenario, policy, pace, capacity, m = case
            prefix = prefix_for(case, run)
            if not valid_existing(case, run):
                raise ValueError(f"Case not audited or output incomplete: {prefix}")
            summary = one_summary(prefix)
            for suffix in SUFFIXES:
                add_file(Path(str(prefix) + "_" + suffix), files, seen)
            if scenario == "fading" and (
                run == 1 or int(summary["received_on_time"]) == 0
            ):
                if int(summary["received_on_time"]) == 0:
                    zero_delivery_fading_runs.append((run, policy))
                for radio in ("ap", "bus"):
                    add_file(pcap_file(prefix, radio), files, seen)
        for policy in ("immediate", "fifo"):
            add_file(P2 / f"v15_stop0_run{run}_{policy}_summary.csv", files, seen)

    output = OUT / f"p3_repeated_{label}_complete.zip"
    checksum_lines = ["SHA256  PATH"]
    for path in files:
        checksum_lines.append(f"{sha256(path)}  {path.relative_to(ROOT)}")
    explanatory = (
        "P3 B10: useful Wi-Fi contact stress tests\n"
        f"Runs {args.start_run}-{args.end_run}: 8 cases per run\n"
        "A: fading m=5, dynamic ARP; B: contention 2Mbps; "
        "C: pacing 3ms and buffer 2MB\n"
        "All 120 original P2 simulations preserved.\n"
        "Goodput is UDP payload per MAC-associated second, not PHY airtime.\n"
        "Zero-reception fading runs are retained in statistical sample.\n"
        f"Fading m=5 zero-UDP cases: {zero_delivery_fading_runs!r}\n"
        "PCAP included for m=5 run=1 and for any m=5 zero-delivery run.\n"
        "95% Student-t intervals apply to the model's RNG runs, not measured roads.\n"
    )
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for file in files:
            archive.write(file, file.relative_to(ROOT))
        archive.writestr("P3_REPEATED_README.txt", explanatory)
        archive.writestr("P3_REPEATED_SHA256_MANIFEST.txt",
                         "\n".join(checksum_lines) + "\n")
    print(f"ZIP: {output} ({len(files)} source files + README + SHA256 manifest)")
    print(f"Fading m=5 zero-reception cases: {zero_delivery_fading_runs}")
    print("Upload ONLY this ZIP. Never remove failed runs from the sample.")


if __name__ == "__main__":
    main()
