# EIP-8025 and an agent marketplace supplying Ethereum

Research date: September 15, 2026. Scope: protocol requirements, agent procurement, artifact economics and an implementable experiment.

## Executive assessment

An L2 marketplace can finance and distribute the reusable knowledge, software and services that agents use to build Ethereum's proving infrastructure. Its strongest product is a compatibility-aware procurement system: agents determine whether to reuse, buy, compose or create a capability, then settle agreed payments for accepted work.

EIP-8025 gives this thesis a concrete technical setting. It describes optional execution proofs, with no protocol incentive for generating them. Its draft status and supplementary validation role must remain distinct from future mandatory proving. [EIP-8025][s1]

The Ethereum Foundation's September 7, 2026 priorities explicitly describe a trajectory toward mandatory execution proofs, while allowing changes in fork ordering. Its companion assessment places EIP-8025 in A-tier for Hegotá. These support investment in tooling; they do not guarantee a launch date, customer budget or purchase of a particular artifact. [EF priorities][s2], [Hegotá assessment][s3]

**Recommended positioning:** An agent capability exchange on Robinhood Chain or Arbitrum that funds, evaluates and distributes reusable artifacts for Ethereum's proving ecosystem. Agents buy useful work when acquisition is cheaper or faster than recreation. Ethereum-facing systems eventually consume compatible outputs.

The immediate buyer is an agent operator, prover business, client team or sponsor. Ethereum is a protocol and security anchor, not an autonomous procurement department. Potential demand beyond theorems is credible, but each artifact category needs its own verification and licensing rules.

Evidence is current to September 15, 2026. Statements labeled design or inference are proposed architecture or analytical judgments. No prototype performance or customer adoption is asserted.

## 1. EIP-8025: what demand means today

Three meanings of demand need separate treatment.

**Protocol requirements:** what implementations must support if they participate in the optional-proof mechanism. These are technical obligations.

**Engineering demand:** work needed to implement, test, operate and improve those systems. This can exist before mandatory adoption.

**Commercial demand:** an identified party willing to pay for an artifact or service. It requires a customer, budget and acceptance conditions. Neither an EIP nor frequent block production supplies those automatically.

### Current technical workflow

#### 1. Notify and coordinate

The EIP-linked Proof Engine snapshot defines hooks for new payloads, fork-choice changes, asynchronous proof requests and proof verification. Its implementation is deliberately client dependent. A request is correlated with the payload-request root. [Pinned Proof Engine specification][s4]

Design consequence: an external provider adapter can sit behind a proof node. The agent marketplace should not replace consensus-client duties or invent incompatible payload identities.

#### 2. Prepare the witness

The execution host collects the material needed to execute without a full local state database at verification time. The pinned witness builder includes account/storage trie nodes, bytecode and ancestor headers, and checks its derived post-state root. It merges accessed nodes using a dictionary before serialization. [Pinned witness builder][s5]

This is important for the earlier experiment: some deduplication already exists in the reference pipeline. That does not prove every prover avoids all repeated decoding, but it rules out assuming that simple witness deduplication is an untouched opportunity.

#### 3. Run the execution guest

The pinned stateless implementation validates chain configuration, constructs witness-backed state and executes the payload request. Its result includes the payload-request root, validation success and chain configuration. The guest entry point decodes schema-prefixed SSZ input and rejects unsupported schema identifiers. [Pinned stateless implementation][s6], [guest entry point][s7], [SSZ definitions][s8]

Design consequence: a theorem, dataset or proof fragment only helps if it connects to this accepted computation. A valid proof about a different program does not satisfy it.

#### 4. Attribute the delivered proof

The consensus snapshot wraps an execution proof in a validator index and BLS signature. It checks active-validator status and signature before invoking proof verification. Its proof-size constant is 400 KiB, marked provisional. [Pinned beacon specification][s9]

An arbitrary agent wallet is therefore not a replacement for the validator identity used in this gossip path. External agents can supply work through an authorized operator's infrastructure; validator signing keys should remain in the validator's controlled signing service.

#### 5. Discover, propagate and retrieve

The networking snapshot adds proof-aware discovery, proof-type advertisements, a gossip topic, and retrieval by range or root. It bounds proof requests, filters duplicate deliveries and requires serving canonical-chain proofs back to the finalized checkpoint. [Pinned networking specification][s10]

Design consequence: there is room to sell reliable production, availability, historical retrieval and operations. A proof that becomes publicly gossiped is difficult to monetize as an indefinitely exclusive file. Service guarantees and sponsored production are more plausible products than exclusive ownership of that public proof.

### What remains unresolved in the draft itself

The EIP leaves the sufficient-proof count k open before Review and leaves supported proof types to local configuration. It also separates future load-bearing validation from today's supplementary path. Those are protocol decisions, not choices this marketplace can settle. [EIP-8025][s1]

## 2. A concrete specification compatibility problem

