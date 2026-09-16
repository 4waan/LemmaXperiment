# apparatus/

Owner: operator. EXPERIMENT.md section 4, steps 1 to 4: reproduce a real
baseline block proof and pin source, dependencies, toolchain, proof mode and
hardware; identify the permitted witness-processing interfaces without
implementing anything; prepare three public development blocks and
independent correctness fixtures; freeze and commit the holdout selection
(the sealed material itself belongs to the evaluator, `evaluation/holdout/`).

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
| `fork_windows.py` | step 3: one fork-support check block per era by a fixed rule (window, lower median gasUsed) |
| `runs/` | one directory per run: command, env, report.csv, timings; `fixtures-<id>/` for harness runs |

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
- It does not touch the holdout blocks. Step 4 sealed them
  (`evaluation/holdout/`); no apparatus run executes them before the final
  evaluation, so nothing under `runs/` or in the public workflow logs can
  reveal them.

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
  gas) for block 20600066 within the run-to-run jitter documented in
  `INTERFACES.md` section 7, with the same vkey and guest ELF hash, and the
  phase columns plus the untracked remainder sum to the total.
- The registry snapshot has the `arena` feature as its seeded
  existing-capability entry (filled at step 5 with the rest of the snapshot).

Status: **closed 2026-09-16** except the registry entry, which belongs to
step 5. Runs 35060320613, 35060327373 and 35060335177 under `runs/`.

## Step 3: development blocks and correctness fixtures

Deliverables live under `evaluation/fixtures/` (see its README):
`development-corpus.json` with the three client inputs committed under
`blocks/1/`, and `trie/fixtures.json` with its generator and the
`evaluation/harness/` runner. `apparatus-execute` gained
`input_source=fixture` (offline, no RPC credential, sha256 checked against
the manifest) and now keeps the executed client input in every artifact.

Fork support was checked with one block per era, chosen by
`fork_windows.py` (records in `pins.json` `fixtures.forkSupport`):

| era | block | gasUsed | result |
| --- | --- | ---: | --- |
| Prague | 22441128 | 16,850,044 | pass, 336.7M cycles (run 35078553836) |
| Osaka | 23945771 | 28,167,520 | pass, 388.4M cycles (run 35078560969); development block 3 |
| BPO1 | 23985839 | 24,099,656 | provider rate limit, not retried (`FAILURES.md` #9) |
| BPO2 | 25988980 | 27,674,793 | fail: host gas mismatch on EIP-7702 authorizations of nonexistent authorities (`FAILURES.md` #10) |
| BPO2, no type 4 | 25988970 | 2,952,836 | pass, 63.1M cycles (run 35081362097) |

The pinned host's `proofs` backend loads every address as an existing
account, so revm grants the 12,500 gas EIP-7702 refund the chain does not
for authorities absent from the parent state, and the host rejects the block
before the guest runs. Current-era blocks almost all carry such
transactions (110 of 120 sampled carry type 4 transactions), so the
supported range for the holdout is the Cancun era, blocks 19426587 to
22431083. The pin stays unpatched.

Gate to step 4 (holdout selection rule, commitment, salt):

- `evaluation/fixtures/development-corpus.json` lists three blocks with
  committed client inputs; each executes offline through
  `input_source=fixture` and reaches the manifest's `stateRoot`.
- `evaluation/fixtures/trie/fixtures.json` regenerates byte-identical from
  the py-trie oracle in CI, and the harness passes it on both upstream
  backends (`pointer` and `arena`): run 35081286192, 31/31 each.
- The supported block range is recorded in `pins.json` and
  `demand/spec.json` before any holdout salt is drawn.

Status: **closed 2026-09-16**; offline corpus executions in runs
35081865737 and 35081874073.

## Step 4: holdout selection rule, commitment and salt

Deliverables live under `evaluation/holdout/`: `RULE.md` (frozen rule:
ten consecutive Cancun-era blocks, exclusion margin around every executed
block, salted start), `holdout.py` (precommit, seal, derive, verify) and
`commitment.json`. Two phases, both pushed to the public repository:

| phase | when | what became public |
| --- | --- | --- |
| precommit | commit 2a537e4, run 35106575645 at 14:09:17Z | sha256 of the preSalt, beacon block 25990577, rule and script hashes; the run logged chain head 25990539, 38 blocks before the beacon |
| sealed | `commitment.json` phase `sealed`, 2026-09-16T14:34:42Z | sha256 of the sealed manifest (`e60d6ced…`), the beacon hash, the evaluator signature |

The salt is `sha256(preSalt || hash of block 25990577)`, so it could not be
chosen after the rule was public: the preSalt was fixed by its published
hash before the beacon block existed, and the beacon hash was read only
after finality. The sealed manifest (ten headers agreed by two providers,
preSalt, salt, derivation trace) and the preSalt live in the evaluator
directory on the operator laptop, outside the repository and the future
creator workspace, and in no GitHub secret.

Not done in this step, by choice: no executability pre-check of the sealed
blocks. Running them through `apparatus-execute` would print them in public
logs, and the laptop cannot build the host. The rule's era is the one the
pinned host reproduces in full (step 3), witness generation happens at
evaluation time, and any failure is retained rather than replaced.

Gate to step 5 (evaluator image, metrics, formal scope, limits):

- `demand/spec.json` `sealedHoldoutCommitment` equals
  `evaluation/holdout/commitment.json` `sealed.commitment`, and the
  precommit run logged a chain head below the beacon block.
- The sealed manifest's sha256 equals the commitment (checked at seal time;
  re-checkable by the evaluator with `sha256sum`).
- The exclusion set in `RULE.md` covers every block listed in
  `pins.json` `fixtures.blockGasUsed` and the development corpus.

Status: **closed 2026-09-16**.
