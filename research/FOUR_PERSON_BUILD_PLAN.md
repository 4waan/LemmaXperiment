# Four-person build plan for LemmaXperiment

Date: 23 September 2026.

Status: execution plan based on the repository, research notes, committed run records, current working tree, and local test results. This document does not change the funded demand, evaluation policy, contracts, or holdout material.

## 1. The product to finish

Build the smallest complete proof of this statement:

> A funded need causes an agent to find, create, or decline a reusable capability. An independent evaluator certifies an exact version for specific claims. A separate worker uses that unchanged version on fresh input, and verified settlement pays the agreed recipients.

The product is an onchain reuse and compatibility protocol for agent capabilities. It is not a generic NFT marketplace, a new prover network, or a speculative asset market.

For the first complete loop, the capability is a public executable module for the pinned RSP and SP1 proving pipeline. Confidential assets, generalized access tokens, capital markets, and multiple asset categories remain later work.

## 2. Current state of the project

### Proven and implemented

1. The apparatus has produced a real Ethereum execution proof, a Groth16 wrap, and positive and negative verifier checks.
2. Development inputs, 31 independent trie fixtures, a sealed holdout commitment, reproducible evaluator policy, PGU acceptance rules, and budget records exist.
3. `CreationBounty`, `ModuleRegistry`, `UsageEscrow`, and the SP1 verifier are deployed and source verified on Robinhood Chain testnet.
4. The contract suite passes 37 local tests, including proof mutation, replay, deadline, recipient, reentrancy, and solvency checks.
5. The restricted agent runner exists with workspace limits, tool policy, budget controls, a transaction controller, resumable runs, and hash chained scrubbed logs.
6. The agent runner passes 11 local tests.
7. A funded demand exists, and its L2 block was confirmed as posted to the parent chain.
8. The research has already resolved the central product position: exact asset identity, scoped evidence, compatibility, adoption receipts, and settlement matter more than a token label.

### Blocked or incomplete

1. The active demand's submission deadline was 22 September 2026. No real creator run submitted a candidate.
2. The latest creator control attempts stopped immediately because the configured Claude organization rejected subscription access. This is the immediate operational blocker.
3. `candidate/` and `formal/` remain scaffolding. There is no completed candidate, theorem package, or integration overlay.
4. There is no signed evaluation report, accepted registry version, paid fresh reuse job, or final experiment verdict.
5. There is no product indexer, buyer facing evidence view, compatibility resolver, or independent pilot flow.
6. Several status documents are stale. The root README still says nothing is implemented, while the repository contains deployed contracts, tests, proofs, and runner code.
7. The latest research file and run records are uncommitted. They must be reviewed before any cleanup or branch split.

### The decisive gap

The project does not need more broad architecture before it closes the loop. It needs a recovered creator path, one evaluated release, one fresh paid reuse, and one independent user attempt.

## 3. Four ownership lanes

Every lane has one accountable owner and one named challenger. The challenger is responsible for trying to invalidate assumptions, not for approving work politely.

### Member 1: protocol and tokenization lead

Suggested owner: the project lead who understands blockchain.

Owns:

1. Contract state machines and onchain invariants.
2. Asset identity, control rights, access rights, and revenue rights.
3. Demand funding, expiry, refunds, evaluator signatures, proof bindings, and settlement transactions.
4. ABI and event definitions consumed by the indexer and agent runtime.
5. Final approval for any contract or token model change.

Does not own:

1. The product interface.
2. Agent prompts and tool behavior.
3. Benchmark execution and economic analysis.
4. Pilot recruitment and evidence packaging.

Required outputs:

1. A one page protocol boundary for each contract flow.
2. Machine readable ABI and event fixtures.
3. A state transition diagram with allowed caller, required inputs, emitted event, failure modes, and terminal state.
4. A tokenization decision record for the MVP.
5. Transaction receipts for expiry or refund, new funding, acceptance, fresh job funding, settlement, and withdrawal.

Primary challenger: Member 3, who tests whether each onchain statement actually supports the economic claim being made.

### Member 2: agent runtime and procurement lead

Owns:

1. Provider neutral creator runtime recovery.
2. The reuse, compose, create, or decline decision path.
3. Tool policies, workspace restrictions, budget enforcement, and run log integrity.
4. Agent and task profile schemas used for hard compatibility filters.
5. Control scenarios that change the agent's decision when price, compatibility, or scope changes.

Required outputs:

1. A passing authenticated smoke run that does not depend on the disabled subscription path.
2. Passing A1 reuse and A3 decline controls with current demand artifacts.
3. A complete creator run record with disposition, hypothesis, revisions, costs, and terminal action.
4. A compatibility decision trace that another member can inspect without reading the full model transcript.
5. Negative tests for forbidden reads, writes, network use, overspending, payee changes, and duplicate terminal actions.

Primary challenger: Member 4, who tests whether a buyer or operator can understand and use the agent outputs.

### Member 3: evaluation and economics lead

Owns:

1. Frozen evaluator execution, correctness fixtures, formal checks, PGU analysis, and verdict construction.
2. Tiered evaluation so cheap admission and execute mode checks happen before expensive proofs.
3. Complete cost accounting for creation, evaluation, integration, execution, settlement, and failed attempts.
4. Buyer build versus buy comparisons and break even calculations.
5. Failure interpretation, including Pass, Fail, and Inconclusive boundaries.

Required outputs:

1. An admission checklist that rejects schema, source path, lockfile, license, and digest violations before expensive runs.
2. A reproducible evaluation report bound to the exact candidate, policy, guest key, evidence, and recipient.
3. A paired performance analysis against upstream and arena alternatives.
4. A fresh reuse comparison that separates functional, technical, and economic outcomes.
5. A claim ledger that labels every number as observed, modeled, quoted, sponsored, or testnet nominal.

Primary challenger: Member 1, who verifies that the verdict and proof bindings are sufficient for settlement.

### Member 4: product, evidence, and pilot lead

Owns:

1. The buyer facing demand, catalog, asset evidence, compatibility explanation, job, and settlement views.
2. A small event indexer and evidence resolver for the existing contracts.
3. The buyer quickstart, pilot brief, task intake, feedback capture, and publication consent.
4. Repository status reconciliation and the final demo evidence pack.
5. Usability tests that reveal where blockchain terminology blocks adoption.

Required outputs:

1. A read only product surface backed by real registry, demand, job, and receipt data.
2. An asset view that shows exact version, claims, scope, evidence, compatibility, rights, price, and limitations.
3. A gap board linking each claim to evidence and each missing fact to an owner.
4. An independent pilot attempt with setup time, interventions, outcome, and feedback.
5. A submission script that distinguishes live actions, prerecorded proving, estimates, and unresolved gaps.

Primary challenger: Member 2, who verifies that the UI represents actual agent choices and machine readable fields.

## 4. Tokenization decision for the MVP

The first release should not introduce a generic asset NFT.

Use four separate concepts:

1. Asset identity: the immutable `ModuleRegistry` version and its digests.
2. Asset control: the address authorized to publish future versions or terms. Keep this as a registry role for the MVP.
3. Access right: not required for the public module experiment. Add a scoped grant only when a confidential or quota limited capability is tested.
4. Revenue right: the contributor and fee snapshotted into each job.

The usage receipt proves that a version was used in a job. It does not confer ownership.

Later options, each requiring a separate decision:

1. ERC-721 for transferable administration of future asset terms.
2. ERC-1155 for a quantity of invocation credits.
3. Nontransferable grants for identity bound access.
4. Custom contract records for operation, quota, expiry, and task scope.

The first loop needs none of these. Registry identity plus escrow settlement is enough. This keeps the rest of the team focused on compatibility, evaluation, and adoption rather than ambiguous token ownership.

## 5. Execution phases and gates

### Phase 0: recover and rebaseline

Target: one to two working days.

Member 1:

1. Read the live state of the expired demand.
2. Execute the permitted expiry and refund path if it has not already occurred.
3. Prepare a new demand only after all preflight gates pass.
4. Do not change contract architecture unless a real blocker is found.

Member 2:

1. Replace the failed subscription path with a working authenticated provider configuration behind the existing runner interface.
2. Run smoke, A1 reuse, and A3 decline controls.
3. Record auth and runtime failures as explicit run outcomes.

