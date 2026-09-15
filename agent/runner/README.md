# agent/runner/

Owner: operator. Launches the creator agent when the bounty is funded.

## Responsibilities

1. Watch CreationBounty for the FUNDED event; wait for the confirmation policy.
2. Materialize a restricted workspace: upstream source at `baselineCommit`,
   public development fixtures, registry snapshot, allowlisted tools.
3. Start the creator agent with the public specification only.
4. Record the run log and forward the final submission through the restricted
   transaction controller.

## The creator cannot

- read held-out fixtures or the evaluator environment
- edit `demand/`, `evaluation/policy.json`, or acceptance thresholds
- access funding or evaluator keys
- change `assignedCreatorPayee`

## Workflow the agent must follow

A. Interpret: record model version, prompt, tool policy, source snapshot, budget, start time.
B. Search: return one disposition: `reuse`, `compose`, `create`, or `decline`.
C. Commit a hypothesis: insertion point, affected operation, baseline share,
   mechanism, failure risks. Hash into the run log before implementation.
D. Build: at most `localAttemptLimit` revisions using public checks. Keep failed ones.
E. Submit: one immutable source commit plus a content-addressed artifact bundle.

## Run log fields (to be finalized)

```text
runId, demandId, agentModel, agentVersion, initialPromptHash, toolPolicyHash
sourceSnapshotHash, registrySnapshotHash, budget, startedAt, endedAt
disposition, dispositionEvidenceHash
hypothesisHash, hypothesisCommittedAt
revisions[]: { revisionId, commit, publicCheckResults, tokenCost, wallTime, computeCost }
submission: { sourceCommit, artifactDigest, submittedAt, txHash }
humanInterventions[]: { at, kind, description }
assistanceLevel: unassisted | assisted-configuration | human-assisted-implementation
```

## Gate to next stage

A submission transaction at or before `submitBy`, or a recorded decline with an
investigation report. Either way the run log is complete and hashed.
