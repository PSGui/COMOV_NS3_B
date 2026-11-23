#!/usr/bin/env python3
"""Create P2 comparison PNGs directly from matched CSV logs (2D only)."""
import argparse
import csv
from pathlib import Path


def load(prefix, suffix):
    with Path(str(prefix) + "_" + suffix + ".csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--immediate-prefix", type=Path, required=True)
    ap.add_argument("--fifo-prefix", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=Path("out/p2"))
    args = ap.parse_args()
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("matplotlib required for P2 PNGs") from exc

    si = load(args.immediate_prefix, "summary")[0]
    sf = load(args.fifo_prefix, "summary")[0]
    if (si["policy"], sf["policy"]) != ("immediate", "fifo"):
        raise ValueError("The prefixes must correspond to immediate and FIFO")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stop = float(si["stop_s"])

    fig, ax = plt.subplots(figsize=(10, 4.4))
    buffer_events = load(args.fifo_prefix, "buffer")
    t = [0.0]
    occ = [0.0]
    for event in buffer_events:
        t.append(float(event["t_s"]))
        occ.append(float(event["queued_bytes"]) / 1e6)
    t.append(200)
    occ.append(occ[-1])
    ax.step(t, occ, where="post", label="Ocupação FIFO (MB)")
    ax.axhline(float(sf["buffer_limit_bytes"]) / 1e6, ls="--",
               label="Capacidade configurada (MB)", color="gray")
    ax.axvline(70, ls=":", color="gray")
    if stop > 0:
        ax.axvline(70+stop, ls=":", color="gray")
    ax.set(xlabel="Tempo (s)", ylabel="Payload na fila (MB)",
           title="B10 P2 — ocupação da FIFO de aplicação")
    ax.set_xlim(0, 200)
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "p2_fifo_occupancy.png", dpi=190)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.4))
    for prefix, label in [(args.immediate_prefix, "Imediato"),
                          (args.fifo_prefix, "FIFO")]:
        counts = [0] * 201
        for row in load(prefix, "received"):
            if row["duplicate"] == "1":
                continue
            sec = int(float(row["t_rx_s"]))
            if 0 <= sec <= 200:
                counts[sec] += 1
        ax.step(range(201), counts, where="post", label=label)
    ax.axvline(70, ls=":", color="gray")
    if stop > 0:
        ax.axvline(70+stop, ls=":", color="gray")
    ax.set(xlabel="Tempo (s)", ylabel="Receções únicas UDP/s",
           title="B10 P2 — receções UDP por política")
    ax.set_xlim(0, 200)
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "p2_udp_arrivals_comparison.png", dpi=190)
    plt.close(fig)

    labels = ["Geradas", "Socket aceita", "Recebidas ≤60 s"]
    values_i = [int(si[k]) for k in
                ("generated", "socket_accepted", "received_on_time")]
    values_f = [int(sf[k]) for k in
                ("generated", "socket_accepted", "received_on_time")]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(labels))
    ax.bar([q-0.19 for q in x], values_i, width=0.38, label="Imediato")
    ax.bar([q+0.19 for q in x], values_f, width=0.38, label="FIFO")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Mensagens")
    ax.set_title("B10 P2 — geração, submissão e entregas no prazo")
    ax.legend()
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(args.output_dir / "p2_policy_accounting.png", dpi=190)
    plt.close(fig)
    print(f"Saved 3 PNGs to {args.output_dir}")


if __name__ == "__main__":
    main()
