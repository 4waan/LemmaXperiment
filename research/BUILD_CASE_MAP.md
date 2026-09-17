# Build map: five cases that establish the product

Date: September 16, 2026. Status: implementation and evidence plan.

Implements the goals in [HACKATHON_GOALS.md](HACKATHON_GOALS.md). Read with [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md), [EXPERIMENT.md](EXPERIMENT.md), [REUSE_PLAN.md](REUSE_PLAN.md) and [recorded results](LemmaXperiment/results/report.md).

This map defines what to build and how to demonstrate it. Proposed evidence paths below do not yet represent completed runs. No acceptance policy, funding or deployment is changed by this document.

## 1. One build, five evidence cases

The common loop is:

```text
Funded demand
  -> restricted agent searches and chooses
  -> immutable candidate or existing release
  -> scoped evaluation and acceptance
  -> accepted module available for acquisition
  -> fresh worker uses it on fresh input
  -> exact proof checked and payment credited
  -> independent operator repeats the buyer workflow
```

Five cases inspect different properties of this loop:

- **A: Working agents.** Choices and actions respond to evidence and constraints.
- **S: Enforced settlement.** Contract rules determine payment and refund outcomes.
- **R: Meaningful rejection.** Bad inputs and forbidden actions fail at the right boundary.
- **M: Measured reuse.** Reusing the exact release produces a measured result against alternatives.
- **P: Independent pilot.** Someone outside the build team can use the product on a relevant task.

Rejection tests accompany every stage. Pilot discovery starts early; independent execution comes after the buyer path is usable. These are not five separate applications.

## 2. Starting point and prerequisite decisions

### Evidence already recorded

The results file records a baseline SP1 proof and Groth16 wrap, positive/negative verifier view calls on Arbitrum Sepolia, development inputs and 31 trie fixtures checked against pointer and arena backends. This map relies on those records; it does not claim to have rerun them.

The inspected contract, agent runner, candidate and reuse directories contain outlines or manifests. Paid reuse and an overall experiment verdict remain unresolved. A successful verifier view call is not a settlement transaction.

### F0: freeze one coherent run profile before funding

Owner: operator and evaluator. Dependencies: existing apparatus and public integration survey.

Resolve and record:

1. **Chain.** Resolved 16 September: every document now names Robinhood testnet (46630) as the settlement venue and Arbitrum Sepolia as the read-only verifier cross-check (`demand/spec.json` `settlement`, `evaluation/policy.json` `settlement`, `apparatus/pins.json` `robinhood`). Still open: contract addresses, verifier code identity and confirmation policy, filled at deployment.
2. **Acceptance metric.** Resolved 16 September in spec and policy revision 0.2-draft: PGU is the single technical gate; `policy.json` `performance.acceptance` fixes the per-block value, the statistic, the bootstrap interval, minimum paired blocks and Pass/Fail/Inconclusive semantics; the latency target became a reported outcome. Both files carry a `revisionHistory` entry so the change is visible, not silent. Hashes are computed at F0 freeze.
3. **Fresh reuse input.** Resolved 16 September: block 20600928, recorded in `LemmaXperiment/reuse/input.json` before any measured use, referenced from `spec.json` `freshReuseInput`. It is disjoint from holdout set 1 by the frozen rule's 1000-block exclusion margin, so no sealed material was opened. ROBINHOOD_CHAIN_PROD G5 updated.
4. **Complete policy.** Fill toolchain, reproducible evaluator image, build limits, execution host, budgets, deadlines, signers, recipient terms and commitments. Use the actual resource plan, not a deadline inferred as q99 from only three proof durations.
5. **Public bindings.** Freeze the accepted guest/wrapper design and exact fields tying source computation to settlement context. The baseline's block-header public values alone do not establish market/job binding. Keep this application statement distinct from EIP-8025 compatibility.
6. **Artifact identity.** Define source bundle, build input, compiled guest and dependency-lock hashes. Specify how the evaluator independently derives the guest key from the accepted source.

F0 exit: one versioned, internally consistent run profile with reproducible hashes, published public criteria, and separately sealed holdout material. No funded candidate run starts with null acceptance-critical fields.

## 3. Shared build milestones

### F1: contracts and verification path

Owner: contract builder. Maps to production B4 and B7, approximately G1.

Build CreationBounty, ModuleRegistry and UsageEscrow using existing primitives. Adapt the restricted signer. Integrate an actual compatible SP1 verifier. Establish one accepted proof fixture and its negative controls; mocks can help isolated state tests but do not satisfy this integration milestone.

Exit: local contract tests and target-chain smoke verification pass; escrow has no administrative bypass for runtime proof acceptance. Save source revisions, test output, deployment manifest and verifier identity.