The inspected EIP snapshot is `ec5fdb982e101ed0262f68742429d230ca960ca3`. It links consensus specifications at `031e521f0a82b0e475ecfc13f79dd251a6284fc2` and execution specifications at `85fc20ca5937719a854472a87cb48d01ef1dffca`. [EIP source snapshot][s11]

The linked beacon snapshot defines `PublicInput` with only `new_payload_request_root`. The linked execution implementation's `StatelessValidationResult` also carries success and chain configuration. These inspected revisions do not expose an identical public-result shape. [Beacon snapshot][s9], [execution snapshot][s6]

The implication is a versioning and integration requirement, not evidence that a deployed client is broken. A marketplace cannot advertise generic EIP-8025 compatibility based on a project name. It needs an adapter manifest tying together the exact consumer revision, serialization schema, guest program and verifier behavior, followed by conformance tests.

Search-indexed branch pages can describe yet other interface shapes. Implementation work should use immutable source revisions and an explicit compatibility matrix. The source snapshots above were inspected as text; their test suites were not executed for this report.

## 3. What EIP-8025 does not supply

### Economic services intentionally outside the proposal

The proposed system below adds commercial functions around proving: budgets, creation bounties, supplier selection, licenses, contributor terms, payment escrow and delivery disputes. These are application responsibilities. They should not be described as defects that Ethereum must repair.

### Missing product infrastructure

A useful market also needs a searchable capability catalog, machine-readable compatibility, reliable artifact retrieval, version lifecycle management, measured performance evidence and a buyer's build-versus-buy policy.

None of those can be inferred from a cryptographic proof merely being valid. A proof of program execution does not establish a module's market value, license provenance, measured wall-clock speedup or developer authorship.

### Engineering needs already partly addressed elsewhere

Witness building, proof orchestration, recursion, optimized computation, formal verification and proof marketplaces have existing implementations. The product must integrate or improve them, rather than presenting their existence as a gap.

For example, the EIP-linked execution tree already has conformance tests covering witness state, bytecodes, headers and public keys. New agent-generated test assets should add missing cases or cross-implementation coverage; reproducing an existing test is not automatically a valuable invention. [Pinned conformance corpus][s12]

**Assessment:** the opening is an evaluated supply network for useful artifacts and services, with procurement and contribution accounting across agents. Whether customers pay for it remains an experiment.

## 4. The market has two speeds

### Development market

Agents buy lemmas, formal models, implementation modules, test corpora, migration adapters or expert evaluation. Creation and checking can take minutes, hours or days. The benefit is less development effort, fewer unsuccessful searches, stronger assurance or faster integration.

This is where the example of one agent fetching another agent's lemma fits most directly.

### Execution market

Already-approved capabilities perform fresh jobs under tight deadlines. Assets are prefetched, environments are warm, dependencies are installed, and access rights are established before a block arrives. The benefit is lower job cost, better completion time or increased reliability.

Runtime proof fragments are useful only when their exact statements match the required subcomputation. A proof from an unrelated block cannot stand in for new execution.

### Why the separation matters

A reusable theorem can save the creator hours without changing the final program's proving cost at all. Conversely, faster guest code may reduce proving time without reducing theorem-search effort.

Report these as separate metrics:

- Formal proof-development time and inference cost.
- Integration/build cost.
- Witness preparation time.
- Runtime proving and wrapping cost.
- End-to-end delivery latency.

The phrase proving time must always identify which of these is being measured.

## 5. Knowledge becomes an artifact through a verification contract

Knowledge is tradable when another agent can locate it, establish what it means, verify its relevant claims, acquire permitted access and use it through a defined interface.

A practical artifact has six parts:

1. **Identity:** immutable digest, creator/operator identity and release version.
2. **Meaning:** statement or interface, preconditions, outputs and intended workload.
3. **Material:** Lean source/proof term, code, data, executable or service endpoint.
4. **Evidence:** checker results, assumptions, tests and benchmark conditions.
5. **Compatibility:** exact toolchain, dependencies, input schema and consuming programs.
6. **Terms:** delivery mode, price, license, recipients, expiry and maintenance policy.

The token records specified rights and references. It does not contain the producing capability. Running code still requires a runtime, authorized inputs, compute resources and compatible verification.

### Artifact families

**Formal theorem package.** A statement, proof, dependencies and toolchain. Verify with the appropriate trusted kernel configuration. Economic value can come from avoiding duplicate proof development or maintaining compatibility.

**Verified implementation package.** Code plus a formal property and evidence relating the model to the implementation. It can improve runtime performance only through a concrete algorithmic or implementation change.

**Runtime proof artifact.** Proof bytes tied to program key and exact public statement. Reuse requires matching inputs and a compatible recursive verifier or consumer. Its usefulness is often narrow and time sensitive.

**Witness/data service.** Fresh state material or historical authenticated data. Verify against the required root and schema; a hash alone does not establish source authenticity or completeness.

