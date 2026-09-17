# ProofMarket: Arbitrum hackathon architecture blueprint

Next build: follow [Experiment 01](EXPERIMENT.md) before implementing this marketplace. The experiment tests funded demand triggering agent creation, independent acceptance and paid reuse inside an existing Ethereum proving pipeline; the architecture below remains a possible later system.

Prepared 15 September 2026 from the supplied study. This is a proposed design, not a claim that the system or its benchmarks already exist. The workspace was empty at review time.

## 1. Recommendation

Build a marketplace where an application funds a specific computation proof, independent workers quote for the job, and an Arbitrum contract pays only after cryptographic verification. Add versioned proof packages with provenance and explicit revenue splits.

The promising part of the study is the combination of proof demand, automated suppliers, reusable software, and verifiable settlement. Its weakest assumption is that a Lean theorem automatically becomes a reusable zkVM execution proof or makes proof generation cheaper. The architecture must keep those objects separate.

**Hackathon pitch:** An Arbitrum marketplace for verifiable computation, where autonomous workers compete for funded jobs and reusable proof packages earn a share of successful work.

**First customer hypothesis:** An application developer who needs batch attestations over committed data and wants to outsource proof generation. Ethereum client operators are a future customer hypothesis, not an established buyer.

## 2. Corrections to the study

