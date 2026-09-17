# Robinhood Chain production wiring: blocks, channels, invariants, reuse

Written 15 September 2026. This is the wiring document. It does not restate the research; it takes the positions already argued in [BLUEPRINT.md](BLUEPRINT.md), [EXPERIMENT.md](EXPERIMENT.md), [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md), [ASSET_SCOPE_AND_CERTIFICATION.md](ASSET_SCOPE_AND_CERTIFICATION.md), [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md), [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md), [PROOF_GRAPH.md](PROOF_GRAPH.md) and [QUEUEING_THEORY.md](QUEUEING_THEORY.md), turns each into something a contract, a signer, an evaluator harness or an indexer can enforce, and names the existing code that already does most of it.

Facts about Robinhood Chain below were checked live against its public RPC and explorer today; the commands are in section 1 so they can be re-run. Everything else is a plan.

## 0. Findings first

1. **Robinhood Chain is a plain Arbitrum Nitro chain and is ready for this system as is.** Testnet chain ID 46630, Nitro `v3.12.0-rc.2`, Stylus enabled (version 3), bn254 precompiles present (so a Groth16 verifier deploys and runs), base fee 0.01 gwei, settles to Ethereum Sepolia, ERC-4337 EntryPoints v0.6/v0.7/v0.8 deployed, Blockscout explorer with a working API, an official faucet that also hands out test stock tokens. Section 1.
2. **No SP1 verifier exists on Robinhood Chain.** `sp1-contracts` ships deployments for 15 chains; 4663 and 46630 are not among them. We deploy `SP1VerifierGroth16` v6.1.0 ourselves. That is one immutable Solidity contract with no owner and no gateway, which is simpler and safer than the Sepolia gateway path (BLUEPRINT section 5 warned about gateway upgrade authority; an owned verifier is not a concern here). The same proof bytes can be cross-checked against the Arbitrum Sepolia gateway at `0x397A5f7f...` as an independent confirmation. Section 1.4.
3. **The clock is the Arbitrum Open House Singapore online buildathon: submissions close 4 October 2026 at 15:59.** Nineteen days from today. Prizes: 70k USDC overall, 15k promising products, 30k grants. At least one podium place is reserved for a Robinhood Chain project. Judging: smart contract quality, product-market fit, innovation, real problem solving. Deploying on any Arbitrum chain qualifies; only Robinhood Chain earns the reserved slot. Section 6.
4. **The apparatus already executes a real mainnet block inside SP1.** Block 18884864: 89,571,530 cycles, 108,529,239 PGU, 30 transactions, 160 s wall on a 4 vCPU runner. Proving on a 16 GB GitHub runner failed four times on memory; the fifth attempt (run 34944035840) has been alive for over four hours of its six-hour cap at the time of writing. The real proof is the critical path of the whole plan, and nothing else waits on it. Section 6, gate G0.
5. **Most of the offchain machinery already exists in Lattice Prime.** The restricted signer that AGENT_MARKETPLACE section 4 asks for (mandate, authority state, atomic budget reservation, projection-before-sign, hash-chained receipt store with secret scrubbing) is about 2,000 lines of tested JavaScript in `~/hedera2026/venue/agent/runtime/`. The relay-plus-independent-verifier pattern for an evidence log is another 2,000 lines in `venue/tools/hcs-*.mjs`. The Solidity credit/withdraw/nonReentrant pattern, epoch clock, domain-separated Merkle leaves, Foundry configuration, deployment evidence JSON and 55 test files are all reusable. Section 5.
6. **The idea is seven blocks and twelve channels.** Every channel carries one typed message, every message is bound by a hash or a signature, and every binding is an invariant with a named enforcement point and a named test. Sections 2 to 4.
7. **Three things are deliberately not on the critical path:** Stylus (available, unnecessary), ERC-4337 wallets (deployed, unnecessary for an operator-run restricted signer), and any private-data or token-transfer feature. Each is noted where it would attach later.

## 1. Robinhood Chain, verified

### 1.1 What the chain reports about itself

Probed 15 September 2026 from the public endpoints. Re-run with `curl` and `cast`; no key is needed.

| Fact | Testnet | Mainnet | How checked |
| --- | --- | --- | --- |
| `eth_chainId` | 46630 (`0xb626`) | 4663 (`0x1237`) | RPC |
| `web3_clientVersion` | `nitro/v3.12.0-rc.2` | `nitro/v3.11.4-rc.3` | RPC |
| `ArbSys.arbOSVersion()` at `0x64` | 116 | 116 | `eth_call` selector `0x051038f2`; Nitro returns 55 plus the ArbOS version |
| `ArbWasm.stylusVersion()` at `0x71` | 3 | not probed | `cast call ... "stylusVersion()(uint16)"` |
| `ArbWasm.inkPrice()` | 10000 | not probed | `cast call` |
| bn254 pairing precompile `0x08` | present, empty input returns 1 | present | `eth_call` |
| Block height | 119,880,346 | 63,609,114 | `eth_blockNumber` |
| Block gas limit | 2^50 | not probed | `cast block latest` |
| Base fee | 0.01 gwei | not probed | `cast block latest` |
| `ArbGasInfo.getPricesInWei()` | L1 estimate 57.7 gwei-equivalent, L2 base 0.01 gwei | not probed | `cast call 0x6C` |
| EntryPoint v0.7 `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | 16,035 bytes of code | documented | `eth_getCode` |
| EntryPoint v0.8 `0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108` | 21,738 bytes | documented | `eth_getCode` |
| EntryPoint v0.6 `0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789` | 23,689 bytes | documented | `eth_getCode` |
| Explorer API `explorer.testnet.chain.robinhood.com/api/v2/stats` | 200, average block time 91 s at current load | `robinhoodchain.blockscout.com` | `curl` |

Reproduction:

```bash
RPC=https://rpc.testnet.chain.robinhood.com
cast chain-id --rpc-url $RPC
cast call --rpc-url $RPC 0x0000000000000000000000000000000000000071 "stylusVersion()(uint16)"
cast call --rpc-url $RPC 0x0000000000000000000000000000000000000064 "arbOSVersion()(uint256)"
cast block --rpc-url $RPC latest --json | python3 -c "import sys,json;b=json.load(sys.stdin);print(int(b['baseFeePerGas'],16))"
```

### 1.2 What the documentation states

From `docs.robinhood.com/chain/` and its `connecting`, `transaction-finality` and `account-abstraction` pages, read today:

- Built on "Arbitrum Dedicated Blockchains"; ETH gas; "Ethereum blobs for data availability"; parent chain Ethereum (testnet settles to Sepolia).
- Sequencing: "first-come, first-served ... determined strictly by the arrival time at the sequencer". No priority-fee ordering.
- Finality: sub-second sequencer soft confirmation, "reversible only if the sequencer posts a batch with a different transaction order"; posted to Ethereum "within minutes"; Ethereum finality "approximately 13 minutes after posting"; canonical withdrawals face "a 7-day challenge period".
- RPC: `https://rpc.testnet.chain.robinhood.com` (public, rate limited) or `https://robinhood-testnet.g.alchemy.com/v2/{key}`; sequencer feed `wss://feed.testnet.chain.robinhood.com`. Mainnet equivalents under `mainnet.chain.robinhood.com` and `robinhood-mainnet.g.alchemy.com`.
- Faucet: `https://faucet.testnet.chain.robinhood.com` gives testETH plus five units each of test stock tokens. Sepolia ETH can also be bridged through `portal.arbitrum.io/bridge` with destination `robinhood-chain-testnet`.
- Account abstraction: Alchemy, ZeroDev, Privy and Dynamic are the named providers; spend policies and gas sponsorship are provider features.
- Tooling: "Hardhat, Foundry, ethers.js, viem, and Wagmi" unchanged; Solidity and Rust via Stylus.

