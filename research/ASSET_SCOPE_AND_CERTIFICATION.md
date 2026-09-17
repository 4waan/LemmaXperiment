# Agent infrastructure assets and the Asset Certification Layer

Design date: September 15, 2026.

Companion to [EIP-8025 research](EIP8025_AGENT_ECONOMY_RESEARCH.md) and [agent marketplace mechanics](AGENT_MARKETPLACE.md). This is a proposed architecture. No asset has been certified or benchmarked by this work.

## 1. The product decision

Build an agent marketplace for **capabilities, authenticated results and bounded delivery commitments**. The Asset Certification Layer makes their claims specific, checkable and usable by an automated buyer.

The attachment has a useful breadth of possibilities, but its ten categories are not ten interchangeable tokens. Separate three commercial forms:

1. **Reusable package:** a lemma, circuit, library, scheduler or adapter. A buyer obtains a license or permitted invocation. Copying does not consume the package.
2. **Result instance:** a witness, execution result or aggregation proof bound to exact inputs. Its information may be copied; applicability is limited by its statement and context.
3. **Service commitment:** a provider promises compute, retrieval, posting or execution within specified constraints. Reservation consumes bounded provider capacity and eventually expires or settles.

One capability can produce many result instances and support many service commitments. Keep their identities, prices, lifetimes and certificates separate.

A certificate adds economic value by reducing evaluation work, integration uncertainty and supplier risk. It cannot create demand, make public information exclusive or guarantee a higher price. A failed evaluation can correctly reduce an asset's value.

The attachment's scarcity-times-demand-times-utility formula is a narrative heuristic, not a valuation model. Copyable software can be valuable through maintenance, assurance, integration and availability. A one-use result can also be valuable when timely production is expensive.

## 2. Shape each asset category

For every category, define a buyer, exact deliverable, purchase unit, acceptance predicate, reuse boundary and invalidation rule.

### 2.1 Proof and formal-methods packages

**Concrete product:** a pinned Lean theorem package, an optimized witness-verification implementation, or a compatible proving circuit with reproducible build inputs. These are distinct subtypes, even if sold together.

**Demand:** a creator agent needs a missing lemma; a prover operator needs a cheaper implementation of a measured bottleneck.

**Delivery and trade:** source package license, creation bounty, maintenance subscription or hosted invocation. A generated execution proof is a separate job result.

**Certification:** theorem statement and permitted assumptions; dependency closure; reproducible build identity; implementation-to-model relationship; accepted guest/verifier profile; benchmark against a named alternative.

**Reuse boundary:** theorem definitions and hypotheses must match. Executable changes require consumer-approved program identity. A property proved about a formal model does not automatically cover deployed code.

**Priority:** core. Measure formal-development savings separately from execution-proving savings. Lean's own validation guidance explicitly distinguishes kernel acceptance from the meaning of the statement and the axioms on which it depends. [Lean proof validation][s1]

### 2.2 State witnesses

**Concrete product:** an authenticated bundle for a requested account and storage-key set at a specified chain, block hash and state root. Include membership or non-membership proofs, canonical key encoding and code bytes where required by the job.

**Demand:** an agent must establish a state predicate or execute a bounded computation without maintaining the relevant state itself.

**Delivery and trade:** per-query retrieval, a batch of queries, a cached bundle download, or a standing witness-service contract. Charge for construction, packaging and fast availability, not exclusive ownership of public state.

**Certification:** verify the account proof against an independently authenticated root, then storage proofs against the account's storage root. Check every requested key, absence semantics and code hashes when relevant. Bind a completeness claim to the requested query set. A few valid storage proofs are not a complete witness for an arbitrary block.

**Reuse boundary:** identical queries at the same authenticated root can reuse the result. Some node bytes can deduplicate across roots, but the membership relationship must still be validated. A reorg can remove the root's canonical relevance without making its mathematical proof malformed.

