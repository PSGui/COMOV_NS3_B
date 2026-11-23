#!/usr/bin/env python3
"""Generate three time-aligned 2D figures for COMOV B10 pilot P1.

Requires matplotlib. Figures are based on real P1 CSV outputs, not examples.
"""
import argparse
import csv
from pathlib import Path


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def annotate_stop(ax, stop_s):
    ax.axvline(70.0, linestyle="--", linewidth=1, color="gray",
               label="Início da paragem")
    if stop_s > 0:
        ax.axvline(70.0 + stop_s, linestyle=":", linewidth=1, color="gray",
                   label="Fim da paragem")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("Falta matplotlib: python3 -m pip install matplotlib") from exc

    prefix = str(args.prefix)
    mobility = read_csv(prefix + "_mobility.csv")
    received = read_csv(prefix + "_received.csv")
    assoc_events = read_csv(prefix + "_association.csv")
    summary = read_csv(prefix + "_summary.csv")[0]
    stop_s = float(summary["stop_s"])
    output_dir = Path(prefix).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(prefix).name

    times = [float(r["t_s"]) for r in mobility]
    distances = [float(r["distance_ap_m"]) for r in mobility]
    association_states = [int(r["associated"]) for r in mobility]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(times, distances, label="Distância entre antenas")
    annotate_stop(ax, stop_s)
    ax.set(xlabel="Tempo de simulação (s)", ylabel="Distância 3D ao AP (m)",
           title="B10 P1 — aproximação, paragem e afastamento")
    ax.set_xlim(0, 200)
    ax.legend()
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(output_dir / (stem + "_distance.png"), dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 3))
    ax.step(times, association_states, where="post", label="Associado (STA MAC)")
    annotate_stop(ax, stop_s)
    ax.set(xlabel="Tempo de simulação (s)", ylabel="Associação Wi-Fi",
           title="B10 P1 — estado de associação",
           yticks=[0, 1], ylim=(-.1, 1.2))
    ax.set_xlim(0, 200)
    ax.legend()
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(output_dir / (stem + "_association.png"), dpi=180)
    plt.close(fig)

    counts = [0] * 201
    late_counts = [0] * 201
    for row in received:
        if row["duplicate"] == "1":
            continue
        second = int(float(row["t_rx_s"]))
        if 0 <= second <= 200:
            counts[second] += 1
            if row["on_time"] == "0":
                late_counts[second] += 1
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(201), counts, width=1, label="Receções únicas/s")
    if any(late_counts):
        ax.bar(range(201), late_counts, width=1,
               label="Recebidas após o limite de 60 s")
    annotate_stop(ax, stop_s)
    ax.set(xlabel="Tempo de simulação (s)", ylabel="Mensagens UDP recebidas/s",
           title="B10 P1 — receções UDP no AP")
    ax.set_xlim(0, 200)
    ax.legend()
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(output_dir / (stem + "_udp_arrivals.png"), dpi=180)
    plt.close(fig)

    print("Criadas 3 figuras PNG: distância, associação e receções UDP.")
    print(f"Eventos de associação/desassociação registados: {len(assoc_events)}")
    print(f"Ficheiros em: {output_dir}")


if __name__ == "__main__":
    main()
