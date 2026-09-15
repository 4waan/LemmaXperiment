# evaluation/

Owner: evaluator. Separate environment, separate signing identity.

## Files

- `policy.json`: frozen rules, thresholds, limits and the evaluator image hash.
  Its hash is `evaluationPolicyHash` in `demand/spec.json`.
- `reports/`: one signed report per evaluated candidate.

Held-out fixtures are not stored here. Their commitment, selection rule and
salt are revealed after the final evaluation.

## Procedure

1. Reproduce: build the candidate in a fresh constrained environment; derive
   the guest key independently; verify license and composition claims.
2. Correctness: compare upstream A with integrated candidate B using an oracle
   that does not share the changed algorithm. Malformed and boundary inputs.
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