**Test and counterexample corpus.** Inputs, expected behavior, provenance and target versions. Verify reproducibility and whether cases add coverage. Useful for development, with no implied runtime speedup.

**Adapters and build recipes.** Reproducible transforms between compatible interfaces, compilers or fork revisions. Verify equivalence and conformance. These may be commercially useful precisely because specifications change.

**Agent policies, tactics or model artifacts.** Search heuristics, solver configurations or inference components. Evaluate on held-out tasks, respect training/distribution rights, and treat measured success as statistical evidence rather than a mathematical guarantee.

Generalize the catalog schema across these families, but keep category-specific evaluators. There is no single proof check that establishes every kind of asset's usefulness.

## 6. The lemma purchase example, implemented honestly

Suppose agent B is formalizing a witness-validation optimization. It needs a property about an immutable lookup structure. Agent A has an appropriate lemma package.

B sends a structured request containing its goal expression, available hypotheses, Lean/toolchain revision, dependency lock, permitted axioms and maximum acquisition budget. The search service first checks local and free compatible libraries, then licensed/private listings.

Candidate retrieval can combine exact identifiers, type/statement search and embedding-based ranking. LeanDojo/ReProver already demonstrates premise retrieval for theorem proving, and Loogle already exposes search over Lean/Mathlib. Thus retrieval itself is established technology. The proposed market adds evaluated releases, private or commissioned supply, commercial terms and receipts. [ReProver][s13], [Loogle][s14]

B checks that the theorem applies through Lean elaboration and kernel checking in its permitted environment. A semantically similar title or embedding is not proof of compatibility. New assumptions, incompatible definitions or a different arithmetic model can make the lemma unusable.

If the package is acquired, B imports it and completes its theorem. A dependency extractor records the referenced declaration and its transitive proof dependencies. Record both reuse and actual acquisition cost. A paid download grants only the stated rights; it cannot force B to pay every time B reuses a retained copy.

**What this demonstrates:** agent-to-agent knowledge procurement can reduce formal-development effort. It does not yet demonstrate cheaper Ethereum execution proofs.

Lean Ethereum's `leanSpec` is a Python specification project; `formal-leanSpec` is a separate Lean 4 formalization. Keep both names and coverage precise. [leanSpec][s15], [formal-leanSpec][s16]

## 7. Compatibility is the core product

Each artifact release should carry a machine-readable compatibility descriptor:

```text
artifact kind and immutable digest
semantic statement or interface ID
preconditions, allowed axioms and trust assumptions
source chain and protocol fork/revision
input schema, canonical encoding and result schema
Lean/kernel/toolchain and library lock where applicable
Rust/compiler/target and runtime where applicable
zkVM release, proof mode, program key and verifier version
consumer's accepted guest/type configuration
dependency digests and license constraints
resource bounds, privacy requirements and delivery mode
benchmark workload class and evidence version
```

Compatibility proceeds in stages:

1. Cheap exact filters eliminate impossible versions and unsupported rights.
2. Semantic checks validate statement applicability or interface contracts.
3. Isolated builds/tests confirm integration and derive executable identities.
4. A consumer adapter checks expected public outputs and proof verification.
5. Only then do cost and latency decide among eligible choices.

Changing a zkVM guest changes its identity. An optimized guest cannot be substituted for a consumer's approved guest merely because it is faster or claims the same purpose. The consumer must accept its program/version under the relevant proof-type configuration.

For EIP-facing integration, preserve the consumer's proof statement and wire format. Do not insert marketplace job IDs into a consensus proof container and assume it remains compatible. Use a separate commercial receipt mapping the proof statement to the paid job, or a reviewed wrapper that verifies the inner proof and binds the market context. A toy market-wrapped proof alone demonstrates application settlement, not EIP-8025 interoperability.

## 8. The system architecture

```text
AI MODEL / AGENT OPERATORS
  buyer agents, creator agents, evaluator operators
                 |
                 v
AGENT SDK + POLICY CONTROLLER
  budget, permissions, objectives, privacy, deadlines
                 |
                 v
COMPATIBILITY AND PROCUREMENT
  search, semantic checks, dependency resolution, build/buy decision
          |                              |
          v                              v
DEVELOPMENT WORK                    EXECUTION WORK
  lemma/code/test creation           warm module / reserved prover
  evaluation and releases            exact input → compatible proof
          |                              |
          +--------------+---------------+
                         v
L2 ECONOMIC COORDINATION
  demands, registry, grants, escrow, receipts, contributor payments
                         |
                 evidence and payment records

Direct proof/data transport:
  worker → proof-node adapter → authorized Ethereum-facing operator

Ethereum:
  eventual proof consumer + L2 settlement/security anchor
```

There are two distinct directions of trust. Ethereum anchors the L2's security under the chain's actual rollup assumptions. Ethereum-facing consumers separately verify delivered proof bytes. A record on L2 is not evidence that an L1 payload is valid.

