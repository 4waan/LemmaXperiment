# Setup plan: working around the operator laptop

Written 2026-09-15 after preflight. Decisions here feed `pins.json` and
`demand/spec.json`.

## The constraint

The laptop (M2, 8 GB RAM, 26 GB free, no Docker daemon) cannot build RSP
comfortably, cannot prove a block, and cannot host the evaluator. Every
proof-related step therefore moves to one rented Linux GPU machine. The
laptop keeps orchestration, contracts, Lean and the report.

## Split of work

| Where | What runs there |
| --- | --- |
| Laptop | contracts (Foundry), Lean, agent runner orchestration, demand and evaluation authoring, results |
| GPU box, "prover host" | RSP build, block execution, Compressed proving, Groth16 wrapping, the evaluator image, the reuse job |
| Alchemy | archive RPC for mainnet (witness fetch), Arbitrum Sepolia RPC |
| Arbitrum Sepolia | CreationBounty, ModuleRegistry, UsageEscrow, SP1 verifier gateway |

## Prover backend decision

Recommended: `SP1_PROVER=cuda` on the rented box.

- The Succinct Prover Network needs PROVE tokens on Ethereum mainnet, and its
  latency includes queueing, which is useless as an A/B timing signal.
- A fixed GPU box gives identical hardware for every paired run, which the
  evaluation policy requires.
- SP1 minimums: Linux x86_64, NVIDIA GPU with compute capability 8.0 or
  higher, 24 GB VRAM, CUDA 12, 16 GB or more RAM for Core/Compress, about
  14 GB extra for Groth16 wrapping. Docker is needed for the Groth16 wrapper.

Target box: 1x A100 40 GB or L40S or RTX 4090 class, 16 or more vCPU, 64 GB
RAM, 300 GB SSD, Ubuntu 22.04, Docker with NVIDIA container toolkit. Providers
in that shape: Lambda, RunPod, Vast, AWS g5/g6, GCP a2. Expect one to three
dollars per hour. Keep the exact instance type as `hardware.provingHost`.

Fallback: network proving for the one baseline proof and the reuse proof only,
never for timing. Requires PROVE deposit; record cost if used.

## Measurement design that fits this hardware

Two metrics, both in `evaluation/policy.json`:

1. **Guest cycle count** from `report.csv`. Deterministic, hardware
   independent, runnable on the laptop in execute mode. This is the
   diagnostic signal the creator agent iterates against.
2. **Wall-clock preparation, proving and wrapping latency** on the pinned GPU
   box. This is the funded metric. Only the evaluator measures it, on holdout
   blocks, in randomized paired A/B order.

Cycle savings that do not appear as wall-clock savings are reported as Narrow.

## RPC and fixtures

With an Alchemy mainnet archive endpoint, `rsp --cache-dir` writes the client
input after the first fetch and later runs are offline. The rsp-tests Docker
cache is then optional, so Docker is not needed on the laptop at all.

Development blocks: 18884864, 20600000 (both already validated by rsp-tests)
plus one recent post-Prague block chosen during setup. Holdout: ten
consecutive blocks selected by salt, fetched once by the evaluator into its
own cache directory, hashed, and never copied to the creator workspace.

## Evaluator isolation on one box

Hackathon-grade isolation, disclosed in the report:

- Creator agent runs first under user `creator`, workspace `/work/creator`.
- Holdout witness cache lives under user `evaluator` at `/work/evaluator`,
  mode 700, fetched only after the creator's final submission is recorded.
- The evaluator's signing key is never on the box. The evaluator report is
  signed on the laptop after the box produces the raw evidence and its hash.
- Between creation and evaluation, snapshot and hash the creator workspace,
  then run the frozen evaluator image.

A second box for the evaluator is better and can be added if budget allows.

## On-chain pieces (Arbitrum Sepolia, chain 421614)

SP1 verifier gateway (Groth16): `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B`
Latest listed Groth16 verifier: V6.1.0 at `0xb69f2584CBcFf99a58C4e7002E8b89Af54a6f4e2`

To confirm during setup: which verifier version SP1 SDK 6.8.0 proofs target
(the gateway routes by the proof's version selector). If 6.8.0 needs a
verifier not yet deployed there, deploy the matching one from sp1-contracts.

Groth16 is required for on-chain verification, so `baseline.sh prove` uses
Compressed for timing, and the reuse job adds a Groth16 wrap step. Both are
timed separately.

Wallets, all generated fresh, all testnet:

| Role | Purpose |
| --- | --- |
| sponsor | deploys contracts, funds bounty and usage escrow |
| creator payee | receives bounty and usage fee |
| evaluator signer | signs verdicts, key held off the prover box |
| worker | runs the reuse job, receives worker compensation |

## Order of operations

1. Credentials and box provisioned (user).
2. `remote/bootstrap.sh` on the box: toolchains, RSP at pin, build, CUDA check.
3. `baseline.sh 18884864 execute` on the box, then `prove` with cuda.
4. Groth16 wrap of that proof, verify against the gateway on Arbitrum Sepolia
   with `cast call`. This closes apparatus step 1.
5. Interface survey (step 2), fixtures (step 3), holdout commitment (step 4).

## Revision 2: no GPU box (2026-09-15)

A rented GPU is out of budget. This section replaces the prover-backend
decision above. The rest of the plan stands.

### What actually needs a real proof

Only three things: the one baseline proof that closes apparatus step 1, the
candidate's proof during evaluation (shows the modified guest still proves and
verifies), and the reuse job's proof that settles UsageEscrow. The 60-run
wall-clock benchmark is the only GPU-sized workload, and it is replaced below.

