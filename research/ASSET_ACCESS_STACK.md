# Agent asset access stack

Research note, 23 September 2026.

Companion to [ASSET_SCOPE_AND_CERTIFICATION.md](ASSET_SCOPE_AND_CERTIFICATION.md), [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md), [EXPERIMENT.md](EXPERIMENT.md), and [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md).

Status: proposed architecture. The existing contracts implement parts of the identity, acceptance, and settlement layers. They do not yet implement the complete access, compatibility, confidential execution, or revocation stack described here.

## 1. Product thesis

The platform should not be defined as a general marketplace or as a system that creates artificial ownership over information.

It should be defined as an onchain reuse and compatibility protocol for agent capabilities:

> An agent discovers a reusable capability, determines whether it can use it, acquires a scoped right to download or invoke it, integrates it through a versioned adapter, and produces a verifiable usage receipt that can settle payment and improve later compatibility estimates.

The marketplace is one interface over that protocol. The defensible layer is the combination of immutable asset identity, scoped evidence, compatibility history, controlled access, adapters, execution receipts, and settlement.

## 2. Non-negotiable information constraint

Once an agent receives information in plaintext, no token, contract, encryption scheme, or ownership transfer can make that agent forget it.

Suppose Alice controls a token associated with secret `S`:

1. Alice receives a key and decrypts `S`.
2. Alice copies `S` into memory, a log, or another machine.
3. Alice transfers the token to Bob.
4. The contract now records Bob as the token holder.
5. Alice still possesses her earlier copy of `S`.

Rotating the encryption key can prevent Alice from decrypting a new ciphertext. It cannot erase plaintext that she already obtained. Re-encrypting the asset for Bob has the same limitation.

Therefore the protocol can enforce transfer of future authorization, but it cannot enforce transfer of exclusive knowledge.

The precise guarantee should be:

> A transfer or revocation changes who may perform future protocol-authorized operations. It does not revoke previously acquired knowledge or outputs.

This constraint determines which asset forms are technically honest.

## 3. Separate the artifact from its rights

Four objects must remain distinct.

### 3.1 Asset identity

An immutable digest identifies exact artifact bytes and a versioned manifest. It does not itself grant ownership or access.

### 3.2 Asset control right

This defines who may publish later versions, change future commercial terms, or administer status. It may be transferable, but a transfer does not alter old accepted jobs or old artifact identities.

### 3.3 Access right

This defines who may download or invoke a version, for which operations, under which quota, and until what time.

### 3.4 Revenue right

This defines who receives payments from later jobs or invocations. It may be separate from technical control and access.

Usage receipts are evidence that an invocation occurred. They are not ownership tokens.

A single ambiguous asset NFT should not represent all four objects.

## 4. Supported asset forms

The initial scope should distinguish three commercial forms.

### 4.1 Public capability package

The agent downloads and runs a versioned module. There is no durable secrecy claim. Value comes from correctness, integration, maintenance, compatibility, performance, and avoided rebuilding cost.

Examples include:

- an optimized proving module;
- a tool adapter;
- a verification library;
- a workflow;
- a theorem package;
- a reproducible evaluation harness.

This is the strongest first asset form because it matches Experiment 01 and supports direct verification.

### 4.2 Confidential capability service

The model, data, strategy, or implementation remains inside a controlled runtime. The agent obtains an invocation right and receives only allowed outputs.

The token or grant represents the right to call the capability. It does not represent ownership of the secret plaintext.

### 4.3 Input-bound result

A worker produces an output or proof for one committed input. It may be reusable only when another job has exactly compatible context and acceptance rules.

This is primarily a job result and receipt, not a generally transferable package.

Service commitments such as reserved compute, posting, or retrieval capacity need separate capacity and failure rules. They should not be collapsed into the package model.

## 5. What exists onchain

The full executable asset usually does not live onchain. The chain acts as the control plane.

The chain should hold or commit to:

- immutable asset and version identifiers;
- manifest and payload digests;
- interface and compatibility-profile digests;
- evidence and evaluator references;
- lifecycle status;
- access-policy commitments;
- scoped access grants;
- job terms and escrow;
- contributor and adapter payment schedules;
- execution receipts or their commitments;
- revocation and supersession events.

The executable bytes, model weights, datasets, proofs, and detailed reports normally live in content-addressed storage, package registries, evaluator storage, or confidential execution infrastructure.

An onchain digest authenticates retrieved bytes. It does not provide availability, secrecy, correct interpretation, or legal ownership by itself.

## 6. End-to-end asset stream