### 1.3 What these facts change in the design

| Fact | Consequence |
| --- | --- |
| FCFS sequencing | Quote competition stays offchain (BLUEPRINT section 7 already says so). No worker can front-run a `submitProof` by paying more; whoever reaches the sequencer first lands, and I-S4 makes that irrelevant to payment. |
| Three finality clocks | Each channel names its confirmation policy (section 3.3). Testnet bounty and job settlement read at soft confirmation; the creation trigger waits for L1 posting so a creator run is never launched on a batch the sequencer could reorder. |
| No SP1 verifier | We own the verifier deployment (section 1.4). Each job snapshots the verifier address; there is no gateway routing by selector to reason about. |
| Base fee 0.01 gwei | A Groth16 verification plus settlement bookkeeping costs a few hundred thousand gas, so under 0.00001 ETH per settlement at this base fee. Gas is not a design constraint on this chain; record it anyway (I-V4). |
| 91 s average block time at current testnet load | Blocks are produced on demand; a single transaction gets its own block quickly, but "block number" is not a clock. Use timestamps for deadlines, as EpochClock already does. |
| ERC-4337 EntryPoints present | Optional later path for buyer-agent wallets with provider-enforced spend policies. The MVP uses the ported EOA restricted signer; the policy lives in our code either way (I-A1). |
| Stylus v3 | Available. Not used. Rust guest execution inside SP1 is not Stylus execution (BLUEPRINT section 9), and no contract here is compute-bound. |
| Faucet stock tokens | Irrelevant to proving; useful only as a labeled example of an asset the venue already hosts if a judge asks what else runs here. |

### 1.4 The verifier deployment

`sp1-contracts` deployments directory today: chains 1, 10, 56, 143, 999, 4217, 8453, 9745, 42161, 84532, 421614, 560048, 52085145, 11155111, 11155420. Not 4663, not 46630.

Decision: deploy `SP1VerifierGroth16` from `sp1-contracts` at the v6.1.0 tag (the circuit version SDK 6.8.0 targets, per `LemmaXperiment/apparatus/pins.json`) to Robinhood testnet with Foundry, verify source on the Blockscout explorer, and pin its address, code hash and `VERIFIER_HASH()` in `demand/spec.json` and in every `UsageEscrow` job. The contract has no owner, no upgrade path, and one entry point: `verifyProof(bytes32 programVKey, bytes calldata publicValues, bytes calldata proofBytes)`.

Cross-check: the same `(vkey, publicValues, proof)` triple is also submitted read-only to the Arbitrum Sepolia gateway `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B`, which routes to the identical `V6_1_0_SP1_VERIFIER_GROTH16` at `0xb69f2584CBcFf99a58C4e7002E8b89Af54a6f4e2`. Two chains agreeing on one proof is cheap evidence that our deployment is faithful. The Sepolia call is not a settlement and pays nobody.

Fallback if the Groth16 wrap cannot be produced (SETUP_PLAN revision 4): submit the compressed proof's public values through a mock verifier on Robinhood testnet and label the onchain step "mechanics only". This fallback can never be presented as a verified proof (I-X2).

## 2. The blocks

```text
                       ┌──────────────────────────────────────────────┐
                       │  B7  POLICY CONTROLLER / RESTRICTED SIGNER   │
                       │  mandate, budget reservation, method         │
                       │  allowlist, projection-before-sign, receipts │
                       └───┬──────────────┬──────────────┬────────────┘
                           │ C1, C8       │ C4           │ C10
   ┌──────────────┐        v              v              v          ┌──────────────┐
   │ B1 DEMAND    │   ┌────────────────────────────────────────┐    │ B5 WORKER /  │
   │ buyer or     │──>│ B4 ROBINHOOD CHAIN (46630)             │<───│ PROVER       │
   │ sponsor,     │   │  CreationBounty  ModuleRegistry        │    │ RSP + SP1,   │
   │ spec + terms │   │  UsageEscrow     SP1VerifierGroth16    │    │ lemma-prove  │
   └──────┬───────┘   └──┬──────────┬──────────────┬───────────┘    └──────▲───────┘
          │ C3           │ C2       │ C7           │ C11                   │ C9
          v              v          │              v                       │
   ┌──────────────┐   ┌──────────┐  │      ┌──────────────────┐            │
   │ B2 CREATOR   │──>│ (runner) │  │      │ B6 INDEXER +     │────────────┘
   │ AGENT in     │   └──────────┘  │      │ PROOF GRAPH      │  witness + job
   │ restricted   │       C5        │      │ LEDGER +         │
   │ workspace    │────────┐        │      │ EXPLORER         │
   └──────────────┘        v        │      └────────┬─────────┘
                    ┌──────────────┐│               │ C12 (redundancy bounty proposal)
                    │ B3 EVALUATOR ││               v
                    │ frozen image,│└──────> back to B1 as a new demand
                    │ own signer   │  C6
                    └──────────────┘
```

| Block | Owner | Runs where | Authority it holds | Authority it must not hold |
| --- | --- | --- | --- | --- |
| B1 Demand | buyer or sponsor | laptop | funds bounties and jobs; freezes spec, policy, holdout commitment | cannot veto a compliant acceptance after funding |
| B2 Creator agent | operator runs it; the model acts | restricted workspace (laptop or a runner) | edits its workspace; runs allowlisted build, test, profile tools; submits through B7 | cannot read holdout, edit spec or policy, change the payee, touch funding or evaluator keys |
| B3 Evaluator | separate identity | GitHub Actions workflow whose file hash is the policy hash; verdict signed on the laptop | rebuilds candidate from source, runs frozen checks, signs one verdict | its signing key never on the execution host; cannot relax criteria |
| B4 Chain | contracts | Robinhood testnet | escrow, state machines, proof verification, single settlement, credits | no admin can mark a proof valid; pause only blocks new work |
| B5 Worker | clean operator account | GitHub runner or any prover host | fetches witness, runs approved guest, submits proof through B7 | cannot change payees, cannot settle without a valid proof |
| B6 Indexer and ledger | operator | laptop or a small service | projects events, replays execute mode, computes labeled metrics | pays nobody; is never read by settlement |
| B7 Policy controller | operator | process next to each spending agent | holds the signing key; enforces mandate limits; writes receipts | never exposes the key to the model; never signs a transaction that fails projection |

