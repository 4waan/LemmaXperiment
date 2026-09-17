# demand/

Owner: buyer / operator. Frozen before the bounty is funded.

## Files

- `spec.json`: the funded requirement and terms. Every field is `null` or `TBD`
  until setup produces a real value. Once funded, this file is immutable; a
  changed objective requires a new `specificationVersion` and a new run.
- `registry-snapshot.json`: the set of existing evaluated capabilities the
  agent may search. The main creation run must contain no prebuilt solution to
  the funded gap. Seeded control entries are labeled.
- `budget.json`: measured run costs, the list-price proof model, the creator,
  compute and evaluation budgets and the deadline rules (step 6). The spec
  carries the limits; this file carries their provenance.
- `spec_hash.py`: `specificationHash` = keccak256 of the canonical JSON of
  `spec.json` with `demandId` and `specificationHash` null; `--check`.
- `funding.json`: the funding transaction, demandId, escrowed amount and the
  confirmation policy for the runner (step 7).

## Produced by

Apparatus stage (EXPERIMENT.md section 4): baseline reproduction, interface
survey, fixture preparation, holdout commitment, evaluator freeze, cost estimate.

## Consumed by

- `agent/runner/` reads `spec.json` and `registry-snapshot.json` at trigger time.
- `contracts/` CreationBounty stores `specificationHash` at funding.
- `evaluation/` binds its verdict to `demandId` and `specificationHash`.

## Gate to next stage

- `spec.json` has no `null` or `TBD` values.
- `specificationHash` equals the hash of the frozen file.
- `sealedHoldoutCommitment` and `evaluationPolicyHash` are stored separately
  from the creator's environment.
- Bounty escrow funded onchain; funding event observed by the runner.