**Priority:** core. EIP-1186 describes account/storage proof retrieval and offline verification with an appropriately trusted block reference. [EIP-1186][s2]

### 2.3 Block access lists and execution plans

**Concrete product:** a validated block access list plus derived prefetch or execution scheduling instructions for a specific client profile. Separate the canonical data from the producer's additional optimization.

**Demand:** a worker wants to schedule storage reads or computation efficiently.

**Delivery and trade:** indexed access-list retrieval, a reusable plan-generator package, or a per-block derived plan. Public protocol data is a weak exclusive asset; fast indexing and effective scheduling are stronger service products.

**Certification:** check encoding and commitment against an authenticated header for the relevant fork; separately check completeness/correctness using accepted block validation or replay. Compare a proposed schedule's result with canonical sequential execution. Measure read latency and end-to-end execution cost.

**Reuse boundary:** a concrete plan binds to its payload and runtime. Its planner can generalize to new blocks. Do not assume a BAL is a complete, ready-made dependency graph: derive and validate the constraints needed by the chosen scheduling algorithm.

**Priority:** next. EIP-7928 is currently in Review and specifies accessed locations and indexed changes with a header commitment. This report makes no independent claim about devnet deployment. [EIP-7928][s3]

### 2.4 Attestation/signature aggregation

**Concrete product:** a reusable aggregation implementation, a reserved aggregation service, or a proof for an exact batch of signed messages.

**Demand:** an authorized consensus-facing operator needs a batch checked or compressed under a deadline.

**Delivery and trade:** per-batch fee or reserved throughput, with source-module licensing as a separate product.

**Certification:** pin signature scheme, parameter set, message/domain, participant commitment, duplicate policy, verification key and consumer profile. Verify the full claimed participant set and message binding. Measure collection delay, proving time, verification time, proof size and failures separately.

**Reuse boundary:** the module generalizes; a batch proof is bound to those messages and signers. Do not merge attestations for different messages into an assertion that everyone signed one message. Aggregators do not acquire validator signing authority.

**Priority:** later integration. The current leanVM repository includes signature-aggregation work but explicitly labels formal verification as in progress and the system as not production ready. Treat profiles as research profiles. [leanVM][s4]

### 2.5 Post-quantum implementation components

**Concrete product:** a versioned signature verifier, hash implementation or parameter-specific aggregation module, with test vectors, formal evidence and reproducible builds.

**Demand:** a research or implementation agent needs a correct, compatible implementation or faster component.

**Delivery and trade:** funded implementation, release license, maintenance or evaluation service. This is a specialization of reusable code assets, not a separate universal token standard.

**Certification:** scheme and parameter identifiers, exact security claims/assumptions, negative test vectors, implementation linkage, scoped formal evidence, platform-specific performance and review scope. Passing vectors does not establish cryptographic security. For stateful signing implementations, key-index management and rollback protection need separate evaluation.

**Reuse boundary:** changes to parameters, primitives, compiler or runtime can invalidate particular certificates. Private signing keys are not marketplace inventory.

**Priority:** research catalog. Public leanSig and leanVM development gives integration targets, not blanket assurance for a newly submitted module. [leanSig][s5], [leanVM][s4]

### 2.6 Blob posting and data-availability services

**Concrete product:** a provider contract to encode and submit a specified payload within a slot window, under an agreed fee cap, with explicit retention obligations if desired.

**Demand:** an L2 operator needs timely data publication and predictable operational cost.

**Delivery and trade:** a bounded posting reservation. If fungible units are introduced later, standardize encoding, usable bytes, window, fee treatment, provider risk and settlement. Reserving a provider's service does not reserve Ethereum protocol blockspace.

**Certification:** before purchase, evaluate operational capacity, collateral and reservation accounting. After execution, verify payload commitment, inclusion under the chosen finality rule and required retrieval evidence. A KZG opening establishes consistency with a commitment, not universal or permanent availability. Retention needs its own service checks.

