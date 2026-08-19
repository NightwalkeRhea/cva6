#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
TRACE_DIR="$REPO_ROOT/fi-results/milestone4b-fixed-traces"
RESULT_DIR="$REPO_ROOT/fi-results/milestone4d-replay"
LOG_DIR="$RESULT_DIR/logs"

RTL_SIM="$RESULT_DIR/rtl-build/alu_replay_rtl"
NETLIST_SIM="$RESULT_DIR/netlist-build/alu_replay_netlist"

mkdir -p "$LOG_DIR"

if [[ ! -x "$RTL_SIM" ]]; then
  echo "Missing RTL simulator: $RTL_SIM" >&2
  exit 1
fi

if [[ ! -x "$NETLIST_SIM" ]]; then
  echo "Missing netlist simulator: $NETLIST_SIM" >&2
  exit 1
fi

for trace in "$TRACE_DIR"/*.csv; do
  trace_name="$(basename "$trace" .csv)"
  log_file="$LOG_DIR/${trace_name}.rtl.log"

  echo "RTL replay: $trace_name"

  timeout 30s "$RTL_SIM" \
    "+trace_file=$trace" \
    | tee "$log_file"
done

for trace in "$TRACE_DIR"/*.csv; do
  trace_name="$(basename "$trace" .csv)"
  log_file="$LOG_DIR/${trace_name}.netlist.log"

  echo "Netlist replay: $trace_name"

  timeout 30s "$NETLIST_SIM" \
    "+trace_file=$trace" \
    | tee "$log_file"
done

echo
echo "All RTL and netlist replays completed successfully."