### F2: restricted agent and evaluator handoff

Owner: runtime builder plus evaluator. Maps to B2, B3, B7 and G2/G3.

Build event handling, workspace materialization, tool/budget policy, action logging and submission delivery. Add independent evaluation and typed verdict signing. Creator-generated code cannot access evaluator secrets or modify acceptance policy.

Exit: a funded-event replay does not launch duplicate paid work; a candidate or decline produces a complete run record. Protected-file and budget checks are demonstrated.

### F3: accepted release and certification

Owner: evaluator and contract builder. Maps to G4, C5/C6/C7.

Rebuild and check the immutable bundle, evaluate the named claims, derive the guest key, and submit a verdict. Acceptance registers the release and credits the creation bounty atomically. A failed or inconclusive result takes the explicitly defined rejection/expiry path.

Exit: release ID, source digest, evaluation profile, report and payment all trace to one accepted subject. Existing third-party software is attributed correctly and does not become a newly invented bounty asset merely by relabeling.

### F4: fresh-job procurement and settlement

Owner: buyer runtime, worker and ledger builder. Maps to B5/B6/B7 and G5.

Select the accepted release through the buyer policy, fund the job, fetch/install in a clean process, execute fresh input, prove, submit and withdraw credited amounts. Compare against a baseline on that same input.

Exit: an actual job transaction verifies the correct statement, credits only stored recipients, settles once and appears in the reconstructed ledger with its evidence.

### F5: independent pilot and submission evidence

Owner: product/operator role plus external participant. Maps to G6, with recruitment preparation starting during F0.

Give an independent participant the buyer quickstart and a relevant task. Record setup friction, use, outcomes, interventions and their own feedback. Package evidence for all five cases.

Exit: an attributable external run exists, or the project explicitly reports pilot pending/unsuccessful. Do not manufacture independence through another team-controlled wallet or process.

## 4. Case A: working agents

### The claim

An agent chooses and performs an economically relevant action within constraints. It is not merely narrating a preselected script.

### Build path

Funded demand event -> runner waits for the frozen confirmation rule -> runner materializes public inputs -> agent searches the registry -> deterministic eligibility checks filter offers -> agent chooses a disposition -> restricted controller executes permitted actions -> run log records outcome.

Components: `agent/runner/`, candidate/formal workspace, registry snapshot and B7 authority controller. Suggested entry point names are `runDemand` and `evaluateOffer`; these are proposed interfaces, not existing APIs.

### Demonstration scenarios

- **A1, reuse:** provide a relevant accepted capability with compatible terms and lower measured/estimated acquisition cost. The agent selects it and avoids claiming a new creation bounty. If it is the upstream arena backend, identify it as upstream and apply its actual license and price.
- **A2, create or compose:** the funded requirement is unmet by available offers. The agent records a hypothesis, works within the revision limit, and submits a candidate. If it uses a dependency, record both technical and commercial relationships. Completion is not guaranteed; preserve failures.
- **A3, decline:** eligible options cannot meet the budget or deadline. The agent records the reason and submits no unauthorized spend.
- **A4, changed conditions:** repeat a public procurement scenario with price or compatibility changed. Verify the choice follows the changed evidence. Label this a controlled scenario; do not leak holdout tasks or pretend synthetic prices are market observations.

The mandatory product evidence is a reuse choice, a bounded missing-capability attempt and a correct decline. A successful composed artifact is additional evidence, not something to fabricate to show all four disposition labels.

### Acceptance and evidence

Pass when logs identify alternatives, eligibility reasons, estimates, actions, actual cost and interventions, with enforceable spending/tool limits. Deterministic checks may enforce safety; the agent still performs real search/planning and tool work.

Proposed files: `LemmaXperiment/results/cases/A/<runId>/run.json`, `actions.jsonl`, `decision.json`, `costs.json`, `interventions.md`.

Include model/runtime identity, prompt and policy digests, timestamps, attempt count, errors and whether amounts were estimates or observed charges. Secrets and private holdouts never enter public logs.

## 5. Case S: enforced settlement

### The claim

Accepted work is paid under frozen terms, once, and failed/expired work releases funds according to explicit rules.

### Build path

**Creation:** funding freezes terms -> creator submits immutable digest -> authorized evaluator signs bound verdict -> Pass registers the release and credits the assigned creator in one transaction -> creator withdraws.

**Runtime:** buyer funds exact job -> worker submits a valid proof -> escrow checks actual verifier and all public bindings -> worker/contributor credits increase -> designated recipients withdraw.

