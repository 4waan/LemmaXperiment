#!/usr/bin/env bash
# Runs the pinned RSP host on one block and records everything needed to
# reproduce it. Usage: baseline.sh <block> execute|prove [state-backend]
#   execute  runs the client in the SP1 executor, no proof (feasible locally)
#   prove    generates a Compressed proof; needs SP1_PROVER=network|cuda
set -euo pipefail

block="${1:?block number}"
mode="${2:?execute|prove}"
backend="${3:-proofs}"

here="$(cd "$(dirname "$0")" && pwd)"
workdir="${RSP_WORKDIR:-$HOME/rsp-baseline}"   # on the prover host: /work/apparatus
rsp_bin="$workdir/rsp/target/release/rsp"
rpc="${RPC_1:-http://localhost:9545/main/evm/1}"
cache="$workdir/cache"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-b${block}-${mode}-${backend}"
run_dir="$here/runs/$run_id"
mkdir -p "$run_dir" "$cache"

[ -x "$rsp_bin" ] || { echo "rsp host not built; run setup.sh"; exit 1; }
if [ "$mode" = prove ] && [ "${SP1_PROVER:-cpu}" = cpu ]; then
  echo "refusing local CPU proving of a block; set SP1_PROVER=network or cuda"; exit 1
fi

args=(--block-number "$block" --chain-id 1 --rpc-url "$rpc" --cache-dir "$cache"
      --state-backend "$backend" --report-path "$run_dir/report.csv")
[ "$mode" = prove ] && args+=(--prove)

{
  echo "run_id: $run_id"
  echo "command: $rsp_bin ${args[*]}"
  echo "sp1_prover: ${SP1_PROVER:-cpu}"
  echo "rsp_commit: $(git -C "$workdir/rsp" rev-parse HEAD)"
  echo "host_sha256: $(shasum -a 256 "$rsp_bin" | cut -d' ' -f1)"
  echo "host_machine: $(uname -m) $(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
  echo "started_at: $(date -u +%FT%TZ)"
} | tee "$run_dir/run.txt"

start=$(date +%s)
set +e
SP1_PROVER="${SP1_PROVER:-cpu}" RUST_LOG="${RUST_LOG:-info}" \
  "$rsp_bin" "${args[@]}" 2>&1 | tee "$run_dir/stdout.log"
status=${PIPESTATUS[0]}
set -e
end=$(date +%s)

{
  echo "ended_at: $(date -u +%FT%TZ)"
  echo "wall_seconds: $((end - start))"
  echo "exit_status: $status"
} | tee -a "$run_dir/run.txt"

# Keep the witness that was actually used so the run is reproducible offline.
if ls "$cache"/*"$block"* >/dev/null 2>&1; then
  for f in "$cache"/*"$block"*; do
    echo "witness: $(basename "$f") sha256=$(shasum -a 256 "$f" | cut -d' ' -f1)" | tee -a "$run_dir/run.txt"
  done
fi

exit "$status"
