#!/usr/bin/env python3
"""Three report-ready figures from P2 paired_statistics.csv (no ns-3 rerun)."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("out/p2/paired_statistics.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/p2"))
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows.sort(key=lambda r: (int(r["speed_mps"]), int(r["stop_s"])))
    if len(rows) != 6 or any(int(r["n_pairs"]) != 10 for r in rows):
        raise ValueError("Expected six scenario rows with n_pairs=10 each")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels = [f'{r["speed_mps"]} m/s · {r["stop_s"]} s' for r in rows]
    x = np.arange(6)
    immediate = np.array([float(r["immediate_delivery_mean_pct"]) for r in rows])
    fifo = np.array([float(r["fifo_delivery_mean_pct"]) for r in rows])
    gain = np.array([float(r["fifo_minus_immediate_mean_pp"]) for r in rows])
    low = np.array([float(r["difference_95ci_low_pp"]) for r in rows])
    high = np.array([float(r["difference_95ci_high_pp"]) for r in rows])
    overflow = np.array([float(r["fifo_overflow_mean"]) for r in rows])
    expired = np.array([float(r["fifo_expired_mean"]) for r in rows])
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.titlesize": 15, "figure.facecolor": "white"})

    fig, ax = plt.subplots(figsize=(12.6, 6.4))
    a = ax.bar(x-.18, immediate, width=.36, label="Envio imediato")
    b = ax.bar(x+.18, fifo, width=.36, label="Buffer FIFO (4 MB)")
    ax.bar_label(a, labels=[f"{v:.1f}%" for v in immediate], padding=3, fontsize=9)
    ax.bar_label(b, labels=[f"{v:.1f}%" for v in fifo], padding=3, fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Mensagens entregues no prazo / geradas (%)")
    ax.set_title("COMOV B10 — Entrega média de mensagens por política", fontweight="bold")
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False)
    fig.text(.12, .018, "n=10 runs emparelhadas · 12 000 mensagens geradas por simulação · prazo 60 s", fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(args.output_dir/"comov_entrega_media_politicas.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # CI for the paired difference only. Never attach it to individual policy rates.
    fig, ax = plt.subplots(figsize=(11.7,6.5))
    for i in range(6):
        ax.errorbar([gain[i]], [i], xerr=[[gain[i]-low[i]],[high[i]-gain[i]]],
                    fmt="o", capsize=5, markersize=7)
        ax.annotate(f"{gain[i]:.3f} pp  [{low[i]:.3f}; {high[i]:.3f}]",
                    xy=(gain[i],i), xytext=(0,-16), textcoords="offset points",
                    ha="center", fontsize=9)
    ax.set_yticks(range(6),labels)
    ax.set_ylim(5.75,-.65)
    ax.set_xlim(30.35,33.68)
    ax.set_xlabel("Ganho FIFO − imediato (pontos percentuais)")
    ax.set_title("COMOV B10 — Diferenças emparelhadas e IC95%", fontweight="bold")
    ax.grid(axis="x", alpha=.2)
    fig.text(.12,.018,"IC de Student-t (9 g.l.) sobre a diferença; não inclui incerteza do canal rodoviário real.",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(args.output_dir/"comov_ganho_fifo_ic95.png",dpi=200,bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12.6,6.4))
    a = ax.bar(x-.18, overflow, width=.36, label="Buffer cheio: drop-newest")
    b = ax.bar(x+.18, expired, width=.36, label="Expiradas antes do envio")
    ax.bar_label(a, labels=[f"{v:.0f}" for v in overflow], padding=3, fontsize=9)
    ax.bar_label(b, labels=[f"{v:.0f}" for v in expired], padding=3, fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, max(max(overflow),max(expired))*1.16)
    ax.set_ylabel("Mensagens por simulação (média de 10 runs)")
    ax.set_title("COMOV B10 — Descartes e expirações do buffer FIFO",fontweight="bold")
    ax.grid(axis="y",alpha=.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right",frameon=False)
    fig.text(.12,.018,"Pico médio: 3,6939 MB (5 m/s) · 4 MB (15 m/s). Expiração ≠ perda PHY.",fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(args.output_dir/"comov_fifo_overflow_expiracao.png",dpi=200,bbox_inches="tight")
    plt.close(fig)

    print("Saved 3 P2 PNG figures in", args.output_dir)


if __name__ == "__main__":
    main()