## 3. The channels

A channel is one typed message from one block to another. Each row names what it carries, what binds it, how it travels, its confirmation policy on the chain clocks, the invariants that guard it, and the closest existing code.

### 3.1 Channel table

| Ch | From → To | Carries | Bound by | Transport | Invariants | Closest existing asset |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | B1 → B4 | `fundDemand(specHash, policyHash, holdoutCommitment, evaluatorSigner, creatorPayee, bounty, submitBy, evaluateBy)` | keccak of canonical `demand/spec.json`; ETH value | transaction via B7 | I-S9, I-S10, I-S11, I-E1, I-E2 | `demand/spec.json` schema (fields exist, values null); mandate `principalBudget` becomes `bountyCeiling` |
| C2 | B4 → B2 runner | `DemandFunded(demandId, specHash, ...)` event | event log; confirmation policy L1-posted | chain event, polled | I-V2, I-L1 | `venue/agent/runtime/worker.mjs` polling loop; `hcs-cursor.json` cursor pattern |
| C3 | runner → B2 | public spec, dev fixtures (blocks 18884864, 20600000, one more), registry snapshot, upstream at pin, tool allowlist, budget | `sourceSnapshotHash`, `registrySnapshotHash`, `toolPolicyHash` in the run log | files in a restricted workspace | I-A3, I-A5, I-A6 | `agent/runner/README.md` run-log fields; `apparatus-build.yml` produces the pinned binaries |
| C4 | B2 → B4 (through B7) | `submitCandidate(demandId, sourceCommit, artifactDigest)` | content address of the bundle | transaction via B7 | I-S10, I-A1, I-A2, I-A4 | `signer.mjs` + `transaction-projector.mjs` with a new ABI |
| C5 | B2 artifacts → B3 | immutable bundle: module, adapter, Lean sources, tests, build recipe, `candidate/manifest.json` | `artifactDigest` equals the onchain submission | content-addressed object (GitHub release asset or object storage) | I-E4, I-E5, I-E6 | `candidate/manifest.json` schema; `receipt-store.mjs` FORBIDDEN_KEYS scrub before publishing |
| C6 | B3 → B4 | EIP-712 `Verdict{chainId, contract, demandId, candidateDigest, policyHash, reportHash, guestKey, recipient, verdict, validUntil, nonce}` | evaluator signature; domain separator includes chainId 46630 and the contract | transaction by anyone carrying the signature | I-S9, I-E3, I-E7, I-E8, I-E9 | Lattice `oracle/sign-dealer-quote.mjs` (typed signing of a quote) as the template |
| C7 | B4 internal | on Pass: `ModuleRegistry.register(version, guestKey, evidenceRef, terms)` and `credit[creatorPayee] += bounty` in one transaction | same transaction | contract call | I-S1, I-S8, I-S11, I-S12 | `AxeBoard.sol` credit accounting |
| C8 | B1 buyer → B4 (through B7) | `fundJob(moduleVersion, guestKey, verifier, worker, contributor, workerFee, contributorFee, statementHash, proveBy)` | job ID = keccak(requester, nonce, statementHash); terms snapshotted | transaction via B7 | I-S5, I-S6, I-S13, I-S14, I-A2 | `signer.mjs` `reserveApprovedBuy` becomes `reserveJob` |
| C9 | B4 → B5 | `JobFunded` event; then worker fetches witness by block number from archive RPC and runs the registered guest | `witnessCommitment` recomputed inside the guest | chain event, then RPC and `lemma-prove --stdin-dir --out-dir --proof-mode groth16` | I-E8 (execute first, compare PGU), I-L5 | `apparatus-execute.yml`, `apparatus-prove.yml`, `apparatus/prover/` |
| C10 | B5 → B4 (through B7) | `submitProof(jobId, publicValues, proofBytes)` | verifier call with snapshotted `guestKey`; public values decoded and compared field by field to the job | transaction via B7, any relayer | I-S2, I-S3, I-S4, I-S5, I-S7, I-V1 | `SP1VerifierGroth16.verifyProof`; `UsageEscrow` to write |
| C11 | B4 → B6 | every event, keyed `(chainId, blockHash, txHash, logIndex)`; plus one execute-mode replay per settled job for the counterfactual matrix | idempotent key; `report.csv` PGU | event polling plus `apparatus-execute` runs | I-L1, I-L2, I-L3, I-L4 | `hcs-verify.mjs` (claims checked against receipts and state); `proof_graph_sim.py` metric functions; `report.csv` columns `prover_gas`, `verify_sp1_proof` |
| C12 | B6 → B1 | proposal only: `enablingExposure` ranked, bounty ceiling `min(exposure, recreationCostEstimate)`; explorer pages with labels | none; it is advice | JSON the buyer may turn into a C1 | I-L2 | `proof_graph_sim.py` T7 logic |

### 3.2 Message shapes that must be frozen before code

The research fixed the field lists (BLUEPRINT section 6, EXPERIMENT sections 2 and 6, EXPERIMENT section 9). What remains is canonical encoding. Decisions:

- **Offchain JSON (spec, policy, manifest, run log, verdict report):** canonical JSON as `policy.mjs` already implements (`canonicalJson`: sorted keys, no whitespace), hashed with keccak256 for anything that goes onchain and sha256 for anything that stays offchain. Never hash pretty-printed files.
- **Onchain structs:** `abi.encode` of fixed-width fields in the documented order; `keccak256` of that. Domain tag as the first field of every struct: `"lemma.demand.v1"`, `"lemma.job.v1"`, `"lemma.verdict.v1"`.
- **Guest public values** (the one encoding the guest and the contract must both implement): fixed order, fixed widths, no length prefixes:

```text
settlementChainId   uint64   46630
marketAddress       address  UsageEscrow
jobId               bytes32
sourceDomain        bytes32  keccak("ethereum-mainnet-block-execution.v1")
blockNumber         uint64
blockHash           bytes32
parentStateRoot     bytes32
computedStateRoot   bytes32
witnessCommitment   bytes32  computed in the guest, not echoed
success             bool
```

The guest wrapper in the reuse job commits exactly this (EXPERIMENT section 9). The evaluation harness runs the same wrapper so reuse overhead is measured, not hidden.

### 3.3 Confirmation policy per channel

| Clock | Meaning on Robinhood | Channels that read at this clock |
| --- | --- | --- |
| Soft (sequencer, sub-second) | reversible only by a sequencer reordering | C7 credits and C10 settlement shown in the UI as "sequenced"; B7 receipts record the soft receipt |
| L1 posted (minutes) | fixed unless Ethereum reorganizes | C2 creation trigger (never launch a paid agent run on a reorderable event); B6 ledger marks rows "posted" |
| Ethereum finality (about 13 min after posting) | irreversible | anything that would release a secret or a real-money payment; none in the MVP |

The UI shows all three states per transaction and never shows a success badge on a locally produced proof (BLUEPRINT section 10).

## 4. Invariants