**Failure:** decline, rejection or deadline expiry -> sponsor/buyer receives the applicable refundable credit -> withdrawal completes. A revert alone does not demonstrate refund recovery.

Components: B4 contracts and B7 signer; production C1, C4, C6, C7, C8 and C10. Relevant invariants: I-S1 through I-S14.

### Acceptance and evidence

Show transaction receipts, before/after liabilities and recipient balances, decoded job terms, exact proof input, event sequence and withdrawal results. A relayer cannot redirect payout; repeated settlement cannot add credits. Reentrancy and pause behavior are covered in contract tests.

Distinguish funding, crediting and withdrawal. Record gas separately from the bounty and fees. Label testnet amounts as test funds.

Proposed files: `results/cases/S/<runId>/transitions.json`, `balances.json`, `receipts.json`, `tests.txt`, plus the deployment manifest under `contracts/deployments/`.

Runtime payment must remain proof-gated. An evaluator signature may authorize scoped creation acceptance, but must not become an override that marks an invalid runtime proof valid.

## 6. Case R: meaningful rejection

### The claim

Failures are caught by the right mechanism before they cause unauthorized adoption or payment.

Keep each negative case paired with a passing control under otherwise identical conditions. A network error or unrelated revert is not proof that the intended check worked.

### Required cases and enforcement locations

- **R1, wrong artifact digest:** change delivered bytes after registration. Fetch/evaluation layer refuses the mismatch; no accepted job uses those bytes.
- **R2, incompatible profile:** change fork, schema, dependency or guest profile. Buyer eligibility rejects before spend; escrow also enforces the snapshotted key and statement.
- **R3, incorrect result:** mutate proof bytes or a public field. Actual verifier/statement checks reject; credits remain unchanged.
- **R4, replay or wrong recipient context:** reuse a receipt across a demand, contract or chain, or resubmit a settled job. Typed signature and consumed-state checks reject. Test wrong evaluator and expired signature too.
- **R5, agent boundary violation:** attempt a holdout read, policy edit, payee change or spend beyond mandate. The filesystem/signer boundary denies it and logs the denial. No real secrets are needed for these tests.
- **R6, timeout/refund:** no valid submission by the deadline. Settlement and refund boundary tests show exactly which action is allowed, then recover refundable funds.
- **R7, correct but unhelpful:** a candidate passes correctness but fails the frozen performance requirement. Report correctness separately; no Pass verdict or creation bounty is awarded under that demand. This is a central certification demonstration.
- **R8, stale status:** where suspension/revocation is implemented, new procurement rejects a disallowed claim. Existing funded jobs follow their frozen incident policy. Do not claim retroactive changes to immutable terms.

### Acceptance and evidence

For each ID save trigger, expected rejecting component, actual error/reason, pre/post state and matching positive control. Run the full matrix locally; use representative negative target-chain calls or transactions where useful. Spending gas to broadcast every known-invalid case is unnecessary.

Proposed files: `results/cases/R/matrix.json` and per-case logs. Mark simulated, local, forked and target-chain evidence distinctly. No public claim of full rejection coverage until the required matrix passes.

## 7. Case M: measured reuse

### The claim

A separate worker can use an unchanged accepted release on fresh input, and the resulting economics are measured against credible alternatives.

### Build path

Accepted version -> buyer compares eligible offers and local alternatives -> fresh job funded -> clean worker verifies artifact digest and installs from instructions -> fresh supported input executed/proved -> actual proof settles -> baseline comparison and cost report saved.

Components: `reuse/`, existing apparatus, evaluator profile and ledger. Baseline and candidate inputs must encode the same semantic workload even if their witness formats differ; freeze and record each variant's serialized input digest. An optimized encoding need not be byte-identical to the baseline encoding.

### Measurement layers

1. **Technical gate:** follow the reconciled frozen policy. The current evaluator draft specifies 10 holdout blocks, 2 execute-mode repetitions per variant per block (40 executions), median PGU improvement of at least 5%, and a per-block regression cap of 10%. Final interval computation and acceptance semantics must be explicitly reconciled at F0. These are drafted criteria, not achieved results.
2. **Fresh reuse:** use input outside both development and holdout sets. No source edits; log installation help. Execute the baseline on the same input when claiming comparative savings.
3. **Procurement economics:** compare fee, search, download, checking, integration, compute and allocated settlement against free/local alternatives. Report cold and warm access separately.
4. **Creation recovery:** separately include creation bounty and one-time integration/evaluation expense. Break-even is meaningful only when observed per-job net savings are positive.

A PGU win is a technical result, not automatically a latency or dollar win. A clean worker operated by our team establishes process separation; it does not satisfy the independent-pilot case.

