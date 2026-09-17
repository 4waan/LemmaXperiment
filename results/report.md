# Experiment 01 results

Status: not started.

## Outcome

One of: Go, Assisted, Reuse, Narrow, Inconclusive, Stop candidate.

Outcome: TBD

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Product feasibility | TBD | |
| Technical value | TBD | |
| Economic feasibility | TBD | |

## Blockers

None. The operator laptop and a zero-budget constraint forced execution and
proving onto GitHub-hosted runners; see `apparatus/SETUP_PLAN.md`.

## Apparatus step 1: baseline proof

| Item | Value |
| --- | --- |
| block | mainnet 20600066 (958,960 gas, 27 txs) |
| pinned RSP | `2013b56`, tag reth-2.2.0-sp1-6.8.0, SP1 6.8.0, circuit v6.1.0 |
| cycles / PGU | 22,629,796 / 28,810,531 |
| vkey | `0x00b22d4bb5487743bd048fde7fdbd7b048b37bc93bafce13610f2d633465bfba` |
| compressed proof | run 35018130745, 4 h 09 min, sha256 `71a22e84…` |
| Groth16 wrap | run 35051478400, 31 min, selector `0x4388a21c` |
| on-chain check | Arbitrum Sepolia gateway `0x397A5f7f…`, verifyProof passes, controls revert |
| assistance | operator-built apparatus; no creator agent involved yet |

## Apparatus step 2: interface survey

`apparatus/INTERFACES.md`. Seam: `rsp_mpt::StateTries` plus the construction
path wired like the upstream `arena` feature; `allowedSourcePaths` and
`integrationInterface` drafted into `demand/spec.json`. The
`execution-witness` host backend is not available on the pinned RPC
provider, so `proofs` is fixed. The `arena` feature is the seeded
existing-capability entry for the registry snapshot.

Per-phase cycles from the `cycle-tracking` build (same guest ELF and vkey as
the standard build; runs 35060320613 and 35060327373):

| phase | 20600066 | 18884864 |
| --- | ---: | ---: |
| deserialize inputs | 30.4% | 22.3% |
| initialize witness db | 23.9% | 19.2% |
| recover senders | 4.9% | 1.6% |
| validate header | 1.1% | 0.4% |
| block execution | 14.3% | 38.5% |
| validate block post-execution | 1.2% | 1.2% |
| compute state root | 15.9% | 11.3% |
| untracked | 8.2% | 5.5% |
| total cycles | 22,628,475 | 89,571,134 |

Witness-only phases: 70.2% and 52.8%. Cycle totals jitter by about 0.01%
across host runs of the same client input (stdin map order); noted in
`evaluation/policy.json`.

## Apparatus step 3: development blocks and fixtures

Development corpus (`evaluation/fixtures/development-corpus.json`, sha256
`0797e833…`): 20600066 (Cancun, 0.96M gas), 18884864 (Shanghai, 4.3M gas),
23945771 (Osaka, 28.2M gas, 388.4M cycles). Client inputs committed and
executed offline.

Trie fixtures: 31 cases from a py-trie oracle (120 lookups, 11 update
batches; inline and hashed nodes with the 31/32-byte boundary, malformed
and noncanonical RLP, absent keys at every divergence point, wrong roots,
missing nodes, forged nodes, updates with branch collapse and boundary
crossings). Upstream pointer backend 31/31, upstream arena backend 31/31
(run 35081286192).

