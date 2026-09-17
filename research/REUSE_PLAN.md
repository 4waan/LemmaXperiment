# A cheaper build path: reuse decisions and integration resources

Checked September 16, 2026. This supplements [TOOLING.md](TOOLING.md), [the production plan](ROBINHOOD_CHAIN_PROD.md) and [asset certification](ASSET_SCOPE_AND_CERTIFICATION.md). Recommendations below prioritize the existing Experiment 01, not a replacement experiment. No dependencies were installed, accounts funded or deployments made during this research.

## 1. Decision

Keep our existing RSP/SP1 apparatus and reuse mature verification, signature, proof-search and provenance tools. Build only the market-specific connections: funded demand, exact artifact identity, compatibility policy, evaluation acceptance, agent procurement and payment allocation.

The cheapest useful product does not need a new prover network, encryption protocol, wallet infrastructure, graph database or theorem search engine. Dependencies earn their place when they remove more work than they introduce.

## 2. What we already have

The current [results record](LemmaXperiment/results/report.md) documents a compressed proof for Ethereum block 20600066, its Groth16 wrap, and positive and negative verifier calls on Arbitrum Sepolia. It also records development inputs and 31 independent trie fixtures passing against both upstream pointer and arena backends. These are recorded results inspected in this session, not tests rerun by this research.

The [onchain verification record](LemmaXperiment/apparatus/runs/wrap-20600066-groth16-35051478400/onchain-verify.md) explicitly says view calls only, no transaction. It is valuable integration evidence; it is not a deployed marketplace or paid reuse job.

Preserve:

- `LemmaXperiment/apparatus/prover/`: existing host wrapper and proof artifacts.
- `LemmaXperiment/apparatus/INTERFACES.md`: the actual StateTries integration seam.
- `LemmaXperiment/evaluation/harness/`: independent fixtures and backend checks.
- `LemmaXperiment/apparatus/pins.json`: exact dependency identity.
- `proof_graph_sim.py` and `queueing_sim.py`: existing planning tools, not certified live pricing or scheduling engines.

The creator, formal, candidate and contract directories still contain scaffolding; the end-to-end experiment verdict and paid reuse remain unresolved in the results record. Some README status text predates the apparatus progress. Read the evidence records before treating an outline-only banner as current status.

## 3. Highest-value reuse decisions

### A. Ethereum execution and proving: retain RSP and SP1

