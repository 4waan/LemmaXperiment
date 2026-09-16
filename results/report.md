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