Fork support: Prague and Osaka rules execute. The pinned host rejects any
block with an EIP-7702 authorization of a nonexistent authority (host loads
every address as existing, revm refunds 12,500 gas the chain does not;
`apparatus/FAILURES.md` #10, upstream succinctlabs/rsp#181). Holdout
blocks are drawn from the Cancun era, 19426587 to 22431083.

## Apparatus step 4: holdout commitment

Set 1 sealed 2026-09-16 (`evaluation/holdout/`). Rule frozen first
(`RULE.md`, sha256 `7d8c630c…`): ten consecutive Cancun-era blocks
(19426587 to 22431083), window rejected within 1000 blocks of any executed
block, start = 19426587 + sha256(domain || salt || k) mod 3004488.
Precommit (commit 2a537e4, run 35106575645): preSalt hash and beacon block
25990577 published while the chain head was 25990539. Salt =
sha256(preSalt || hash of the finalized beacon block). Commitment = sha256
of the sealed manifest: `e60d6cedd068915cba662170dc310b4d5f35e227feec35233dd60a71b389b362`, signed by the evaluator key
(EIP-191). Manifest and preSalt stay in the evaluator directory on the
laptop, outside the repository; reveal after the final evaluation is
signed, verifiable with `holdout.py verify`.

No executability pre-check of the sealed blocks (it would print them in
public logs); witnesses are produced at evaluation time and any failure is
retained.

## Apparatus step 5: evaluator image, metrics, formal scope, limits

`evaluation/policy.json` 1.0 frozen 2026-09-16; keccak256 hashes in
`demand/spec.json` (policy `b369e567…`, correctness `a591d7a7…`, formal
`840e425e…`), image tree hash `b0cee076…` over 25 files, guarded by the
`evaluation-policy` workflow. Metric: PGU per holdout block, median paired
improvement of at least 5% with a percentile bootstrap interval above zero
and no block regressing more than 10%; the saving per block is the smaller
of the saving against upstream A and against the upstream arena backend C.
Formal: Lean `leanprover/lean4:v4.34.0`, three standard axioms only,
`leanchecker` re-check, human reviewer; the procedure passed on the smoke
project (run 35122594002). Limits: 2 h per execution, 4 h per build,
16 GB, 5.9 h per proof.

Measured: the arena backend, upstream and unaudited, cuts PGU by 20.8% to
28.5% on the three development blocks (`apparatus/INTERFACES.md` section
8), so it is the counterfactual and the bar for a candidate. Replaying a
saved stdin reproduces cycles and PGU exactly for both variants; the
evaluation uses one RPC run plus one replay per block and variant (60
executions planned). Peak resident set 7.5 to 8.8 GB on every run.

## Apparatus step 6: proof-run costs and budgets

`demand/budget.json` (2026-09-17). Measured: execute 83 to 549 s from RPC,
59 to 127 s from a saved input; build 21 min; compressed proof 4 h 09 min
for 22.6M cycles (5.5M cycles per hour, 30M-cycle ceiling under the 6 h
cap). List price of a proof (Succinct network, not bought): 0.26 to 1.16
PROVE per corpus block; a candidate at the 5% gate over the arena saves
0.002 to 0.036 PROVE per job, so per-job value is small at this block size
and volume decides break-even. Creator budget: `claude-opus-5`, 300 USD,
400M tokens, 72 h, 3 revisions (scenario 210 USD); compute: corpus-only
executions, no proofs, about 10 free runner hours. Evaluation: about 20
runner hours over 2 days, operator-paid. Deadlines: submitBy = funding + 4
days, evaluateBy = submitBy + 5 days. Sponsor amounts: bounty 0.05 testnet
ETH, usage fee 0.002 + 0.02, labeled mechanics only.

## Apparatus step 7: contracts and funding

2026-09-17, Robinhood Chain testnet (46630). Sponsor funded by bridging 0.15
Sepolia ETH through the rollup's delayed inbox. Deployed and source-verified:
`SP1VerifierGroth16` v6.1.0 `0x2d67d20E…` (accepts the real step 1 proof,
rejects a mutated one), `ModuleRegistry` `0x92695F85…`, `CreationBounty`
`0x2C920C76…`, `UsageEscrow` `0xC5cf8351…`; 37 Foundry tests including the
solvency invariant. Demand funded: id `0x5aa24f98…`, tx `0x8f1e3be9…`,
block 120638142, 0.05 testnet ETH, spec hash `0x51541fd6…`, policy hash
`0x4d586005…`, holdout commitment `0xe60d6ced…`; submitBy 2026-09-21T05:00Z,
evaluateBy 2026-09-26T05:00Z. Payment mechanics, testnet.

## Disposition

Agent disposition: TBD (reuse / compose / create / decline)
Hypothesis hash: TBD

## Evaluation summary

Verdict: TBD
Report hash: TBD
Candidate digest: TBD

## Reuse

Fresh job settled: TBD
Tx hash: TBD

## Cost accounting

```text
buyer net saving per future job
  = baseline comparable total cost
  - optimized comparable total cost before module fee
  - module usage fee

buyer break-even jobs
  = ceiling((creation bounty + buyer integration cost)
            / positive net saving per future job)

creator experiment margin
  = creation bounty + observed usage fees
  - inference/development/proving costs
  - creator-paid settlement and support costs
```

All values: TBD until the runs happen. Estimates and price bases are in
`demand/budget.json`; testnet settlement is labeled payment mechanics
demonstrated, and the creator's inference bill is the only USD cost.

## Human interventions

Assistance level: TBD

| When | Kind | Description |
| --- | --- | --- |

## Controls

| Control | Expected | Observed |
| --- | --- | --- |
| Existing capability | reuse, no bounty | TBD |
| No viable opportunity | decline with evidence | TBD |