Each invariant has an ID, a statement, its source in the research, the block or channel that enforces it, and the test that proves it. "Exists" means the pattern is in Lattice Prime or the apparatus and needs porting; "build" means new.

### 4.1 Settlement contracts (B4, channels C7, C8, C10)

| ID | Invariant | Source | Enforced by | Test | Status |
| --- | --- | --- | --- | --- | --- |
| I-S1 | `address(this).balance >= activeEscrow + activeBonds + sum(credit)` after every state change | BLUEPRINT 7 | `UsageEscrow`, `CreationBounty` | Foundry invariant test with a handler over fund/submit/expire/withdraw | exists (`AxeBoard.sol` credit map) + build handler |
| I-S2 | A job settles at most once; a second valid submission reverts | BLUEPRINT 7, 13 | state machine | `test_settleTwice_reverts` | build |
| I-S3 | Settlement requires the decoded public values to equal the stored job on every field of section 3.2 and `success == true`, and the verifier call to succeed with the snapshotted `guestKey` | BLUEPRINT 5, 6; EXPERIMENT 9 | `UsageEscrow.submitProof` | one test per field mutated (chain, market, jobId, domain, block, roots, witness, success) | build |
| I-S4 | The address that submits a proof never affects who is paid | BLUEPRINT 7 (mempool copying) | payees read from storage only | `test_relayerCannotRedirect` | build |
| I-S5 | Submission allowed while `block.timestamp <= proveBy`; refund allowed only when `block.timestamp > proveBy`; `proveBy` chosen from a measured `q99(S)` plus settlement margin, not a round number | BLUEPRINT 7; QUEUEING 10.1 | contract for the boundary; `queueing_sim.py find` for the value | `test_boundary_atDeadline_settles`, `test_boundary_afterDeadline_refunds` | build; sim exists |
| I-S6 | Module version, guest key, verifier address, worker, contributor, amounts and statement hash are immutable after funding | EXPERIMENT 9 | no setters | `test_termsImmutable` | build |
| I-S7 | No function can mark a proof valid without the verifier; pause blocks only new funding and leaves refunds and settlement of existing jobs reachable | BLUEPRINT 5 | absence of admin path; `whenNotPaused` only on `fundJob`/`fundDemand` | `test_pausePreservesRefund`, review of the ABI | build |
| I-S8 | `ModuleRegistry` entries are created only inside the bounty acceptance path | EXPERIMENT 9 | `onlyBounty` | `test_registerDirect_reverts` | build |
| I-S9 | Evaluator verdict is EIP-712 typed, domain-separated by chainId and contract, carries a nonce and `validUntil`; the same signature cannot be reused for another demand, contract or chain | EXPERIMENT 9; ASSET_SCOPE 6 | `CreationBounty.decide` | replay tests across demandId, contract address, chainId, expired `validUntil` | exists (Lattice typed quote signing) + build |
| I-S10 | `evaluateBy > submitBy`; one submission at or before `submitBy`; expiry after `submitBy` without submission, or after `evaluateBy` without decision, credits the sponsor | EXPERIMENT 9 | constructor and state machine | four timing tests | build |
| I-S11 | A Pass verdict registers and credits in one transaction; the sponsor has no veto after funding | EXPERIMENT 8 | atomic `decide` | `test_passRegistersAndCredits_atomically` | build |
| I-S12 | All payouts are pull withdrawals guarded against reentrancy | BLUEPRINT 7 | `credit` map + `nonReentrant withdraw()` | reentrancy test with a malicious payee | exists (`AxeBoard.withdraw`) |
| I-S13 | Payee schedule is flattened, deduplicated, at most eight entries, snapshotted at funding | BLUEPRINT 5 | `fundJob` validation | `test_ninePayees_reverts`, `test_duplicatePayee_reverts` | build |
| I-S14 | Verifier address and its `VERIFIER_HASH()` are snapshotted per job; the deployment is unowned | this document 1.4 | job struct | `test_verifierPinned` | build |

### 4.2 Evaluation (B3, channels C5, C6)

| ID | Invariant | Source | Enforced by | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| I-E1 | Spec hash, policy hash and evaluator identity are committed onchain at funding, before any creator work | EXPERIMENT 2, 4 | C1 | `DemandFunded` event predates the run log `startedAt` | build |
| I-E2 | Holdout selection rule and salt are committed before creation and revealed after the verdict; holdout witnesses are fetched inside the evaluator job and never copied to the creator | EXPERIMENT 4; TRIE_MODULE_PROTOCOL 8 | `holdoutCommitment` in C1; `select_blocks.py` | commitment preimage published with the report | exists (`select_blocks.py`) + build reveal |
| I-E3 | One holdout evaluation per demand; a retry needs a new sealed set and a new demand version | EXPERIMENT 7 | `CreationBounty` one-decision rule | I-S10 tests | build |
| I-E4 | Evaluator and creator have different keys and different execution environments; the evaluator signing key is never on the execution host | EXPERIMENT 3; SETUP_PLAN | workflow separation, laptop signing | `.env` layout, workflow file hashes | exists (design) |
| I-E5 | Lean check uses the pinned toolchain; `sorryAx` forbidden; axioms limited to `propext`, `Classical.choice`, `Quot.sound`; a reviewer confirms the theorem addresses the implemented optimization | EXPERIMENT 7; ASSET_SCOPE 5; `policy.json` | evaluator job runs `#print axioms` on the exported theorem | axiom report in the evidence bundle | build |
| I-E6 | The correctness oracle does not share the changed algorithm (independent Python trie implementation, committed fixtures) | TRIE_MODULE_PROTOCOL 7 | evaluator fixtures | fixture manifest with expected outcomes | build |
| I-E7 | Verdict is one of Pass, Fail, Inconclusive; insufficient compute yields Inconclusive, never invented timings | EXPERIMENT 7 | policy | report template | exists (`policy.json`) |
| I-E8 | PGU is the funded metric; it is deterministic, so two executions of the same variant on the same block must agree byte for byte, and a third-party replay must reproduce it | SETUP_PLAN rev 2; PROOF_MODULE_VALUE 13.1 | evaluator job runs each variant twice; ledger replay | `report.csv` pairs compared | exists (`apparatus-execute.yml`) + build comparison |
| I-E9 | The counterfactual is the best registered alternative (RSP `arena` backend), not the naive baseline; the smaller saving is the one reported | PROOF_MODULE_VALUE 3, 13.3; PROOF_GRAPH 13.1 | evaluator runs A, B, arena, B+arena | four-configuration matrix per holdout block | build |

### 4.3 Agents and the policy controller (B2, B5, B7, channels C3, C4, C8, C10)