**Reuse boundary:** a reservation is consumed or expires. Never sell the same committed capacity to several buyers unless the contract explicitly describes shared capacity and scheduling.

**Priority:** separate future market. EIP-4844 supplies blob transactions and commitment mechanics, not your provider's future-capacity guarantee. Do not treat its original throughput parameters as current network limits. [EIP-4844][s6]

### 2.7 Inclusion and preconfirmation commitments

**Concrete product:** a named provider's signed, collateralized promise concerning a transaction hash, chain, deadline and precise inclusion or execution condition.

**Demand:** an agent needs a bounded transaction outcome and recourse if the provider fails.

**Delivery and trade:** a per-transaction commitment issued only by a provider with relevant authority or an explicit downstream agreement. Relaying alone does not control inclusion.

**Certification:** verify provider authority, commitment signatures, resource conflicts, collateral and exclusions before purchase. Verify actual inclusion and, when promised, successful execution afterward. Define handling of invalid transactions, reorgs, fee changes and chain stalls. Cross-chain settlement needs an authenticated observation mechanism.

**Reuse boundary:** transaction commitments are per instance; provider capability and observed delivery history persist.

**Priority:** defer. FOCIL is a draft censorship-resistance mechanism, with conditional inclusion and no explicit participant rewards. It does not assign this marketplace tradable inclusion rights. A refund compensates within its terms; it does not force Ethereum to include a transaction. [EIP-7805][s7]

### 2.8 Intent execution and solver capabilities

**Concrete product:** a solver strategy or route adapter as a reusable package; a fresh signed order as a service demand; and a fulfillment receipt as the result.

**Demand:** a buyer agent specifies acceptable output, deadline, chains and maximum spend.

**Delivery and trade:** quoted fulfillment, capacity reservation or a licensed strategy. A public intent template is generally a descriptor, not scarce inventory.

**Certification:** package tests and supported routes before use; actual balances/output, recipient, nonce and deadline at settlement. Pin token units, partial-fill rules and the reference used for any slippage claim. Simulated profitability does not certify future execution price. Preserve user authorization when any fulfillment right is delegated.

**Reuse boundary:** routes and code generalize; prices, liquidity and authorizations are time dependent.

**Priority:** later expansion. ERC-7683 provides a cross-chain intent interface to examine for integration, not automatic correctness or profitability of a solver. [ERC-7683][s8]

### 2.9 Historical-state retrieval

**Concrete product:** an authenticated answer for a specified historical block and query set, served from a maintained archive or reconstructed state.

**Demand:** an agent conducting verification, analysis or dispute reconstruction needs historical evidence.

**Delivery and trade:** per-query retrieval, authenticated segment download, archive subscription or reconstruction bounty.

**Certification:** anchor the historical header/root through a buyer-accepted trust path, validate queried state, and measure coverage and retrieval latency under an explicit region and load. Distinguish block/receipt history from historical state. Possessing old block bodies does not automatically provide efficient arbitrary historical-state queries.

**Reuse boundary:** immutable finalized queries can be highly cacheable. Archive completeness and ongoing availability remain service claims requiring monitoring.

**Priority:** next, sharing witness infrastructure. EIP-4444 concerns bounded historical data in execution clients; it should not be represented as a universal historical-state retrieval protocol. [EIP-4444][s9], [statelessness roadmap][s10]

### 2.10 Execution fragments

**Concrete product:** a bounded computation package with explicit preconditions and outputs; optionally, a fresh execution proof bound to exact inputs. Start with a narrow primitive rather than claiming arbitrary EVM transaction splitting.

**Demand:** a worker can outsource a well-defined subcomputation or reuse its implementation.

**Delivery and trade:** package license, hosted invocation or a compatible proof result.

**Certification:** bind inputs, outputs, code identity and environment. For state transitions, cover relevant roots, state read/write behavior, gas semantics, reverts and observable effects. A parent must verify the child's statement and establish that composition preserves its own semantics.