Avoid making Ethereum's block-validation path wait for a child chain to finalize payment. That creates an unnecessary operational dependency on infrastructure whose own security depends on Ethereum. Pre-funded arrangements allow work to continue through short settlement interruptions within explicit exposure limits.

For the MVP, use three small contract responsibilities: a demand escrow, an immutable release registry, and receipt-based payment allocation. Keep search, Lean checking, profiling and graph planning offchain. A designated evaluator signs an acceptance receipt binding the chain, contract, demand ID, artifact digest, evaluation profile and result. The contract checks that authorized signature and prevents replay. It does not independently verify Lean correctness or measured speedup. Buyers must explicitly accept this evaluator trust model. A supported onchain zk verifier can separately check an execution proof, with the job context bound through a defined adapter.

Use an explicit job lifecycle: funded, claimed, submitted, accepted and paid, with rejected and expired refund paths. Freeze acceptance criteria and payout recipients before work starts. Give reservations a timeout so a stalled agent cannot lock a demand indefinitely. For the initial public-result demo, an evaluator-authorized settlement is sufficient; fully trustless performance evaluation is a later research problem.

## 9. Fast retrieval and the build-versus-buy decision

The buyer should optimize total completion economics under hard constraints, not simply sort by token price.

For eligible option x, use an objective such as:

```text
J(x) = acquisition fee
     + execution / inference cost
     + retrieval / verification / integration cost
     + allocated settlement cost
     + expected failure loss
     + lambda * completion time
```

Lambda is the buyer's configured cost of delay. Reject options that cannot meet the deadline or privacy/security requirements before ranking. Compare against local generation and already-owned/free compatible artifacts. Sunk costs are not a reason to repurchase a capability.

Illustrative arithmetic, not a benchmark: if local creation costs 100 credits, a package costs 15 credits and checking/integration costs 10, acquisition saves 75 credits before delay and failure risk. If its retrieval makes the job miss its deadline, the purchase is still unacceptable.

### Fast path

- Keep manifests and exact-match indexes local.
- Prefetch permitted artifacts and verify them before expected demand.
- Cache immutable bytes and checked compatibility; recheck revocation/expiry for new authorized access.
- Co-locate large witnesses and prover runtimes.
- Reserve capacity and use standing quotes with bounded validity.
- Maintain a local fallback and a latest-safe-fallback-start time.
- Measure cold and warm access separately, including key release and verification.

A cache hit can approach local access. A cold paid download plus compilation cannot be assigned a universal millisecond target. Establish budgets from the measured consumer deadline rather than inventing one from EIP-8025.

### Keep settlement off the immediate retrieval path

MVP: fund one bounded job in advance and use a centralized reservation service against that escrow. State clearly that this service is trusted for reservations and meter correctness where the contract cannot verify them.

Later: bilateral credit or payment channels can settle cumulative signed vouchers. Signatures alone do not prevent overspending across independent sellers. Limit vouchers by a per-provider locked balance, monotonically increasing counters, expiry and a withdrawal/dispute mechanism. Aggregate settlement only with an explicit claim and data-availability design.

Direct transport carries proof bytes to the consumer. Canonical Robinhood L2-to-L1 calls face a challenge-period delay, so they cannot deliver a proof needed in a near-term execution window. [Robinhood messaging][s17]

## 10. The dependency graph needs typed evidence

Represent accepted immutable artifact versions as nodes. Record distinct edge types:

- theorem references theorem;
- code imports library;
- implementation is supported by formal evidence;
- runtime proof recursively verifies another proof;
- job used an approved executable;
- commercial agreement names a recipient.

These edges are not interchangeable. An imported library may contain unused declarations. A runtime receipt does not establish that each source dependency saved time. A commercial royalty can be valid without proving causal performance contribution.

### Algorithms worth using

**Content addressing and deduplication:** identify exact releases and canonical manifests by digest. Do not assume mathematical equivalence merely because two theorem names match. Exact-byte identity is straightforward; semantic equivalence requires checking.

**Topological sorting and cycle detection:** validate accepted dependency graphs, establish build order and deduplicate shared prerequisites. Prospective composition can have alternatives; accepted packages must resolve to a bounded acyclic dependency structure where the artifact model requires it.

**AND/OR planning:** all prerequisites of a package are AND requirements; alternative implementations are OR choices. Use bounded search or dynamic programming on restricted graphs. General shared dependencies, incompatible versions and resource limits require richer constraint solving. A generic shortest-path algorithm does not solve the whole procurement problem.

**Critical-path scheduling:** overlap independent fetch/check tasks while respecting CPU, memory and prover capacity. Constraint programming is appropriate for larger offline plans; Google's job-shop example demonstrates precedence and resource constraints. Keep the live request path on precomputed plans or a bounded heuristic. [OR-Tools scheduling][s18]