| ID | Invariant | Source | Enforced by | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| I-A1 | The model never holds a signing key; B7 enforces contract and method allowlists, per-job and per-day caps, expiry, maximum concurrency, permitted counterparties and a separate bounty ceiling | AGENT_MARKETPLACE 4, 11 | `mandate.mjs` schema (`identity`, `ticket`, `limits`, `time`, `control`) | mandate tests | exists; adapt keys |
| I-A2 | Budget is reserved atomically before funding; an idempotency key binds buyer, intent and request digest; a duplicate key with different content fails | AGENT_MARKETPLACE 9, 11 | `policy.mjs` `reserve*` + `signer.mjs` action IDs | existing tests | exists; adapt |
| I-A3 | The creator cannot read holdout fixtures, edit `demand/` or `evaluation/policy.json`, or change `assignedCreatorPayee` | EXPERIMENT 3, 5 | filesystem layout of the restricted workspace; payee stored onchain at C1 | workspace manifest hash | build |
| I-A4 | Every human intervention is logged with kind and description; the run reports one assistance level | EXPERIMENT 5 | run log | `humanInterventionLogHash` in the manifest | exists (schema) |
| I-A5 | Third-party manifests, READMEs and error text are data; they cannot instruct B7 to spend, expose credentials or change policy | AGENT_MARKETPLACE 10 | B7 accepts only structured actions that pass projection | projection tests | exists (`transaction-projector.mjs`) |
| I-A6 | The agent returns one disposition in {reuse, compose, create, decline}; a hypothesis is hashed into the run log before implementation; renaming existing code is not creation | EXPERIMENT 5 | runner | `hypothesisHash`, `hypothesisCommittedAt` | build |
| I-A7 | Every signed transaction is projected from the mandate first and must match the projection byte for byte; a transaction that fails projection is never signed | Lattice design | `assertTransactionMatchesProjection` | existing tests | exists |
| I-A8 | Receipts are hash-chained and scrubbed of secrets (`privatekey`, `witness`, `salt`, `signedtransaction`, ...) before storage | Lattice design; AGENT_MARKETPLACE 6 | `receipt-store.mjs` FORBIDDEN_KEYS | existing tests | exists |

### 4.4 Indexer and ledger (B6, channels C11, C12)

| ID | Invariant | Source | Enforced by | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| I-L1 | Projection is idempotent by `(chainId, blockHash, txHash, logIndex)`, rolls back on reorg, and can be rebuilt from chain state alone | BLUEPRINT 9 | indexer | rebuild-from-zero equals incremental | exists (`hcs-index`/`hcs-verify` pattern) + build |
| I-L2 | Nothing pays out on any ledger metric; settlement reads only the snapshotted schedule | PROOF_GRAPH 14; PROOF_MODULE_VALUE 14 | contracts have no read path into the ledger | ABI review; explorer footer text | design |
| I-L3 | Every published metric carries its label: receipts = contractual, reach = exposure, attributed saving = measured or modeled, enabling exposure = at risk, independence = disclosure | PROOF_GRAPH 12 | explorer | rendered labels | build |
| I-L4 | Sponsored jobs are labeled sponsored; payer independence (effective payers, top-payer share) is published with every value sentence | PROOF_MODULE_VALUE 12; PROOF_GRAPH 8.2 | ledger row `payer` | value sentence template | build |
| I-L5 | Wall-clock on shared runners is never a gate; runner queue time is reported separately from proving time | SETUP_PLAN rev 4; QUEUEING 10.2 | ledger schema | `observedProvingSeconds` nullable, `queueSeconds` separate | build |
| I-L6 | Nodes, edges and the counterfactual matrix are recorded from the first settled job; metrics are computed only when at least two market modules exist | PROOF_GRAPH 12 | indexer | schema present, metrics gated | build |

### 4.5 Labels and claims (all blocks)

| ID | Invariant | Source |
| --- | --- | --- |
| I-X1 | Testnet payments are labeled "payment mechanics demonstrated"; sponsored demand is never called customer validation | EXPERIMENT 8, 12 |
| I-X2 | A prerecorded proving stage is labeled a recording; no local proof shows a success badge; a mock-verifier fallback is labeled "mechanics only" | BLUEPRINT 10, 13; SETUP_PLAN rev 4 |
| I-X3 | The Lean theorem is model-level; the model-to-Rust gap is written in the evidence panel; "formally verified prover" is never claimed | EXPERIMENT 7; TRIE_MODULE_PROTOCOL 6 |
| I-X4 | Proving cost is PGU at a quoted rate; latency is modeled from PGU or measured on pinned hardware, and the label says which | PROOF_MODULE_VALUE 2 |
| I-X5 | One creation and one reuse demonstrate feasibility, not a market | EXPERIMENT 1, 15 |

### 4.6 Venue-specific (Robinhood Chain)

| ID | Invariant | Enforced by | Test |
| --- | --- | --- | --- |
| I-V1 | Public values carry `settlementChainId = 46630` and the `UsageEscrow` address; a proof produced for a Sepolia deployment cannot settle on Robinhood and vice versa | guest wrapper + I-S3 | `test_wrongChainId_reverts` |
| I-V2 | C2 waits for L1 posting before launching a creator run; C7 and C10 may act on soft confirmation on testnet; the UI names the clock for each receipt | runner confirmation policy; explorer | runner config; rendered state |
| I-V3 | Quote competition and job assignment are offchain and signed; nothing in the design relies on transaction ordering or priority fees | BLUEPRINT 7; FCFS sequencing | design review |
| I-V4 | Gas used by `verifyProof` and by settlement is recorded per job in the ledger at the observed base fee | indexer | ledger row `settlementGas` |
| I-V5 | Deployment evidence (`deployments/46630-*.json`) records deployer, addresses, code hashes, verifier hash, source verification IDs and the block of deployment, in the Lattice Prime format | deploy script | file present and hashed in the report |

## 5. Existing assets to reuse

Ranked by how much build time each removes. Paths are absolute so nothing is guessed.

### 5.1 From `LemmaXperiment/` (this folder; GitHub `4waan/LemmaXperiment`)

| Asset | Gives | Block / channel | Adaptation |
| --- | --- | --- | --- |
| `apparatus/pins.json` | every version we depend on, plus the Sepolia verifier addresses | all | add `robinhood` section: chainId 46630, RPC, our verifier address and hash, explorer |
| `.github/workflows/apparatus-build.yml` | pinned RSP + `lemma-prove` binaries as a 90-day artifact | B5, B3 | none |
| `.github/workflows/apparatus-execute.yml` | one block in execute mode: cycles, PGU, `report.csv`, stdin dump, in minutes | B3 (holdout), B6 (counterfactual replays), B2 (dev iteration) | add `--state-backend` matrix for the arena configuration (I-E9) |
| `.github/workflows/apparatus-prove.yml` | CPU proof of a small block with memory-lean settings, swap, memory sampler | B5 | on success, add the Groth16 wrap step and the two verifier calls |
| `apparatus/prover/` (`lemma-prove`) | `--stdin-dir`, `--out-dir`, `--proof-mode groth16` on the unmodified pinned host | B5, C9 | none for baseline; the reuse job adds the public-values wrapper guest |
| `apparatus/select_blocks.py` | salted holdout selection | I-E2 | commit rule + salt hash at C1 |
| `apparatus/runs/execute-18884864-.../report.csv` | the first real numbers (89.6 M cycles, 108.5 M PGU) | B6 seed row | none |
| `apparatus/FAILURES.md` | the discipline: every failure counted, cause, fix | results | keep it going |
| `demand/spec.json`, `evaluation/policy.json`, `candidate/manifest.json`, `agent/runner/README.md` | the message schemas for C1, C5, C6, run log | C1, C3, C5, C6 | fill values, add canonical hashing script |
| `contracts/README.md` | the three-contract state machines and the verdict binding fields | B4 | write the Solidity |

