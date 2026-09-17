# agent/runner/

Owner: operator. Launches the creator agent for the funded demand and keeps
every credential on this side of the line (EXPERIMENT.md sections 5 and 13;
ROBINHOOD_CHAIN_PROD.md B2, B7, C2 to C4, I-A1 to I-A8).

## What it does

1. **Trigger (C2):** reads the funded demand from `CreationBounty`
   (`demand/funding.json`) and refuses to start until the funding block is
   posted to the parent chain (`NodeInterface.findBatchContainingBlock`,
   I-V2) and `submitBy` is still ahead.
2. **Workspace (C3):** clones this repository at the operator's HEAD into
   `workspaces/<runId>/repo` on a `creator/<runId>` branch with no push URL,
   checks out the pinned RSP source under `upstream/rsp/` (read-only
   reference), and leaves `candidate/` and `formal/` as the only writable
   trees.
3. **Session (B2):** runs the creator through the Claude Agent SDK with
   `permissionMode: dontAsk`, an explicit tool policy (`tool-policy.json` in
   the run directory, hashed into the manifest) and the OS sandbox for Bash.
   Edits and writes are allowed only under the two trees; reads of `.env`,
   `~/.lemma-evaluator`, `~/.claude`, `~/.config/gh`, `~/.ssh` and this
   runner's records are denied; `git push`, `gh`, `curl`, `cast`, `forge`
   and network beyond crates.io, github.com and the Lean release hosts are
   denied. Verified by the smoke run (`runs/smoke-*`): reading `.env` and
   writing `demand/` are refused, `git push` and `curl` are refused,
   `cargo` runs, `candidate/` is writable.
4. **Tools (`lib/tools.mjs`):** everything beyond files and local commands
   goes through an in-process MCP server the runner owns:
   `record_disposition`, `record_hypothesis`, `publish_revision` (commits
   and pushes the two trees with the runner's credentials, returns the
   bundle digest), `dispatch_build`, `dispatch_execute`,
   `dispatch_fixtures`, `dispatch_formal` (GitHub Actions with validated
   inputs and the `demand/budget.json` dispatch counts; corpus blocks only;
   candidate builds need a recorded hypothesis and count as revisions up to
   `localAttemptLimit`), `workflow_status`, `fetch_run` (artifacts
   downloaded into the workspace and scrubbed), `submit_candidate` and
   `decline_demand` (one terminal action per run).
5. **Controller (B7, `lib/controller.mjs`):** holds the creator payee key,
   projects `submitCandidate` and `decline` to calldata from typed
   arguments, checks the mandate (demand, contract, deadline, one action),
   compares the transaction with the projection byte for byte, signs and
   sends. The model never sees the key or the token.
6. **Run log (`lib/log.mjs`):** `runs/<runId>/actions.jsonl` is hash-chained
   and scrubbed (provider keys, private keys, forbidden fields);
   `RunLog.verify` re-checks the chain. `run.json` carries the manifest
   fields below; `messages.jsonl` is the scrubbed transcript;
   `prompt.md` and `tool-policy.json` are what the model saw.
7. **Budget:** `maxBudgetUsd`, `maxTurns`, wall time (abort timer) and the
   token limits from `demand/budget.json`; the session stops at the first
   one hit and the log records which.

## Commands (Node 22, `npm install` once)

```text
node run.mjs status          demand state, posting clock, hours left, budgets
node run.mjs dry-run         workspace + manifest + tool policy, no model
node run.mjs smoke           a few Haiku turns exercising the tools and the denials (dispatch off)
node run.mjs start           the creation run (claude-opus-5, demand/budget.json limits)
node run.mjs control A1|A3   disposition-only control runs (demand/registry-snapshot.json)
npm test                     canonical json, log chain, scrubbing, controller, workspace, tool rules
```

## Run log fields

```text
runId, mode, demandId, specificationHash, evaluationPolicyHash
sourceSnapshotHash, registrySnapshotHash, initialPromptHash, toolPolicyHash
model, budget, dispatches, fundingBlock, postedInBatch, workspace, branch
startedAt, endedAt, usage {turns, inputTokens, outputTokens, cacheRead, cacheWrite, costUsd}
disposition, hypothesisHash, revisions[], published[], dispatches, runs[]
submission {commit, sourceCommit, candidateDigest, txHash} | declined
humanInterventions[], assistanceLevel
```

## The creator cannot

- read held-out material, `.env`, the evaluator directory or this runner's records
- edit anything outside `candidate/` and `formal/`
- push, dispatch, fetch or send a transaction except through the tools above
- change `assignedCreatorPayee`, the demand, the policy or the thresholds

## Gate to next stage

A submission transaction at or before `submitBy`, or a recorded decline with
`candidate/investigation.md`; run log complete and verified; assistance
level stated in `run.json`.