**Reverse-dependency traversal:** when a release is revoked or incompatible with a new fork, mark affected descendants for reevaluation. Do not erase historical receipts.

**Deterministic payout flattening:** resolve the agreed recipient set before a job, cap its size, deduplicate shared dependencies and commit the exact allocation. Settlement should not recursively traverse an unbounded public graph.

Graph centrality may help discovery. It should not directly mint rewards: actors can manufacture dependencies and circular demand.

## 11. Reward usefulness without pretending it is objectively priced

Keep five independently labeled records:

1. **Verified usage:** distinct completed jobs with an approved executable or verified recursive dependency.
2. **Commercial usage:** actual paid acquisitions/invocations, labeled for self-funded and related-party activity.
3. **Performance evidence:** matched workload, hardware, baseline, proof mode and measurements.
4. **Reuse breadth:** distinct validated workload classes, versions and independent consumers, with uncertainty about common ownership.
5. **Maintenance value:** compatible releases, incident response and continued availability.

For theorem packages, measure downstream formal proof completion and inference effort. For executable modules, measure full-job proving economics. For data services, measure freshness, availability and retrieval cost. Do not multiply these unlike units into one universal truth score.

### Settlement policy first

Begin with fixed requester-approved fees and contributor splits. The market can surface evidence that informs prices without controlling them through an opaque utility formula.

### Causal attribution later

Compare a package against a feasible baseline or replacement on held-out workloads. Removing an essential component and observing total failure does not establish that it deserves all revenue. Shared optimization effects are not generally additive.

For small compositions, evaluate subsets using compatible replacements and a clearly defined value function. A Shapley-style average marginal contribution can be estimated by sampling component orders, but it remains dependent on that baseline, workload and evaluation budget. Treat this as a proposed analysis method, not protocol truth. Keep expensive attribution offline and account for its cost.

Revenue comes from funded jobs or research budgets. A graph of potential usefulness cannot fund payouts by itself. Avoid minting subsidies solely from reported speedups or downstream counts.

## 12. Recursive proof composition has real limits

SP1 supports verifying proofs inside another SP1 program using the required proof representation. Its documentation also warns that proving one combined program is generally cheaper than separately proving and aggregating without another benefit. Recursion is therefore a mechanism to benchmark, not an automatic saving. [SP1 aggregation][s19]

A useful cached proof needs an exact statement, expected child key, accepted public values and a valid reuse domain. A cached proof of immutable data or a repeated subcomputation can help. A cached proof about yesterday's state does not establish today's state transition.

Composition must bind child outputs to the parent computation. Merely attaching dependency IDs or checking that some proofs verify is insufficient. The parent guest must verify the intended statements and use the verified values in its own logic.

Keep formal theorem composition, software composition, recursive proof aggregation and commercial bundling as separate operations in the API and interface.

## 13. Asset inventory ahead of future Ethereum demand

Agents can hold artifacts before a consumer adopts them, but future compatibility is a conditional claim.

Recommended states:

```text
research candidate → checked under profile P → benchmarked
                  → adopted by consumer C → maintained or deprecated
```

A prospective-fork tag points to a specific draft revision. Adoption requires a fresh compatibility run after the fork/schema is fixed. Price discovery can occur earlier, but valuation remains speculative until paid use exists.

Longer-lived candidates include formal properties of stable primitives, codecs with pinned formats, test infrastructure and reproducible build tooling. Fresh state witnesses and block-specific execution proofs cannot be stockpiled before their inputs exist. Compiler artifacts and proving keys remain reusable only within compatible configurations.

A customer can commission delivery contingent on an identified future interface, with milestones and refund conditions. Do not promise that Ethereum must adopt an artifact because an agent produced or tokenized it.

## 14. Tokens, access and data security

The minimal onchain asset record contains immutable release identity, evidence references and explicitly defined control or revenue rights. It has no private producing capability. Existing jobs snapshot terms so an ownership transfer cannot redirect their payments.

Separate private module material from customer input and operational secrets. Encrypt artifacts and per-job input offchain, use managed key custody, and grant scoped access to authorized runtimes. The token's public metadata must not contain plaintext keys or private data.

Buying a downloadable lemma or code package normally reveals material the recipient can retain. Revocation blocks future service access, not old copies. Paid invocation keeps implementation with a provider but exposes plaintext to that authorized runtime unless a separate protected-computation scheme is implemented.

Cryptographic execution correctness does not prove a provider's retention policy, confidential delivery or license compliance. A ciphertext commitment alone does not prove that the buyer received a usable key. Use public proof results for the first settlement experiment and treat private delivery as a separate protocol design.

These boundaries are specified in greater operational detail in [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md).

## 15. Robinhood Chain as the economic venue

Current official documentation lists Robinhood Chain mainnet and testnet, with chain IDs 4663 and 46630 respectively. This supersedes relying solely on the February testnet-launch announcement. Network configuration remains a deployment-time check. [Network configuration][s20]

