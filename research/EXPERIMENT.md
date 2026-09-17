# Experiment 01: Demand triggers an agent-created proof asset

Status: proposed experiment, not implemented or benchmarked.
Revision 2, 15 September 2026.

Research update: [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) separates theorem-procurement savings from executable proving savings. Its Section 18 adds a paired agent-procurement experiment. The reference witness builder already deduplicates accessed nodes, so profile the selected prover before choosing trie caching as this experiment's optimization.

Venue wiring: [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md) moves settlement to Robinhood Chain testnet (chain 46630, verified live 15 September 2026), maps every block and channel of this experiment to enforceable invariants, lists the Lattice Prime and apparatus code to port, and sets the gated plan against the 4 October buildathon deadline. Where it and this document differ on venue or verifier, it takes priority.

Operational extension: [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md) defines agent procurement, token rights, encrypted storage and job-scoped access. The initial experiment retains public proof results; private-result fair exchange remains outside scope.

## 1. The experiment

**A buyer funds a missing proving capability. An agent investigates and creates a reusable module. A separate evaluator checks whether it meets the demand. Arbitrum pays the creation bounty. A fresh job then reuses the accepted module and pays its contributor again.**

```text
Funded outcome specification
    ↓
Agent searches existing capabilities and profiles the workload
    ↓
Reuse / compose / create / decline
    ↓
Candidate module + formal evidence + integration package
    ↓
Independent evaluation against frozen criteria
    ↓
Accepted version registered + creation bounty paid
    ↓
Fresh proof job adopts the unchanged module
    ↓
Proof verified on Arbitrum + usage fee paid
```

This document replaces the previous experiment plan and takes priority over BLUEPRINT.md for the next build. The earlier trie-cache idea is an optional candidate in [TRIE_MODULE_PROTOCOL.md](TRIE_MODULE_PROTOCOL.md). The agent chooses an approach from evidence within the funded scope.

### Questions to answer

- Can a funded, precise requirement trigger an agent to produce a useful asset?
- Can it find existing solutions and avoid unnecessary creation?
- Can the candidate pass correctness, scoped formal verification and integrated performance evaluation?
- Can a fresh worker/job adopt the release without a human rewriting it?
- Can creation and usage fees make economic sense for buyer and contributor?

One success demonstrates feasibility for one demand and agent configuration. It does not establish an autonomous invention market at scale.

## 2. The first demand

> Improve state-witness processing in this pinned Ethereum block-proving pipeline. Preserve its accepted computation and proof security settings. Deliver a reusable module with a machine-checked optimization property and documented integration. Meet the frozen end-to-end latency target. Successful delivery earns the creation bounty; later jobs using the approved version pay the agreed usage fee.