### Acceptance and evidence

**M-functional passes:** unchanged accepted artifact, fresh supported input, correct result and paid job.

**M-technical passes:** frozen evaluator thresholds pass.

**M-economic passes:** complete measured acquisition/reuse cost beats the relevant alternative for the reported workload, within its deadline. If prices are hypothetical, report scenario economics instead of observed savings.

Report these separately. Successful settlement cannot hide performance regression. Economic failure can narrow the product claim while leaving valid functional evidence.

Proposed files: existing `reuse/install-log.md`, `reuse/job.json`, `reuse/proof/`, plus `results/cases/M/comparison.json`, `costs.json` and `summary.md`. Retain failed attempts and distinguish observed provider bills, estimates and testnet nominal fees.

## 8. Case P: independent pilot user

### The claim

An operator outside the implementation team can evaluate and use the buyer workflow for a task they recognize as useful.

### Start early

Owner: project lead. Prepare a short outreach brief during F0/F1. Target a prover developer, formal-methods developer or infrastructure agent operator with a matching workload. Recruiting someone is an external dependency; the build cannot invent their participation.

The brief explains the task, expected time, current trust model, testnet status, artifact visibility and feedback requested. Sending outreach is a separate authorized action; this map does not send messages or claim partnerships.

### Pilot sequence

1. Participant states their own task and current alternative.
2. Agree the permitted data, supported profile and success condition.
3. Give them the buyer quickstart, published artifact and declared evaluator policy.
4. They run from a separate environment using their own operational choices. If we supply test funds or compute, disclose that sponsorship.
5. They inspect the certificate, accept or reject the offer, and attempt the fresh job.
6. Capture setup time, completion, failures, assistance and their own feedback.
7. Ask whether they would repeat the task and what would make it worth paying for. Record the answer, not an inferred endorsement.

### Evidence levels

- **P-interest:** interview or expression of interest only.
- **P-attempt:** independent installation or execution attempt, including failure.
- **P-use:** participant completes a relevant buyer/reuse workflow.
- **P-repeat:** participant returns for another task.
- **P-paid:** non-team money funds actual use under agreed terms.

Buildathon target: P-use with an attributable run and feedback. Repeat and paid use strengthen the case but are not to be assumed. An independently run agent still belongs to a human/operator responsible for its budget.

Proposed files: `LemmaXperiment/pilot/brief.md`, `quickstart.md`, `runs/<pilotId>/record.json`, `feedback.md`, `interventions.md`, and a permission-to-publish record. Publish only consented identity/quotes and non-sensitive logs. A privacy-preserving alias can be used with privately verifiable independence.

If nobody completes the pilot, mark it pending or unsuccessful and present internal usability evidence separately. Do not label another team-controlled wallet as a customer.

## 9. Common evidence contract

Every case record includes:

```text
caseId, runId, status
codeCommit, profileHash, artifactDigest
chainId, deploymentManifestDigest
startedAt, endedAt, operatorRole
inputCommitments, expectedOutcome, observedOutcome
acceptanceChecks, evidencePaths, evidenceDigests
costBasis, costs, humanInterventions
limitations, publicationScope
```

Case status is `planned`, `running`, `passed`, `failed`, `inconclusive` or `blocked`. A record cannot become passed merely because files exist. The corresponding exit checks and evidence references must validate.

Keep evidence append-only by run identity. Corrections supersede old records with reasons. Public logs reference secret or private evidence through appropriately protected commitments rather than disclosing it.

## 10. What the demo should show

Use one primary successful trace and a short rejection panel:

1. Demand and available options, including the free baseline.
2. Agent decision and budget, with actual tool actions.
3. Scoped certificate and one failed claim/candidate.
4. Fresh-job input, exact accepted version and proof verification.
5. Contract credits/withdrawals and contributor allocation.
6. Measured comparison, including overhead and limits.
7. Independent pilot outcome, labeled by its actual evidence level.

Long proving runs can execute before the presentation. Show authenticated run records and real receipts; label what is prerecorded. Do not present cached proof playback as live generation.

## 11. First implementation slice

Build F0 then F1's smallest meaningful path: a fixed job, an actual compatible proof, immutable recipients, one settlement and a replay rejection. This covers S and part of R before spending on creator runs.

In parallel with that engineering, prepare the pilot brief and buyer task description. Then implement the agent/evaluator handoff, accepted release, fresh reuse and external pilot. Avoid adding asset categories until the five cases are either evidenced or explicitly reported as unmet.

Final reporting must preserve three distinctions: plans versus observations, testnet settlement versus willingness to pay, and internal clean-room reuse versus independent adoption.