```text
CREATION AND REGISTRATION

Creator builds payload
    ↓
Creator produces canonical manifest
    ↓
Payload and manifest receive immutable digests
    ↓
Evaluator checks scoped claims under a pinned profile
    ↓
Registry records identity, evidence, status, and terms


DISCOVERY AND PROCUREMENT

Agent states task requirements and its execution profile
    ↓
Indexer resolves candidate versions from registry events
    ↓
Hard compatibility filters remove ineligible candidates
    ↓
Compatibility estimator ranks eligible candidates
    ↓
Agent compares reuse, compose, create, and decline
    ↓
Agent funds a job or acquires a scoped access grant


ACCESS AND EXECUTION

Agent proves control of the authorized identity
    ↓
Access broker checks grant, status, quota, nonce, and expiry
    ↓
Broker releases a wrapped key or an invocation capability
    ↓
Versioned adapter converts agent input to asset input
    ↓
Local sandbox or confidential runtime executes the asset
    ↓
Output validator checks schema, bindings, and proof
    ↓
Agent receives only the result required by its task


RECEIPT AND SETTLEMENT

Runtime or worker produces an execution receipt
    ↓
Escrow verifies the proof or accepted receipt policy
    ↓
Worker, contributor, and adapter payees receive credits
    ↓
Usage event updates realized value and compatibility history
```

## 7. Payload layer

The payload is the useful object:

- executable code;
- model weights;
- private data;
- a circuit;
- a proof package;
- a workflow;
- an adapter;
- a query engine.

For a public package:

```text
payloadDigest = hash(exact asset bytes)
```

Any byte change creates a new version.

For an encrypted package:

```text
dataKey = random symmetric key
ciphertext = Encrypt(dataKey, assetBytes)
plaintextDigest = hash(assetBytes)
ciphertextDigest = hash(ciphertext)
```

The plaintext digest binds evaluation to the actual asset. The ciphertext digest binds delivery to the stored encrypted object.

Publishing a digest can expose a low-entropy secret through guessing. Commitments to predictable data need a random salt or must remain inside an appropriate access boundary.

## 8. Manifest layer

The payload is not usable without a machine-readable description.

```text
AssetManifest
  schemaVersion
  assetId
  version
  payloadDigest
  payloadLocation
  interfaceDigest
  inputSchema
  outputSchema
  runtimeRequirements
  dependencyLockDigest
  supportedProfiles
  deliveryMode
  accessPolicyDigest
  evidenceReferences
  adapterReferences
  licenseReference
  pricePolicy
  contributorSchedule
  confidentialityPolicy
```

Canonical serialization is required. The same logical manifest must always produce the same digest.

The confidentiality section should state:

```text
deliveryMode
confidentialityThreatModel
keyCustody
plaintextExposure
permittedOperations
allowedQueryTypes
queryBudget
outputLeakagePolicy
revocationSemantics
runtimeAttestationPolicy
```

A confidentiality claim must name who can see plaintext. Possible readers include the creator, storage operator, key service, runtime operator, evaluator, invoking agent, and hardware environment.

## 9. Evidence and claim layer

Evaluation should issue independent scoped claims, not one universal score.

Examples:

```text
Identity claim:
  exact payload X was rebuilt from source commit Y

Correctness claim:
  X passed test suite C under evaluator profile P

Compatibility claim:
  X ran with agent profile A through adapter D

Performance claim:
  X reduced PGU against registered alternative Z

Confidentiality claim:
  plaintext was available only inside runtime profile R
```

Each claim binds:

```text
subjectDigest
claimType
statementDigest
evaluationProfileDigest
inputDomainDigest
evaluatorIdentity
evidenceDigest
result
issuedAt
validUntil
statusReference
```

Evidence methods should remain explicit: producer-declared, tested, independently reproduced, formally checked under assumptions, or observed in live use.

## 10. Registry layer

A future registry record could extend the current `ModuleRegistry.Version`:

```solidity
struct AssetVersion {
    bytes32 manifestDigest;
    bytes32 payloadDigest;
    bytes32 interfaceDigest;
    bytes32 evidenceSetDigest;
    bytes32 accessPolicyDigest;
    address controller;
    address contributor;
    uint256 contributorFee;
    uint8 accessMode;
    uint8 status;
    uint64 registeredAt;
}
```

The registry should make versions immutable. Corrections create a new version or status event rather than modifying historical identity.

Suggested asset lifecycle:

```text
Draft
  ↓
Submitted
  ↓
Certified
  ↓
Active
  ↓
Suspended, Superseded, or Revoked
```