Default integration target: a pinned RSP/SP1 pipeline. RSP documents Ethereum block proof generation through SP1. Setup must establish compatible revisions, hardware, supported fork and insertion points. [RSP proving documentation](https://succinctlabs.github.io/rsp/Generating-proofs)

The buyer specifies the outcome and constraints. The request does not tell the agent to implement a cache. Authenticated node reuse or decoding improvements are possible hypotheses, contingent on profiling. Alloy documents Ethereum trie-proof tooling; its existence does not establish an unoptimized opportunity in the selected prover. [Alloy trie tooling](https://alloy.rs/reference/protocol-and-rpc-types/)

### Demand schema

```text
demandId, specificationVersion, specificationHash
buyer, assignedCreatorPayee, evaluatorSigner
baselineCommit, dependencyLockHash, toolchainManifestHash
workloadRelation, allowedSourcePaths, integrationInterface
publicDevelopmentCorpusHash
sealedHoldoutCommitment, evaluationPolicyHash
correctnessPolicyHash, formalScopePolicyHash
latencyTarget, maximumRegression, resourceLimits
creationBounty, usageFeePolicy, licenseRequirements
agentBudget, computeBudget, localAttemptLimit
submitBy, evaluateBy
```

Amounts and budgets become concrete before funding. Setup produces a hardware estimate; the sponsor sets the bounty and usage terms. Use testnet ETH for the hackathon and label it accordingly.

### Proposed acceptance criteria

1. Preserve required results, rejection behavior and proof security settings.
2. Deliver a Lean theorem addressing the optimization, with explicit assumptions and a model-to-Rust evidence boundary.
3. Reduce median complete-job preparation/proving/wrapping latency by at least 5% against unchanged upstream on held-out blocks, with a paired 95% interval entirely above zero.
4. No held-out block regresses more than 10%, unless an avoidance policy is part of the frozen request and is evaluated with the candidate.
5. Report comparable total costs and the room for a positive usage fee. Speed alone does not establish economic viability.

These are proposed decision rules, not predicted results. Freeze them before creation. The creator cannot relax them after failure. Module-level savings are diagnostic; the buyer commissions an integrated outcome.

## 3. Roles and authority

**Buyer / operator:** supplies demand, funds the bounty and prepares the apparatus. The project team can sponsor the first request; call it sponsored demand, not external customer validation.

**Creator agent:** receives the public specification, development fixtures, upstream source and bounded tools. It searches, profiles, proposes, implements, proves, tests and submits. Use one creator agent; a competitive agent network is later scope.

**Evaluator:** runs a frozen harness in a separate environment and controls a separate signing identity. Deterministic checks are supplemented by a designated review of whether the formal statement and assumptions address the optimization. Another model approving its own work is insufficient.

The creator cannot edit evaluation rules, inspect held-out fixtures during development, or access funding/evaluator keys. The evaluator is trusted for accurate performance measurement and its signed verdict. Onchain signatures authenticate that verdict; they do not prove a benchmark was honest.

## 4. Prepare the apparatus, then fund creation

1. Reproduce a real baseline block proof and pin source, dependencies, toolchain, proof mode and hardware.
2. Identify permitted witness-processing interfaces without implementing the solution.
3. Prepare three public development blocks and independent correctness fixtures.
4. Freeze a selection rule for ten consecutive supported historical holdout blocks. Commit the rule, fixture manifest and random salt; store them separately from the creator.
5. Freeze evaluator image, metrics, formal scope, limits, timeout and thresholds.
6. Estimate proof-run costs and choose explicit agent and evaluation budgets.
7. Fund the bounty. The funded event triggers the creation runner after the chosen confirmation policy.

A committed holdout prevents silent case replacement. Hidden fixtures reduce tuning but cannot prove the model has never seen public historical blocks. Reveal the committed material and salt after final evaluation.

If the baseline cannot run, record an environment blocker. No simulated proof can satisfy the real-proving requirement.

## 5. Agent workflow

### A. Interpret

Parse the demand and record the agent/model version, initial prompt, tool policy, source snapshot, budget and start time. Confirm the public fixtures and baseline are usable.

### B. Search

Inspect the frozen registry snapshot and upstream dependencies. Return a structured disposition:

- **Reuse:** an existing evaluated module meets the request. Recommend it; no new-creation bounty is earned in this experiment.
- **Compose:** a substantive adapter or executable integration is needed. Identify existing components, licenses and the new contribution.
- **Create:** evidence supports building a missing implementation or optimization.
- **Decline:** the opportunity does not fit the scope or budget. Return the investigation report.

The funded terms allow original implementation or substantive composition. Renaming existing code cannot qualify as creation.

### C. Commit a hypothesis

Profile development fixtures. Record the insertion point, affected operation, baseline share, mechanism and failure risks before implementation. Hash this hypothesis into the run log.

Trie-node reuse is an option. If upstream already eliminates redundant authentication/decoding, do not disable its optimization to manufacture a baseline. Investigate another permitted approach within the fixed budget or decline.

### D. Build

Proposed limit: three local candidate revisions using public checks, followed by one final holdout submission. Freeze actual token, wall-time and compute limits before launch. Preserve unsuccessful revisions and their costs.

The agent produces module code, adapter, scoped Lean evidence, tests, reproducible build and manifest. It can change hypotheses within the permitted scope. Changing the buyer's objective requires a new demand version and run.

### E. Submit

Submit one immutable source commit and content-addressed artifact bundle. A failed or declined attempt cannot register an accepted asset or release the success bounty.

### Permissions and human involvement

The creator can edit its workspace and run allowlisted build, test and profiling tools. It cannot change the baseline, evaluator, holdout storage, recipient or acceptance rules. A restricted transaction controller handles authorized submission operations without exposing treasury keys to the model.

Log every human intervention: configuration help, debugging hints, edits, replacement code and manual proof repairs. Report the run as unassisted within its supplied environment, assisted configuration/debugging, or human-assisted implementation. Do not attribute human-written work to autonomous creation.

## 6. Asset manifest

```text
candidateId, demandId, sourceCommit, artifactDigest
moduleInterface, compatibilityManifest
reproducibleBuildRecipe, guestProgramKey
dependencyVersions, dependencyLicenses
originalContributions, compositionManifest
theoremStatements, LeanToolchain, axiomReport
modelToImplementationMap, knownFormalGaps
publicCheckResults, developmentBenchmarkReport
integrationInstructions, contributorPayee
licenseReference, agreedUsageTerms
agentRunManifestHash, humanInterventionLogHash
```

Track three states: **candidate**, **accepted asset**, and **adopted asset**. Acceptance applies to an immutable version under a named evaluation policy. Adoption requires a subsequent job using that version.

The registry records provenance, evidence and terms. It does not grant exclusive ownership of mathematics or public software. Transferable tokens are outside this experiment.

## 7. Independent evaluation

### Reproduce and inspect

Build the candidate in a fresh constrained environment. Enforce resource limits on untrusted build steps and prohibit unrestricted network access. Independently derive its guest key and verify license/composition claims.

### Correctness

Compare unchanged upstream A with integrated candidate B. Preserve upstream validation. Use an independent implementation or fixture oracle that does not share the changed algorithm. Construct malformed inputs and boundary cases.

For trie candidates, cover inline and hashed nodes, malformed RLP, absent keys, incorrect roots, missing witnesses, forged handles, capacity boundaries and trie updates. See [TRIE_MODULE_PROTOCOL.md](TRIE_MODULE_PROTOCOL.md) for the optional detailed protocol.

Any unexplained correctness mismatch blocks acceptance. All required real proofs must verify against their expected statements and derived keys.

### Formal evidence

Run Lean with the frozen toolchain. Check statements, axioms and dependencies against policy. A reviewer confirms the theorem addresses the implemented optimization and does not assume the desired result.

The initial standard is a checked model-level theorem plus independently checked Rust behavior. Publish the model-to-code mapping and gap. This does not establish compiler correctness or complete formal verification of Ethereum.

### Performance

- Ten fixed holdout blocks, three paired runs per block: 60 planned A/B proof runs.
- Randomized A/B order; identical resources, security settings and acceleration patches.
- Fresh per-job caches and consistent toolchain warmup.
- Separate preparation, guest work, proving, wrapping, verification and peak-resource measurements.
- Uninstrumented timing runs; diagnostic logging measured separately.
- Retain all failures and timeouts. Do not replace inconvenient fixtures.
- Analyze block-level medians and paired changes, with a bootstrap interval over blocks. Adjacent blocks and a small corpus limit generalization.

One final holdout evaluation per demand. Later attempts need a newly sealed set and versioned evaluation; repeated feedback must not turn private cases into a tuning set.

Publish Pass, Fail or Inconclusive with report hash, raw evidence, derived key, formal-review result, exact candidate digest and evaluator signature. Insufficient compute produces an inconclusive result, never invented timings.

## 8. Two payments

### Creation bounty

Funds are escrowed before creation. A signed passing evaluation releases the fixed bounty to the assigned creator and registers the accepted version atomically. The sponsor cannot veto a compliant evaluator acceptance after funding.

This first experiment pays for successful delivery. Failed-attempt costs remain with the creator; evaluation infrastructure is separately budgeted by the operator. Record subsidies and costs even when the team pays both sides.

### Usage fee

A second request buys a new proof from the accepted executable. It snapshots worker compensation and a fixed contributor fee. Real proof verification releases both payments. Terms cannot change during that job.

Use a separate clean worker process/account for reuse. Creator and worker can have the same operator, but disclose their relationship.

### Economic checks

```text
buyer net saving per future job
  = baseline comparable total cost
  - optimized comparable total cost before module fee
  - module usage fee

buyer break-even jobs
  = ceiling((creation bounty + buyer integration cost)
            / positive net saving per future job)

creator experiment margin
  = creation bounty + observed usage fees
  - inference/development/proving costs
  - creator-paid settlement and support costs
```

Include evaluation charges in the relevant payer's accounting. Avoid double counting. Separate fixed-machine cost models from observed commercial prices. Testnet payment demonstrates distribution mechanics; it does not establish willingness to pay.

## 9. Minimal contracts

Three logical components can share a deployment in the prototype.

### CreationBounty

```text
FUNDED → SUBMITTED → ACCEPTED
   |          |
   |          +→ REJECTED
   +----------+→ EXPIRED
```

Funding fixes demand hash, creator, evaluator, policy, amount and deadlines. A creator decline can close the demand early and refund the sponsor.

One submission is permitted at or before submitBy. An unsubmitted bounty expires after submitBy. A submitted candidate can receive a decision at or before evaluateBy; absent a decision it expires after evaluateBy. Require evaluateBy > submitBy.

The evaluator signature binds chain, contract, demand, candidate digest, policy, report hash, derived guest key, recipient, verdict and validity deadline. Prevent replay across jobs/chains. Acceptance registers and credits once. Rejection or expiry credits the sponsor. Use protected pull withdrawals and solvency accounting.

This is trusted evaluation of development work. The evaluator's signature cannot establish that a speedup was measured honestly.

### ModuleRegistry

Stores accepted immutable versions, evidence references, guest keys, compatibility and contributor terms. For this run, only the defined bounty-acceptance path creates an accepted entry. Metadata alone cannot grant acceptance.

### UsageEscrow

A funded proof job can settle once or expire with a refund. Snapshot module version, verifier, guest key, worker, contributor, amounts, statement and deadline. Verify the real proof and exact public bindings; any relayer pays the stored recipients. Permit submission at the deadline and refund only afterward.

The guest wrapper commits settlement chain, contract, job ID, source domain, input/block commitments, computed result and success. Preserve upstream execution checks. Include the same wrapper convention in evaluation so reuse overhead is not hidden.

SP1 exposes verification using a program key, public values and proof bytes. Deploy the pinned `SP1VerifierGroth16` v6.1.0 on Robinhood Chain testnet (chain 46630) during setup; the Arbitrum Sepolia gateway stays a read-only cross-check. [SP1 contracts](https://github.com/succinctlabs/sp1-contracts)

Creation payment relies on the evaluator's report. Usage payment verifies execution of an approved guest. Neither establishes Ethereum canonicality when the sponsor supplies the accepted block context.

## 10. The decisive reuse test

After acceptance, use the fresh input recorded before any measured use (block 20600928, `LemmaXperiment/reuse/input.json`, outside development and holdout sets). Fund a fresh job. A clean worker installs the immutable release using its instructions, generates a new runtime proof, submits it on Robinhood Chain testnet (46630) and earns payment alongside the contributor.

No source edits or human-written replacement implementation are permitted for this reuse claim. New code requires a new version and evaluation. Log installation assistance.

Run the baseline on the new input if claiming continued savings. Report regressions even if payment succeeds. One reuse proves reuse feasibility, not recurring market demand.

## 11. Product controls

**Existing-capability control:** provide a separate request already satisfied by an asset in the registry snapshot. The agent should recommend reuse without claiming a creation bounty. Label the seeded control.

**No-viable-opportunity control:** provide a request whose required change is outside all allowed integration paths. The agent should decline with evidence rather than change the request or fabricate success. This tests one explicit constraint, not universal recognition of impossible optimizations.

**Main creation run:** supply tools, source and fixtures but no prebuilt solution to the funded gap. Existing code and composition are permitted with attribution. Log human seed code and assistance.

These controls can be lightweight disposition runs; they do not require another 60-proof benchmark suite.

## 12. Gates and outcomes

**Product feasibility:** funded demand precedes creation; the agent delivers a substantive accepted contribution within budget; a fresh job adopts the unchanged version and pays. Disclose assistance.

**Technical value:** correctness and formal scope pass; integrated holdout performance meets the request; the fresh job does not contradict the published scope.

**Economic feasibility:** comparable measured or explicitly modeled costs leave a fee and stated break-even. Testnet settlement alone receives the label payment mechanics demonstrated.

Outcomes:

- **Go:** creation, technical value and reuse pass, with supported cost accounting. Build the demand board and registry next.
- **Assisted:** useful creation and reuse pass, but human implementation work is material.
- **Reuse:** an existing asset satisfies the demand; routing works, new creation is not demonstrated.
- **Narrow:** benefits apply to a specific workload; record that scope. A missed funded threshold still cannot release this bounty.
- **Inconclusive:** budget, environment or measurement quality prevents a decision.
- **Stop candidate:** correctness or usefulness fails. Preserve the report without registering an accepted asset.

## 13. Build order and files

1. Apparatus, one to two days: baseline, fixtures, evaluator, verifier feasibility and budgets.
2. Demand-to-agent runner, one day: schema, funded trigger, restricted workspace and run log.
3. Creation run, one to three days: bounded investigation, local revisions, code and formal evidence.
4. Evaluation, one to two days plus proving: reproduction, independent checks, review, holdout and verdict.
5. Acceptance and reuse, one to two days: bounty payment, registry, fresh proof job and final report.

These are planning estimates with prover access assumed. Prepare the apparatus before a short hackathon. Budget exhaustion is a recorded outcome.

```text
demand/spec.json                 frozen requirement and terms
demand/registry-snapshot.json    existing capabilities
agent/runner/                   funded trigger, tool limits, run log
candidate/                      agent-produced code and package
formal/                         theorem and evidence
evaluation/policy.json          rules and evaluator image hash
evaluation/reports/             verdicts and reproducible evidence
contracts/                      bounty, registry, usage escrow
reuse/                          clean integration and fresh proof job
results/report.md               outcome, costs, interventions
```

These paths are proposed, not implemented. Private holdout storage lives in the evaluator's separate environment.

## 14. Demo

1. Buyer posts the outcome and funds the bounty.
2. Agent identifies a gap, commits a hypothesis and creates a candidate.
3. Evaluator shows correctness, formal scope and actual measurements.
4. Passing verdict releases the bounty and registers the asset.
5. A new job installs the asset, proves a fresh input and pays a usage fee.
6. Show a reuse or decline control so every request does not mint an asset.

Long creation/proving stages may use a clearly labeled recording. Show real manifests and transactions. Never present prerecorded work as live latency.

## 15. Brief flaws

- Sponsored demand does not establish external customer interest.
- Evaluator signatures authenticate reports, not measurement honesty.
- Formal model correctness leaves an implementation gap.
- Human assistance and reused code need explicit attribution.
- Search may miss existing solutions; publish the search scope.
- Success-only bounties leave creators exposed to failed-work costs.
- Open modules can earn no royalties when used elsewhere.
- Full proof evaluation may dominate cost and elapsed time.
- One creation and one reuse do not establish a continuous market.

**First build:** a funded demand specification, working baseline and creator runner that can choose reuse, compose, create or decline. Accepted asset registration follows evaluation.
