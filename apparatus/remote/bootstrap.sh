#!/usr/bin/env bash
# Bootstrap the rented Linux GPU prover host. Run as a sudo-capable user on
# Ubuntu 22.04 x86_64. Idempotent. Mirrors setup.sh but for the prover host.
set -euo pipefail

RSP_COMMIT="${RSP_COMMIT:-2013b56184f9770bd12d1027495eebd1a0b81745}"
SP1_VER="${SP1_VER:-6.8.0}"
WORK="${RSP_WORKDIR:-/work/apparatus}"

echo "== host"
uname -a; nproc; free -g | head -2; df -h / | tail -1
if [ "${SKIP_GPU:-0}" = 1 ]; then echo "SKIP_GPU=1: execution-only host"; else nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || { echo "no NVIDIA GPU visible (set SKIP_GPU=1 for an execution-only host)"; exit 1; }; fi

echo "== packages"
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential pkg-config libssl-dev clang cmake git curl jq python3 >/dev/null

echo "== docker + nvidia toolkit (needed for Groth16 wrapper and cuda prover)"
if [ "${SKIP_GPU:-0}" = 1 ]; then echo "skipped"; elif ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi
if [ "${SKIP_GPU:-0}" != 1 ] && ! dpkg -l | grep -q nvidia-container-toolkit; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -sL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
  sudo apt-get update -qq && sudo apt-get install -y -qq nvidia-container-toolkit >/dev/null
  sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
fi

echo "== go (for native-gnark Groth16 wrap on arm64)"
command -v go >/dev/null || sudo apt-get install -y -qq golang-go >/dev/null
go version

echo "== rust"
command -v rustup >/dev/null || { curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y; }
. "$HOME/.cargo/env"

echo "== sp1 toolchain $SP1_VER"
[ -x "$HOME/.sp1/bin/sp1up" ] || curl -L https://sp1up.succinct.xyz | bash
export PATH="$HOME/.sp1/bin:$PATH"
sp1up --version "v$SP1_VER"
cargo prove --version

echo "== rsp at $RSP_COMMIT"
sudo mkdir -p "$WORK" && sudo chown "$USER" "$WORK"
[ -d "$WORK/rsp/.git" ] || git clone https://github.com/succinctlabs/rsp "$WORK/rsp"
git -C "$WORK/rsp" fetch -q origin && git -C "$WORK/rsp" checkout -q "$RSP_COMMIT"
( cd "$WORK/rsp" && cargo build --release --bin rsp 2>&1 | tail -3 )

{
  echo "built_at: $(date -u +%FT%TZ)"
  echo "host: $(hostname) $(uname -m)"
  echo "cpu: $(nproc)x $(lscpu | awk -F: '/Model name/{print $2}' | xargs)"
  echo "ram_gb: $(free -g | awk '/Mem/{print $2}')"
  echo "gpu: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo none)"
  echo "rsp_commit: $(git -C "$WORK/rsp" rev-parse HEAD)"
  echo "cargo_prove: $(cargo prove --version 2>&1 | head -1)"
  echo "rustc: $(cd "$WORK/rsp" && rustc --version)"
  echo "host_sha256: $(sha256sum "$WORK/rsp/target/release/rsp" | cut -d' ' -f1)"
} | tee "$WORK/build-record.txt"

echo
echo "next: export RPC_1=<alchemy mainnet archive url>; ./baseline.sh 18884864 execute"
