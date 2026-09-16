# apparatus/

Owner: operator. EXPERIMENT.md section 4, steps 1 and 2: reproduce a real
baseline block proof and pin source, dependencies, toolchain, proof mode and
hardware; then identify the permitted witness-processing interfaces without
implementing anything.

Nothing downstream can start until this stage produces a verified proof of a
real block with the pinned configuration. If it cannot, record the blocker in
`results/report.md`. A simulated or mock proof does not satisfy this stage.

## Files

| File | Purpose |
| --- | --- |
| `pins.json` | every version, commit, backend and host that the experiment fixes |
| `INTERFACES.md` | step 2: where witness processing happens in the pinned RSP, the `StateTries` seam, the two host backends, what is frozen, proposed `allowedSourcePaths`, measured cycle share per phase |
| `FAILURES.md` | every failed run with cause and fix |
| `SETUP_PLAN.md` | how the compute problem was worked around, revision by revision |
| `prover/` | `lemma-prove` and `lemma-wrap`, the thin wrappers the workflows run; two build variants |
| `environment.md` | what the operator machine is and what it cannot do |
| `preflight.sh` | read-only checks: tools, disk, RPC, prover credentials |
| `setup.sh` | installs the SP1 toolchain, clones RSP at the pin, builds the host |
| `baseline.sh` | executes, then optionally proves, one block and records the report |
| `runs/` | one directory per baseline run: command, env, report.csv, timings |

## Procedure

1. `./preflight.sh` and fix anything it flags.
2. `./setup.sh` (long; builds reth and revm). Set `RSP_WORKDIR` to a volume
   with 20 GB free.
3. Bring up the offline RPC cache: `docker compose up -d` inside the
   `rsp-tests` clone that `setup.sh` creates.
4. Execute only, offline: `./baseline.sh 18884864 execute`. This confirms the
   host, client ELF and fixtures work and writes the cycle report.
5. Choose the prover backend, record it in `pins.json`, then prove:
   `SP1_PROVER=network NETWORK_PRIVATE_KEY=... ./baseline.sh 18884864 prove`.
6. Verify the proof against the derived verifying key (baseline.sh records
   the vkey; the on-chain check happens in the contracts stage).
7. Fill in `hardware.provingHost`, `sp1.proverBackend` and the archive RPC
   provider in `pins.json`. Copy the pins into `demand/spec.json`.

## What this stage explicitly does not do

- It does not implement or prototype any optimization.
- It does not choose between `proofs` and `execution-witness` for the agent;
  both backends are recorded as permitted insertion candidates for step 2.
- It does not select holdout blocks. That is step 4 and needs a committed
  salt stored away from the creator.

## Gate to step 2 (interface survey)

Status: **closed 2026-09-16**. See `SETUP_PLAN.md` outcome and `runs/`.

- One real Compressed proof of a mainnet block verifies with the derived vkey.
- `pins.json` has no `null` values in `rsp`, `sp1` and `hardware`.
- A `runs/<id>/` directory holds the exact command, environment, report.csv
  and wall-clock phase timings for that proof.

## Step 2: interface survey

`INTERFACES.md` is the deliverable. It was written from the pinned source,
not from upstream docs, and it implements nothing. Alongside it, the
`cycle-tracking` build variant (see `prover/README.md`) makes the per-phase
cycle columns of `report.csv` real; the standard build leaves them at 0
because SP1 6.8.0 only parses the guest's cycle-tracker labels under its
`profiling` feature.

Gate to step 3 (development blocks and correctness fixtures):

- `INTERFACES.md` names the seam, the frozen parts and proposed
  `allowedSourcePaths`, and `demand/spec.json` carries the proposal.
- The cycle-tracking build reproduces the step 1 totals (cycles and prover
  gas) for block 20600066 with the same vkey, and the phase columns sum to
  the total within the untracked remainder.
- The registry snapshot has the `arena` feature as its seeded
  existing-capability entry (filled at step 5 with the rest of the snapshot).
