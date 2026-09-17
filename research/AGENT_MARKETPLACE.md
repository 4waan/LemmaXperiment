# Agent capability marketplace: functional design

Design proposal, 15 September 2026. Complements [EXPERIMENT.md](EXPERIMENT.md); no implementation or measured results are implied.

## 1. What the product does

An agent encounters work it cannot complete within its limits. It discovers evaluated capabilities, negotiates a machine-readable offer, buys permission to invoke one, receives a verifiable result, and continues its task. When no suitable capability exists, funded demand commissions a creator agent to build it.

**The traded unit is a defined capability with an interface, evidence and commercial terms.** A token can represent control of the asset. Jobs and licenses grant scoped permission to use it.

For the initial proof-focused product:

- Buyer agent operates an application or proving workflow.
- Creator agent builds or composes a module when funded demand appears.
- Provider runner executes approved modules and generates proofs.
- Evaluator independently reviews new versions and benchmarks.
- Humans configure budgets, privacy policies and escalation boundaries, and inspect failures.

The same operator can run multiple roles in the demo, but disclose that relationship. Independent machines and wallets alone do not establish independent economic actors.

## 2. Three kinds of purchase

### Invoke, the default

Buy one execution of module M at version V on committed input I. The provider keeps the implementation, executes it and returns the required proof/result. Payment settles on verified completion.

This offers enforceable per-service billing because future executions pass through the service. It does not stop a creator or authorized provider from copying their own code. Confidential customer input also remains visible to the provider unless a separate protected-computation design is implemented.

### Download, optional later

Buy access to a versioned package for local execution. Deliver encrypted artifacts to an authorized runtime. The buyer can retain the plaintext after decryption. Expiry stops future downloads or updates, not use of an existing copy. Licensing terms cannot be mistaken for cryptographic prevention of copying.

### Commission, when there is a gap

Fund a creation request with an interface, outcome, acceptance policy, budget and deadline. A creator can reuse, compose, create or decline. A passing evaluation releases the bounty and registers the new accepted version. Subsequent invocation jobs pay usage fees.

Do not add a token for each category merely to increase token count. Start with one asset registry and contract records for demands, grants and jobs.

## 3. What makes this an agent marketplace

The normal purchasing surface is an API/SDK with typed inputs and deterministic status codes. A monitoring dashboard is for the human operator.

The buyer's procurement loop:

1. Detect a capability or cost gap from its actual task.
2. Search using interface, version, trust, data-handling and budget constraints.
3. Reject incompatible offers before considering price.
4. Request signed quotes from eligible providers.
5. Reserve spending budget and fund one job, or commission a missing capability.
6. Authenticate to the provider, submit allowed data and track the job.
7. Verify the result and record the receipt.
8. Resume its parent task or follow a bounded failure policy.

Descriptions help discovery; the machine-readable contract determines compatibility. A persuasive listing cannot override the buyer's spending or privacy rules.

### Illustrative capability manifest

```json
{
  "schemaVersion": 1,
  "assetId": "proof-witness-module",
  "release": "1.0.0",
  "interface": "ethereum.block-proof.v1",
  "inputSchema": "content-addressed-schema-reference",
  "outputSchema": "content-addressed-schema-reference",
  "delivery": "invoke",
  "proofSystem": "pinned-sp1-release",
  "verificationKeyRef": "registered-guest-key-reference",
  "dataPolicy": {
    "providerSeesInput": true,
    "trainingUse": false,
    "declaredRetentionSeconds": 0
  },
  "pricing": {"mode": "quote-per-job"},
  "evidenceRef": "accepted-evaluation-reference"
}
```

This is an illustrative schema, not an actual listing. Retention and training declarations are contractual/provider claims unless independently enforced or audited. They are not proven by a zkVM execution proof.

## 4. Keep three identities separate

**Agent identity:** which operator controls this service and its registered endpoints.

**Asset identity:** which immutable module version, program key, evidence and commercial policy are being offered.

**Session authority:** what this particular agent process may spend or access now.