### 5.2 From Lattice Prime (`~/hedera2026/venue/`)

| Asset | Lines | Gives | Block / channel | Adaptation |
| --- | --- | --- | --- | --- |
| `agent/runtime/mandate.mjs` | 292 | typed mandate: identity (chainId, execution account, deployment hash, policy hash, nonce), ticket (engine, permitted methods), limits (budgets, max pending, evaluation slots), time, control (pause, revocation generation) | B7, I-A1 | rename `engine`/`token` to `market`/`registry`; limits become `bountyCeiling`, `jobBudget`, `dailyCap`, `maxConcurrentJobs` |
| `agent/runtime/policy.mjs` | 196 | canonical JSON, mandate ID, authority state with cumulative reservations | B7, I-A2 | `reserveApprovedBuy` becomes `reserveJob`/`reserveBounty` |
| `agent/runtime/signer.mjs` | 830 | key isolation, action IDs, outstanding-stage tracking, legacy state migration, signing only after projection | B7, I-A1, I-A7 | swap the Hedera protocol adapter for a plain ethers `JsonRpcProvider` on the Robinhood RPC; EIP-1559 fields unchanged (Nitro accepts them) |
| `agent/runtime/transaction-projector.mjs` | 225 | ABI-level projection of every permitted call, checked against the mandate before signing | B7, I-A5, I-A7 | new ABI: `fundDemand`, `submitCandidate`, `fundJob`, `submitProof`, `withdraw`, `expireJob` |
| `agent/runtime/receipt-store.mjs` | 492 | durable hash-chained receipts, atomic file writes, FORBIDDEN_KEYS scrub | B7, run log, I-A8, I-A4 | none; add `humanIntervention` receipt kind |
| `agent/runtime/worker.mjs`, `supervisor.mjs`, `signer-process.mjs` | 138 + 532 + more | polling loop, local control HTTP surface with pairing tokens, signer in a separate process | C2 runner, B7 | trim the static-file table |
| `tools/hcs-relay.mjs`, `tools/hcs-verify.mjs`, `tools/hcs.mjs` | 686 + 489 + 868 | an ordered evidence log whose every claim is re-checked against receipts, budgets and contract state; a cursor file; an index bundle the UI boots from | B6, I-L1 | Robinhood has no HCS; replace the topic with chain events plus a hash-chained `ledger.jsonl`; keep the verifier structure (claims vs receipts vs state) |
| `oracle/sign-dealer-quote.mjs` | small | typed signing of an offchain quote | C6 verdict signing, later worker quotes | new struct |
| `src/market/AxeBoard.sol` (credit map, `nonReentrant withdraw`, `goodUntil` expiry) | | I-S1, I-S12, I-S5 patterns | B4 | copy the pattern, not the contract |
| `src/policy/EpochClock.sol` | | timestamp-based windows | I-S5 | optional |
| `src/merkle/MerkleSet.sol` | | domain-separated leaf and node hashing | input commitments, membership workload from BLUEPRINT 3 if revived | optional |
| `foundry.toml` (solc 0.8.24, size measured every build, fuzz 512, fs permissions for fixtures) | | | B4 | drop Hedera RPC alias, add `robinhood_testnet = "${RPC_46630}"` |
| `test/*.t.sol` (55 files) | | naming and fixture conventions, invariant handlers | B4 | conventions only |
| `deployments/296-venue.json` (keys: network, chainId, deployedAt, deployer, actors, evidence, sourcify, superseded) | | deployment evidence format | I-V5 | `deployments/46630-lemma.json` |
| `script/*.s.sol` | | Foundry deploy scripts with evidence output | B4 | new scripts |
| `agent/formal/check_release.py` (z3) | | bounded two-execution equivalence checks | I-E8 replay agreement, optional formal check that guest and contract decode public values identically | new relation |
| `DEMO-SCRIPT.md`, `JUDGING-CRITERIA.md`, `SUCCESS.md` | | the shape of a submission that already scored | section 6, G6 | rewrite content |
| `.github` workflows and Vercel config | | static app deployment | explorer | optional |

### 5.3 From this folder

| Asset | Gives | Use |
| --- | --- | --- |
| `proof_graph_sim.py` | AND/OR minimum-cost `C(G)`, cascade `MC`, Shapley over nodes and over payees, recreation cap, the three attacks | lift the functions into the ledger's metric module; the synthetic `MODULES` table becomes the real registry |
| `queueing_sim.py` (`run`, `find`, `grid`) | `P(T <= D)` for given `S` distribution, pool size and policy | `find` sets `proveBy` for the reuse job from the three measured proofs (I-S5); `grid` produces the worker-count table for the report |

### 5.4 Upstream, not ours

| Asset | Use | Check before relying on it |
| --- | --- | --- |
| `succinctlabs/sp1-contracts` v6.1.0 `SP1VerifierGroth16.sol` | our verifier deployment | `VERIFIER_HASH()` matches the SDK 6.8.0 circuit; gnark wrapper image `sp1-gnark:v6.1.0` is amd64 only (fine on GitHub runners) |
| RSP `arena` feature | the registered existing capability; the best-alternative counterfactual (I-E9); the reuse-control entry in the registry snapshot | it is labeled unaudited upstream; say so |
| `rsp-tests` cached blocks 18884864, 20600000 | development fixtures | already pinned |
| OpenZeppelin `ReentrancyGuard`, `EIP712`, `ECDSA` | I-S9, I-S12 | pin the version in `foundry.lock` |
| Alchemy or ZeroDev AA on Robinhood | later: buyer-agent wallets with provider-enforced spend policies | not needed for the MVP; the policy lives in B7 regardless |
| Blockscout API v2 on the testnet explorer | source verification, a second event source for I-L1 rebuild checks | rate limits |

## 6. The plan: apparatus to working prod in nineteen days

Today: Monday 15 September 2026. Submission closes Sunday 4 October, 15:59. Every gate below has an exit condition taken from the research and a fallback that is honest rather than simulated.

### Critical path

The only slow thing is a real CPU proof (hours per compressed proof, plus a Groth16 wrap). Three are needed: baseline, candidate at evaluation, reuse job. Everything else runs on execute mode in minutes. So: keep a prove job running at all times from G0 onward, and never let the rest of the build wait on it.

### G0. First real proof (in flight)

Run 34944035840 started 07:53 UTC today with 24 GB swap, 2^19 shards, one worker per stage. Six-hour cap at 13:53 UTC.

