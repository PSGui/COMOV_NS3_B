#!/usr/bin/env bash
# Usage: bash scripts/run_p2.sh ../../ns-3 [immediate|fifo] [5|15] [0|10|30] [run] [pacing_ms] [ap_x_m]
# The same C++ topology and generation timeline is used for BOTH policies.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 7 ]]; then
  echo "Usage: bash scripts/run_p2.sh ../../ns-3 [immediate|fifo] [5|15] [0|10|30] [run] [pacing_ms] [ap_x_m]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS3_DIR="$(realpath "$1")"
POLICY="fifo"
SPEED=5
STOP=10
RUN=1
PACE=2
AP_X=0
if [[ $# -ge 2 ]]; then POLICY="$2"; fi
if [[ $# -ge 3 ]]; then SPEED="$3"; fi
if [[ $# -ge 4 ]]; then STOP="$4"; fi
if [[ $# -ge 5 ]]; then RUN="$5"; fi
if [[ $# -ge 6 ]]; then PACE="$6"; fi
if [[ $# -ge 7 ]]; then AP_X="$7"; fi
if [[ "$POLICY" != "immediate" && "$POLICY" != "fifo" ]]; then
  echo "Policy must be immediate or fifo" >&2
  exit 2
fi
if [[ "$SPEED" != "5" && "$SPEED" != "15" ]]; then
  echo "Speed must be 5 or 15 m/s" >&2
  exit 2
fi
if [[ "$STOP" != "0" && "$STOP" != "10" && "$STOP" != "30" ]]; then
  echo "Stop duration must be 0, 10 or 30 s" >&2
  exit 2
fi
if ! [[ "$RUN" =~ ^[0-9]+$ ]] || [[ "$RUN" -eq 0 ]]; then
  echo "RNG run must be a positive integer" >&2
  exit 2
fi
if [[ ! "$PACE" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "Pacing must be a positive decimal number in ms" >&2
  exit 2
fi
# Robustness AP coordinates are intentionally discrete for reproducibility.
if [[ "$AP_X" != "0" && "$AP_X" != "-30" && "$AP_X" != "30" ]]; then
  echo "AP x position must be -30, 0 or +30 m" >&2
  exit 2
fi
if [[ ! -x "$NS3_DIR/ns3" || ! -d "$NS3_DIR/scratch" ]]; then
  echo "Expected ns-3 source tree with ./ns3 and scratch/: $NS3_DIR" >&2
  exit 2
fi

python3 "$ROOT/scripts/check_wifi_modes.py"

SRC="$ROOT/src/b10-p2-buffer-compare.cc"
DEST="$NS3_DIR/scratch/b10-p2-buffer-compare.cc"
if [[ -e "$DEST" ]] && ! head -n 1 "$DEST" | grep -q 'COMOV B10 - P2'; then
  echo "Refusing to overwrite unrelated scratch source: $DEST" >&2
  exit 1
fi
cp "$SRC" "$DEST"
mkdir -p "$ROOT/out/p2"
PREFIX="$ROOT/out/p2/v${SPEED}_stop${STOP}_run${RUN}_${POLICY}"
if [[ "$POLICY" == "fifo" && "$PACE" != "2" ]]; then
  PREFIX="$PREFIX"_pace"$PACE"
fi
if [[ "$AP_X" == "-30" ]]; then
  PREFIX="${PREFIX}_apxm30"
elif [[ "$AP_X" == "30" ]]; then
  PREFIX="${PREFIX}_apxp30"
fi
echo "ns-3 source: $NS3_DIR"
echo "Program: $DEST"
echo "Output prefix: $PREFIX"

cd "$NS3_DIR"
./ns3 run "scratch/b10-p2-buffer-compare --policy=$POLICY --speed=$SPEED --stop=$STOP --seed=1 --run=$RUN --bufferBytes=4000000 --pacingMs=$PACE --apX=$AP_X --prefix=$PREFIX"
python3 "$ROOT/scripts/review_p2.py" --prefix "$PREFIX" --require-contact
echo "P2 CSVs and validated analysis: $PREFIX"