### Funded metric becomes prover gas units (PGU)

SP1's executor reports cycles and PGU for a run without proving. PGU is
deterministic for a given guest ELF and input, hardware independent, and it is
exactly what the Succinct Prover Network bills: `0.2 PROVE base + up to
2 PROVE per billion PGU` at time of writing. So a PGU reduction is a priced
cost reduction, which is what the buyer is paying for.

Changes to `evaluation/policy.json`:

- primary metric: median PGU per holdout block, candidate vs upstream, at
  least 5 percent lower, paired bootstrap interval over blocks above zero
- per-block regression cap: 10 percent PGU
- secondary, reported not gated: total cycles, per-phase cycle breakdown
  from `report.csv`, host preparation wall time on the execution host
- proving wall time: reported only for the three real proofs, labeled as
  network latency, never used as a gate

Ten holdout blocks, one execute per variant per block, because the metric
is deterministic. Repeat once to confirm identical output. This is 20
executions instead of 60 proofs.

Disclosed limitation: PGU predicts proving cost, not measured proving wall
time on a fixed machine. The report must say the latency claim is modeled.

### Real proofs go through the Succinct Prover Network

Request the three proofs in Groth16 mode directly so no local Docker wrap is
needed, and they verify against the gateway on Arbitrum Sepolia as is.

Cost per Ethereum block proof: base fee plus PGU price. A mainnet block is
on the order of a few hundred million to a few billion PGU, so expect a few
PROVE per proof. Fund the requester account with enough PROVE for about five
proofs to leave room for one retry. Record every request id, PGU, price and
proof latency in `apparatus/runs/`.

If even that is out of reach, ask the hackathon organizers or Succinct for
credits before building anything else; without one real verified proof the
experiment cannot pass its own gate and must be reported as Inconclusive.

### Free execution hosts

Building RSP and running execute mode needs about 16 GB RAM and 20 GB disk,
not a GPU. Options in order of preference:

1. **Oracle Cloud Always Free** ARM VM: 4 cores, 24 GB RAM, 200 GB disk, no
   charge. SP1 supports Linux aarch64 for execution. This also becomes the
   evaluator host, separate from the laptop.
2. **GitHub Actions** free runners: 4 vCPU, 16 GB RAM, 14 GB disk. Enough for
   execute mode if the RSP build is cached; disk is tight. Useful as the
   evaluator harness because the workflow file is the frozen policy.
3. **The laptop**, after freeing 15 GB: `cargo build -j2`, slow, swaps, but
   works. Use only for the interface survey if 1 and 2 are unavailable.

Creator workspace and evaluator host should differ. Laptop as creator plus
Oracle VM as evaluator is the cheapest arrangement that keeps them apart.

### Revised pins

- `sp1.proverBackend`: `network` (Groth16 requests), three proofs total
- `hardware.executionHost`: the Oracle VM shape, or the laptop, whichever
  runs the evaluator executes
- `hardware.provingHost`: "Succinct Prover Network, not fixed hardware"

### Revised order of operations

1. Alchemy keys, four testnet wallets, one Oracle Always Free VM (user).
2. `remote/bootstrap.sh` on the VM with `SKIP_GPU=1`; build RSP at the pin.
3. `baseline.sh 18884864 execute` on the VM: cycles, PGU, report.csv.
4. Fund a network requester account with PROVE (user). Request one Groth16
   proof of that block; verify it with `cast call` against the gateway.
   Apparatus step 1 closes here.
5. Interface survey, fixtures, holdout commitment.

## Revision 3: no PROVE spend either (2026-09-15)

The network requester account cannot be funded. Real proofs move to the
Oracle Always Free ARM VM using SP1's CPU prover. Slow, but free, and the
proof is real. PGU stays the funded metric (revision 2).

### Facts checked

- `cargo_prove_v6.8.0_linux_arm64` exists; SP1 6.8.0 builds and proves on
  aarch64 Linux. CPU Core/Compress wants 16 GB or more; the VM has 24 GB.