- **Success:** artifact contains the compressed proof and vkey. Next: Groth16 wrap on an amd64 runner with `sp1-gnark:v6.1.0` (about 14 GB; may fit), then `cast call verifyProof` against the Sepolia gateway. This closes apparatus step 1 for Sepolia; G1 repeats the call against our Robinhood deployment.
- **Failure on memory again:** the next lever (FAILURES.md) is a custom worker builder in `lemma-prove` replacing SP1's fixed `ProverSemaphore::new(4)`. If that also fails, switch the baseline block to 20600066 (0.96 M gas, 27 transactions) for all three real proofs. Record the change in `pins.json` and the report; the PGU metric is unaffected.
- **Hard rule:** no simulated proof. If no real proof exists by G5, the outcome is Inconclusive and the onchain step is labeled mechanics only (I-X2).

### G1. Venue up on Robinhood testnet (days 1 to 3, 15 to 17 September)

1. Four wallets from `cast wallet new` (sponsor, creator payee, evaluator signer, worker); fund from `faucet.testnet.chain.robinhood.com`; record addresses in `.env` per `.env.example`.
2. Deploy `SP1VerifierGroth16` v6.1.0; verify source on `explorer.testnet.chain.robinhood.com`; record `VERIFIER_HASH()`.
3. Write `CreationBounty`, `ModuleRegistry`, `UsageEscrow` (one deployment acceptable). Port the credit/withdraw pattern. Foundry tests for I-S1 to I-S14 and I-V1, including the invariant handler for I-S1.
4. Deploy; write `deployments/46630-lemma.json` in the Lattice evidence format (I-V5).
5. Fill `pins.json` with the Robinhood section.

**Exit:** all contract tests green; a hand-built `(vkey, publicValues, proof)` from a tiny SP1 program (not RSP) settles a test job on Robinhood testnet and the same triple verifies read-only on the Sepolia gateway. A tiny program is enough here because G1 tests the contract path, not the block-proving path.

### G2. Freeze the demand (days 3 to 6, 17 to 20 September)

1. Fill `demand/spec.json`: objective as written, pinned commits, `allowedSourcePaths` (the witness-processing interfaces found in the survey), fixtures, budgets, deadlines (`submitBy`, `evaluateBy` in Unix time), bounty amount in testnet ETH.
2. Registry snapshot with two entries: the RSP `arena` backend (existing capability, unaudited) and a seeded control entry for the reuse control.
3. `select_blocks.py` with a fresh salt; commit `keccak(rule || salt)` as `holdoutCommitment`; store the salt on the laptop only.
4. Evaluator workflow file written and its hash placed in `policy.json` as `evaluatorImageHash`; `policyHash` = keccak of canonical `policy.json`.
5. `fundDemand` on Robinhood testnet through B7 (C1). Wait for L1 posting (I-V2).

**Exit:** `DemandFunded` event with `specHash`, `policyHash`, `holdoutCommitment` visible on the explorer; the creator run log records `startedAt` after the posting block.

### G3. Creator run (days 4 to 9, 18 to 23 September, overlapping G2)

1. Port B7 from Lattice Prime: mandate, policy, signer, projector, receipt store, with the new ABI (section 5.2). Mandate tests pass.
2. Runner: watch C2, materialize the restricted workspace (C3), start the creator with the public spec and tool allowlist, forward the final submission through B7 (C4).
3. Creator agent: Interpret, Search (disposition), Hypothesis (hashed), Build (three revisions maximum, each with `apparatus-execute` runs on the development blocks and the arena configuration), Lean theorem with the pinned toolchain, Submit.
4. Run the two controls as disposition-only runs (reuse control, decline control).

**Exit:** `CandidateSubmitted` at or before `submitBy`, or a recorded decline with an investigation report. Run log complete and hashed. Assistance level stated.

### G4. Evaluation (days 9 to 14, 23 to 28 September)

1. Evaluator workflow: fresh checkout at `sourceCommit`, rebuild, derive the guest key, license and composition checks.
2. Correctness: independent Python trie fixtures (I-E6), adversarial cases from `policy.json`, A/B/C regression on development blocks.
3. Formal: Lean build with the pinned toolchain, `#print axioms` report, reviewer note (I-E5).
4. Performance: reveal nothing yet; the workflow fetches the ten holdout blocks by the committed rule into its own cache; runs upstream, candidate, arena, candidate+arena, each twice per block (80 executions, minutes each); paired bootstrap on block medians; per-block regression cap.
5. One real proof of the candidate guest on a holdout block under 5 M gas (starts as soon as the candidate is frozen; runs in parallel with the executions).
6. Verdict signed on the laptop (C6), submitted; on Pass, C7 registers and credits atomically. Reveal the holdout salt.

**Exit:** report hash onchain; `ModuleRegistered` event; creator payee `credit > 0`; `results/report.md` gates table filled for product feasibility and technical value.

### G5. Reuse and ledger (days 12 to 17, 26 September to 1 October)

1. Buyer funds a job (C8) on block 20600928 (`LemmaXperiment/reuse/input.json`; 20600066 is a development block, so it is not eligible) with `proveBy` from `queueing_sim.py find` using the three measured proof durations plus margin (I-S5).
2. Clean worker account installs the immutable release by its instructions, runs execute (PGU recorded), proves, wraps, submits (C10) through its own B7 instance. Settlement credits worker and contributor.
3. Indexer projects every event (C11), replays execute mode for the counterfactual matrix, writes ledger rows in the PROOF_MODULE_VALUE section 11 shape, computes nothing beyond receipts and reach until a second module exists (I-L6).
4. Explorer: static pages from `ledger.jsonl` with the five labels and the sentence "no payout is derived from this page" (I-L3).

**Exit:** `JobSettled` on Robinhood testnet; both credits withdrawable; value sentence rendered with the sponsored label (I-L4); economic feasibility row filled with measured PGU and modeled latency.

### G6. Demo, report, submission (days 17 to 19, 1 to 4 October)

1. `results/report.md` complete: outcome, gates, blockers, interventions, controls, cost accounting.
2. Demo script in the Lattice `DEMO-SCRIPT.md` shape: fund, search and hypothesis, evaluation evidence, acceptance transaction, reuse settlement, one control. Long proving stages as labeled recordings (I-X2).
3. Submission on `arbitrum-singapore.hackquest.io` before 15:59 on 4 October, deployed on Robinhood Chain testnet, with the explorer links, deployment evidence, and the invariant table of this document as the smart-contract-quality exhibit.

### What to cut, in order, if behind

1. Explorer becomes a single static page from `ledger.jsonl`.
2. Lean theorem narrows to the smallest refinement obligation (a cache hit returns the same authenticated node the uncached path returns) with the rest listed as gaps (I-X3).
3. The reuse-job real proof moves to the smallest block available; the ledger row is still real.
4. Controls become one control, the decline.
5. The candidate real proof at G4 is dropped and the verdict says so; PGU evidence stands on execute mode.

Never cut: the sealed holdout, the separate evaluator key, the pull-payment and single-settlement tests, the labels.

## 7. Positions taken in this document