Revocation does not erase historical receipts. It changes whether new procurement or execution may proceed.

## 11. Discovery and compatibility layer

Contracts provide identity and events, but they are not suitable search engines. An indexer builds a searchable catalog from registry state and evidence.

The agent supplies two profiles.

```text
TaskProfile
  requestedCapability
  inputDomain
  inputSchema
  requiredOutput
  deadline
  maximumSpend
  correctnessPolicy
  confidentialityPolicy

AgentProfile
  supportedRuntimes
  toolchainVersions
  availableResources
  availablePermissions
  trustedEvaluators
  supportedInterfaces
  sandboxPolicy
```

Compatibility has two stages.

### 11.1 Hard eligibility

A candidate is removed when any mandatory condition fails:

- incompatible input or output schema;
- unsupported runtime or proof system;
- unacceptable license;
- inactive or revoked required claim;
- missing permission;
- impossible deadline;
- unsatisfied privacy policy;
- incompatible dependency lock.

### 11.2 Probabilistic fit

Eligible candidates are ranked using prior evaluations and observed adoption receipts.

The estimate is conditional on asset version, agent profile, task, adapter, and environment. It is not a permanent property of the asset.

The agent then compares:

```text
asset price
+ retrieval cost
+ preflight cost
+ expected adaptation cost
+ execution cost
+ settlement cost
+ expected failure loss
+ delay cost
```

against the estimated costs of composition, creation, or decline.

## 12. Adapter layer

The adapter converts the agent's internal request into the asset's canonical interface and validates the response.

```text
agent-native request
    ↓
validate task fields
    ↓
map schemas and supply permitted defaults
    ↓
resolve dependencies
    ↓
invoke asset version
    ↓
validate proof and output bindings
    ↓
return agent-native result
```

An adapter must be versioned and identified by a digest. A correct asset combined with a faulty adapter can still produce an incorrect agent result.

A compatibility claim should therefore bind:

```text
assetVersion
agentProfileDigest
taskProfileDigest
adapterDigest
runtimeProfileDigest
evaluationResult
```

Adapters can themselves become reusable assets with their own provenance, evidence, dependencies, and payees.

## 13. Access grant layer

An agent acquires a scoped grant before delivery or execution.

```text
AccessGrant
  grantId
  assetVersion
  grantee
  permittedOperations
  callsRemaining
  validFrom
  expiresAt
  transferability
  spendingLimit
  outputPolicyDigest
  nonceDomain
```

Suggested grant lifecycle:

```text
None
  ↓
Active
  ↓
Exhausted, Expired, or Revoked
```

A custom grant record may be clearer than a generic NFT because agent access often requires quotas, deadlines, task scope, and identity binding.

Possible token use remains precise:

- an ERC-721 can represent administration of future asset terms;
- an ERC-1155 can represent a number of invocation credits;
- a nontransferable grant can bind access to one agent identity;
- a registry entry identifies the version without being a token;
- a receipt records completed use without granting access.

## 14. Access broker layer

The access broker connects onchain authorization to offchain delivery.

For each access attempt:

1. The broker sends a fresh random challenge.
2. The agent signs the challenge with the identity associated with the grant.
3. The broker verifies the signature and nonce.
4. The broker reads sufficiently confirmed registry and grant state.
5. It checks asset status, expiry, quota, operation, version, and task scope.
6. It releases a wrapped data key or a short-lived invocation capability.

A short-lived capability can bind:

```text
assetVersion
grantId
agentIdentity
permittedMethod
inputLimit
expiresAt
uniqueNonce
brokerSignature
```

The execution runtime independently verifies this capability. A broker response must not become an unlimited bearer credential.

## 15. Delivery modes

### 15.1 Local encrypted delivery

1. The payload is encrypted under a random data key.
2. The broker verifies the agent's active grant.
3. The agent supplies an ephemeral encryption public key.
4. The broker wraps the data key to that public key.
5. The agent fetches the ciphertext and verifies its digest.
6. The agent unwraps the data key and decrypts the package.
7. The agent verifies the plaintext digest.
8. The agent loads the package into a sandbox.

At step 6 the agent gains plaintext. The protocol can record licensing and attribute a leak, but it cannot ensure deletion after transfer or revocation.

### 15.2 Confidential invocation

