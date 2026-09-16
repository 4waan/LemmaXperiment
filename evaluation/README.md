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
- `reports/`: one signed report per evaluated candidate.

Held-out fixtures are not stored here. Their commitment, selection rule and
salt are revealed after the final evaluation.

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
4. Performance: 10 holdout blocks, 3 paired runs each, randomized order, fresh
   caches, identical resources. Separate preparation, guest, proving, wrapping,
   verification and peak-resource measurements.
5. Verdict: Pass, Fail or Inconclusive. Signed. Never invented timings.

## Report fields

```text
reportId, demandId, candidateDigest, policyHash, evaluatorImageHash
reproductionResult, derivedGuestKey
correctnessResult, formalResult, formalReviewNote
performance: { perBlockMedians, pairedDeltas, bootstrapInterval, regressions }
verdict, reportHash, evaluatorSignature, validUntil
```