Member 3:

1. Confirm the evaluator image and policy still reproduce.
2. Prepare a new sealed holdout for a new demand version, because a retry should not silently reuse a previous demand's private evaluation set.
3. Freeze the admission sequence and available compute.

Member 4:

1. Reconcile stale status text with committed evidence.
2. Create the shared gap board and demo evidence index.
3. Prepare the pilot brief and identify candidate users.

Gate R0:

1. Old demand state is resolved and evidenced.
2. Current authentication works in an actual control run.
3. New policy, holdout, hashes, deadlines, and budgets are internally consistent.
4. No secret appears in commands, logs, artifacts, or commits.
5. The new demand remains unfunded until every item above passes.

### Phase 1: make the product spine usable

Target: two working days.

Member 1 builds or confirms only the contract and event interfaces required by the current loop.

Member 2 finalizes canonical `TaskProfile`, `AgentProfile`, and compatibility result schemas. Hard incompatibility must reject before price ranking.

Member 3 implements the cheap admission report and verifies that the paired analysis, axiom checks, and report construction run from clean inputs.

Member 4 builds a small indexer and read only evidence view from existing events and repository evidence. No graph database is needed.

Gate R1:

1. A non blockchain team member can inspect a demand, candidate shape, policy, and expected settlement without asking what each contract field means.
2. The agent can consume the same canonical profile fields.
3. The evaluator can bind its result to those exact fields.
4. The UI shows facts from chain or signed evidence, never invented status.

### Phase 2: execute the creator and evaluation loop

Target: three to five working days, depending on model and runner availability.

Member 2 runs the creator with bounded revisions and preserves failures.

Member 3 performs tiered evaluation. Reject early on manifest, build, correctness, formal, or execute mode failure. Spend on real proofs only after the candidate survives earlier gates.

Member 1 handles only authorized submission and verdict transactions. The model never receives signing keys.

Member 4 observes the run as a buyer, records confusing outputs, and updates the evidence view without changing acceptance rules.

Gate R2:

1. One immutable candidate or a defensible decline exists.
2. The run log verifies and contains actual cost, interventions, and decision evidence.
3. The evaluator produces Pass, Fail, or Inconclusive under the frozen policy.
4. A Pass registers and pays exactly once. A Fail or Inconclusive follows the defined non acceptance path.

### Phase 3: prove adoption through fresh reuse

Target: two to three working days.

Member 4 operates the buyer flow from a clean environment.

Member 2 verifies artifact digest, installs through the declared adapter, and records every intervention.

Member 3 runs baseline and accepted variant comparisons on the fresh input and calculates total acquisition economics.

Member 1 funds and settles the fresh job, then verifies credits and withdrawals.

Gate R3:

1. The exact accepted version runs on the precommitted fresh input without source edits.
2. Its proof binds the intended job, contract, chain, input, output, guest key, and recipients.
3. The job settles once and appears in the indexer.
4. Functional reuse, technical improvement, and economic benefit are reported separately.

### Phase 4: independent pilot and submission

Target: two to three working days, while recruitment starts in Phase 0.

Member 4 leads the pilot. The participant supplies a real task and current alternative.

Member 2 observes agent and adapter friction.

Member 3 records setup cost, completion, failure, and willingness to repeat without converting feedback into a fake metric.

Member 1 supports only wallet, funding, or chain issues that the quickstart cannot resolve.

Gate R4:

1. An external participant attempts the buyer workflow from a separate environment.
2. The team records whether the outcome is interest, attempt, completed use, repeat use, or paid use.
3. The final claim never exceeds the actual evidence level.
4. The demo contains one successful trace and a short rejection panel.

## 6. Coordination system

### One shared unit of work

Every task must contain:

1. Claim: what becomes true when the task is complete.
2. Consumer: who needs the output next.
3. Inputs: exact files, hashes, contracts, profiles, and assumptions.
4. Output: exact artifact or evidence path.
5. Positive check: what should succeed.
6. Negative check: what nearby invalid case must fail.
7. Cost: time, compute, model, chain, and money used.
8. Limitation: what the task does not prove.
9. Challenger: who tries to invalidate it.