1. **EIP-8025 is a draft, not installed market demand.** Its opt-in design supplies no protocol payment incentive. A sponsor or application must actually fund your jobs. Do not draw Ethereum itself emitting paid requests. [EIP-8025](https://eips.ethereum.org/EIPS/eip-8025)
2. **Proof delivery is not consensus acceptance.** An application receiving a valid proof is distinct from a consensus client supporting a particular execution-proof format. Keep that integration explicitly future scope. [EIP-8025](https://eips.ethereum.org/EIPS/eip-8025)
3. **Lean Ethereum and Lean 4 are different names.** `leanEthereum/leanSpec` is a Python protocol specification and test-vector project. `NyxFoundation/formal-leanSpec` is a separate Lean 4 formalization. Neither name establishes complete formal verification of today's Ethereum consensus. [leanSpec](https://github.com/leanEthereum/leanSpec), [formal-leanSpec](https://github.com/NyxFoundation/formal-leanSpec)
4. **Arbitrum's SP1 work supports the technical direction, not your economics.** The reported work proves Arbitrum execution, including Stylus. It does not establish that Lean assets reduce proving cost or that an application automatically inherits a zkVM prover. [Arbitrum technical announcement](https://blog.arbitrum.io/zk-settlement-is-coming/)
5. **Keep bridges out of the fast proof path.** Canonical child-to-parent messages await assertion confirmation. Send proof bytes directly to the consumer, which verifies them itself; settlement can remain on Arbitrum. [Arbitrum messaging documentation](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l2-to-l1-messaging)

## 3. First workload: batch Merkle membership

Prove that every item in a requested batch belongs to a specified binary Merkle tree. Use a fixed schema and hash function, bounded tree depth, ordered item indices, and explicit leaf/internal-node domain separation.

This is a deliberately narrow Ethereum-style building block. It is not an Ethereum execution proof, an Ethereum account/storage trie proof, or an SSZ proof unless those exact formats are implemented separately.

### A concrete consumer

A `BatchEligibilityConsumer` on Arbitrum has a campaign root chosen by its operator. It requests proof that a committed list of participant leaves belongs to that root. After settlement, it reads the verified result from `ProofMarket` and records the batch as eligible.

This demonstrates a real application consuming the result without requiring Ethereum consensus changes. Root authenticity comes from the campaign operator in this MVP. Merkle membership alone cannot prove that a root represents canonical Ethereum state.

### What the guest proves

- Inputs: root, ordered leaf/index list, sibling paths, and job binding fields.
- Checks: schema version, bounds, index validity, exact path length, and correct root reconstruction for every leaf.
- It recomputes the public input commitment from the actual inputs.
- It commits a public result with `success = true` only if every check passes.

Start with one straightforward Rust guest. Later compare it with a guest that verifies a shared-node multiproof. Both must implement the same membership relation and produce the same result schema. A multiproof may save repeated hashing; whether it reduces total proving cost is an experiment.

For small batches, direct onchain membership checking may be cheaper. Benchmark against it. This first workload tests the architecture; it does not prove a profitable market.

## 4. System map

```text
Application / sponsor
    | funds request and fixes accepted statement
    v
ARBITRUM
    ProgramRegistry        PackageRegistry
    approved guest keys    manifests, dependencies, payees
              \             /
                ProofMarket
             escrow + assignment
                    |
                    | events
                    v
OFFCHAIN
    Indexer + quote API <------ Worker A / Worker B / Worker C
                    |            |
           requester selects     | fetch committed input
                    |            v
                    |        Rust guest in SP1
                    |            |
                    |        proof + public values
                    |            |
                    v            v
ARBITRUM         ProofMarket --> VerifierAdapter --> SP1 verifier
                    |
             verified result + withdrawal credits
                    |
              Application consumer

BUILD-TIME SIDE PATH
    Lean theorem -> kernel check -> evidence report
    Rust implementation -> conformance tests -> immutable package manifest
    Manifest binds these artifacts; it does not prove translation correctness.

LATER
    Worker -> direct proof delivery -> Ethereum-side consumer
    Arbitrum continues to handle payment.
```

### Layer responsibilities

**Onchain:** Ownership and authorization, exact job commitments, accepted verifier versions, escrow, assignment, deadlines, proof acceptance, single settlement, revenue credits.

**Offchain:** Input acquisition, package storage, bidding, scheduling, expensive proving, indexing, telemetry, and user notifications.

**Build time:** Lean checking, Rust compilation, guest key derivation, dependency resolution, semantic conformance tests, and package release approval.

The backend can affect availability and quote visibility. It must not be able to declare an invalid proof valid or withdraw customer escrow.

## 5. Contracts and their boundaries

### ProgramRegistry

Registers immutable program versions containing:

- `programId`, workload relation ID, public-value schema ID.
- Guest executable hash, program verification key, proof system/version.
- Verifier adapter address and verifier implementation/version commitment.
- Associated package version and manifest hash.

MVP registration is curator controlled. Registry approval means the team reviewed the program's intended relation; cryptographic verification alone cannot establish that the chosen guest implements the customer's intended computation.

Never replace the meaning of an existing program ID. Publish a new version. Freeze each job's accepted programs at creation. Check any external verifier gateway's upgrade authority before treating its behavior as immutable.

### PackageRegistry

Registers immutable, content-addressed manifests. Each package includes executable artifacts, evidence, compatibility, dependencies, licensing metadata, and proposed payees.

Allow a composite package to reference older package versions. It does not burn or merge its dependencies. Require an acyclic graph, deduplicate shared dependencies, and flatten the final payee schedule before job acceptance. Use a proposed MVP limit of eight unique payees per job to bound gas.

An optional ERC-721 can represent control of future package commercial terms. Existing accepted jobs keep their snapshotted payees. The token grants only rights explicitly defined by the protocol or license; it does not create exclusivity over public mathematics or hide downloadable source code.

### ProofMarket

Owns the job state machine and native testnet ETH escrow. Suggested external operations:

- `createJob(spec, acceptedPrograms)` with funded maximum reward.
- `acceptQuote(jobId, signedQuote)` callable by the requester.
- `activateAssignment(jobId)` callable by the chosen worker with its bond.
- `submitProof(jobId, publicValues, proofBytes)` callable by anyone, paying the assigned worker.
- `expireJob(jobId)` and `cancelOpenJob(jobId)` under defined timing rules.
- `withdraw()` for accumulated credits.

Keep payment accounting in this contract for the MVP. A separate treasury contract adds little value yet.

### VerifierAdapter

Calls the pinned proof verifier with the expected guest key and exact public-value bytes. SP1 exposes verification through a program key, public values, and proof bytes. After verification, the market must still check that those public values match this job. [SP1 contract interface and integration](https://github.com/succinctlabs/sp1-contracts)

No admin override that marks a proof valid. Pause new requests if needed; preserve refunds for outstanding jobs.

### BatchEligibilityConsumer

Reads a settled result for its own job ID, checks the campaign root and ordered batch commitment, and records consumption once. Use a separate call after settlement, so consumer failures cannot block worker payment.

## 6. Core data contracts

Define canonical byte encoding, integer widths, field order, domain tags, and hash function before implementation. Do not hash arbitrary JSON serialization.

```text
JobSpec
  requester, consumer, requesterNonce
  settlementChainId, marketAddress
  sourceDomain, workloadRelationId, inputSchemaId
  root, orderedBatchCommitment, inputCommitment
  acceptedProgramIds
  maxReward, acceptBy, activateBy, proveBy
  bondRequired

Quote
  jobId, worker, programId, packageVersion
  allInPrice, expiry, quoteNonce
  payoutScheduleHash

PublicResult
  settlementChainId, marketAddress, jobId
  sourceDomain, workloadRelationId, inputSchemaId
  inputCommitment, root, orderedBatchCommitment
  itemCount, success

PackageManifest
  packageVersion, artifactHashes, sourceCommit
  programId, guestHash, programVKey
  proofSystemVersion, publicSchemaId
  dependencyVersions, licenseReference
  leanToolchain, theoremStatementHash, axiomReportHash
  conformanceReportHash, benchmarkReportHash
  proposedPayees
```

The public statement binds the proof to this chain, market, job, source domain, and requested computation. The guest computes commitments rather than echoing unchecked host values. `jobId` binds immutable commercial terms held onchain. Package identity is resolved through the approved program mapping, not trusted from a worker's arbitrary string.

Private witness paths may remain offchain. Public values and proof bytes must be available for verification. Witness access must be arranged before a worker activates its assignment; for the hackathon, use public fixtures.

## 7. Full job lifecycle

```text
OPEN -> RESERVED -> ASSIGNED -> SETTLED
  |        |           |
  |        |           +-> EXPIRED
  |        +-> EXPIRED
  +-> CANCELLED or EXPIRED
```

1. The requester uploads input data and funds the maximum reward. `OPEN` contains immutable commitments and accepted program versions.
2. Workers retrieve input, estimate costs, and return domain-separated signed quotes. Quotes are offchain; the API is replaceable.
3. The requester chooses an eligible quote before `acceptBy`. The contract verifies signature, nonce, expiry, price cap, program compatibility, and the snapshotted payout schedule. State becomes `RESERVED`.
4. The worker activates before `activateBy` and deposits the agreed bond. State becomes `ASSIGNED`. No-show reservation expiry refunds the requester; there is no bond to slash before activation.
5. The worker generates and locally verifies the proof, then submits it before `proveBy`.
6. The contract verifies the proof and all public bindings. It changes state to `SETTLED`, credits worker/package payees, returns the bond, and credits unused escrow to the requester. All changes occur atomically.
7. The consumer reads and uses the verified result. An indexer updates package receipts and worker statistics from events.

**Failure rules:** An invalid submission reverts and leaves the assignment active until its deadline. Expiry after activation refunds escrow and credits the worker bond to the requester under the pre-agreed rule. An open job may be cancelled; a reserved or assigned job may not be cancelled at will. Failed jobs are terminal in the MVP; repost with a new job ID to retry.

**Boundary rule:** Submission is permitted at or before `proveBy`; expiry only after it. Apply similarly unambiguous boundaries to reservation and activation.

**Accounting rule:** Refunds and payouts are withdrawal credits, protected against reentrancy. Maintain solvency: contract balance must cover active escrow, active bonds, and all unpaid credits.

**Mempool copying:** Anyone may relay the exact proof, but payment always goes to the stored assignment and snapshotted payees. Copying a transaction cannot redirect earnings.

## 8. Reusable assets, Lean, and revenue

There are three distinct artifacts:

1. A **formal theorem** establishes a property of a specified mathematical model.
2. A **program package** supplies runnable code and its build/evidence manifest.
3. A **runtime proof** certifies a particular execution of a particular program on committed inputs.

For this build, Lean belongs to the package's assurance process. Prove that an optimized traversal or multiproof verifier agrees with the simple membership specification under stated bounds and hash assumptions. Pin the Lean toolchain, audit theorem dependencies and axioms, and reject unfinished proof placeholders.

A checked Lean model plus passing Rust tests is not an end-to-end proof of Rust or compiler correctness. Record that gap in the evidence panel. Do not run Lean inside SP1 for the MVP.

### What can plausibly improve performance

- Less repeated hashing through shared-node multiproofs.
- Faster guest code with the same verified statement.
- Cached witness construction, when the exact cache key remains valid.
- Future recursive proof reuse where verified child statements exactly match required subcomputations.

These mechanisms differ. Recursive aggregation verifies child proofs; an NFT bundle only groups references. A static lemma cannot replace fresh computation for an unrelated block or input.

### Payment model

Use requester-approved splits over the accepted all-in quote. For example, a proposed 90% worker and 10% package-creator split is a configurable demo policy, not a measured market rate. Settlement gas is paid by the submitter and should be priced into the quote. Unused maximum reward returns to the requester.

Royalties are enforceable for jobs settled through this market. They are not automatically enforceable when someone copies open code and uses another market.

Record package-associated completed jobs and earned fees. Call them usage receipts, not proof that the package caused a speed improvement. Avoid the study's multiplicative utility score as a pricing oracle; self-funded jobs can inflate it.

## 9. Worker and backend design

**Worker loop:** Discover job, validate compatibility, fetch witness, estimate cost, sign quote, wait for reservation, activate, prove, verify locally, submit, track settlement.

Run two or three workers with separate accounts. A baseline worker uses the simple guest. An optimized worker uses the approved multiproof guest. A third can represent a different price/queue policy without pretending it uses different cryptography.

Use deterministic limits for maximum spend, supported programs, bond size, and transaction signing. An optional LLM can propose a bid policy or explain choices from telemetry; validated structured output passes through these limits. Ordinary scheduled workers are autonomous software agents, but should not be marketed as AI if no model is used.

**Suggested stack:** Rust/SP1 guest and worker runner; Solidity/Foundry contracts; TypeScript API and event indexer; PostgreSQL for job projections and quote history; object storage for artifacts; React interface with wallet support. Pin versions during the first verification spike.

**Minimal API:** `GET /jobs`, `GET /jobs/:id`, `POST /quotes`, `GET /packages/:id`, and a server event stream. The backend supplies transaction parameters; users/workers sign their own transactions. No backend endpoint is authoritative for settlement status.

**Operations:** Index events idempotently by chain/block hash/transaction/log index, roll back reorged projections, and rebuild from chain state. Resume proving/submission after worker restart. Apply job input bounds and isolate artifact execution. Never give an LLM unrestricted signing keys.

**Stylus decision:** Use Solidity for the first settlement loop. Add Stylus only for a measured useful contract component, such as batch commitment validation, after confirming support on the selected chain. Rust guest execution in SP1 is not Stylus execution.

## 10. Product screens

1. **Create job:** Select workload/package compatibility, root, input batch, maximum payment, and deadline. Show exactly what will be proved.
2. **Live market:** Quotes, worker accounts, estimated completion, selected assignment, and event-derived state. Distinguish quote estimates from observed durations.
3. **Job detail:** Input commitment, program version, proof verification transaction, result, credits, and consumer receipt.
4. **Package explorer:** Versioned dependency graph, evidence scope, benchmark conditions, royalty policy, paid receipts, and artifact links.
5. **Worker console:** Queue, accepted quotes, proof progress, balances, failures, and measured costs.

Keep proof-generation progress separate from chain inclusion and finality. Do not display a success badge merely because a local worker returned a proof.

## 11. Build sequence and completion gates

### Gate 1: Proving feasibility

Implement one membership guest, generate a real proof, and verify it through the intended verifier on the chosen Arbitrum testnet. Measure time, proof size, and transaction gas. Confirm prover hardware/service access before adding the marketplace.

**Exit:** A valid proof succeeds; a changed public root fails. If this gate fails, the core architecture has not been demonstrated.

### Gate 2: Funded settlement

Implement registry, escrow, quote acceptance, worker activation, proof settlement, withdrawals, expiry, and a consumer receipt. Initially use one worker.

**Exit:** A real funded job pays exactly once; invalid proofs cannot pay; timeout refunds work.

### Gate 3: Competition and packages

Add multiple worker accounts, quote UI, immutable manifests, dependency references, revenue splits, and event indexing.

**Exit:** A requester selects a quote and successful settlement credits its exact agreed recipients.

### Gate 4: Evidence and demo

Add one meaningful Lean theorem/evidence report, then compare the baseline and optimized package under matched inputs and hardware. Finish the package explorer and scripted demonstration.

**Exit:** The demo clearly separates real transactions, measured performance, estimates, and future features.

### After the hackathon

Add a stronger paid workload, external worker onboarding, recursive proof composition if useful, and independently verified performance data. Then consider direct Ethereum application verification. Full execution-proof client integration comes after witness acquisition, fork/program compatibility, delivery format, and latency have been demonstrated.

## 12. Proposed repository layout

```text
contracts/src/        ProgramRegistry, PackageRegistry, ProofMarket,
                      VerifierAdapter, BatchEligibilityConsumer
contracts/test/       settlement, binding, expiry, accounting tests
programs/membership/  baseline Rust guest
programs/multiproof/  optimized guest after baseline works
workers/              proof runner and quote policy
services/api/         quote relay and job queries
services/indexer/     event projection and reorg recovery
apps/web/             requester, package and worker views
packages/schema/     shared encoding rules and fixtures
formal/              Lean model, theorem and axiom report
artifacts/           versioned manifests and evidence references
benchmarks/          matched-input scripts and raw results
docs/                deployments, demo runbook and assumptions
```

These are proposed paths, not implemented files.

## 13. Verification and demo

### Meaningful checks

- Valid proof and expected public values settle once.
- Wrong root, job ID, chain, market, program key, schema, or result flag cannot settle.
- Expired/replayed quotes and unauthorized assignment changes fail.
- Copied proof submission never changes the payee.
- Timeout, unused escrow, bond return/forfeiture, and withdrawals conserve funds.
- Shared package dependencies are paid once; recipients cannot change mid-job.
- Independent membership fixtures and negative cases validate guest behavior.
- A worker restart resumes safely; repeated/reorged events do not duplicate UI records.

### Benchmark protocol

Use the same membership claims, tree sizes, input batches, prover version, hardware, and proof mode. Measure witness preparation, guest cycles, proving, proof wrapping, verification gas, and total elapsed time separately. Report cold and warm runs separately. Retain raw observations and use repeated runs before claiming an improvement.

Also compare direct onchain checking. Record package preparation cost separately rather than hiding it outside the measurement window. Do not attribute backend caching or stronger hardware to Lean theorem reuse.

### Demo narrative

1. Register a baseline package and its optional optimized variant with honest evidence labels.
2. Fund an eligibility proof request on Arbitrum.
3. Show two or three signed worker quotes and requester selection.
4. Generate the actual proof and show onchain verification.
5. Show worker/package credits and the application's consumed result.
6. Submit a modified-input proof or run an expiry case to demonstrate the boundary.

Use measured deadlines. The study's second-level timings and rewards are illustrative and must not appear as achieved results. A precomputed proof may be a clearly labeled fallback recording, but does not demonstrate live proving latency.

## 14. Flaws to resolve one by one

- **F1, first:** No demonstrated Lean-to-zkVM speedup. Benchmark one concrete algorithmic optimization.
- **F2, first:** No established paying customer. Fund the demo explicitly and validate one external buyer.
- **F3, first:** Runtime proof validity depends on the correct registered program and authentic input root. Pin both trust boundaries.
- **F4:** Public artifacts are copyable; token ownership is not an exclusive computation capability. Define narrow rights.
- **F5:** Package receipts cannot establish causal performance contributions. Keep rewards contractual initially.
- **F6:** Tiny membership jobs may cost less to verify directly. Measure the crossover before claiming savings.
- **F7:** Ethereum proof delivery, L2 settlement, and L1 finality have different clocks. Separate them.
- **F8:** Prover hardware and proof wrapping may dominate latency. Run the feasibility spike first.
- **F9:** Bundling dependencies is not cryptographic aggregation. Implement and label them separately.
- **F10:** Quote selection/indexing and program approval start centralized. Make those roles explicit in the demo.
- **F11:** An assigned worker can stall; deposits only limit the economic damage. Keep timeout/refund paths complete.
- **F12:** Root reorgs, witness availability, and client compatibility expand sharply for Ethereum workloads. Keep that adapter outside the MVP.
- **F13:** Open House edition, current eligibility, and sponsor requirements are unspecified. Confirm the exact event before choosing a prize-target deployment.

The first three affect the thesis. The rest are bounded engineering or product decisions and do not need to block the initial vertical slice.

## 15. Arbitrum Open House positioning

Use Arbitrum as the actual coordination and settlement layer: funded jobs, permissionless submission of proofs, deterministic verification, and package revenue distribution. This gives the chain a concrete role.

The official London 2026 announcement lists relevant builder themes and Robinhood-focused tracks, but that edition's online buildathon ran May 25 to June 14 and the Founder House July 10 to 12. Those dates are already past at this review date. The supplied request does not identify a current edition, so prize eligibility and submission deadlines remain unverified. [Official London announcement](https://forum.arbitrum.foundation/t/arbitrum-open-house-london-2026/30975)

Default engineering target (superseded 16 September 2026): Robinhood Chain testnet, chain 46630, with our own `SP1VerifierGroth16` v6.1.0 deployment; verified live in [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md). Arbitrum Sepolia is a read-only cross-check of proof bytes and the fallback venue only. Do not build multichain settlement into the first version merely for a prize category.

**Recommended first action:** Make one real guest proof verify on the target chain. Then build the payment loop around it. That is the shortest route from this study to a credible end-to-end product.
