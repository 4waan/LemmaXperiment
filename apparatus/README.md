# apparatus/

Owner: operator. EXPERIMENT.md section 4, steps 1 to 5: reproduce a real
baseline block proof and pin source, dependencies, toolchain, proof mode and
hardware; identify the permitted witness-processing interfaces without
implementing anything; prepare three public development blocks and
independent correctness fixtures; freeze and commit the holdout selection
(the sealed material itself belongs to the evaluator, `evaluation/holdout/`);
freeze the evaluator image, metrics, formal scope, limits and thresholds
(`evaluation/policy.json`) and measure the existing capability; estimate
proof-run costs and fix the agent, compute and evaluation budgets
(`demand/budget.json`).

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
| `prover/` | `lemma-prove` and `lemma-wrap`, the thin wrappers the workflows run; three build variants (standard, cycle-tracking, arena) and stdin replay |
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

## Step 5: evaluator image, metrics, formal scope, limits

Deliverable: `evaluation/policy.json` version 1.0, hashed into
`demand/spec.json` (`evaluationPolicyHash` `b369e567…`,
`correctnessPolicyHash` `a591d7a7…`, `formalScopePolicyHash` `840e425e…`,
keccak256 over canonical JSON; `evaluation/freeze.py --check` and the
`evaluation-policy` workflow guard them). What was wired and measured:

| piece | where | evidence |
| --- | --- | --- |
| evaluator image | `policy.json` `evaluatorImage`: 25 files tree-hashed (`b0cee076…`), binaries by sha256, runner statement | builds 35120130617 and 35122594072 byte-identical for all three variants |
| candidate build | `apparatus-build.yml` `overlay_ref` + `variant`; `evaluation/overlay.py` enforces `allowedSourcePaths`; `build_run` on execute | overlay tool tested on a synthetic overlay with one denied path |
| counterfactual C | `arena` variant of `lemma-prove` (upstream feature, forwarded to the guest) | 20.8% to 28.5% PGU below A on the corpus (`INTERFACES.md` section 8, `demand/registry-snapshot.json`) |
| determinism | `lemma-prove --stdin-file`, `apparatus-execute` `input_source=replay` | identical cycles and PGU on replay for arena and standard (runs 35122892653, 35124461684) |
| metric and rule | `policy.json` `performance`; `evaluation/analysis/paired.py` | self-test: ten blocks, two regressions still pass, three fail; 4.9% median fails |
| formal scope | `policy.json` `formal`; `evaluation-formal.yml`; `evaluation/analysis/axioms.py`; `evaluation/formal-smoke` | run 35122594002 pass; local negative test rejects sorryAx and native_decide |
| limits | `policy.json` `performance.limits`, `reproduction`; `demand/spec.json` `resourceLimits` | build 21 min; execute 82 to 549 s; peak RSS 7.5 to 8.8 GB on every run |
| registry snapshot | `demand/registry-snapshot.json` | arena entry with measurements, control requests A1 (reuse) and A3 (decline) |

Gate to step 6 (cost estimate, agent and evaluation budgets):

- `evaluation-policy` passes on `main` (hashes match, self-test runs,
  policy consistent with pins, smoke toolchain and holdout commitment).
- `demand/spec.json` carries the three policy hashes, `baselineCommit`,
  `dependencyLockHash`, `toolchainManifestHash`, `resourceLimits` and
  `candidateBundle`; remaining nulls are budgets, deadlines, parties and
  the settlement addresses.
- The counterfactual is registered with measured numbers and both control
  requests are written.

Status: **closed 2026-09-16**.

## Step 6: proof-run costs and budgets

Deliverable: `demand/budget.json`, carried into `demand/spec.json` 0.4-draft
(`agentBudget`, `computeBudget`, `creationBounty.amount`, `usageFeePolicy`,
`licenseRequirements`, `buyer`, `assignedCreatorPayee`, deadline rules).
Every number names its provenance.

| item | value | basis |
| --- | --- | --- |
| execute from RPC | 83 to 549 s per block | measured, five runs |
| replay or fixture execute | 59 to 127 s (about 80 s SP1 setup) | measured, four runs |
| build | 21 min per variant | measured, two runs |
| compressed proof | 4 h 09 min for 22.6M cycles, about 5.5M cycles per hour; 6 h cap means about 30M cycles | measured, run 35018130745 |
| proof list price | 0.2 PROVE + 2.0 PROVE per bPGU: 0.26 to 1.16 PROVE per corpus block; a 5% gain over the arena saves 0.002 to 0.036 PROVE per job | list price, not bought |
| creator | `claude-opus-5`, 300 USD cap, 400M tokens, 4M output, 3000 turns, 72 h, 3 revisions; scenario 210 USD | price sheet read 2026-09-17 |
| creator compute | 8 builds, 60 executes (corpus only), 6 fixtures, 6 Lean checks, no proofs; about 10 runner hours | free public-repo minutes |
| evaluation | 1 build, 9 corpus runs, 30 witness runs + 30 replays, 2 proofs, 2 wraps, 2 h review; about 20 runner hours, 2 elapsed days | operator-paid, 0 USD |
| deadlines | submitBy = funding + 4 days; evaluateBy = submitBy + 5 days | measured plan plus margin; absolute values at funding |
| sponsor amounts | bounty 0.05, usage fee 0.002 + 0.02, gas reserve 0.01, testnet ETH | nominal, mechanics only |

`evaluation/policy.json` moved to 1.1 for two wording fixes found while
budgeting (a candidate that changes the witness type executes the corpus
from RPC, as the arena does) and a budget pointer; hashes refrozen.

Gate to step 7 (fund the bounty):

- `demand/spec.json` nulls are only `demandId`, `specificationHash`, the
  absolute `submitBy`/`evaluateBy` and the settlement addresses.
- Sponsor and worker wallets funded on Robinhood Chain testnet with bounty,
  fees and gas reserve (`demand/budget.json` `sponsorAmounts`).
- Contracts deployed and verified (`contracts/`), `SP1VerifierGroth16`
  v6.1.0 address recorded; `fundDemand` carries the spec hash, policy hash
  `4d586005…` and holdout commitment `e60d6ced…`.
- The runner (`agent/runner/`) enforces the creator limits in `budget.json`.

Status: **closed 2026-09-17** for the estimate and the budgets; the
absolute deadlines and amounts become final at funding.