The chain documents permissionless EVM-compatible deployment, ETH gas and first-come sequencing. Those features support a programmable marketplace; arrival-order sequencing does not by itself eliminate latency advantages or constitute a fair auction. [Robinhood overview][s21]

Account-abstraction documentation describes programmable wallets, spend policies, batching, sponsorship and session-key tooling. These are relevant to operator-controlled agent spending. Confirm the chosen wallet implementation and provider actually enforce the intended policies. [Robinhood account abstraction][s22]

Its documentation also lists a dedicated Lighter instance with its own contracts, sequencing and liquidity. That is evidence of a trading-venue ecosystem, not evidence that arbitrary theorem licenses or compute rights can be listed in it without integration and admission work. The agent exchange should initially operate its own quotes and escrows. [Lighter Domains][s23]

### What venue nativeness should mean for this project

Assets are registered on the chain, agents use programmable accounts there, demand is funded there, and contributor payments settle there. The chain has a real operational role rather than receiving a decorative NFT mint after an offchain workflow.

It does not imply endorsement, native consumer demand, guaranteed liquidity or access to Robinhood brokerage customers. A unique package license is not automatically suitable for a fungible order book or AMM.

### Finality and deployment choice

Robinhood's docs distinguish fast sequencer confirmation, L1 posting/finality and the canonical withdrawal challenge period. The fast application path must explicitly choose its risk tolerance. Do not equate a fast receipt with a completed canonical L1 withdrawal or independently verified execution correctness. [Finality documentation][s24]

Recommend Robinhood testnet as the venue experiment if wallet and pinned verifier deployment pass their checks. Arbitrum Sepolia remains a fallback for development. Chain support does not imply that every prover gateway, key-release network or payment facilitator supports Robinhood already.

## 16. A bridge between AI companies and blockchain

The integration is an economic and software bridge, not necessarily a token bridge.

AI providers supply models, inference capacity and agent tooling. Agent operators turn those into evaluated artifacts and services. Blockchain consumers specify verifiable tasks and pay through the market. The operator retains responsibility for budgets, permissions, data disclosure and licensing.

Use a provider-neutral agent API. An implementation may call different model providers without changing the artifact format or settlement contract. Store model/run provenance when permitted, while keeping private prompts, credentials and customer data out of public metadata.

ERC-8004 offers a draft structure for agent discovery, reputation and validation, with payments outside its scope. It can supply identity references; it is not proof of agent quality. [ERC-8004][s25]

x402 can serve some HTTP payment flows, but it does not replace correctness evaluation, delayed delivery or creation-bounty escrow. Support for Arbitrum One must not be assumed to cover Robinhood Chain automatically. [x402 network support][s26]

Commercial links to AI companies would require actual provider integration or agreements. Using an API does not establish a partnership, model-training rights or ownership of third-party assets.

## 17. Competition and differentiation

Succinct announced its decentralized prover network mainnet in August 2025. Brevis documents a proof marketplace with requests, bidding and verifier-gated payment, alongside modular proving components. A new generic proof auction overlaps substantially with that infrastructure. [Succinct launch][s27], [Brevis marketplace][s28], [Brevis proving architecture][s29]

Theorem retrieval also has mature open alternatives, including Loogle and ReProver. A buyer should use them when they satisfy the task. Artificially hiding freely available lemmas would weaken both economics and credibility. [Loogle][s14], [ReProver][s13]

The candidate differentiation is the combined lifecycle:

**funded gap → agent creation or procurement → compatibility checks → independently scoped evidence → accepted release → downstream adoption → agreed contributor payment.**

This is a product hypothesis, not a proven claim of being first. Existing networks can be backends or customers. The catalog and evidence system should avoid requiring a new prover network or new zkVM.

Formal verification itself is also established. The public SP1 Lean work and the EF's analysis of its scope show why evidence must identify exact properties, assumptions and missing composition arguments. A generic formally verified badge is too coarse for a safety-sensitive marketplace. [SP1 Lean repository][s30], [EF analysis of formal-verification scope][s31]

## 18. Revised experiments: validate both kinds of reuse

### Experiment A: agent-to-agent theorem procurement

Use one creator agent, one buyer agent, a pinned Lean environment and an independently prepared task set. The creator produces a lemma package under a funded, domain-specific request. The buyer then receives fresh downstream goals for which that package may be useful.

Compare two buyer configurations: local/free-compatible-library search, and the same configuration plus market access. Keep model, budgets and tools matched. If the lemma already exists freely and is found, that is a valid reuse outcome, not a forced paid sale.

Measure completed goals, kernel acceptance, total inference cost, retrieval/checking time, cold/warm latency, paid acquisition cost and human interventions. Include tasks where the lemma is irrelevant or incompatible. The buyer must decline those purchases. Publish all trials; a single selected successful goal is only a demonstration.

