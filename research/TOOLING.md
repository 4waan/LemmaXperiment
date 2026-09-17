# Tooling: libraries, MCP servers and services that remove build work

Written 15 September 2026 against [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md) (blocks B1 to B7, channels C1 to C12, gates G0 to G6) and [EXPERIMENT.md](EXPERIMENT.md). Every version number and chain fact below was checked today with the command shown or with the GitHub, npm and PyPI APIs. Recommendations are marked as such.

Update, September 16: [REUSE_PLAN.md](REUSE_PLAN.md) prioritizes integration against the current apparatus, records the baseline proof success, qualifies network pricing, and checks EAS/Fangorn reuse. Read that supplement before acting on the earlier blockers or install list below.

## 0. Findings that change the plan

1. **This laptop cannot run any heavy stage.** `uname -m` is arm64, 8 GB RAM, 8 cores. The Groth16 wrapper image `ghcr.io/succinctlabs/sp1-gnark:v6.1.0` is linux/amd64 only (checked with `docker manifest inspect`) and needs about 14 GB. Block proving, wrapping and the evaluator's 80 executions all run on GitHub runners or rented hardware. Keep the laptop for signing, contracts, the runner and the ledger.
2. **The real proof is still the critical path, and two cheap outs exist.** Run 34944035840 was at 5h33m of its 6h cap when checked. Options that cost under a few dollars:
   - **Succinct Prover Network.** Pricing per the quickstart: 0.2 PROVE base fee plus up to 2.0 PROVE per bPGU (billion PGU). Block 18884864 is 108.5 M PGU, so about 0.11 bPGU, roughly 0.42 PROVE per proof. Requires PROVE on Ethereum mainnet (token `0x6BEF15D938d4E72056AC92Ea4bDD0D76B1C4ad29`) deposited through the Succinct explorer account page, and `NETWORK_PRIVATE_KEY` for the requester key. `pins.json` already lists `network` as the fallback.
   - **Rented GPU.** SP1 CUDA no longer needs Docker or nvidia-container-toolkit: Linux x86_64, CUDA 12 runtime, a GPU with compute capability 8.0 or higher and at least 24 GB VRAM (A10G, L4, RTX 4090, A100), 4 cores and 16 GB host RAM. `SP1_PROVER=cuda` or `ProverClient::builder().cuda()`. Spot prices for these cards are typically well under one dollar per hour.
   Either turns a six-hour CPU job into minutes and makes the three real proofs (baseline, candidate, reuse) routine instead of a gamble.
3. **I-V2 (wait for L1 posting) is one `eth_call`.** `NodeInterface` at `0xC8` answers on Robinhood testnet: `getL1Confirmations(bytes32 blockHash)` returned 0 for the latest block and 281 for a one-hour-old block; `findBatchContainingBlock(uint64)` returned batch 46484 for the same block and reverts for unposted blocks. Works on the public RPC and on PublicNode. No `@arbitrum/sdk` needed.
4. **A second public RPC exists.** PublicNode serves `https://robinhood-sepolia-rpc.publicnode.com` and `wss://robinhood-sepolia-rpc.publicnode.com` (chain id 46630 confirmed). The WebSocket endpoint is useful for the indexer. Chainlist also records the official RPC as `https://rpc.testnet.chain.robinhood.com/rpc`; the bare host works too.
5. **viem already knows the chain.** `viem/chains` ships `robinhoodTestnet` and `robinhood`. Chainscout knows 46630 with the self-hosted explorer, so the Blockscout MCP server resolves the chain by id.
6. **Node 16 is installed and is too old for everything below.** Claude Agent SDK needs Node 18 or later, `@anthropic-ai/sandbox-runtime` needs 20.11 or later, Ponder needs 22. `nvm` is present: `nvm install 22`. Bun 1.3.14 is present as a second runtime. System Python is 3.9.6; `py-trie` 4.0.0 needs 3.10 or later, so install `uv` and let it manage Python 3.12.
7. **G1's hand-built triple already exists as a template.** `succinctlabs/sp1-project-template` contains `script/src/bin/evm.rs` (writes a Groth16 fixture: vkey, public values, proof bytes), `contracts/src/fixtures/groth16-fixture.json`, and `contracts/test/Fibonacci.t.sol` verifying through `sp1-contracts`. Swap the program for the public-values wrapper of section 3.2 and G1's exit test is mostly copy work.
8. **The independent trie oracle (I-E6) exists in pure Python.** `ethereum/execution-specs` has `src/ethereum/merkle_patricia_trie.py` and `state_mpt.py` (fork independent). `py-trie` 4.0.0 (ApeWorX, released 22 August 2026) is the second option. Neither shares code with `reth-trie`.
9. **No Lean 4 MPT or RLP formalization exists to reuse.** `NethermindEth/EVMYulLean` delegates the trie to Python files and only has `EvmYul/SpongeHash/Keccak256.lean` in Lean (toolchain v4.22.0). The theorem stays model-level as EXPERIMENT section 7 already assumes.
10. **`leanchecker` ships inside the installed toolchain.** `~/.elan/toolchains/leanprover--lean4---v4.34.0/bin/leanchecker` exists, so the independent kernel re-check the policy wants costs nothing extra. The standalone `lean4checker` repository's newest tag is v4.29.0-rc8; use the bundled binary instead.

