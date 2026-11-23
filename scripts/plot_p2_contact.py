#!/usr/bin/env python3
"""Report plots for the question: does onboard storage use AP contact better?

Reads contact_metrics_summary.csv created from 120 raw P2 simulation outputs.
The goodput measure excludes 802.11 PHY overhead and is NOT airtime usage.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_data(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("No contact analysis rows")
    if any(float(r["ap_x_m"]) != 0 for r in rows):
        raise ValueError("Baseline graph accepts AP x=0 m only")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path,
                   default=Path("out/p2/contact_metrics_summary.csv"))
    p.add_argument("--output-dir", type=Path, default=Path("out/p2"))
    a = p.parse_args()
    rows = read_data(a.input)
    grouped = {}
    for r in rows:
        key = (int(r["speed_mps"]), int(r["stop_s"]))
        grouped.setdefault(key, {})[r["policy"]] = r
    if len(grouped) != 6 or any(set(g) != {"fifo", "immediate"}
                                for g in grouped.values()):
        raise ValueError("Expected the six physical scenarios, both policies")
    order = sorted(grouped)
    labels = [f"{v} m/s · {s} s" for v, s in order]
    x = np.arange(len(order))
    p0 = [float(grouped[k]["immediate"]["on_time_goodput_mbps_mean"])
          for k in order]
    p1 = [float(grouped[k]["fifo"]["on_time_goodput_mbps_mean"])
          for k in order]
    a.output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    b0 = ax.bar(x - .18, p0, .36, label="Envio imediato")
    b1 = ax.bar(x + .18, p1, .36, label="FIFO (4 MB)")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Mbit úteis entregues no prazo / segundo associado")
    ax.set_title("Aproveitamento do contacto Wi-Fi: goodput útil de aplicação")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.2)
    ax.set_axisbelow(True)
    ax.bar_label(b0, labels=[f"{v:.2f}" for v in p0], padding=2, fontsize=9)
    ax.bar_label(b1, labels=[f"{v:.2f}" for v in p1], padding=2, fontsize=9)
    ax.set_ylim(0, max(p0 + p1) * 1.18)
    fig.text(.1, .01,
             "n=10 runs por cenário · 1000 B/UDP · não mede ocupação do canal PHY.",
             fontsize=9)
    fig.tight_layout(rect=(0,.035,1,1))
    fig.savefig(a.output_dir / "p2_contact_goodput_policies.png",
                dpi=200, bbox_inches="tight")
    plt.close(fig)

    # Show the FIFO tradeoff in delay; mean/P95 of each run averaged across 10.
    means = [float(grouped[k]["fifo"]["latency_mean_s_mean"]) for k in order]
    p95 = [float(grouped[k]["fifo"]["latency_p95_s_mean"]) for k in order]
    fig, ax = plt.subplots(figsize=(12, 6))
    b0 = ax.bar(x - .18, means, .36, label="FIFO — atraso médio")
    b1 = ax.bar(x + .18, p95, .36, label="FIFO — média dos P95 por run")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Segundos")
    ax.set_title("Custo do armazenamento: atraso das mensagens recebidas")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.2)
    ax.set_axisbelow(True)
    ax.bar_label(b0, labels=[f"{v:.2f}" for v in means], padding=2, fontsize=9)
    ax.bar_label(b1, labels=[f"{v:.2f}" for v in p95], padding=2, fontsize=9)
    ax.set_ylim(0, max(p95) * 1.19)
    fig.text(.1, .01,
             "Só mensagens recebidas; a média dos percentis não é o percentil global.",
             fontsize=9)
    fig.tight_layout(rect=(0,.035,1,1))
    fig.savefig(a.output_dir / "p2_fifo_delivery_delay.png",
                dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved contact-goodput and latency figures to {a.output_dir}")


if __name__ == "__main__":
    main()