**Reuse boundary:** bytecode alone is insufficient for result reuse. State, caller, chain context and gas can alter behavior. Independent valid fragments can still compose incorrectly. A BAL can assist dependency planning; it does not establish arbitrary fragments are independent.

**Priority:** bounded core candidate. Begin with a storage-predicate computation or witness-verification primitive and label its scope explicitly. Full EVM fragment composition is later research.

## 3. Scope recommendation

**Build one coherent path first:** authenticated state query, reusable verification/computation package, and a fresh checked result. Let one creator buy a formal dependency while building the package.

That demonstrates data procurement, knowledge procurement and executable reuse without requiring ten settlement systems.

The dependency directions are clearer as: a payload plus parent-state access enables witness construction; the payload and witness feed stateless execution/proving; verification checks the resulting statement. Witness collection may itself run an instrumented execution. It is not always a simple state-to-execution-to-witness pipeline.

Next add historical retrieval and access-plan generators. Treat aggregation and PQ components as additional evaluator profiles. Keep blob reservations, inclusion commitments and capital-bearing intent fulfillment as later service markets because they need distinct authority, capacity and dispute machinery.

## 4. The Asset Certification Layer

### 4.1 What the certificate says

A certificate is an issuer's signed statement about **one subject, one claim, one evaluation procedure and one applicability scope**.

Example: evaluator E checked release R using verifier V under profile P, with evidence bundle B. It accepted a named property under listed assumptions at time T. It makes no unlisted claims.

Use a collection of independent claim records, not a single certified/not-certified flag or a gold-tier badge. An artifact can have accepted correctness evidence and an unproven performance claim. A witness may need deterministic verification but no benchmark to be useful.

A certificate's subject can be:

- an immutable package release;
- an exact result instance;
- a provider deployment and service profile;
- a specific reservation;
- a composition with pinned dependencies.

A service certificate cannot be copied onto every result it produces. Each result still needs its relevant verification.

### 4.2 Seven claim families

**Identity and provenance:** what exact bytes were evaluated, how they were built, and who submitted them. Signed build provenance can record builder and inputs; it does not prove authorship or correctness. SLSA is a useful format reference. [SLSA provenance][s11]

**Correctness:** a named theorem, membership predicate, execution relation or acceptance test. Declare whether evidence is kernel checked, cryptographically verified, differentially tested or manually reviewed.

**Compatibility:** exact schema, fork, toolchain, runtime, accepted guest/verifier and dependency lock. Passing against one consumer profile does not imply all-Ethereum compatibility.

**Performance:** measured cost, latency, memory and success distribution under a frozen benchmark. Preserve the baseline, workload, hardware, environment, repetitions, failed runs and raw evidence.

**Delivery:** endpoint availability, capacity reservation, historical service observations and explicit delivery obligations. Historical latency is an observation, not a guarantee about every future request.

**Rights and access:** signed license declarations, permitted delivery mode and dependency-license inventory. Automated checks cannot conclusively establish ownership of all submitted material. Specify the review level.

**Composition and usage:** verified relationships to pinned dependencies, plus independently labeled paid-use receipts. An import graph is not causal proof of savings, and certificate possession is not usage.

### 4.3 Evidence grades, without a universal score

Record the method per claim: producer-declared, tested, independently reproduced, formally checked under assumptions, or observed in live jobs. These are not interchangeable levels on one ladder. Mathematical correctness and operational reliability answer different questions.

A market score may rank eligible offers for a particular buyer. It must not turn empirical speedup into mathematical certainty or let a high reputation compensate for an invalid proof.

## 5. Certification workflow

