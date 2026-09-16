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

All values: TBD. Testnet settlement is labeled payment mechanics demonstrated.

## Human interventions

Assistance level: TBD

| When | Kind | Description |
| --- | --- | --- |

## Controls

| Control | Expected | Observed |
| --- | --- | --- |
| Existing capability | reuse, no bounty | TBD |
| No viable opportunity | decline with evidence | TBD |
