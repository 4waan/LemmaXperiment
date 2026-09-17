# Operator environment record

Recorded 2026-09-15 on the operator laptop. This is not the pinned proving
hardware; it is the machine used to prepare the apparatus.

| Item | Value |
| --- | --- |
| CPU | Apple M2, 8 cores |
| RAM | 8 GB |
| Free disk | about 26 GB of 228 GB |
| rustc / cargo | 1.97.1 (RSP pins channel 1.94.0; rustup will fetch it) |
| cargo-prove (SP1 toolchain) | missing, install 6.8.0 via sp1up |
| docker | 29.8.0 CLI only; no compose plugin, no daemon running, no Docker Desktop in /Applications |
| forge | 1.5.1 |
| lean / lake | Lean 4.34.0 via elan |
| archive RPC key | none found in environment |

## Consequences

0. `docker compose` is unavailable, so the rsp-tests offline RPC cache cannot
   start yet. Install Docker Desktop (or colima plus the compose plugin) or
   skip the offline cache and use an archive RPC for development blocks.

1. Local CPU proving of an Ethereum block is not feasible on this machine.
   The pinned prover backend must be `network` (Succinct Prover Network, needs
   `NETWORK_PRIVATE_KEY`) or `cuda` on a rented GPU host. Decide and record in
   `pins.json` before funding.
2. Execution without proving (`rsp --block-number N --rpc-url ...`) is feasible
   here and is enough for the interface survey and public fixture preparation.
3. Building the RSP host pulls reth and revm. Expect 10 to 20 GB of `target/`
   output. Disk is at 87 percent; build on an external volume or clear space
   before running `setup.sh`.
4. The two rsp-tests blocks give offline development fixtures without an
   archive RPC. The third development block and all ten holdout blocks need a
   real archive endpoint (Alchemy recommended by RSP; QuickNode reported broken
   for `eth_getProof` on old blocks).

## Preflight result, 2026-09-15

```text
FAIL  docker compose missing
warn  cargo-prove missing (setup.sh installs 6.8.0)
warn  8 GB RAM: local CPU proving infeasible
warn  NETWORK_PRIVATE_KEY unset
warn  no RPC_1/RPC_URL
warn  RPC_421614 unset
warn  unresolved pins: proverBackend, hardware.executionHost, hardware.provingHost
```

## Environment variables the scripts read

Names only; values live in the gitignored `.env` on the laptop and, for the
archive endpoint, in the repository secret `RPC_1`: `RPC_1`, `RPC_421614`,
`SP1_PROVER`, `SPONSOR_PRIVATE_KEY`, `EVALUATOR_PRIVATE_KEY`,
`CREATOR_PAYEE_PRIVATE_KEY`, `CREATOR_PAYEE_ADDRESS`, `WORKER_PRIVATE_KEY`.
The evaluator key never leaves the laptop.