## 1. Tooling per block

### B4 Contracts (CreationBounty, ModuleRegistry, UsageEscrow, verifier)

| Need | Use | Version checked | What it removes |
| --- | --- | --- | --- |
| Toolchain | Foundry (installed) | 1.5.1 | nothing to install |
| Verifier | `succinctlabs/sp1-contracts` tag `v6.1.0`: `SP1VerifierGroth16.sol`, `Groth16Verifier.sol`, `ISP1Verifier.sol` | tags: v6.1.1, v6.1.0, v6.0.0, v5.0.0 | writing or auditing a Groth16 verifier |
| Reentrancy, typed data, signatures, nonces, pause | OpenZeppelin Contracts `ReentrancyGuard`, `EIP712`, `ECDSA`, `SignatureChecker` (ERC-1271 aware), `Nonces`, `Pausable` | v5.7.0 | I-S9, I-S12, I-S7 primitives |
| Credit map, `nonReentrant withdraw`, `goodUntil` | Lattice Prime `src/market/AxeBoard.sol`, `src/policy/EpochClock.sol` | in `~/hedera2026/venue` | I-S1, I-S5, I-S12 patterns |
| Invariant test for I-S1 | `forge test` invariant mode with a handler | built in | no framework |
| Symbolic check of deadline boundaries (I-S5, I-S10) | `halmos` | v0.3.3 | optional, one afternoon |
| Static analysis for the "smart contract quality" judging axis | `slither`, `aderyn`, `forge lint`, `forge coverage` | slither 0.11.6, aderyn 0.6.8 | a report to attach to the submission |
| Source verification on the explorer | `forge verify-contract --chain 46630 --verifier blockscout --verifier-url https://explorer.testnet.chain.robinhood.com/api/ <addr> <Contract>` | | manual explorer uploads |
| Deployment evidence (I-V5) | `forge script --broadcast` writes `broadcast/<script>/46630/run-latest.json`; a 40-line script converts it to `deployments/46630-lemma.json` in the Lattice format | | hand-written evidence files |
| Local chain for tests | `anvil --chain-id 46630` | 1.5.1 | Arbitrum precompiles are absent locally, so mock `NodeInterface` in tests and hit the real chain in the fork test |

`foundry.toml` additions: `robinhood_testnet = "${RPC_46630}"` under `[rpc_endpoints]`, `[etherscan]` entry not needed for Blockscout. Remappings: `@openzeppelin/=lib/openzeppelin-contracts/`, `sp1-contracts/=lib/sp1-contracts/contracts/`.

### B7 Policy controller / restricted signer

