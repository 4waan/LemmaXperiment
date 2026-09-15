# apparatus/

Owner: operator. EXPERIMENT.md section 4, step 1: reproduce a real baseline
block proof and pin source, dependencies, toolchain, proof mode and hardware.

Nothing downstream can start until this stage produces a verified proof of a
real block with the pinned configuration. If it cannot, record the blocker in
`results/report.md`. A simulated or mock proof does not satisfy this stage.

## Files

| File | Purpose |
| --- | --- |
| `pins.json` | every version, commit, backend and host that the experiment fixes |
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

- One real Compressed proof of a mainnet block verifies with the derived vkey.
- `pins.json` has no `null` values in `rsp`, `sp1` and `hardware`.
- A `runs/<id>/` directory holds the exact command, environment, report.csv
  and wall-clock phase timings for that proof.
