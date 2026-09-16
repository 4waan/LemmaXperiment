# evaluation/

Owner: evaluator. Separate environment, separate signing identity
(`0x71A15b55313737472e455F17eF79e117038ECa9E`, key on the laptop only).

## Files

- `policy.json`: the frozen rules (version 1.0): evaluator image, reproduction
  and limits, correctness, formal scope, performance metric and acceptance,
  verdict and signature. Its keccak256 over canonical JSON is
  `evaluationPolicyHash` in `demand/spec.json`; `freeze.py` writes and
  `freeze.py --check` verifies every hash.
- `freeze.py`: evaluator image tree hash into `policy.json`, policy hashes
  into `demand/spec.json`.
- `overlay.py`: applies a candidate's `candidate/rsp/` overlay onto the pinned
  RSP after checking every file against `allowedSourcePaths`; used by
  `apparatus-build.yml` and `apparatus-fixtures.yml`.
- `analysis/paired.py`: the acceptance computation (per-block medians,
  improvement against A and against the arena counterfactual C, percentile
  bootstrap, regression cap, verdict for the performance gate).
  `--self-test` prints the rule's behavior on synthetic ten-block sets.
- `analysis/axioms.py`: the Lean check (toolchain pin, `lake build`,
  `#print axioms` against the allowed set, `leanchecker --fresh`, source
  scan), run by `.github/workflows/evaluation-formal.yml`.
- `formal-smoke/`: a two-theorem Lean project of the expected shape that
  the formal workflow runs on every change, so the procedure is known to
  work before a candidate exists.
- `fixtures/`: the public development corpus (three blocks with committed
  client inputs) and the independent trie fixtures with their py-trie
  generator; see `fixtures/README.md`.
- `harness/`: `lemma-fixtures`, runs the trie fixtures against a
  `StateTries` backend inside the pinned RSP workspace
  (`.github/workflows/apparatus-fixtures.yml`).
- `holdout/`: the frozen selection rule for the ten held-out blocks
  (`RULE.md`), the script that implements it (`holdout.py`) and the public
  commitment (`commitment.json`). The sealed manifest and the preSalt live
  in the evaluator environment, outside the repository, and are published
  under `holdout/revealed/` only after the final evaluation is signed.
- `reports/`: one signed report per evaluated candidate.

## Procedure (policy.json, mechanical steps name their workflow)

1. Reproduce: `apparatus-build.yml` with `overlay_ref` = the candidate
   commit and `variant` = its cargo feature. `overlay.py` refuses any file
   outside `allowedSourcePaths`; the pinned RSP commit is never changed.
   The evaluator's `vkey.txt` must equal the manifest's guest key; the
   build's `Cargo.lock` diff against the baseline lock must be the declared
   dependencies only.
2. Correctness: `apparatus-fixtures.yml` on the candidate backend (expected
   outcomes come from py-trie, not from A) through an adapter arm the
   evaluator writes and publishes; forged-handle and capacity families
   instantiated against the candidate's encoding; then A, B and C execute
   every development-corpus block (`apparatus-execute.yml`) and must reach
   the manifest `stateRoot` with identical public values.
3. Formal: `evaluation-formal.yml` with `ref` = the candidate commit and
   `project` = `formal`; then a person writes the reviewer note (does the
   theorem address the implemented optimization, does any hypothesis assume
   the result, what does the model omit).
4. Performance: the ten sealed holdout blocks (`holdout/RULE.md`). Per block
   and variant one RPC-backed run (`input_source=rpc`) produces the stdin
   and one replay (`input_source=replay`) re-executes the same bytes; the
   two PGU values must be identical. Variants A (upstream), B (candidate),
   C (upstream arena). Order drawn from the bootstrap seed, one job at a
   time, fresh caches. Failures and timeouts are retained; no block is
   replaced. `analysis/paired.py` computes the gate.
5. Real proofs: A and B on the smallest holdout block whose A cycle count
   is under 30M (else block 20600066, labeled), `apparatus-prove.yml`;
   both must verify against the evaluator's derived keys.
6. Verdict: Pass, Fail or Inconclusive per `policy.json` `verdict`; report
   written, hashed and signed on the laptop (EIP-712 Verdict); holdout
   reveal after signing.

## Report fields

```text
reportId, demandId, candidateDigest, candidateCommit, policyHash, evaluatorImageHash
reproduction: { buildRun, lemmaProveSha256, guestElfSha256, derivedGuestKey, manifestGuestKey, overlayFiles, cargoLockSha256, lockDiffReviewed }
correctness: { fixturesRun, harnessSha256, adapterSha256, results, corpusRuns, publicValuesIdentical }
formal: { formalRun, toolchain, theorems, axioms, leancheckerPass, reviewer, reviewNoteSha256, modelToCodeSha256 }
performance: { executions[] (block, variant, run, stdinSha256, pgu, cycles, peakRssKb, wallSeconds), perBlock, statistic, interval, seed, regressions, counterfactual, latencyReported }
proofs: { block, runs, vkeys, verified }
verdict, reasons, reportHash, evaluatorSignature, validUntil, holdoutReveal
```