No new library. Port `mandate.mjs`, `policy.mjs`, `signer.mjs`, `transaction-projector.mjs`, `receipt-store.mjs` from Lattice Prime; they import only `ethers` (6.17.0 already in that repo's `node_modules`) and Node built-ins. The one substantive swap is `hedera-protocol-adapter.mjs` for an ethers `JsonRpcProvider` on the Robinhood RPC. Add a confirmation helper:

```js
const NODE_INTERFACE = "0x00000000000000000000000000000000000000C8";
const abi = ["function getL1Confirmations(bytes32) view returns (uint64)"];
// confirmations > 0 means the batch containing the block is on Sepolia (I-V2)
```

EIP-712 signing of the verdict (C6): `wallet.signTypedData(domain, types, value)` in ethers v6, template in Lattice `oracle/sign-dealer-quote.mjs`. On the Solidity side, OpenZeppelin `EIP712._hashTypedDataV4` plus `ECDSA.recover`, replay tests with `vm.chainId` and a second deployed instance.

### B2 Creator agent (restricted workspace)

| Need | Use | Version checked | Notes |
| --- | --- | --- | --- |
| Agent loop with tool allowlist | `@anthropic-ai/claude-agent-sdk` | 0.3.272, Node 18 or later | `permissionMode: "dontAsk"` plus scoped `allowedTools`: `Bash(cargo build *)`, `Bash(cargo test *)`, `Bash(lake build *)`, `Bash(gh workflow run apparatus-execute.yml *)`, `Read`, `Edit(candidate/**)`, `Edit(formal/**)`. Deny rules: `Edit(//abs/path/demand/**)`, `Edit(//abs/path/evaluation/**)`, `Read(//abs/path/holdout/**)`, `WebFetch`, `WebSearch`. A `PreToolUse` hook appends every call to the run log (I-A4, I-A6). Deny rules apply in every mode, including bypass. |
| OS-level enforcement of I-A3 | `@anthropic-ai/sandbox-runtime` (`srt`) | 0.0.76, Node 20.11 or later, macOS `sandbox-exec` or Linux bubblewrap | Filesystem read and write deny lists for holdout, demand, policy and key paths; network allowlist limited to `api.anthropic.com`, `github.com`, `api.github.com`, `crates.io`, `static.crates.io`, `index.crates.io`. Wrap the whole agent process: `srt --settings creator-srt.json node runner.mjs`. SDK rules and OS rules together give two independent layers. |
| Lean assistance for the theorem | `lean-lsp-mcp` (`uvx lean-lsp-mcp`) | pushed 19 Aug 2026, 506 stars, Lean 4 only | goals, diagnostics, hover, LeanSearch; expose to the creator as an MCP server so proof iteration is not blind `lake build` loops |
| Up-to-date docs for SP1 6.8, reth 2.2, alloy, RSP | Context7 MCP (`upstash/context7`) | pushed today, 62k stars | remote server, no install |
| Trigger execute-mode runs on the development blocks | `gh` with a fine-grained PAT limited to `actions: write` on `4waan/LemmaXperiment` | gh 2.95.0 installed | the creator never gets a broader token |
| Canonical hashing of run log, hypothesis, manifest | Lattice `canonicalJson` for JS; if Python must hash the same bytes, use RFC 8785 on both sides: npm `canonicalize` 5.0.0 and PyPI `rfc8785` 0.1.4 | | cross-language hash agreement without a custom spec |

### B3 Evaluator (frozen harness, own signer)

| Need | Use | Version checked | Notes |
| --- | --- | --- | --- |
| Host | GitHub Actions (existing `apparatus-*.yml`) | | workflow file hash is the policy hash, as planned |
| Provenance of evaluator artifacts | `actions/attest-build-provenance` | v4.2.2 | signed statement that the report artifact came from workflow X at commit Y; cheap evidence for I-E4 |
| Independent trie oracle (I-E6) | `ethereum/execution-specs` module `ethereum.merkle_patricia_trie` (install from the git tag) or `trie` 4.0.0 from PyPI | | Python 3.10 or later; use `uv` |
| RLP for adversarial fixtures | `rlp` (PyPI) or `ethereum_rlp` from execution-specs | | malformed RLP cases from TRIE_MODULE_PROTOCOL section 7 |
| Paired bootstrap interval (acceptance criterion 3) | `scipy.stats.bootstrap` with `paired=True`, or a 30-line stdlib resampler | | the stdlib version keeps the folder convention; scipy is fine inside LemmaXperiment |
| Lean check (I-E5) | pinned `lean-toolchain` file, `lake build`, `#print axioms`, then `leanchecker` from the same toolchain for the independent kernel pass | v4.34.0 installed | `policy.json` `leanToolchain` is still null; fill it |
| Rust to Lean bridge for the model-to-code gap (I-X3) | Aeneas (`AeneasVerif/aeneas`, pushed today, 963 stars) or hax (`cryspen/hax`) | Aeneas pins Lean 4.28 in the latest experience report | Optional and probably too heavy for 19 days: the 2026 experience report hit unsupported generics with trait bounds, external-crate calls and `while` loops needing termination measures. Record the gap in the evidence panel instead, and list Aeneas as later work. |
| PGU determinism (I-E8) | `apparatus-execute.yml` twice per variant | exists | nothing new |

### B5 Worker / prover

| Need | Use | Version checked | Notes |
| --- | --- | --- | --- |
| SP1 toolchain on runners | `sp1up`, `cargo prove` 6.8.0 (SP1 v6.8.0 released 11 Sep 2026); RSP tag `reth-2.2.0-sp1-6.8.0` | matches `pins.json` | already in `apparatus-build.yml` |
| Prover backend | `SP1_PROVER=cpu|cuda|network`, `ProverClient::from_env()` | | see finding 2 |
| Groth16 wrap | `ghcr.io/succinctlabs/sp1-gnark:v6.1.0` | amd64 only | GitHub ubuntu runner, never the laptop |
| Local verification before submission | `sp1-verifier` crate (Groth16 verification offchain) | 6.8.0 | the worker's "verify locally" step without a chain call |
| G1 tiny program | `succinctlabs/sp1-project-template` | pushed 20 Feb 2026 | finding 7 |

### B6 Indexer, ledger and proof graph

Two options; the second is recommended for the MVP because the plan already commits to `ledger.jsonl` and a static explorer.

| Option | What it gives | Cost |
| --- | --- | --- |
| Ponder 0.17.10 | declare `chains: { robinhoodTestnet: { id: 46630, rpc, ws } }` and ABIs; indexing functions in TypeScript; reorg rollback and idempotency built in (I-L1); PGlite for dev, Postgres for prod; GraphQL and SQL endpoints | Node 22, a new framework, a database; overkill for one demand and two jobs |
| viem `getLogs` polling plus hash-chained `ledger.jsonl` | the Lattice `hcs-index` / `hcs-verify` structure (claims checked against receipts and chain state); rebuild-from-zero is `getLogs` from the deployment block; the Blockscout API v2 (`/api/v2/addresses/<addr>/logs`, working today) is the second event source for the rebuild check | a few hundred lines, no database |

Metric functions lift from `proof_graph_sim.py` unchanged. `queueing_sim.py find` sets `proveBy` (I-S5).

### Explorer

Static pages generated from `ledger.jsonl` with Lattice `tools/gen-page.mjs`. If a wallet-connected page is ever wanted, `viem` 2.56.5 plus `wagmi` with the built-in `robinhoodTestnet` chain; not on the critical path.

## 2. MCP servers for the operator's own Claude Code session

These help whoever is building the system. They are separate from the creator agent's tool policy in section 1.

| Server | Command | Value here | Priority |
| --- | --- | --- | --- |
| Blockscout (official, `blockscout/mcp-server`) | `claude mcp add --transport http blockscout https://mcp.blockscout.com/mcp --header "Blockscout-MCP-Pro-Api-Key: <key>"` | reads contracts, logs, transactions on 46630 by chain id; `direct_api_call` for anything else | medium; needs a free PRO key from the Blockscout developer portal, or run `ghcr.io/blockscout/mcp-server` locally. `curl` against `explorer.testnet.chain.robinhood.com/api/v2` already works without it |
| lean-lsp-mcp | `claude mcp add lean-lsp -- uvx lean-lsp-mcp` | Lean goals and diagnostics while writing or reviewing the theorem | high during G3 and G4 |
| Context7 | `claude mcp add --transport http context7 https://mcp.context7.com/mcp` | current docs for SP1 6.8, reth 2.2, alloy, OpenZeppelin 5.7, viem | high; avoids stale API guesses |
| GitHub (official `github/github-mcp-server`) | remote server per its README | Actions runs, artifacts, releases | low; `gh` already does this |
| Foundry (`PraneshASP/foundry-mcp-server`, 253 stars, or `maxencerb/foundry-mcp`) | see repos | forge, cast, anvil as tools | low; Bash with forge and cast is equivalent |
| Alchemy (`alchemyplatform/alchemy-mcp-server`) | see repo | Alchemy supports `robinhood-testnet` | low |

The existing `~/hedera2026/.mcp.json` (Hedera) is irrelevant to this project. No official Arbitrum or Succinct MCP server exists; the Arbitrum docs are reachable through Context7.

## 3. Checked and set aside

| Item | Why not |
| --- | --- |
| `@arbitrum/sdk` | no bridging in the design; the one L1-confirmation query is a precompile call (finding 3) |
| Stylus SDK | decision in ROBINHOOD_CHAIN_PROD section 7 |
| ERC-4337 providers (Alchemy, ZeroDev, Privy, Dynamic) | the policy lives in B7; AA is a later option |
| ERC-8004 | adapter only, per AGENT_MARKETPLACE section 4 |
| IPFS pinning (Pinata, w3up) | GitHub release assets plus a sha256 digest onchain already give content addressing |
| Ponder as the primary ledger | see B6; keep as an upgrade path |
| Aeneas or hax in the evaluation | see B3; list as future work with the honest gap |
| Running the sp1-gnark wrapper on this Mac | amd64 image, 14 GB, 8 GB machine |

## 4. Install list

```bash
# JS runtime (Node 16 is installed and too old)
nvm install 22 && nvm use 22

# Python 3.12 and packages for the evaluator harness
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/.venvs/lemma --python 3.12
uv pip install --python ~/.venvs/lemma/bin/python trie rlp rfc8785 scipy numpy lean-lsp-mcp

# Contracts
cd LemmaXperiment/contracts
forge install foundry-rs/forge-std OpenZeppelin/openzeppelin-contracts@v5.7.0 succinctlabs/sp1-contracts@v6.1.0

# Agent runtime
npm i @anthropic-ai/claude-agent-sdk @anthropic-ai/sandbox-runtime ethers viem canonicalize

# Static analysis for the submission
uv tool install slither-analyzer
cargo install aderyn  # or the Cyfrin installer
uv tool install halmos  # optional

# SP1 (runner side; already in apparatus-build.yml, listed for completeness)
curl -L https://sp1up.succinct.xyz | bash && sp1up --version 6.8.0

# MCP servers for this Claude Code session
claude mcp add --transport http context7 https://mcp.context7.com/mcp
claude mcp add lean-lsp -- uvx lean-lsp-mcp
```

## 5. Reproduction of the facts checked today

```bash
RPC=https://rpc.testnet.chain.robinhood.com
NI=0x00000000000000000000000000000000000000C8
H=$(cast block --rpc-url $RPC 119887593 --json | python3 -c "import sys,json;print(json.load(sys.stdin)['hash'])")
cast call --rpc-url $RPC $NI "getL1Confirmations(bytes32)(uint64)" $H          # 281 at 14:45 UTC
cast call --rpc-url $RPC $NI "findBatchContainingBlock(uint64)(uint64)" 119887593  # 46484
cast chain-id --rpc-url https://robinhood-sepolia-rpc.publicnode.com              # 46630
curl -s https://chains.blockscout.com/api/chains/46630 | head -c 300              # Chainscout knows the chain
docker manifest inspect ghcr.io/succinctlabs/sp1-gnark:v6.1.0 | grep architecture # amd64 only
gh api repos/succinctlabs/sp1/releases/latest -q .tag_name                          # v6.8.0
gh api repos/succinctlabs/sp1-contracts/tags -q '.[0:3][].name'                     # v6.1.1 v6.1.0 v6.0.0
gh api repos/OpenZeppelin/openzeppelin-contracts/releases/latest -q .tag_name       # v5.7.0
ls ~/.elan/toolchains/leanprover--lean4---v4.34.0/bin | grep leanchecker
```

## 6. Decisions the operator still owns

- Fund the fast proving path: PROVE on mainnet for the Succinct network, or a GPU rental account. Without one of these the three real proofs depend on the 16 GB runner that has failed four times.
- Whether the Blockscout PRO key is worth requesting (free tier) or `curl` against the explorer API is enough.
- Pin `leanToolchain` in `evaluation/policy.json` (v4.34.0 is installed and has `leanchecker`).
- Approve `nvm install 22` and `uv` on the laptop.