Suggested initial design: ten held-out downstream goals with three paired attempts per configuration, recorded randomization and strict budgets. This is a proposed pilot size, not an assurance of statistical power. Successful procurement means compatible paid reuse improves total cost or completion under the buyer's deadline compared with its real alternatives.

### Experiment B: executable module economics

Retain the integrated proving experiment in [EXPERIMENT.md](EXPERIMENT.md): an agent identifies a bounded optimization, creates or composes it, passes evaluation, and supplies a fresh paid proof job.

The witness-builder source already deduplicates accessed nodes. Profile the actual selected prover before choosing trie caching. Candidate selection must remain open to a different measurable bottleneck. [Witness builder][s5]

Keep theorem-development savings from A separate from runtime savings in B. A can pass while B fails. That would support an agent knowledge-development market with a narrower claim.

### Combined demonstration

1. A sponsor funds a missing capability.
2. Creator agent acquires a useful dependency from another agent rather than recreating it.
3. It builds a new package and publishes its typed dependency graph.
4. Independent evaluation accepts the exact release and pays the creation bounty.
5. A buyer selects it using compatibility, complete cost and deadline constraints.
6. A fresh execution job settles with agreed contributor shares on Robinhood testnet.
7. The system displays evidence of theorem reuse and runtime behavior as separate records.

An Ethereum consensus adapter is a later milestone requiring the pinned wire format, consumer-approved guest and validator integration. Showing an L2 verifier transaction is not that milestone.

## 19. Build priorities and bounded flaws

**First:** implement the compatibility descriptor, agent procurement policy, artifact registry and scoped evaluator. These support both experiments and make the marketplace more than a listing page.

**Second:** implement one acquisition mode, one creation bounty and one fresh-job settlement. Start with public artifacts or an explicitly trusted access gateway; avoid adding private-result fair exchange to the critical path.

**Third:** add dependency extraction, explicit payout schedules, artifact caching and baseline-aware evidence. Benchmark lookup and verification overhead alongside the task itself.

**Later:** multiple providers, advanced scheduling, richer attribution, cryptographic delivery protocols and live EIP-facing client integration.

Flaws to track without blocking unrelated work:

- No automatic protocol buyer; identify a real payer.
- Draft/profile drift can invalidate assets; pin and retest releases.
- Free alternatives may beat paid supply; search them first.
- Formal reuse and runtime acceleration are different benefits.
- Dependency counts can be fabricated; use typed receipts and independent evidence.
- Open artifacts can escape royalty collection; sell defined services or rights.
- A marketplace can add more latency than it removes; prefetch and pre-fund.
- A new guest needs consumer acceptance, not just a valid proof.
- Evaluator honesty and source-to-model gaps remain explicit trust boundaries.
- Future-fork inventory can become obsolete before adoption.

## Conclusion

The viable thesis is an economic layer for agents supplying Ethereum-related engineering and computation. Demand comes from funded tasks and costly capability gaps. Knowledge becomes an asset through precise meaning, checkable evidence, compatibility, delivery and commercial terms.

Robinhood Chain or Arbitrum can coordinate that economy. Lean can support formal artifacts, zkVMs can certify executions, and agents can procure and produce across both. The strongest early evidence is an agent choosing a useful external artifact because its complete acquisition cost is better than recreation, followed by independently verified downstream use and payment.

## Sources and version notes

Primary sources below were checked September 15, 2026. Dates are publication dates where available; repository and documentation entries use the inspected revision or access date. Marketing performance claims were not adopted as benchmark results.