1. **Fund the demand and freeze criteria.** The buyer names its evaluator policy, acceptance profile, budget and deadlines. A certification commission is itself a service demand.
2. **Submit an immutable candidate.** Canonicalize the manifest and commit the payload digest, dependency lock and requested claims. Draft listings may exist, clearly labeled.
3. **Run cheap admission checks.** Validate schemas, signatures, size/resource limits, supported formats and declared rights. A digest authenticates bytes, not their origin story.
4. **Evaluate in isolation.** Rebuild from permitted inputs in a pinned sandbox. Treat package instructions as untrusted data. Evaluator signing keys and buyer wallets are inaccessible to submitted code.
5. **Execute the category-specific checks.** Lean, state-proof verification, program verification, replay, benchmarking or service evaluation according to the requested claim.
6. **Issue separate outcomes.** Accept supported claims, reject failed ones, and record unsupported or inconclusive claims. Preserve evidence and failure reasons.
7. **Publish the signed certificate and evidence reference.** Register status on L2. A signature proves the attester made the claim; trust depends on method and the buyer's issuer policy.
8. **Gate procurement and settlement.** A buyer checks applicability, issuer, status and any cheap result verification. The contract enforces the agreed acceptance predicate before release of funds.
9. **Monitor and supersede.** New code creates a new subject digest. New benchmarks create new claims. Incidents can suspend affected claims and trigger dependency reevaluation.

For Lean packages, use an isolated source rebuild and inspect the transitive assumptions of the actual exported theorem. Reject incomplete proofs relying on `sorryAx`; apply an explicit allowlist to other axioms and compiler-trust extensions. A text search for the word sorry is insufficient. [Lean axioms][s12]

## 6. Proposed machine-readable certificate

This is an illustrative schema, not a real certificate or established standard:

```json
{
  "schema": "asset-claim/v1",
  "subject": {
    "kind": "package-release",
    "manifestDigest": "digest of canonical manifest",
    "payloadDigest": "digest of delivered bytes",
    "dependencyLockDigest": "digest of exact dependency closure"
  },
  "claim": {
    "type": "correctness",
    "predicateId": "witness-query-verification/v1",
    "statementDigest": "digest of precise checked claim",
    "result": "accepted",
    "assumptionsDigest": "digest of declared trust assumptions"
  },
  "scope": {
    "consumerProfileDigest": "digest of pinned integration profile",
    "inputDomainDigest": "digest of permitted input domain"
  },
  "evaluation": {
    "method": "independent-reproduction",
    "evaluatorIdentity": "authorized evaluator identifier",
    "checkerImageDigest": "digest of pinned evaluation environment",
    "evidenceDigest": "digest of report and raw evidence",
    "evidenceURI": "content-addressed evidence location"
  },
  "lifecycle": {
    "issuedAt": "timestamp",
    "validUntil": "timestamp or profile-defined no-expiry",
    "statusReference": "registry record",
    "supersedes": null
  }
}
```

A benchmark certificate additionally commits its baseline, workload, environment and result distribution. A witness result additionally binds chain, block hash, state root and query digest. A reservation certificate additionally binds provider, capacity unit, time window, collateral and unique reservation ID.

Sign with explicit schema version, chain and registry domain separation. Canonical encoding must be deterministic. Use a separate demand-bound acceptance receipt with a nonce to authorize payment, so a reusable certificate cannot be replayed to collect unrelated bounties.

## 7. Trust, contracts and revocation

### Minimum implementation

- **Profile registry:** immutable evaluation profiles, approved issuer policies and governance/version changes.
- **Certification registry:** claim IDs, subject digests, issuer, evidence commitment, issuance/expiry and append-only status events.
- **Demand escrow:** frozen acceptance policy, authorized evaluator, amount, deadline and refund rules.
- **Settlement:** consumes a job receipt once and pays the snapshotted recipients.
- **Offchain workers:** perform checking, experiments, monitoring and content delivery.

These are responsibilities, not a requirement for five contracts. A compact implementation can combine registries and extend the existing escrow.

Existing attestation infrastructure such as EAS can be considered for records and schemas after checking deployment and SDK support on the chosen chain. It does not supply artifact-specific evaluators or establish that attestations are true. [EAS contracts][s13]

