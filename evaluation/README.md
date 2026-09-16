# evaluation/

Owner: evaluator. Separate environment, separate signing identity.

## Files

- `policy.json`: frozen rules, thresholds, limits and the evaluator image hash.
  Its hash is `evaluationPolicyHash` in `demand/spec.json`.
- `fixtures/`: the public development corpus (three blocks with committed
  client inputs) and the independent trie fixtures with their py-trie
  generator; see `fixtures/README.md`.
- `harness/`: `lemma-fixtures`, runs the trie fixtures against a
  `StateTries` backend inside the pinned RSP workspace
  (`.github/workflows/apparatus-fixtures.yml`).
- `holdout/`: the frozen selection rule for the ten held-out blocks
  (`RULE.md`), the script that implements it (`holdout.py`) and the public
  commitment (`commitment.json`: preSalt hash, beacon block, sha256 of the
  sealed manifest, evaluator signature). The blocks themselves are not
  here: the sealed manifest and the preSalt live in the evaluator
  environment, outside the repository, and are published under
  `holdout/revealed/` only after the final evaluation is signed. Anyone can
  then run `holdout.py verify`.
- `reports/`: one signed report per evaluated candidate.

## Procedure

1. Reproduce: build the candidate in a fresh constrained environment; derive
   the guest key independently; verify license and composition claims.
2. Correctness: run `fixtures/trie/fixtures.json` through `lemma-fixtures`
   on the candidate backend (expected outcomes come from py-trie, not from
   A), instantiate the forged-handle and capacity families against the
   candidate's own encoding, then execute the development corpus offline
   with A and B and compare public values.
3. Formal: run Lean with the frozen toolchain; check axioms against policy;
   a designated reviewer confirms the theorem addresses the optimization.
4. Performance: the 10 sealed holdout blocks (`holdout/RULE.md`), witnesses
   produced at evaluation time with `apparatus-execute input_source=rpc`
   after the candidate's final submission is immutable; paired executions
   in randomized order, fresh caches, identical resources. Separate
   preparation, guest, proving, wrapping, verification and peak-resource
   measurements. Failures and timeouts are retained; no block is replaced.
5. Verdict: Pass, Fail or Inconclusive. Signed. Never invented timings.

## Report fields

```text
reportId, demandId, candidateDigest, policyHash, evaluatorImageHash
reproductionResult, derivedGuestKey
correctnessResult, formalResult, formalReviewNote
performance: { perBlockMedians, pairedDeltas, bootstrapInterval, regressions }
verdict, reportHash, evaluatorSignature, validUntil
```
