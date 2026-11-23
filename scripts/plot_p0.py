#!/usr/bin/env python3
"""Create two report-ready P0 figures from the ns-3 CSV (optional matplotlib).

This plots simulation CSV values; the absence of decoded frames is NOT 0 dBm.
"""
import argparse
import csv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("out/p0"))
    args = parser.parse_args()
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("matplotlib em falta: python3 -m pip install matplotlib") from exc

    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("No observations in P0 CSV")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    x = [float(row["horizontal_m"]) for row in rows]
    theory = [float(row["theoretical_pr_dbm"]) for row in rows]
    measured_points = [(float(row["horizontal_m"]), float(row["phy_rss_mean_dbm"]))
                       for row in rows if row["phy_rss_mean_dbm"]]

    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.plot(x, theory, label="Previsão log-distance", marker="o", linewidth=1.8)
    if measured_points:
        ax.scatter([p[0] for p in measured_points],
                   [p[1] for p in measured_points],
                   label="RSS PHY (frames descodificados)", marker="x", s=60, zorder=3)
    ax.set_xlabel("Distância horizontal ao AP (m)")
    ax.set_ylabel("Potência recebida (dBm)")
    ax.set_title("P0 — potência teórica e receções no ns-3")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    outfile = args.output_dir / "p0_potencia.png"
    fig.savefig(outfile, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    counts = [int(row["decoded_frames_at_sta"]) for row in rows]
    ax.bar([str(int(d)) for d in x], counts)
    ax.set_xlabel("Distância horizontal ao AP (m)")
    ax.set_ylabel("Frames descodificados (contagem por ponto)")
    ax.set_title("P0 — receções PHY registadas")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    outfile2 = args.output_dir / "p0_frames.png"
    fig.savefig(outfile2, dpi=200)
    plt.close(fig)
    print(f"Generated {outfile} and {outfile2}")


if __name__ == "__main__":
    main()