### Who certifies the certifier?

Start with a buyer-approved, separately operated evaluator and deterministic, published profiles. A separate agent using the creator's code and credentials is not independent evaluation. Use independent checker implementations or baselines when practical. AI can propose tests and explain failures; it should not issue correctness acceptance from prose alone.

Pay evaluators for completed evaluation work, not only favorable outcomes. Disclose producer funding and related-party relationships. Make rejected submissions visible to the requesting buyer so producers cannot silently shop only favorable reports. Add a second reproduction for higher-exposure claims when the cost warrants it.

For later disputes, distinguish reproducible fraud, ambiguous measurement disagreements and service incidents. Predetermine the arbiter, appeal period and admissible evidence. Bonds only deter behavior to the extent that violations are adjudicable and consequences are enforceable. Stake is not a correctness oracle.

### Revocation semantics

Keep an append-only record: active, suspended, revoked, expired or superseded, with reasons. Revocation does not erase what was observed historically. Suspend affected claim families rather than declaring every property false. A changed network profile can remove compatibility while an old theorem remains valid.

At job acceptance, snapshot the certificate and policy. Define whether later safety incidents cancel undelivered work; do not retroactively confiscate completed-job payments through an unspecified rule. Check the latest required status atomically at settlement where onchain policy requires it. Short-lived offchain status caches have explicit freshness and exposure limits.

Traverse typed reverse dependencies to find affected compositions. Child certificates do not automatically certify their parent: the integration relationship itself must be checked.

## 8. Certification should make buying faster

Expensive release checks happen before demand reaches the live execution path. Cache immutable manifests, downloaded bytes and checked compatibility. Keep certificate-status freshness separate from payload caching.

At purchase time, the agent performs cheap filters: exact subject digest, supported profile, trusted issuer/method, live status, valid rights, complete cost and deadline. Fresh witness or proof results still undergo their cheap deterministic verification. A third-party certificate never replaces root authentication.

Proposed policy:

```text
eligible = compatible
       AND required claims accepted by buyer policy
       AND certificate status sufficiently fresh
       AND access rights and privacy constraints satisfied
       AND estimated completion meets deadline

choose eligible offer minimizing:
  fee + retrieval + verification + integration + execution
  + allocated settlement + expected failure cost + cost of delay
```

Certification amortizes when repeated buyers avoid repeating an expensive evaluation. Measure the issuer's cost, buyers' residual checking cost and status lookup latency. If a local check is cheaper than fetching a certificate, perform it locally. Do not require a new onchain attestation transaction for every tiny witness query.

## 9. Benchmarks and economic evidence

Require paired comparisons with the same security level, output semantics, workload and hardware constraints. Separate cold and warm retrieval; include verification, queueing and settlement overhead. Preserve failures and timeouts rather than reporting only successful runs.

Use held-out tasks and randomized run order. Record corpus provenance and disclosure rules so certification does not silently leak a buyer's private workload. Do not claim a stable tail-latency guarantee from a handful of runs; report sample count and uncertainty. With private hardware, timing claims remain dependent on the evaluator or measurement environment.

Certificate fields report observed utility. Prices remain offers and agreed terms. Reward breadth using evidence of distinct workloads and independent users, while acknowledging that account count does not establish independence. Contributor splits come from agreed schedules. Causal performance attribution requires separate controlled evaluation.

The certification business can earn a fixed evaluation fee, renewal/monitoring fee or paid compatibility-maintenance fee. Creator bounties and usage revenue remain distinct. Avoid financing rewards by minting tokens merely because a certificate was issued.

## 10. Security of the asset and its evidence

Public metadata contains identifiers, scope and non-sensitive claims. Store private payloads and evidence encrypted offchain with scoped access. Use separate keys for evaluator signing, artifact encryption and agent spending. Certificates bind the evaluated plaintext digest inside the appropriate access boundary and the encrypted distribution object when needed. Low-entropy private data should not be exposed through guessable public commitments.

