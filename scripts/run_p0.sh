#!/usr/bin/env bash
# Usage: bash scripts/run_p0.sh /absolute/path/to/ns-3.48 [11g|11a]
# Copies this project's scratch source into the ns-3 source tree and runs it.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash scripts/run_p0.sh /path/to/ns-3.48 [11g|11a]" >&2
  exit 2
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="$(realpath "$1")"
STANDARD="${2:-11g}"
if [[ "$STANDARD" != "11g" && "$STANDARD" != "11a" ]]; then
  echo "Invalid standard $STANDARD (use 11g or 11a)" >&2
  exit 2
fi
if [[ ! -x "$NS3_DIR/ns3" || ! -d "$NS3_DIR/scratch" ]]; then
  echo "Expected ns-3 source tree with ./ns3 and scratch/: $NS3_DIR" >&2
  exit 2
fi

SRC="$PROJECT_DIR/src/b10-p0-propagation.cc"
DEST="$NS3_DIR/scratch/b10-p0-propagation.cc"
if [[ -e "$DEST" ]] && ! head -n 1 "$DEST" | grep -q 'COMOV B10 - P0'; then
  echo "Refusing to overwrite an unrelated scratch program: $DEST" >&2
  exit 1
fi
python3 "$PROJECT_DIR/scripts/check_wifi_modes.py"
cp "$SRC" "$DEST"
mkdir -p "$PROJECT_DIR/out/p0"
CSV="$PROJECT_DIR/out/p0/p0_${STANDARD}.csv"
echo "ns-3 source: $NS3_DIR"
echo "Program: $DEST"
echo "CSV: $CSV"
cd "$NS3_DIR"
./ns3 run "scratch/b10-p0-propagation --standard=$STANDARD --csv=$CSV"
python3 "$PROJECT_DIR/scripts/evaluate_p0.py" --input "$CSV"
