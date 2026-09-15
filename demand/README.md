# demand/

Owner: buyer / operator. Frozen before the bounty is funded.

## Files

- `spec.json`: the funded requirement and terms. Every field is `null` or `TBD`
  until setup produces a real value. Once funded, this file is immutable; a
  changed objective requires a new `specificationVersion` and a new run.
- `registry-snapshot.json`: the set of existing evaluated capabilities the
  agent may search. The main creation run must contain no prebuilt solution to
  the funded gap. Seeded control entries are labeled.

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