- Venue: Robinhood Chain testnet (46630) for every funded transaction. Arbitrum Sepolia is used only as a read-only cross-check of proof bytes and as the fallback venue if a Robinhood-specific blocker appears; both qualify for the buildathon, only Robinhood earns the reserved place.
- Verifier: our own unowned `SP1VerifierGroth16` v6.1.0 deployment, pinned per job by address and verifier hash. No gateway.
- Signing: the ported Lattice Prime restricted signer on plain EOAs. ERC-4337 is deployed on the chain and is a later option, not a dependency.
- Contracts: Solidity only. Stylus is available and unused.
- Funded metric: PGU from execute mode; three real proofs total; wall clock on shared runners is context, never a gate.
- Ledger: recorded from job one, metrics gated on a second module, nothing paid from it.
- Every claim in the demo carries the label its source document assigned to it.

## 8. What needs the operator before G1 can start

- Alchemy key for `robinhood-testnet` (or accept the public RPC's rate limits) and confirmation that the existing `RPC_1` mainnet archive key stays the only runner secret.
- Faucet claims for the four wallets.
- A decision on the creator model and its token budget for `demand/spec.json`.
- Confirmation that the public GitHub repository remains the evaluator host (workflow hash as policy hash), or a second machine if one appears.
- The bounty and usage fee amounts in testnet ETH, so `fundDemand` can be sent.

## 9. Post-quantum verification: the trade

Added 15 September 2026 after review. Groth16 in Lattice Prime was a forced choice: no pairing-friendly curve is post-quantum. The same is true here, so the question is where a hash-based proof can sit in this system today and what it costs.

### 9.1 What in the SP1 stack is hash-based

- **Core and compressed proofs:** STARKs over KoalaBear (p = 2^31 - 2^24 + 1) with Poseidon2 hashing, no trusted setup, no pairing. Soundness rests on hash and field assumptions only. This is the post-quantum-sound object.
- **Groth16 and PLONK proofs:** the compressed STARK re-proved inside a BN254 circuit. Groth16 has a circuit-specific trusted setup; PLONK uses the Aztec Ignition universal setup. Both are pairing-based, neither is post-quantum. They exist only to make onchain verification cost about 270k to 300k gas on 260 to 868 bytes.

Compressed proof size is not stated in the Succinct documentation; measure it from the artifact of the first successful prove run and record it in `pins.json`.

### 9.2 Options for verifying on Robinhood Chain

| Option | PQ-sound onchain | Exists today | Cost and blockers | Fits 4 October |
| --- | --- | --- | --- | --- |
| A. Groth16 wrap, our `SP1VerifierGroth16` | no | yes | 260 B, ~270k gas; trusted setup | yes |
| B. PLONK wrap, `SP1VerifierPlonk` | no | yes | 868 B, ~300k gas, about 90 s longer to generate; universal setup | yes |
| C. Solidity verifier for the compressed STARK | yes | no | proof in the megabyte range as calldata; Poseidon2 over KoalaBear and the Hypercube polynomial commitment in the EVM; tens of millions of gas and months of work; L2 gas is cheap here but the verifier does not exist | no |
| D. Stylus (Rust to WASM) verifier for the compressed STARK | yes | no | SP1's compressed verifier is not packaged for `no_std`/wasm32; Stylus caps a program at 24 KB compressed WASM; calldata size unchanged | no; a research spike after the buildathon |
| E. External hash-based verification (for example zkVerify) with an attestation relayed to Robinhood | verification is PQ elsewhere; on Robinhood you trust a relayer's root | not for Robinhood Chain as far as checked | introduces a party that can mark a proof valid, which I-S7 forbids | no |
| F. Hybrid: settle on A, commit the compressed STARK digest in the same settlement, publish the STARK bytes as evidence | the settlement is classical; the archived evidence is PQ-sound and re-verifiable | yes, all pieces exist | one extra `bytes32` per job plus object storage for the proof bytes | yes |

### 9.3 Decision: F now, D as the first commissioned demand

Settlement authorization on this chain is classical regardless of proof system: every transaction is ECDSA over secp256k1, the evaluator verdict is an ECDSA EIP-712 signature, and the rollup's own fraud proofs and Ethereum's signatures are classical. A payment authorization expires the moment it is spent, so a quantum adversary in the future gains nothing from it. The execution proof is different: it is the long-lived evidence that a block was executed correctly and that a module was adopted, and it must still be believable when pairings are not. So the post-quantum property is required on the artifact, not on the payment.

Concretely:

1. The worker produces the compressed STARK first, then the Groth16 wrap. Both are outputs of `lemma-prove --out-dir`.
2. `submitProof` takes an additional `bytes32 compressedProofDigest` (keccak256 of the canonical compressed proof bytes). The Groth16 settlement therefore commits to the hash-based proof it was derived from.
3. The compressed proof bytes are published to the evidence store under that digest. The ledger row records `compressedProofDigest`, `compressedProofBytes` (size) and `pqEvidence: available | missing`.
4. Any third party can re-verify the compressed proof offchain today with the SP1 SDK at the pinned version against the same guest key, and can re-verify it onchain later when a hash-based verifier for this proof system exists on the chain. Historical jobs then become re-checkable without re-proving.
5. The first `C12` proposal the ledger emits is a commissioned demand for option D: a Stylus verifier for SP1 compressed proofs on Arbitrum chains. It is a real capability gap, it is exactly the shape of demand this marketplace is built to fund, and it is post-quantum infrastructure for Ethereum proving, which is the EIP-8025 trajectory the research follows.

### 9.4 Invariants added

| ID | Invariant | Enforced by | Test |
| --- | --- | --- | --- |
| I-Q1 | Every settled job carries `compressedProofDigest`; settlement reverts if it is zero | `UsageEscrow.submitProof` | `test_zeroCompressedDigest_reverts` |
| I-Q2 | The claim "post-quantum-sound execution proof" attaches only to a compressed STARK whose bytes are published under their digest and have been re-verified by an independent `verify_compressed` replay; the Groth16 wrap is labeled "classical settlement wrapper" everywhere it appears | ledger, explorer, report | replay log present; label rendered |
| I-Q3 | No claim of post-quantum payment authorization or post-quantum chain security is made; the demo states that signatures on this chain are ECDSA | report, demo script | text review |
| I-Q4 | The compressed proof digest is computed over canonical serialized bytes at the pinned SP1 version; the serialization is recorded in `pins.json` so the digest is reproducible | worker, evaluator | evaluator recomputes the digest from the published bytes |

### 9.5 What this changes in the plan

- G1: `submitProof` signature gains the digest; one more test.
- G0 and G4: keep the compressed proof artifact, not only the Groth16 wrap; record its size.
- G5: publish the reuse job's compressed proof and run one independent `verify_compressed` replay on a different runner; that replay is the evidence for I-Q2.
- G6: the demo says, in one sentence, which object is post-quantum-sound and which is not.

Nothing else moves. If option C or D later exists on Robinhood Chain, `UsageEscrow` v2 verifies the compressed proof directly, and every v1 job is re-verifiable from its recorded digest.