A wallet address does not establish competence. Agent identity tokens should not automatically unlock customer data or spending authority. ERC-8004 is a draft framework for agent discovery, reputation and validation; it explicitly leaves payments separate. It is a possible adapter, not a requirement for this MVP. [ERC-8004](https://eips.ethereum.org/EIPS/eip-8004)

The human/operator owns a treasury account. The runtime uses a restricted signer/controller with contract/method allowlists, per-job and daily caps, expiry, maximum concurrency, permitted counterparties and a separate bounty ceiling. The model receives capability handles, not the treasury private key.

Validate signatures for both ordinary wallets and supported smart accounts. EIP-712 defines typed signing, while ERC-1271 defines contract signature validation. Replay prevention still needs application nonces and deadlines. [EIP-712](https://eips.ethereum.org/EIPS/eip-712), [ERC-1271](https://eips.ethereum.org/EIPS/eip-1271)

## 5. What a token actually stores

A proposed AssetToken can identify the controller of future commercial listings for an asset family. Releases remain immutable.

Public onchain records may contain:

- Asset ID and controller address.
- Release manifest digest and evidence digest.
- Approved guest verification key and schema IDs.
- License/usage-policy reference.
- Payment recipient or rule for future offers.

The token must not contain plaintext customer data, decryption keys, wallet keys, service credentials or private source code. Smart-contract private fields and Base64 metadata are not secrecy mechanisms. ERC-721 metadata is a URI-based public interface, not an encrypted vault. [OpenZeppelin ERC-721](https://docs.openzeppelin.com/contracts/5.x/erc721)

### Transfer semantics

A transfer changes only the explicitly defined control rights for future offers. Existing jobs retain their version, recipients and terms. Transfer does not erase the former owner's files, give the new owner historical customer inputs, or establish legal IP ownership beyond the actual license agreement.

For the MVP, the registry controller is sufficient. Add ERC-721 ownership only if transferring that control is part of the demo. Invocation rights should remain scoped to jobs, not be a side effect of holding the creator token.

## 6. Where private data lives

Distinguish three data classes.

### Asset code and evidence

Default: publish the specification, evidence scope and public manifest. If implementation confidentiality is needed, encrypt the source/binary bundle in object storage. Approved evaluators and provider runners receive controlled access. Buyers using invoke mode do not receive the bundle.

Public source is also a valid choice. In that case customers pay for execution, maintenance and evaluated integration rather than an exclusive secret.

### Customer job inputs

Private inputs are encrypted per job and delivered only to the selected runtime. They are not part of the reusable asset and never transfer with its token. The marketplace index stores opaque references and the minimum necessary commitment.

Start with public historical Ethereum fixtures for the proving experiment. Add a separate private-payload access test using synthetic data. This separates proof feasibility from confidentiality claims.

### Operational secrets

Signing keys, storage credentials and encryption master keys stay in a managed secret/key service and narrowly authorized processes. Never include them in prompts, package metadata, logs, transaction calldata or agent memory exports.

Data sent to a hosted language model is exposed to that model service under its terms. Keep sensitive witness bytes in deterministic tool runtimes where the agent can operate on handles and status summaries.

## 7. A practical encryption and authorization flow

Use an established envelope-encryption library and managed key service for the MVP. Envelope encryption uses a data key for the content and a separate key to protect that data key. [AWS Encryption SDK concepts](https://docs.aws.amazon.com/encryption-sdk/latest/developer-guide/concepts.html)

1. Generate a random data key per artifact version or job through the supported encryption library.
2. Encrypt the content with authenticated encryption. Let the library manage nonce generation safely. Bind tenant, object ID, version and policy version as authenticated context.
3. Store ciphertext in private object storage. Store the wrapped data key separately in its metadata service; never place the plaintext key onchain.
4. Register a ciphertext digest and opaque object reference. If a plaintext commitment is needed for private low-entropy data, use an appropriate hiding commitment, such as a domain-separated salted hash with the salt kept private until authorized disclosure. An ordinary hash does not conceal guessable inputs.
5. The agent obtains a one-use challenge and signs it with its authorized session identity. Bind audience, chain, resource, action, nonce and expiration.
6. The gateway checks identity, delegated session scope, the exact funded job or grant, expiry, revocation, policy version and chain confirmation policy. It reserves any usage atomically.
7. For invoke mode, authorize only the selected runner to unwrap the data key. Run it in an isolated process with minimal network access. Return only declared outputs and the proof.
8. Record a scoped receipt. Expire access and remove transient data under the retention policy. Treat deletion as an operational promise subject to backups and copies, not as something the blockchain proves.

The initial storage/gateway/runner operator can access decrypted data. KMS protects key custody and access policy; it does not make an authorized malicious runtime unable to leak data.

Threshold access-control services are a possible later replacement for parts of the key gateway. Lit documents wallet-authenticated decryption conditions. Validate current network support and its trust assumptions before integration. It cannot retract plaintext already delivered. [Lit access-control flow](https://developer-dev.litprotocol.com/docs/howitworks/)

## 8. What token gating can and cannot secure

- An unpaid agent cannot obtain a new authorized session or ciphertext decryption through the gateway.
- An expired grant cannot authorize a new invocation.
- A forged object reference cannot cross the tenant or job boundary.
- Ciphertext tampering is detected by authenticated encryption and artifact verification.
- A stolen authorized session can act within its limits until revoked or expired. Minimize scope and lifetime.
- A stolen asset-controller wallet can control its defined future rights. Tokenization does not prevent theft.
- A recipient that obtained plaintext can copy it. Key rotation affects future access, not old copies.
- Hosted execution reduces source distribution, but trusts the provider with code and input.
- A zero-knowledge proof can conceal designated witness material from the verifier when the chosen proof mode supports that property. Public outputs can still leak information, and the proving runtime usually sees the witness.

Do not claim encrypted delivery, zero knowledge, an NFT or a TEE alone provides perfect secrecy, noncopyability or fair payment-for-data exchange.

## 9. One invocation, end to end

1. Buyer agent searches compatible accepted versions and requests a quote.
2. Provider returns a signed quote binding asset/version, expected program key, price, worker, contributor share, input policy, proof/result format, deadline and quote expiry.
3. Buyer's policy controller validates the quote and atomically reserves its budget before funding. Concurrent agents cannot spend the same remaining budget twice.
4. UsageEscrow snapshots terms and emits the funded job.
5. Buyer signs a job-scoped challenge and uploads allowed input. The gateway checks the funded assignment rather than a client-supplied payment screenshot or transaction hash alone.
6. Runner validates/decrypts input, generates the proof and locally checks it.
7. For the MVP's public proof results, submit proof and public values on Arbitrum. Contract verification checks the exact guest and job/domain/input/result bindings, then credits fixed recipients once.
8. Buyer obtains the result from transaction data or the result service, independently verifies it, and continues its task. Invalid/late proofs cannot settle. Timeout refunds follow the frozen contract rules.

All retries use an idempotency key binding buyer, intent and request digest. The same key with different request content fails. Duplicate messages do not create extra jobs, charges or consumption. Retry limits and backoff are bounded.

**Private result delivery is separate future scope.** A ciphertext hash does not prove that the buyer received a usable decryption key. Do not release payment for private data solely because a seller posted an encrypted blob. A reviewed encrypted-result verification protocol or an explicitly trusted delivery/dispute service is needed. The initial proof demo uses public results to avoid making that unimplemented claim.

## 10. Machine-facing API

Conceptual tool names and responsibilities:

```text
market.search_capabilities(requirements)
market.get_manifest(assetId, version)
market.request_quote(assetId, version, inputDescriptor)
market.fund_job(signedQuote, idempotencyKey)
market.get_job(jobId)
market.get_access_challenge(jobId, action)
market.invoke(jobId, signedChallenge, inputHandle)
market.fetch_result(jobId)
market.post_creation_demand(spec, budget, idempotencyKey)
market.submit_candidate(demandId, artifactDigest)
```

Expose an OpenAPI/JSON interface first and an MCP adapter for agent tool use. Async job progress comes through polling or signed/event-correlated notifications. Machine responses include stable codes such as INCOMPATIBLE_VERSION, BUDGET_EXCEEDED, ACCESS_EXPIRED, NO_CAPABILITY, PROOF_REJECTED and JOB_EXPIRED.

MCP supplies callable tools; the market's contracts and authorization service decide what those calls are allowed to do. Treat third-party manifests, README files and returned error text as untrusted data. They cannot instruct the controller to send money, expose credentials or change evaluator policy.

x402 can later support simple pay-per-HTTP services. Its documentation lists Arbitrum One support, but payment verification does not establish that an answer is correct or implement this creation bounty. Keep the initial proof escrow as the authoritative settlement mechanism; do not charge the same work through both paths. [x402 network support](https://docs.x402.org/core-concepts/network-and-token-support), [facilitator responsibilities](https://docs.x402.org/core-concepts/facilitator)

## 11. Data access grants and quotas

A grant records subject agent/session, asset version, action (invoke or download), expiry, maximum calls, input policy and revocation version. It is bound to its subject and is nontransferable in the MVP.

For first implementation, a funded job is a one-invocation grant. This avoids complex subscription metering. Reserve the grant transactionally before execution; retries resume the same job. A per-job key-service authorization checks that reservation. Two concurrent invocations cannot consume one grant twice.

Where to enforce limits:

- Treasury controller: maximum spend, allowed contracts and counterparties.
- API/gateway: identity, job ownership, resource authorization, replay checks.
- Runner: CPU/memory/time/input limits and outbound-network restrictions.
- Contract: immutable job, exact verification, deadline, payout once and refund.

A public token ID can be discoverable. Private resource handles are opaque, but authorization must work even when an attacker knows a valid handle.

## 12. Composition and creator payments

A composite module references immutable component versions and licenses. At listing time the provider declares a bounded, flattened payout schedule. The quote snapshots that schedule, and the final job proof uses a registered composite guest key.

That pays the agreed contributors for this service. It does not measure the causal contribution of every library at runtime. Deduplicate shared dependencies and avoid unbounded onchain dependency traversal.

Private modules are harder to compose. The next creator needs authorized source access, an approved executable interface, or a separate service invocation with compatible proof outputs. Nested service calls add latency and fees. Start with one module and one contributor; demonstrate composition only after its technical and licensing path is clear.

## 13. Concrete MVP deployment

Logical services can share one backend initially:

1. Buyer agent with restricted signer and procurement policy.
2. Creator agent with a sandbox and public development fixtures.
3. Independent evaluator environment with held-out tests and signing identity.
4. Market API/indexer plus PostgreSQL for manifests, requests and idempotency.
5. Authorization gateway plus managed keys and encrypted object storage.
6. Provider runner with the approved SP1 guest and resource limits.

On Arbitrum: CreationBounty, ModuleRegistry and UsageEscrow from the experiment. Optional AssetToken controls future listings; it is not needed for proof correctness or encrypted storage.

Use server-side authorization on every resource/action. Lock down artifact fetching against internal-network access and redirects. Reject archive path traversal, cap payload/decompression size and sandbox builds. Validate schemas and signatures before scheduling work. Event indexing must handle duplicates and reorgs; key release is irreversible, so select a confirmation policy before releasing sensitive plaintext.

## 14. Practical demo and checks

### Product demo

- Buyer agent receives a proving task and searches the market without a human selecting a listing.
- If nothing fits, it posts funded demand within its commission budget.
- Creator submits a candidate; evaluator accepts or rejects it.
- Acceptance pays the bounty and publishes the manifest.
- Buyer funds invocation, obtains job-scoped access and receives a verified result.
- A second agent uses the same accepted release and pays a contributor fee.

### Separate synthetic privacy checks

- Ciphertext/object metadata is visible without revealing plaintext.
- Unpaid agent and another tenant are denied access.
- Correct job/session succeeds; expired/revoked session fails.
- Replayed challenges and double invocations cannot double-consume a grant.
- Tampered ciphertext fails authentication.
- Transferring asset control does not grant historical customer-input access or rewrite an existing payout.
- Plaintext previously downloaded remains available to its recipient; the UI does not promise otherwise.

### Completion claim

Agents discovered, commissioned and purchased an evaluated capability under spending limits. The system protected offchain content from unauthorized gateway access and paid for verified execution. The provider and evaluator remain explicit trust assumptions.

That is a concrete agent marketplace. Its public-facing dashboard shows what the agents did; it is not the purchasing mechanism.