Resources: [RSP](https://github.com/succinctlabs/rsp), [SP1 contracts](https://github.com/succinctlabs/sp1-contracts), [SP1 project template](https://github.com/succinctlabs/sp1-project-template).

Reuse: execution machinery, proving backend, serialization already pinned in our wrapper, standard verifier and fixture-based verification examples. RSP is an existing Ethereum block-execution proving implementation. Its repository metadata reports Apache-2.0.

Our adapter: bind an accepted module release and approved guest identity to each fresh job. The existing proof's public values commit a block header; do not assume they already bind our market demand, module digest or payout terms. That linkage remains custom work.

Cost-saving rule: use execute-mode correctness and profiling during iteration. Produce expensive proofs at meaningful gates after a candidate survives those checks. Preserve proof artifacts and do not regenerate the same proof merely to replay a demo. A fresh-work claim still requires a fresh compatible input and proof. PGU reduction alone is not measured wall-clock or dollar savings.

Deployment: reuse an existing supported verifier after checking runtime code, circuit selector, gateway route/freeze policy and positive/negative fixture calls. The recorded Sepolia address is not automatically valid on Robinhood. Where absent, deploy the exact upstream compatible verifier, not a newly written verifier.

License check: the repository-level GitHub license field was empty, but the inspected v6.1.0 `SP1VerifierGroth16.sol` has an MIT SPDX header. Inspect headers of every imported file at the selected pin; do not infer repository-wide licensing from one header.

Integration estimate: low additional work for the retained baseline; medium for market binding and candidate integration. These are planning categories, not tested estimates.

### B. Contract building blocks: OpenZeppelin plus Foundry

Resource: [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts), MIT according to repository metadata.

Reuse: typed signing, signature verification, access control, safe token transfers, reentrancy protection and pause primitives. Retain Foundry rather than adding a second contract toolchain.

Our work: CreationBounty, ModuleRegistry and UsageEscrow behavior, evaluator authorization, immutable job terms, deadline/refund logic, replay protection and contributor shares. OpenZeppelin does not implement those business rules for us.

Acceptance spike: valid acceptance pays once; wrong chain, contract, demand, module digest or nonce fails; expiry refunds according to terms; the escrow remains solvent across all permitted transitions. Library reuse does not remove the need to test our composition.

Integration estimate: low for primitives, medium for domain logic.

### C. Certification transport: EAS, with a bounded decision gate

Resources: [EAS contracts](https://github.com/ethereum-attestation-service/eas-contracts), [EAS SDK](https://github.com/ethereum-attestation-service/eas-sdk). Both report MIT.

Reuse candidate: schemas, attestation records, issuer identity, reference IDs, expiration/revocation fields and SDK signing/encoding. This removes work on a generic certificate envelope. EAS does not run Lean, establish benchmark honesty or enforce our buyer policy.

Our schema: artifact digest, claim type, statement/profile digest, dependency-lock digest and evidence digest. Our policy decides which issuer and evidence method satisfy a demand. A reusable certificate and a demand-bound payment authorization remain separate objects.

Default for the existing experiment: keep its planned EIP-712 evaluator receipt and OpenZeppelin verification. Add EAS only if a short spike confirms that the exact selected chain has a usable deployment or an inexpensive deployment path, and our acceptance/revocation checks become simpler. Do not deploy an entire attestation platform solely for one certificate.

Spike exit: issue, encode, fetch, validate issuer/profile, revoke and reject the revoked claim through the buyer path. Check SDK/contract versions and chain-specific addresses. An offchain attestation does not automatically give the escrow an onchain revocation check. Resolve that path before adopting it.

Keep a small `CertificationAdapter` boundary so an EAS UID can be added later without replacing evaluators or demand terms.

Integration estimate: low to medium on an already-supported deployment; higher on an unverified chain. EAS signing is offchain, but publication/revocation transactions and hosting still have costs.

### D. Formal search and checking: Lean tooling, not a new search engine

Resources: [Mathlib](https://github.com/leanprover-community/mathlib4), [Loogle](https://github.com/nomeata/loogle), [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp).

Reuse: Mathlib and Loogle for existing theorem discovery; lean-lsp-mcp for goals and diagnostics during authoring; pinned Lean checking for acceptance. Metadata reports Apache-2.0 for Mathlib and Loogle, MIT for lean-lsp-mcp.

Our work: manifest describing the actual exported theorem, applicability checks, allowed assumptions, evaluated downstream tasks and purchase economics. Search free compatible libraries before buying or creating. Do not claim that a renamed free theorem is newly invented paid knowledge.

Scope the authoring MCP tools to the public development workspace. A tool exposing web search must not silently bypass the creator's frozen-data policy. Separate operator documentation tools from the benchmarked creator's allowed tools.

Avoid training a retrieval model or deploying a vector database for the pilot. Start with exact profile filters and type/statement search. Use local search for confidential goals.

Integration estimate: low for diagnostics; medium for a reproducible procurement evaluation. The installed Lean checker can be useful, but a second invocation of the same trusted implementation is a recheck, not proof of independent implementation diversity.

### E. Independent trie evidence: keep py-trie fixtures

Resource: [py-trie](https://github.com/ApeWorX/py-trie), MIT according to metadata.

Reuse: our existing oracle fixtures, malformed input cases and comparison harness. Do not write another MPT implementation just to evaluate one.

Our work: connect the candidate to the frozen harness and add only cases justified by changed semantics. The oracle can disagree with the candidate; disagreement must be investigated, not resolved by automatically changing expected outputs.

Integration estimate: low because the fixtures already exist.

### F. Agent authority: adapt our own Lattice code

Existing local sources:

- `/Users/awaansiddiqui/hedera2026/venue/agent/runtime/mandate.mjs`
- `/Users/awaansiddiqui/hedera2026/venue/agent/runtime/policy.mjs`
- `/Users/awaansiddiqui/hedera2026/venue/agent/runtime/signer.mjs`
- `/Users/awaansiddiqui/hedera2026/venue/agent/runtime/transaction-projector.mjs`
- `/Users/awaansiddiqui/hedera2026/venue/agent/runtime/receipt-store.mjs`

These files exist, and selected source was inspected. Reuse their separation of authority, transaction projection and durable receipts. The signer directly depends on trading actions such as commit/reveal/cancel and context-specific schemas. Porting requires replacing those projectors and authorization predicates with our demand/job actions. It is not just a network URL swap.

Keep the creator away from evaluator keys and transaction-signing authority. Reuse the existing chosen model runtime rather than integrating multiple agent frameworks for the demo. A model subscription or open-source SDK does not imply free inference.

The local canonical JSON helper sorts object keys but is not established here as a complete RFC 8785 implementation. Do not silently change hashes for old records. For new cross-language manifests, adopt one pinned encoding and shared test vectors.

Integration estimate: medium. Port relevant denial and replay tests alongside logic; old-chain tests are not sufficient evidence for the new action vocabulary.

### G. Evidence provenance: GitHub's existing attestation tools

Resource: [attest-build-provenance](https://github.com/actions/attest-build-provenance). Its current README recommends [actions/attest](https://github.com/actions/attest) for new integrations; the former is now a wrapper.

Reuse: signed workflow/artifact provenance and existing GitHub CLI verification. Record workflow identity, commit and artifact digest. This establishes origin, not the truth of a speedup or formal claim.

Keep the evaluator workflow and acceptance policy outside creator control. Pin third-party Actions by reviewed immutable commit. Use existing runners for reproducible build/test work where they fit; heavy proving still has runtime and memory limits.

The docs state that standard hosted runners are free for public repositories; private use, storage and larger runners have separate conditions. Artifact attestations in private repositories require an eligible plan. Do not publish private evidence or holdouts just to obtain free execution. [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Integration estimate: low for public build artifacts. Confirm the account plan for private evidence before committing to the feature.

### H. Indexing and storage: keep the small design

Use our existing ledger/static-explorer design, one existing EVM client library, bounded log retrieval and content hashes. Retain block hashes, transaction/log identity and a replay cursor. Rebuild or roll back on reorgs. A hash-chained JSONL log is not a substitute for verifying canonical chain receipts.

A GitHub release or ordinary object store can distribute public artifacts. Verify bytes against the pinned digest and keep backups. A URL is not immutable availability, and an Actions artifact can expire.

Upgrade resource: [Ponder](https://github.com/ponder-sh/ponder), MIT according to metadata. It is a reasonable indexing framework when multiple users and query load justify its database/runtime. It is unnecessary just to display a small number of paid jobs.

Do not add Neo4j or a general graph service for a few releases. Store typed edges in manifests and perform bounded graph traversal offchain. Fix payment recipients at job creation; settlement should not traverse an unbounded dependency graph.

Integration estimate: low for a pilot ledger, medium for a hosted indexer.

## 4. Competitor reuse: what Fangorn actually offers today

Resources: [Fangorn SDK](https://github.com/fangorn-network/fangorn), [contracts](https://github.com/fangorn-network/contracts).

The current SDK README describes namespace graphs, content addressing, commit history and onchain pointers. It explicitly says encrypted fields and purchase/claim/fetch settlement are not available in the current release. Its supported-network section lists Arbitrum Sepolia. This narrows what we can reuse compared with its earlier hackathon pitch.

Recommendation: optional adapter spike after the core loop works. Publish a sample manifest and typed dependency edges, fetch from a clean buyer, validate digests, and recover a previous version. Keep only if this removes more code than its storage, chain and key-management dependencies introduce.

SDK metadata reports MIT. The separate contracts repository returned no detected license, and its recursive file listing showed no license file. That is an unresolved reuse condition, not proof that every file is unlicensed. Check individual headers or obtain explicit terms before copying code. The contracts README also documents a deployment-argument mismatch, so it is not a turnkey deployment path.

Do not transplant its complete stack into the MVP. Our novel work is claim evaluation and procurement; preserving that boundary makes future interoperability easier.

## 5. Payment and identity integrations to defer

Resource: [x402](https://github.com/coinbase/x402), Apache-2.0 according to metadata. Use later for immediate paid HTTP reads or invocations when the selected chain, token and facilitator are supported. It does not replace delayed creation-bounty acceptance, proof verification or escrow refunds. Adding it now would create a second payment path before our first is complete.

Similarly, use agent identity standards as references when needed; a wallet address and signed provider manifest suffice for a closed pilot. Do not deploy our own generalized reputation protocol. Defer account-abstraction providers unless an actual sponsor requirement or operator need justifies their integration.

Privacy: keep the first artifacts/results public as planned. Private delivery introduces key custody and fair-exchange obligations. Adopt a supported service only when a real buyer needs privacy, with a clear trust model and measured delivery cost. Avoid presenting unfinished Fangorn features as that service.

## 6. Compute spending policy

The existing report records hours of CPU proving for the small baseline. Free runner charges do not mean free time. Conversely, network or rented GPU proving is not guaranteed to cost only cents once setup, failures, wrapping and data transfer are included.

The [Succinct quickstart](https://docs.succinct.xyz/docs/sp1/prover-network/quickstart) requires a funded PROVE requester and compatible SDK. Its sample log contains auction fees; those are an example, not a current binding quote. Request a quote for our pinned guest, proof mode and input before spending. Do not reuse TOOLING.md's earlier per-proof estimate as a guaranteed current price.

Recommended sequence:

1. Reuse cached development witnesses and build outputs.
2. Run cheap correctness and execute-mode profiling first.
3. Reject noncompetitive candidates before expensive full proving.
4. Preserve the experiment's agreed evaluation gates. If budgets require fewer trials, revise the protocol explicitly before evaluation and label the evidence limit.
5. For remaining proofs, compare an actual network quote against the measured runner completion time and a bounded GPU rental quote.
6. Impose max spend, wall-time and retry caps. Never automatically repeat a failed paid job indefinitely.

No new paid infrastructure is required just to implement local contracts, schemas, fixtures and the public demonstration UI. Actual agent inference and full proving remain separately metered costs. This report does not promise a zero-cost finished experiment.

## 7. The custom work we should retain

Only build the behavior specific to this product:

1. A capability/demand manifest that binds exact profiles, deliverables, deadlines and terms.
2. Evaluator adapters that produce narrowly scoped acceptance evidence.
3. An agent procurement policy comparing compatible reuse, creation and decline.
4. Domain contracts enforcing funding, accepted registration and fresh-job payment.
5. Typed dependency records and agreed contributor allocation.
6. A buyer-visible evidence view that explains acceptance, rejection and measured cost.

Reuse tools underneath these boundaries. Avoid outsourcing acceptance semantics to a generic attestation badge or a framework's reputation number.

## 8. Integration order and stop conditions

**First session:** preserve existing pins and artifacts; inventory exact reusable local files; implement one signed acceptance payload with OpenZeppelin verification. Exit: replay and mismatched subject fail.

**Second session:** connect the frozen evaluation output to that payload and registry. Evaluate EAS only within a bounded spike if its records remove work. Exit: accepted evidence references the exact release; revoked/invalid claims are handled by explicit policy.

**Third session:** connect the restricted buyer/creator loop and existing ledger. Exit: the agent can choose an existing compatible capability or decline, without access to evaluator keys.

**Then:** prove and settle a fresh accepted job under the retained experiment; record reuse and creation costs separately. Exit: the receipt maps to the actual verified public statement and accepted program identity.

Treat sessions as dependency order, not promised implementation duration. Do not spend days integrating optional graph storage, encryption or identity while these exits remain unmet.

## 9. License and adoption checklist

Repository metadata was checked through GitHub's public API, plus selected source headers and README contents. It is an initial filter, not a full dependency-license audit.

Before importing any code: pin an immutable release/commit, inspect LICENSE/NOTICE and relevant file headers, retain attribution, inspect transitive dependencies, and record local patches. Do not automatically upgrade our working SP1/RSP pins to latest. The target chain and compiler must pass a small integration check before a dependency becomes part of the deployment plan.

Immediate reuse: existing apparatus; upstream compatible SP1 verifier; OpenZeppelin; pinned Lean; py-trie fixtures; relevant local authority/receipt patterns.

Conditional reuse: EAS, Fangorn graph SDK, Ponder, paid prover backend.

Defer: new encryption system, new agent framework, new prover network, full graph database, autonomous valuation engine, custom chain and ten asset-specific markets.
