#!/usr/bin/env python3
"""Bundle all P3 pilot evidence in one ZIP for reproducible peer review."""
import argparse
import hashlib
import zipfile
from pathlib import Path

from run_p3_pilots import CASES, prefix_for

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = (
    "summary.csv", "association.csv", "received.csv", "generated.csv",
    "sent.csv", "buffer.csv", "mobility.csv", "analysis.json",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--speed", type=int, choices=(5, 15), default=15)
    parser.add_argument("--stop", type=int, choices=(0, 10, 30), default=0)
    args = parser.parse_args()
    title = f"p3_pilots_v{args.speed}_stop{args.stop}_run{args.run}"
    prefix_root = ROOT / "out" / "p3"
    summary = prefix_root / f"{title}.csv"
    if not summary.is_file():
        raise FileNotFoundError(f"Run scripts/run_p3_pilots.py first: {summary}")

    paths = [summary]
    for scenario, policy, pace, capacity in CASES:
        prefix = prefix_for(
            scenario, policy, args.speed, args.stop, args.run, pace, capacity
        )
        for suffix in SUFFIXES:
            path = Path(str(prefix) + "_" + suffix)
            if not path.is_file():
                raise FileNotFoundError(f"Missing evidence for {scenario}/{policy}: {path}")
            paths.append(path)
    for policy in ("immediate", "fifo"):
        baseline = (ROOT / "out" / "p2" /
                    f"v{args.speed}_stop{args.stop}_run{args.run}_{policy}_summary.csv")
        if not baseline.is_file():
            raise FileNotFoundError(f"Missing original P2 control: {baseline}")
        paths.append(baseline)
    destination = prefix_root / f"{title}_complete.zip"
    checksum_lines = ["SHA256  PATH"]
    for path in paths:
        checksum_lines.append(f"{sha256(path)}  {path.relative_to(ROOT)}")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT))
        archive.writestr("P3_SHA256_MANIFEST.txt",
                         "\n".join(checksum_lines) + "\n")
    print(f"ZIP: {destination} ({len(paths)} files + manifest)")
    print("Upload this one ZIP; do not paste 8 logs separately.")


if __name__ == "__main__":
    main()
