#!/usr/bin/env bash
# Usage: bash scripts/run_p1.sh ../../ns-3 [speed:5|15] [stop:0|10|30] [run-number]
# Copies P1 into the ns-3 scratch/ directory and validates generated CSVs.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 4 ]]; then
  echo "Usage: bash scripts/run_p1.sh ../../ns-3 [5|15] [0|10|30] [run-number]" >&2
  exit 2
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NS3_DIR="$(realpath "$1")"
SPEED=5
STOP=10
RUN=1
if [[ $# -ge 2 ]]; then SPEED="$2"; fi
if [[ $# -ge 3 ]]; then STOP="$3"; fi
if [[ $# -ge 4 ]]; then RUN="$4"; fi

if [[ "$SPEED" != "5" && "$SPEED" != "15" ]]; then
  echo "Speed must be 5 or 15 m/s" >&2
  exit 2
fi
if [[ "$STOP" != "0" && "$STOP" != "10" && "$STOP" != "30" ]]; then
  echo "Stop duration must be 0, 10 or 30 s" >&2
  exit 2
fi
if ! [[ "$RUN" =~ ^[0-9]+$ ]] || [[ "$RUN" -eq 0 ]]; then
  echo "Run number must be a positive integer" >&2
  exit 2
fi
if [[ ! -x "$NS3_DIR/ns3" || ! -d "$NS3_DIR/scratch" ]]; then
  echo "Expected ns-3 installation with ./ns3 and scratch/: $NS3_DIR" >&2
  exit 2
fi

SOURCE="$PROJECT_DIR/src/b10-p1-mobility-udp.cc"
SCRATCH="$NS3_DIR/scratch/b10-p1-mobility-udp.cc"
if [[ -e "$SCRATCH" ]] && ! head -n 1 "$SCRATCH" | grep -q 'COMOV B10 - P1'; then
  echo "Refusing to overwrite unrelated scratch program: $SCRATCH" >&2
  exit 1
fi
python3 "$PROJECT_DIR/scripts/check_wifi_modes.py"
cp "$SOURCE" "$SCRATCH"
mkdir -p "$PROJECT_DIR/out/p1"
PREFIX="$PROJECT_DIR/out/p1/v${SPEED}_stop${STOP}_run${RUN}"
echo "ns-3 source: $NS3_DIR"
echo "Program: $SCRATCH"
echo "Results prefix: $PREFIX"
cd "$NS3_DIR"
./ns3 run "scratch/b10-p1-mobility-udp --speed=$SPEED --stop=$STOP --seed=1 --run=$RUN --prefix=$PREFIX"
python3 "$PROJECT_DIR/scripts/review_p1.py" --prefix "$PREFIX" --require-contact
echo "For plots, optionally run:"
echo "  python3 \"$PROJECT_DIR/scripts/plot_p1.py\" --prefix \"$PREFIX\""