An attested digest does not prove delivery of a working decryption key. Define the trusted delivery gateway for the MVP. Download licenses cannot technically prevent recipients retaining plaintext. Hosted invocation keeps material with the operator but does not conceal it from that runtime by default.

A certificate claiming confidentiality needs evidence about the specific execution and key-release environment. A zk execution proof alone is not such evidence. Public examples are appropriate for the first demonstration.

## 11. Concrete hackathon experiment

**Scenario:** a buyer needs authenticated answers to a family of storage queries. A creator supplies a reusable query-verification package, optionally acquiring a Lean dependency from a second agent. A witness provider supplies fresh query bundles. The buyer uses the accepted package and verifies each result against its trusted root.

Implement two evaluator profiles first: `lean-package/v1` and `state-query/v1`. Add a small performance profile only after these deterministic checks work. A storage predicate is not a full Ethereum execution proof; display that limit.

Demonstrate these outcomes:

1. A funded capability request triggers creation or procurement.
2. A valid release receives scoped claim records and a creation payment.
3. An incompatible release and an invalid witness are rejected.
4. A valid but slower package retains correctness evidence while its speed claim fails.
5. A fresh buyer acquires a useful package and pays the agreed recipients.
6. A wrong-root result is rejected even if its provider has good reputation.
7. A revoked compatibility claim blocks new incompatible purchases while historical receipts remain inspectable.

Measure formal task completion/inference cost, acquisition/checking overhead, repeated-buyer evaluation savings, fresh-query latency, failure handling and certification cost. Show paid dependency use without assuming every imported lemma earned a causal share of speedup.

Suggested pass condition: the buyer accepts the correct subject under its policy, rejects deliberately mismatched cases, settles only accepted work, and demonstrates net procurement or evaluation savings on reported tasks. Quantitative thresholds must be frozen from the selected workload and baseline before candidate evaluation. No arbitrary percentage is asserted here.

## 12. Bounded flaws to track

- Certificates need trustworthy evaluators and precisely written claims.
- Benchmarks can be gamed; freeze profiles and expose all outcomes.
- Public data is copyable; sell useful production and delivery services.
- Future capacity needs actual provider authority and reservation accounting.
- Fork and toolchain changes require targeted recertification.
- Correct parts can compose incorrectly; evaluate integration separately.
- Broad reuse is evidence, not an automatic royalty entitlement.
- Certification costs can exceed small-job savings; amortize and batch.

## Conclusion

The differentiating layer is a machine-readable contract between an agent's claim and another agent's decision to spend. It connects exact artifacts, scoped evidence, consumer compatibility and commercial settlement.

Build a common catalog and certification envelope, then specialize evaluators and contracts by asset type. This supports a broad infrastructure economy without pretending that a theorem, a state witness and a future inclusion promise offer the same kind of guarantee.

## Primary sources

Sources checked September 15, 2026. Protocol status and repository behavior can change; deployment work must pin exact revisions. Source-backed facts above are separate from the proposed product design.

[s1]: https://lean-lang.org/doc/reference/latest/ValidatingProofs/
[s2]: https://eips.ethereum.org/EIPS/eip-1186
[s3]: https://eips.ethereum.org/EIPS/eip-7928
[s4]: https://github.com/leanEthereum/leanVM
[s5]: https://github.com/leanEthereum/leanSig
[s6]: https://eips.ethereum.org/EIPS/eip-4844
[s7]: https://eips.ethereum.org/EIPS/eip-7805
[s8]: https://eips.ethereum.org/EIPS/eip-7683
[s9]: https://eips.ethereum.org/EIPS/eip-4444
[s10]: https://ethereum.org/roadmap/statelessness/
[s11]: https://slsa.dev/spec/v1.2/provenance
[s12]: https://lean-lang.org/doc/reference/latest/Axioms/
[s13]: https://github.com/ethereum-attestation-service/eas-contracts