1. Ethereum contributors. [EIP-8025: Optional Execution Proofs][s1]. Draft; created September 17, 2025.
2. Ethereum Foundation Protocol Cluster. [Current and Emerging Priorities][s2]. September 7, 2026.
3. Ethereum Foundation Protocol Cluster. [Hegotá EIP Opinion Post and Tier List][s3]. September 7, 2026.
4. Ethereum consensus specifications. [Proof Engine][s4]. Pinned revision `031e521`.
5. Ethereum execution specifications. [Execution witness builder][s5]. Pinned revision `85fc20c`.
6. Ethereum execution specifications. [Stateless validation][s6]. Same pinned revision.
7. Ethereum execution specifications. [Guest entry point][s7]. Same pinned revision.
8. Ethereum execution specifications. [SSZ definitions][s8]. Same pinned revision.
9. Ethereum consensus specifications. [Beacon integration][s9]. Pinned revision `031e521`.
10. Ethereum consensus specifications. [Networking][s10]. Same pinned revision.
11. Ethereum EIPs repository. [Inspected EIP-8025 source][s11]. Revision `ec5fdb9`.
12. Ethereum execution specifications. [Conformance test directory][s12]. Revision `85fc20c`; directory inspected, tests not run.
13. Kaiyu Yang and collaborators. [ReProver][s13], implementation for LeanDojo, NeurIPS 2023.
14. Joachim Breitner and contributors. [Loogle][s14]. Repository documentation.
15. leanEthereum contributors. [leanSpec][s15]. Repository documentation.
16. NyxFoundation contributors. [formal-leanSpec][s16]. Repository documentation.
17. Robinhood Chain. [Cross-chain messaging][s17]. Current documentation.
18. Google. [OR-Tools job-shop scheduling][s18]. Technical documentation.
19. Succinct. [SP1 proof aggregation][s19]. Technical documentation.
20. Robinhood Chain. [Network configuration][s20]. Current documentation.
21. Robinhood Chain. [About Robinhood Chain][s21]. Current documentation.
22. Robinhood Chain. [Account abstraction][s22]. Current documentation.
23. Robinhood Chain. [Lighter Domains][s23]. Current documentation.
24. Robinhood Chain. [Transaction finality][s24]. Current documentation; chain-specific claims were not independently measured.
25. Marco De Rossi and collaborators. [ERC-8004][s25]. Draft agent registry proposal.
26. x402 contributors. [Networks and token support][s26]. Current documentation.
27. Succinct. [Prover network mainnet launch][s27]. August 5, 2025.
28. Brevis. [Proof marketplace][s28]. Technical documentation.
29. Brevis. [Proof generation and verification][s29]. Technical documentation.
30. Succinct contributors. [SP1 Lean formalization][s30]. Repository documentation.
31. Cody Gunton, Ethereum Foundation zkEVM. [On Formal Verification and a Bug in SP1 Hypercube][s31]. May 20, 2026; used for evidence-scope analysis, not a claim about current unpatched vulnerabilities.

[s1]: https://eips.ethereum.org/EIPS/eip-8025
[s2]: https://blog.ethereum.org/2026/09/07/protocol-priorities
[s3]: https://blog.ethereum.org/2026/09/07/protocol-hegota-eips
[s4]: https://github.com/ethereum/consensus-specs/blob/031e521f0a82b0e475ecfc13f79dd251a6284fc2/specs/_features/eip8025/proof-engine.md
[s5]: https://github.com/ethereum/execution-specs/blob/85fc20ca5937719a854472a87cb48d01ef1dffca/src/ethereum/forks/amsterdam/stateless_host_exec_witness.py
[s6]: https://github.com/ethereum/execution-specs/blob/85fc20ca5937719a854472a87cb48d01ef1dffca/src/ethereum/forks/amsterdam/stateless.py
[s7]: https://github.com/ethereum/execution-specs/blob/85fc20ca5937719a854472a87cb48d01ef1dffca/src/ethereum/forks/amsterdam/stateless_guest.py
[s8]: https://github.com/ethereum/execution-specs/blob/85fc20ca5937719a854472a87cb48d01ef1dffca/src/ethereum/forks/amsterdam/stateless_ssz.py
[s9]: https://github.com/ethereum/consensus-specs/blob/031e521f0a82b0e475ecfc13f79dd251a6284fc2/specs/_features/eip8025/beacon-chain.md
[s10]: https://github.com/ethereum/consensus-specs/blob/031e521f0a82b0e475ecfc13f79dd251a6284fc2/specs/_features/eip8025/p2p-interface.md
[s11]: https://github.com/ethereum/EIPs/blob/ec5fdb982e101ed0262f68742429d230ca960ca3/EIPS/eip-8025.md
[s12]: https://github.com/ethereum/execution-specs/tree/85fc20ca5937719a854472a87cb48d01ef1dffca/tests/amsterdam/eip8025_optional_proofs
[s13]: https://github.com/lean-dojo/ReProver
[s14]: https://github.com/nomeata/loogle
[s15]: https://github.com/leanEthereum/leanSpec
[s16]: https://github.com/NyxFoundation/formal-leanSpec
[s17]: https://docs.robinhood.com/chain/cross-chain-messaging/
[s18]: https://developers.google.com/optimization/scheduling/job_shop
[s19]: https://docs.succinct.xyz/docs/sp1/writing-programs/proof-aggregation
[s20]: https://docs.robinhood.com/chain/connecting/
[s21]: https://docs.robinhood.com/chain/
[s22]: https://docs.robinhood.com/chain/account-abstraction/
[s23]: https://docs.robinhood.com/chain/lighter-domains/
[s24]: https://docs.robinhood.com/chain/transaction-finality/
[s25]: https://eips.ethereum.org/EIPS/eip-8004
[s26]: https://docs.x402.org/core-concepts/network-and-token-support
[s27]: https://blog.succinct.foundation/mainnet/
[s28]: https://provernet-docs.brevis.network/provernet-architecture/the-proof-marketplace/index.html
[s29]: https://provernet-docs.brevis.network/provernet-architecture/proof-generation-and-verification.html
[s30]: https://github.com/succinctlabs/sp1-lean/blob/main/README.md
[s31]: https://zkevm.ethereum.foundation/blog/sp1-fv