1. A controlled runtime fetches the encrypted payload.
2. The runtime produces evidence about the code and environment it is running.
3. A key service validates that evidence and the access grant.
4. The key service releases the data key only to the approved runtime.
5. The runtime decrypts the payload internally.
6. The agent supplies a committed input.
7. The runtime executes the registered function.
8. The runtime returns only the allowed output, proof, and receipt.
9. The runtime clears invocation plaintext when execution ends.

This protects against direct recipient copying, but it still depends on the chosen runtime, hardware, key-service, and operator threat models.

Repeated queries can leak a model, dataset, or strategy without directly revealing its bytes. Confidential assets need query budgets, output restrictions, anomaly detection, rate limits, and asset-specific leakage tests.

### 15.3 Privacy mechanism boundaries

- Encryption protects stored and transmitted bytes. It does not control plaintext after decryption.
- A hosted service keeps plaintext from the buyer, but the service operator can normally inspect it.
- A trusted execution environment narrows plaintext exposure to attested hardware and code, subject to hardware and operational trust.
- Multiparty computation prevents one operator from holding the complete secret, at greater protocol and compute cost.
- Fully homomorphic encryption permits selected computations on ciphertext, generally with significant performance and implementation constraints.
- A zero knowledge proof can prove that a computation followed a statement without exposing its witness to the verifier. It does not by itself hide the secret from the machine performing the computation.
- Watermarking helps attribute leakage. It does not prevent copying.

## 16. Agent runtime integration

The safest integration does not place the raw asset in the language model's context.

The agent installs a public capability descriptor:

```text
toolName
assetVersion
description
inputSchema
outputSchema
compatibilityEstimate
estimatedCost
invocationEndpoint
requiredGrant
adapterDigest
```

When the planner selects the capability:

1. The planner produces structured input.
2. The adapter validates and translates it.
3. The tool executor proves authorization.
4. The executor invokes a local sandbox or remote runtime.
5. The executor validates the returned output and proof.
6. Only the task-relevant result is placed into model context.

The phrase "the agent has the asset" can mean three different states:

1. The planner knows that the asset exists.
2. The executor is authorized to invoke the asset.
3. The model or runtime has received the raw asset contents.

The first two are sufficient for confidential capabilities. The third should be avoided unless local plaintext delivery is intentional.

## 17. Execution receipt layer

Every invocation should produce a receipt:

```text
ExecutionReceipt
  jobId
  assetVersion
  grantId
  agentProfileDigest
  taskProfileDigest
  adapterDigest
  runtimeDigest
  inputCommitment
  outputCommitment
  executionStatus
  executionCost
  startedAt
  completedAt
  proofOrAttestationReference
```

The receipt binds actual use to a version, adapter, runtime, and committed task. It supplies the evidence needed for settlement and later compatibility estimates.

Suggested invocation lifecycle:

```text
Requested
  ↓
Authorized
  ↓
Executing
  ↓
Completed
  ↓
Verified
  ↓
Settled
```

Alternative terminal states include rejected, failed, expired, and disputed. These should not be merged into asset revocation automatically.

## 18. Settlement and learning loop

After execution:

1. The escrow checks the proof or accepted receipt policy.
2. The job moves to its terminal state.
3. The worker receives execution compensation.
4. The asset contributor receives the snapshotted usage fee.
5. An adapter contributor may receive an integration fee.
6. Unused buyer funds are credited back.
7. A usage event records the exact version and receipt commitment.
8. The indexer updates realized value and compatibility history.

Compatibility evolves through evidence:

```text
registry and evaluation history
    ↓
prior compatibility estimate
    ↓
agent-specific preflight
    ↓
updated estimate and adapter plan
    ↓
paid execution outcome
    ↓
observed compatibility and actual cost
```

The changing estimate should remain offchain. The underlying evidence, profile commitments, version identities, receipts, and payments can be anchored onchain.

## 19. Security invariants

The stack should preserve these invariants.

1. An asset version never changes meaning after registration.
2. Every claim binds one exact subject, method, scope, and evidence bundle.
3. Hard incompatibility cannot be overridden by reputation or a probabilistic score.
4. An access grant names exact operations, identity, version, quota, and expiry.
5. A transfer affects future authorization only.
6. A downloaded plaintext asset is treated as permanently disclosed to that recipient.
7. A confidential invocation never releases the underlying asset key to the agent.
8. Every adapter used by a paid job is identified and snapshotted.
9. Every settlement binds the job, asset, adapter, runtime, input, output, and recipients required by its policy.
10. Historical receipts remain inspectable after suspension or supersession.
11. Payments do not rely on a mutable aggregate compatibility score.
12. A proof verifies only its encoded statement. It does not establish unencoded confidentiality, ownership, or economic value.

