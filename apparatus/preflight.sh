#!/usr/bin/env bash
# Read-only checks for the apparatus stage. Exits non-zero if a hard
# requirement is missing. Nothing here installs or modifies anything.
set -u

fail=0
ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  warn  %s\n' "$*"; }
bad()  { printf '  FAIL  %s\n' "$*"; fail=1; }

echo "toolchains"
command -v cargo >/dev/null && ok "cargo $(cargo --version | cut -d' ' -f2)" || bad "cargo missing"
command -v rustup >/dev/null && ok "rustup present" || bad "rustup missing (RSP pins channel 1.94.0)"
if command -v cargo-prove >/dev/null; then
  ok "cargo-prove $(cargo prove --version 2>/dev/null | head -1)"
else
  warn "cargo-prove missing; setup.sh installs SP1 toolchain 6.8.0 via sp1up"
fi
command -v docker >/dev/null && ok "docker $(docker --version | cut -d' ' -f3 | tr -d ,)" || bad "docker missing (needed for rsp-tests offline RPC)"
docker compose version >/dev/null 2>&1 && ok "docker compose available" || bad "docker compose missing"
command -v git >/dev/null && ok "git present" || bad "git missing"

echo "resources"
mem_gb=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
if [ "$mem_gb" -ge 64 ]; then ok "${mem_gb} GB RAM"; else warn "${mem_gb} GB RAM: local CPU proving infeasible; use SP1_PROVER=network or a GPU host"; fi
workdir="${RSP_WORKDIR:-$HOME/rsp-baseline}"
free_gb=$(df -g "$(dirname "$workdir")" 2>/dev/null | awk 'NR==2{print $4}')
if [ "${free_gb:-0}" -ge 20 ]; then ok "${free_gb} GB free at $(dirname "$workdir")"; else bad "${free_gb:-?} GB free at $(dirname "$workdir"); need 20 GB for the RSP build (set RSP_WORKDIR)"; fi

echo "credentials"
if [ -n "${NETWORK_PRIVATE_KEY:-}" ]; then ok "NETWORK_PRIVATE_KEY set (prover network)"; else warn "NETWORK_PRIVATE_KEY unset; proving via network not possible yet"; fi
if [ -n "${RPC_1:-}" ] || [ -n "${RPC_URL:-}" ]; then ok "archive RPC configured"; else warn "no RPC_1/RPC_URL; only rsp-tests offline blocks (18884864, 20600000) are usable"; fi
if [ -n "${RPC_421614:-}" ]; then ok "Arbitrum Sepolia RPC set"; else warn "RPC_421614 unset; needed later for verifier check"; fi

echo "pins"
pins="$(dirname "$0")/pins.json"
python3 - "$pins" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
missing = [k for k in ("proverBackend",) if p["sp1"].get(k) is None]
missing += [f"hardware.{k}" for k, v in p["hardware"].items() if v is None]
print("  warn  unresolved pins: " + ", ".join(missing) if missing else "  ok    all hard pins resolved")
PY

exit $fail
