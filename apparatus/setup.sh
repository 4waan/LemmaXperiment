#!/usr/bin/env bash
# Installs the SP1 toolchain at the pinned version, clones RSP and rsp-tests
# at their pinned commits, and builds the RSP host. Idempotent.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
pins="$here/pins.json"
workdir="${RSP_WORKDIR:-$HOME/rsp-baseline}"

rsp_commit=$(python3 -c "import json;print(json.load(open('$pins'))['rsp']['commit'])")
tests_commit=$(python3 -c "import json;print(json.load(open('$pins'))['fixtures']['rspTests']['commit'])")
sp1_ver=$(python3 -c "import json;print(json.load(open('$pins'))['sp1']['cargoProveToolchain'])")

mkdir -p "$workdir"
echo "workdir: $workdir"

# 1. SP1 toolchain (cargo-prove + succinct rust toolchain)
if ! command -v cargo-prove >/dev/null 2>&1; then
  echo "installing sp1up"
  curl -L https://sp1up.succinct.xyz | bash
  export PATH="$HOME/.sp1/bin:$PATH"
fi
echo "installing SP1 toolchain $sp1_ver"
"$HOME/.sp1/bin/sp1up" --version "v$sp1_ver"
cargo prove --version

# 2. RSP at pinned commit
if [ ! -d "$workdir/rsp/.git" ]; then
  git clone https://github.com/succinctlabs/rsp "$workdir/rsp"
fi
git -C "$workdir/rsp" fetch --quiet origin
git -C "$workdir/rsp" checkout --quiet "$rsp_commit"
echo "rsp at $(git -C "$workdir/rsp" rev-parse HEAD)"

# 3. rsp-tests offline RPC cache at pinned commit
if [ ! -d "$workdir/rsp-tests/.git" ]; then
  git clone --depth 1 https://github.com/succinctlabs/rsp-tests "$workdir/rsp-tests"
fi
git -C "$workdir/rsp-tests" fetch --quiet --depth 1 origin "$tests_commit" || true
git -C "$workdir/rsp-tests" checkout --quiet "$tests_commit" || echo "warn: could not check out pinned rsp-tests commit"

# 4. Build host (this also builds the client ELF via build.rs)
echo "building rsp host (long)"
( cd "$workdir/rsp" && cargo build --release --bin rsp 2>&1 | tail -5 )

# 5. Record what was actually built
{
  echo "built_at: $(date -u +%FT%TZ)"
  echo "rsp_commit: $(git -C "$workdir/rsp" rev-parse HEAD)"
  echo "rsp_tests_commit: $(git -C "$workdir/rsp-tests" rev-parse HEAD)"
  echo "cargo_prove: $(cargo prove --version 2>&1 | head -1)"
  echo "rustc: $(cd "$workdir/rsp" && rustc --version)"
  echo "host_binary: $workdir/rsp/target/release/rsp"
  echo "host_sha256: $(shasum -a 256 "$workdir/rsp/target/release/rsp" | cut -d' ' -f1)"
} | tee "$here/build-record.txt"

echo
echo "next: (cd $workdir/rsp-tests && docker compose up -d) then ./baseline.sh 18884864 execute"