## 20. Mapping to the current implementation

The current repository already covers parts of the proposed stack.

### Creation and acceptance

`contracts/src/CreationBounty.sol` freezes demand, evaluator, policy, deadlines, and payment. A passing signed verdict registers the accepted version and releases the creation bounty.

### Immutable asset identity

`contracts/src/ModuleRegistry.sol` records the demand, candidate digest, source commit, guest key, evaluation policy, report, contributor, and contributor fee. This is the first asset registry.

### Verified usage and payment

`contracts/src/UsageEscrow.sol` snapshots the accepted version, verifier identity, statement, worker, contributor, fees, and deadline. It settles only after verifying the proof and exact public bindings.

### Payload and integration description

`candidate/manifest.json` already anticipates the module interface, compatibility manifest, dependencies, composition, formal evidence, integration instructions, license, terms, and contributor identity.

### Procurement agent

`agent/runner/` constrains the creator and requires a structured reuse, compose, create, or decline decision. The seeded existing-capability and no-opportunity controls are early procurement-policy tests.

### Current missing middle

The repository does not yet implement:

- a complete canonical asset manifest and resolver;
- agent and task profile schemas;
- compatibility claim registration;
- adapter registration and attribution;
- access grants;
- an access broker;
- encrypted key release;
- a confidential invocation runtime;
- generalized execution receipts;
- asset and claim suspension or revocation;
- compatibility-history aggregation.

These are later layers, not prerequisites for completing the current public-module reuse experiment.

## 21. Recommended implementation order

### Phase 1: complete the public capability path

1. Finish Experiment 01 with one immutable accepted module.
2. Adopt it unchanged in the fresh reuse job.
3. Record the adapter, compatibility profile, execution cost, and settlement receipt.
4. Compare acquisition and integration cost with the best available alternative.

### Phase 2: make compatibility explicit

1. Define canonical `AgentProfile`, `TaskProfile`, and `CompatibilityClaim` schemas.
2. Bind the exact adapter and runtime to each compatibility result.
3. Add hard eligibility filtering and an explainable offchain cost estimate.
4. Record success, failure, and actual integration cost for every attempted adoption.

### Phase 3: add scoped access

1. Define `AccessGrant` with identity, operation, quota, expiry, and nonce rules.
2. Implement a broker that verifies onchain grants.
3. Issue short-lived invocation capabilities.
4. Keep access rights separate from asset identity and revenue rights.

### Phase 4: test one confidential capability

1. Choose one asset whose value genuinely depends on secret state.
2. Keep the asset behind a remote invocation boundary.
3. Document exactly who can see plaintext.
4. Add runtime evidence, key-release policy, query limits, and output leakage tests.
5. Demonstrate revocation of future calls without claiming deletion of prior outputs.

Do not begin by making every asset confidential. Confidential execution introduces a second security system and can obscure whether the core reuse economics work.

## 22. Scope recommendation

The first and most important asset should be:

> A versioned, independently evaluated executable capability that reduces an agent's total task cost and exposes a stable machine-readable invocation interface.

Its value need not depend on secrecy. The system should prove that the agent can discover it, establish compatibility, integrate it without human rewriting, execute it, verify the result, and pay its contributors.

For secret-bearing assets, the product should sell a controlled capability invocation rather than pretend to transfer exclusive ownership of information.

The long-term platform asset is the resulting compatibility graph:

```text
asset version
+ task profile
+ agent profile
+ adapter
+ runtime
+ evaluation evidence
+ adoption outcome
+ realized cost
```

Each verified use makes the next acquire, compose, create, or decline decision cheaper and more reliable.

## 23. Open design decisions

1. Which asset record fields belong directly in `ModuleRegistry`, and which remain committed through the manifest digest?
2. Should access grants be custom contract records, ERC-1155 usage credits, account-bound authorizations, or a combination?
3. Which party operates the access broker, and what prevents selective denial or stale-chain authorization?
4. Which execution receipt types are accepted for ordinary software that does not produce a cryptographic proof?
5. How are adapter contributors paid without making payout schedules unbounded?
6. What revocation conditions affect new jobs, authorized but unstarted jobs, and executing jobs?
7. How does a confidential runtime prove its identity and key-handling policy to the buyer?
8. Which output leakage tests apply to models, datasets, strategies, and query engines?
9. When is agent-specific preflight cheaper than relying on prior certification?
10. How should external preexisting assets enter the registry without passing through a creation bounty?

These questions should be answered per asset class. A universal answer would hide materially different trust and execution models.