### Daily cadence

1. Fifteen minute dependency check. Each member reports only completed evidence, current blocker, and next consumer.
2. Two focused work blocks per member.
3. Thirty minute challenge review. One member attacks another lane's latest claim using a prepared negative case.
4. End of day evidence update. No status becomes complete without a linked artifact, test, receipt, or signed report.

### Twice weekly integration review

Run one end to end trace using current artifacts. Stop at the first broken interface. File the break against the producer of the interface, not the person who discovered it.

### Decision rule

A decision is reversible when it affects only offchain presentation, ranking, or adapters. A decision is protocol critical when it changes hashes, rights, signatures, state transitions, proof statements, recipients, deadlines, or acceptance. Member 1 approves protocol critical changes. The lane owner decides reversible changes after recording the trade.

## 7. How every member finds gaps

Use five gap lenses on every feature:

1. Meaning gap: does the field or claim mean the same thing to buyer, agent, evaluator, and contract?
2. Binding gap: are the exact bytes, version, input, output, adapter, runtime, payees, and chain committed where required?
3. Authority gap: can any component read, write, sign, spend, or publish more than its mandate allows?
4. Economic gap: is a measured saving still positive after search, checking, integration, execution, failure, and settlement costs?
5. Evidence gap: can a third party reproduce the claim from preserved inputs and records?

Every gap receives severity, owner, evidence, affected gate, proposed test, and closure condition. A gap is not closed by discussion.

High severity examples:

1. A proof verifies but is not bound to the intended escrow job.
2. An evaluator report refers to a different artifact digest than the registered version.
3. The agent can change payees, policy, or hidden evaluation data.
4. An expired demand is presented as active.
5. A PGU result is presented as observed dollar savings.

## 8. Blockchain handoff packet for non blockchain members

For every contract action, Member 1 supplies a packet with:

1. Plain language purpose.
2. Caller and signer.
3. Required state before the call.
4. Function name and typed inputs.
5. Value transferred.
6. Expected event.
7. State after success.
8. Named revert cases.
9. One successful fixture transaction or local test.
10. One deliberately failing fixture.
11. Confirmation rule and reorg assumption.
12. What the event proves and what it does not prove.

Members 2, 3, and 4 build against this packet. They do not need to understand Solidity internals to test profile mapping, evidence binding, UI state, economic claims, or agent behavior. If the packet is ambiguous, that ambiguity is a protocol gap owned by Member 1.

## 9. Definition of done for the project

The build is ready for submission only when all of the following are true:

1. The expired demand is resolved and not shown as live.
2. The creator runtime can authenticate and complete a real bounded run.
3. One immutable asset version is accepted under a frozen policy, or the project honestly records that the candidate failed.
4. A clean worker uses an accepted version unchanged on fresh input.
5. A real proof settles a fresh job and pays stored recipients once.
6. The rejection panel includes wrong digest, incompatible profile, invalid proof, replay, forbidden agent action, and timeout or refund.
7. The report separates functional, technical, economic, and adoption outcomes.
8. One independent participant attempts the buyer workflow.
9. All status pages agree with the evidence.
10. No secret or credential appears in repository history, run records, artifacts, screenshots, or command lines.

## 10. Explicitly deferred work

Do not place these on the critical path:

1. A general NFT for every asset.
2. Confidential execution and key release.
3. A generalized reputation protocol.
4. Capital allocation based on usage metrics.
5. A graph database.
6. Multiple prover networks or model providers beyond the recovery abstraction.
7. Live EIP-8025 consensus integration.
8. Speculative valuation or royalty promises for public information.
9. Multiple asset categories before the first loop closes.

## 11. First 48 hours

1. Member 1 resolves the expired demand state and drafts the MVP tokenization decision record.
2. Member 2 makes authentication work and reruns smoke, A1, and A3.
3. Member 3 reproduces evaluator checks and prepares the next sealed holdout and admission checklist.
4. Member 4 reconciles repository status, creates the gap board, and drafts the pilot brief.
5. The team runs the R0 review before any new funding transaction.

If R0 fails, do not fund again. Fix the failed interface, rerun its positive and negative controls, and preserve the failed evidence.
