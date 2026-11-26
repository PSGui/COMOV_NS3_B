#!/usr/bin/env bash
# Usage: bash scripts/run_p3.sh ../../ns-3 reference|fading|contention immediate|fifo 15 0 1 2 4000000
# Scenario source is SEPARATE from the validated P2 120-run program.
set -euo pipefail

if [[ $# -ne 8 && $# -ne 9 ]]; then
  echo "Usage: $0 NS3_DIR scenario policy speed stop run pacing_ms buffer_bytes [staticArp=0|1]" >&2
  exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS3_DIR="$(realpath "$1")"
SCENARIO="$2"
POLICY="$3"
SPEED="$4"
STOP="$5"
RUN="$6"
PACE="$7"
CAPACITY="$8"
STATIC_ARP="${9:-0}"
if [[ ! -x "$NS3_DIR/ns3" || ! -d "$NS3_DIR/scratch" ]]; then
  echo "Invalid ns-3 directory: $NS3_DIR" >&2; exit 2
fi
if [[ "$SCENARIO" != "reference" && "$SCENARIO" != "fading" && "$SCENARIO" != "contention" ]]; then
  echo "scenario must be reference/fading/contention" >&2; exit 2
fi
if [[ "$POLICY" != "immediate" && "$POLICY" != "fifo" ]]; then
  echo "policy must be immediate/fifo" >&2; exit 2
fi
if [[ "$SPEED" != "5" && "$SPEED" != "15" ]] || [[ "$STOP" != "0" && "$STOP" != "10" && "$STOP" != "30" ]]; then
  echo "speed must be 5/15 and stop must be 0/10/30" >&2; exit 2
fi
if ! [[ "$RUN" =~ ^[1-9][0-9]*$ ]]; then
  echo "run must be positive" >&2; exit 2
fi
if [[ "$PACE" != "2" && "$PACE" != "3" ]] || [[ "$CAPACITY" != "4000000" && "$CAPACITY" != "2000000" ]]; then
  echo "P3 pilot pacing=2/3 ms; buffer capacity=2/4 MB" >&2; exit 2
fi
if [[ "$STATIC_ARP" != "0" && "$STATIC_ARP" != "1" ]]; then
  echo "staticArp must be 0/1" >&2; exit 2
fi
if [[ "$STATIC_ARP" == "1" && "$SCENARIO" != "fading" ]]; then
  echo "staticArp diagnostic applies only to fading" >&2; exit 2
fi
python3 "$ROOT/scripts/check_wifi_modes.py"
SRC="$ROOT/src/b10-p3-stress.cc"
DEST="$NS3_DIR/scratch/b10-p3-stress.cc"
if [[ -f "$DEST" ]] && ! head -n 1 "$DEST" | grep -q 'COMOV B10 - P3'; then
  echo "Refusing to overwrite an unrelated ns-3 scratch source" >&2; exit 1
fi
cp "$SRC" "$DEST"
mkdir -p "$ROOT/out/p3"
PREFIX="$ROOT/out/p3/p3_${SCENARIO}_v${SPEED}_stop${STOP}_run${RUN}_${POLICY}_pace${PACE}_buf${CAPACITY}"
if [[ "$STATIC_ARP" == "1" ]]; then
  PREFIX="${PREFIX}_staticarp"
fi
echo "P3 output prefix: $PREFIX"
cd "$NS3_DIR"
./ns3 run "scratch/b10-p3-stress --scenario=$SCENARIO --policy=$POLICY --speed=$SPEED --stop=$STOP --seed=1 --run=$RUN --pacingMs=$PACE --bufferBytes=$CAPACITY --backgroundRateBps=2000000 --staticArp=$STATIC_ARP --prefix=$PREFIX"
python3 "$ROOT/scripts/review_p3.py" --prefix "$PREFIX"
echo "P3 validated CSV prefix: $PREFIX"