- SDK 6.8.0 uses circuit `v6.1.0`. The `V6_1_0_SP1_VERIFIER_GROTH16` is
  deployed on Arbitrum Sepolia at `0xb69f2584CBcFf99a58C4e7002E8b89Af54a6f4e2`
  and the gateway `0x397A5f7f...` routes to it. No verifier deployment needed.
- The Groth16 wrapper image `ghcr.io/succinctlabs/sp1-gnark:v6.1.0` is
  linux/amd64 only. On the ARM VM use the `native-gnark` SDK feature (pure Go
  via FFI, needs a Go toolchain). This lives in a separate tiny wrap tool,
  `apparatus/wrap/`, so the pinned RSP host is not modified.
- Archive RPC works: `eth_getProof` on Cancun-era blocks returns data.
- Block sizes (gasUsed): 18884864 is 4.27M / 30 txs, 20600000 is 14.9M /
  187 txs, 20600066 is 0.96M / 27 txs. Latest mainnet block ~25.98M.

### Proof cost plan on 4 ARM cores

Proving time scales with cycles, and cycles scale with gas plus a fixed
witness-verification overhead. Real proofs use small blocks:

| Proof | Block | Why |
| --- | --- | --- |
| baseline (apparatus step 1) | 18884864 | rsp-tests validated, 4.27M gas |
| candidate at evaluation | one holdout block under 5M gas | shows the modified guest still proves |
| reuse job | 20600066 or similar under 2M gas | outside dev and holdout sets |

Expect hours per Compressed proof, not minutes. Run each under `nohup`, log
wall time, and never claim a proving latency number from these runs as a
benchmark. The PGU metric does not need any of them.

Fork scope: Cancun-era blocks are validated by rsp-tests. Whether the pinned
RSP client executes Prague and later blocks is checked in the interface
survey; until then, development and holdout ranges stay pre-Prague and the
`workloadRelation` in the demand says so.

### Revised pins

- `sp1.proverBackend`: `cpu` on the ARM VM, `native-gnark` for the wrap
- `hardware.provingHost`: the Oracle VM shape, same as the execution host
- `verifier.sp1VerifierVersion`: `v6.1.0`, resolved

### Revised order of operations

1. Oracle VM reachable; wallets funded from a faucet (user).
2. `remote/bootstrap.sh` with `SKIP_GPU=1` on the VM. Adds Go for native-gnark.
3. `baseline.sh 18884864 execute` on the VM: cycles, PGU, report.csv.
4. `baseline.sh 18884864 prove` with `SP1_PROVER=cpu` under nohup. Hours.
5. Wrap to Groth16 with `apparatus/wrap/`, verify with `cast call` against
   the gateway. Apparatus step 1 closes here.
6. Interface survey, fixtures, holdout commitment.

## Revision 4: GitHub Actions free runners (2026-09-15)

Oracle's A1 shape is capped at 1 OCPU / 6 GB on the new tenancy. Decision:
all execution and proving runs on GitHub-hosted runners (ubuntu-24.04,
4 vCPU, 16 GB RAM, x86_64), from a public repository for unlimited minutes.

### How it works

| Workflow | Does | Limits |
| --- | --- | --- |
| `apparatus-build` | clones RSP at the pin, injects `lemma-prove`, builds both, uploads binaries as a 90 day artifact | runs once per pin change |
| `apparatus-execute` | one block in execute mode: cycles, PGU, report.csv, stdin dump | minutes per block |
| `apparatus-prove` | CPU proof of one small block, compressed or groth16 | 6 hour job cap |

`lemma-prove` (`apparatus/prover/`) exists because the upstream CLI discards
proof bytes and hides `--stdin-dir`. It is built inside the pinned workspace
so every dependency version matches upstream exactly; the build record names
the workspace edit.

### What this changes about the experiment

- Execution host is a shared runner. PGU and cycles are unaffected (they are
  deterministic); host wall times are noisy and reported only as context.
- The 6 hour cap means real proofs must be of small blocks. If a compressed
  proof of 18884864 does not fit, use a block under 2M gas (20600066).
- Groth16 wrapping needs about 14 GB RAM and the amd64 gnark Docker image;
  the runner has 16 GB. It may fit; if not, the fallback is to submit the
  compressed proof's public values with a mock verifier on testnet and label
  the on-chain step as mechanics only.
- Evaluator separation: the evaluator harness is a separate workflow file
  whose hash is the evaluation policy hash; runs are logged by GitHub with
  the commit they ran at. Holdout witnesses are fetched inside the evaluator
  job from RPC using the salted rule, never committed to the repository.
- The `RPC_1` secret is the only credential the runners hold. No wallet keys
  ever go into GitHub secrets.

### Existing capability found during setup

The pinned RSP has an `arena` feature: an alternative, unaudited arena-based
MPT backend for the witness path, forwarded to the guest. The registry
snapshot must list it so the creator agent can weigh reuse or composition
against creating something new.
