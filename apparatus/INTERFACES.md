# Interface survey (apparatus step 2)

EXPERIMENT.md section 4, step 2: identify permitted witness-processing
interfaces without implementing the solution. This file is the survey. It
names every place in the pinned RSP where state-witness processing happens,
which of those places a candidate may change, and which must stay as they
are. It proposes no optimization and contains no hypothesis about where the
cycles could go; that is the creator's step C, done against the numbers in
section 7.

Every reference is to RSP at commit `2013b56184f9770bd12d1027495eebd1a0b81745`
(tag `reth-2.2.0-sp1-6.8.0`, `apparatus/pins.json`). Line numbers are for that
commit and were checked by reading the source, not upstream docs.

## 1. What the guest does with the witness

The guest program is `bin/client/src/main.rs`. It reads stdin, calls
`ClientExecutor::execute` (`crates/executor/client/src/executor.rs:53`) and
commits the derived block header. `execute` is split into labelled phases by
the `profile_report!` macro (`crates/executor/client/src/utils.rs`), which
prints `cycle-tracker-report-start/end: <label>` from inside the zkVM. The
labels are the constants at `executor.rs:28-34`; the CSV columns of
`report.csv` are named after them (`bin/host/src/execute.rs`, which the
`lemma-prove` wrapper copies verbatim).

| label | where | what runs | witness work inside it |
| --- | --- | --- | --- |
| `deserialize inputs` | `bin/client/src/main.rs:20` | `sp1_zkvm::io::read_vec()` then `bincode::deserialize::<EthClientExecutorInput>` | the whole witness (`parent_state: EthereumState`, `bytecodes`, headers, block) is decoded here on the default backend; the arena backend decodes only a small header here and reads the trie blob as a second stdin item (`main.rs:28-30`) |
| `initialize witness db` | `executor.rs:68` | `input.witness_db(&sealed_headers)` (`io.rs:111`) which is `build_trie_db` (`io.rs:235`) | state-root anchor check `tries.state_root()`; `storage_roots()` hashes every revealed storage trie and compares with the account leaf; every bytecode is hashed (`hash_slow`) into a map; ancestor headers are hash-linked; the result is the `TrieDB` revm reads from. On the default backend the node hash cache is `#[serde(skip)]` (`crates/mpt/src/mpt.rs:101`), so this phase recomputes every node hash of every trie from scratch |
| `recover senders` | `executor.rs:78` | signature recovery | none |
| `validate header` | `executor.rs:85` | consensus header checks against parents | none (this label is not a CSV column; `execution.json` carries it) |
| `block execution` | `executor.rs:103` | reth `BasicBlockExecutor` over `WrapDatabaseRef(TrieDB)` | every account read is `keccak256(address)` plus a state-trie walk (`TrieDB::basic_ref`, `io.rs:195`); every storage read is `keccak256(address)`, `keccak256(slot)` plus a storage-trie walk (`storage_ref`, `io.rs:215`); bytecode and block hashes are map lookups. These reads are witness processing but they are inseparable from EVM cycles in the CSV |
| `validate block post-execution` | `executor.rs:106` | receipts root, gas used, requests, bloom | none |
| `compute state root` | `executor.rs:130` | `hash_state_slow` on the outcome, then `tries.update(&post_state)` and `tries.state_root()` | inserts and deletes into storage tries and the state trie, rehash along every modified path |

After the last phase, `executor.rs:144` compares the computed root with the
block header's `state_root` and fails with `MismatchedStateRoot` otherwise.
That comparison, together with the committed header, is what makes every
host-supplied byte of the witness untrusted-but-safe. It is not an interface;
it is the soundness anchor every candidate must leave in place.

## 2. The seam: `rsp_mpt::StateTries`

`crates/mpt/src/lib.rs:442` defines the backend-agnostic trie view the
executor drives:

```text
trait StateTries {
    fn state_root(&self) -> B256;
    fn account(&self, hashed_address: B256) -> Option<TrieAccount>;
    fn storage_value(&self, hashed_address: B256, hashed_slot: B256) -> U256;
    fn storage_roots(&self) -> impl Iterator<Item = (B256, B256)> + '_;
    fn update(&mut self, post_state: &HashedPostState);
}
```

Two implementations exist at the pin:

| backend | type | impl | construction (outside the trait) | wire format |
| --- | --- | --- | --- | --- |
| default (pointer MPT, from zeth) | `EthereumState { state_trie: MptNode, storage_tries: HashMap<B256, MptNode> }` (`lib.rs:34`) | `lib.rs:461` | serde: the guest gets it by bincode inside `ClientExecutorInput.parent_state` (`io.rs:87`) | bincode of `MptNode` trees, hash cache dropped |
| `arena` (feature, unaudited) | `ArenaTries<'a> { state_trie: arena::Mpt, storage_tries, pre_state_storage_roots }` (`lib.rs:249`) | `lib.rs:491` | `ArenaTries::decode(&bump, &blob)` (`lib.rs:275`), zero-copy over a separate stdin item; every node's reference is checked against its parent's expectation while decoding (`arena/trie.rs:193`) | flat blob produced by `EthereumState::to_arena_witness` (`lib.rs:195`): framed tries plus the `psr` section of pre-state storage roots, sorted |

The generic consumers of the trait are `TrieDB<'a, T: StateTries>`
(`io.rs:174`, the revm `DatabaseRef`) and `build_trie_db` (`io.rs:235`).
Everything else that knows the backend is `cfg`-gated on the `arena`
feature, and that gating is the map of what a third backend has to touch:

| side | file | lines | backend-specific content |
| --- | --- | --- | --- |
| guest | `crates/executor/client/src/io.rs` | 86-90, 108-136 | type of `parent_state`; `witness_db` and `tries` constructors |
| guest | `crates/executor/client/src/executor.rs` | 50-75, 130-142 | bump and decode before `INIT_WITNESS_DB`; which `update`/`state_root` runs in `COMPUTE_STATE_ROOT` |
| guest | `bin/client/src/main.rs` | 20-33 | one stdin item or two |
| guest | `crates/executor/client/Cargo.toml`, `bin/client/Cargo.toml` | `[features] arena` | feature and its optional dependency (`bumpalo`) |
| host | `crates/executor/host/src/host_executor.rs` | 252-258 | the host always builds `EthereumState` first (line 188, `rpc_db.state(...)`) and then either ships it or re-encodes it (`to_arena_witness`) |
| host | `crates/executor/host/src/full_executor.rs` | 66-75 | `build_stdin`: one `write_vec` or two |
| host | `crates/executor/host/Cargo.toml`, `bin/host/Cargo.toml` | `[features] arena` | feature plumbing |
| host | `bin/host/build.rs` | all | forwards `CARGO_FEATURE_ARENA` so the guest ELF is built with the same backend as the host |

Note on `io.rs:230-234`: upstream records that calling the trie-db
constructor through a bare trait method instead of the inherent `witness_db`
costs over 5M extra cycles in the zkVM. The call shape is part of the
interface; a candidate that changes it inherits that cost or explains why not.

## 3. Host state backends: `proofs` and `execution-witness`

These are two ways for the host to obtain the witness. They are a runtime
choice (`StateBackend`, `crates/executor/host/src/lib.rs:46`, CLI flag
`--state-backend`, `bin/host/src/cli.rs:53`), dispatched at
`host_executor.rs:89-127`. Both end in an `EthereumState` through the
`RpcDb` trait (`crates/storage/rpc-db/src/lib.rs:22`: `state()`,
`bytecodes()`, `ancestor_headers()`), and the guest cannot tell which one
produced its input.

| backend | host type | RPC calls | witness builder | availability here |
| --- | --- | --- | --- | --- |
| `proofs` | `BasicRpcDb` (`rpc-db/src/basic.rs:27`) | `eth_getProof` per touched account at the parent block (accessed keys) and at the block (modified keys), `eth_getCode`, `eth_getStorageAt`, headers | `EthereumState::from_transition_proofs` (`lib.rs:41`) which is `transition_proofs_to_tries` (`mpt.rs:1153`): proof nodes are deduplicated by node reference into one store, non-inclusion leaves from the post-state proofs are added so deletions can be applied (`add_orphaned_leafs`), then `resolve_nodes` builds one sparse trie per root | used for every run in this apparatus (pinned) |
| `execution-witness` | `ExecutionWitnessRpcDb` (`rpc-db/src/execution_witness.rs:18`) | one `debug_executionWitness(block)` | `EthereumState::from_execution_witness` (`lib.rs:89`) which is `build_validated_tries` (`mpt/execution_witness.rs:12`): every RLP node is decoded into maps by hash and by reference, the state trie is resolved from the pre-state root, storage tries from each account leaf's storage root (untouched accounts have none), then both roots are validated | not available: the pinned RPC provider answers `debug_executionWitness is not available on the ETH_MAINNET` (checked 2026-09-16); RSP's own docs say hosted providers usually lack the `debug` namespace |

What differs between them is the set of nodes the witness carries, which
changes guest cycles for the same block. What does not differ is any guest
code. For this experiment the backend is fixed to `proofs`: the evaluator can
only run that one, and switching backends between A and B would compare
witnesses, not modules.

The line in EXPERIMENT.md that the reference witness builder already
deduplicates accessed nodes is visible in both builders: one node store keyed
by `MptNodeReference` per trie (`mpt.rs:1170-1180`, `execution_witness.rs:21-30`).
Duplicate authentication does not come from the host; whatever the guest
re-hashes, it re-hashes because of how it decodes and uses the tries.

## 4. The two trie implementations under the seam

Pointer MPT, `crates/mpt/src/mpt.rs`:

- `MptNode { data: MptNodeData, cached_reference: Mutex<Option<MptNodeReference>> }`
  (line 95); `MptNodeData` is `Null | Branch([Option<Box<MptNode>>; 16]) | Leaf | Extension | Digest(B256)` (line 164).
- Operations the guest uses: `get_rlp` (539), `insert_rlp` (709), `delete`
  (582), `hash` (449), `clear` (384), `for_each_leaves` (416). `hash` goes
  through `reference` (412) and `calc_reference` (480), which RLP-encodes the
  node and keccaks it when the encoding is 32 bytes or longer.
- Serialized with serde. The hash cache is skipped (line 101), so a
  deserialized trie carries no hashes.
- In scope of the Veridise audit in `audits/VAR_FLUENT_250512_STF_SP1.pdf`
  (May 2025, RSP commit `0d04ea9`; finding VUL-006 is about this file).

Arena MPT, `crates/mpt/src/arena/` (ported from `openvm-eth`):

- `Mpt<'a> { nodes: Vec<NodeData<'a>>, cached_references: Vec<Cell<Option<NodeRef>>>, bump }`
  (`trie.rs:60`): flat node vector, `u32` child ids, paths and values borrowed
  from the input blob or a `bumpalo` bump.
- `encode_trie` (158, host only) and `decode_trie` (193): each node's RLP is
  padded to 4-byte alignment and its reference is verified against the
  parent's expected reference while decoding, so decode doubles as
  authentication.
- `from_mpt_node` (109) converts a pointer trie; `get_rlp` (551),
  `insert_rlp` (570), `delete` (585), `hash` (522) mirror the pointer API.
- `ArenaTries::update` (`lib.rs:321`) applies changes in canonical witness
  order and falls back to the `psr` cache for accounts whose storage was not
  touched. The `psr` bytes are not hash-committed; their soundness rests on
  the final state-root check (documented at `lib.rs:168-192`).
- Marked "not yet audited, opt-in only" in
  `crates/executor/client/Cargo.toml`. Tests: `arena/tests.rs`, the
  round-trip and tamper tests at the bottom of `lib.rs`; a host-side
  micro-benchmark at `crates/mpt/examples/bench_arena_mpt.rs`.

The arena backend is prior art that exists at the pin. It goes into the
registry snapshot as the seeded existing-capability entry. A candidate that
amounts to "decode the witness zero-copy into a flat arena" is a reuse of it,
not a creation; a candidate may compose with it (build on the arena feature)
if the compatibility manifest says so.

## 5. Not interfaces for this demand

These parts touch the witness path or its neighbours and are frozen. The
demand text says "preserve its accepted computation and proof security
settings"; this list is what that means at the pin.

| frozen | why |
| --- | --- |
| `crates/executor/client/src/custom.rs` (precompiles, `CustomCrypto`, `CustomEvmFactory`) and `[patch.crates-io]` in the workspace `Cargo.toml` (sha2, sha3, bn, k256, p256 SP1 patches) | accepted computation and acceleration settings; changing them changes what the proof attests |
| `crates/executor/client/src/executor.rs` outside the two `cfg`-gated blocks, including the phase labels, the state-root comparison (144) and the header derivation | the labels are the measurement; the comparison is the soundness anchor |
| `bin/client/src/main.rs:35-43` (`EthClientExecutor::eth`, `commit::<CommittedHeader>`) | the public-values layout is what the on-chain verifier binds |
| `crates/executor/client/src/tracking/**`, `into_primitives.rs`, `crates/primitives/**`, `crates/provider/**` | not witness processing |
| `crates/storage/rpc-db/**` | host-side witness fetching; the evaluator fixes the backend to `proofs` and A/B must consume the same witness bytes |
| `crates/storage/witness-db/**` | orphaned: a workspace member with no dependents at the pin (`WitnessDb`, a HashMap-backed `DatabaseRef` from before the MPT witness). Listed so nobody mistakes it for the insertion point |
| `crates/executor/host/src/host_executor.rs` outside lines 252-258 | host-side validation (state root verified on the host before the guest runs) stays |
| `bin/host/src/execute.rs` | the report format is the evaluator's |
| `rust-toolchain.toml`, reth/revm/alloy versions in `Cargo.toml`, `sp1-*` at `=6.8.0`, `Cargo.lock` except entries the module's own crates add | the pin |
| SP1 proof mode, circuit version, prover environment knobs | `apparatus/pins.json`; the evaluator's workflow files own them |

## 6. Proposed values for the demand

For `demand/spec.json` (draft until step 5 freezes it):

`allowedSourcePaths`

```text
crates/mpt/**                                 (new backend, or a new crate under crates/)
crates/executor/client/src/io.rs              (parent_state type, witness_db constructor)
crates/executor/client/src/executor.rs        (only the cfg-gated backend blocks, 50-75 and 130-142)
crates/executor/client/Cargo.toml
bin/client/src/main.rs                        (only stdin reading, 20-33)
bin/client/Cargo.toml
crates/executor/host/src/host_executor.rs     (only the witness encoding, 252-258)
crates/executor/host/src/full_executor.rs     (only build_stdin, 66-75)
crates/executor/host/Cargo.toml
bin/host/Cargo.toml
bin/host/build.rs
```

`integrationInterface`

```text
Implement rsp_mpt::StateTries (crates/mpt/src/lib.rs:442) for the new
representation, wire its construction into ClientExecutorInput exactly as the
upstream `arena` feature is wired (guest: io.rs, executor.rs, bin/client;
host: host_executor.rs encoding from EthereumState, full_executor.rs stdin),
behind one cargo feature declared on bin/host and bin/client and forwarded to
the guest by bin/host/build.rs. The unchanged `lemma-prove` wrapper built
with that feature is the integration: no other entry point is evaluated.
```

Candidate identity for the evaluator: an RSP fork commit whose parent is the
pin, the feature name(s) to pass for `-p rsp -p lemma-prove`, and the
compatibility manifest. The evaluator derives the guest key from its own
build; a candidate cannot ship an ELF.

Control for the registry snapshot: the seeded existing-capability entry is
the `arena` feature (section 4). The no-viable-opportunity control is a
request whose change lies outside the paths above, for example fewer cycles
in `recover senders` or in a precompile; the expected disposition is decline.

## 7. Baseline share per phase

Measured with the `cycle-tracking` build variant (`apparatus/prover/README.md`,
"Build variants"), which is the same guest ELF as the standard build; only
the SP1 host executor differs. Totals and prover gas are checked against the
standard-build baseline of step 1 before the per-phase numbers are used.

PENDING: filled in from the cycle-tracking execute runs.

What the columns cannot tell apart: trie reads happen inside `block
execution`. A creator that needs finer attribution has two upstream tools,
both diagnostic-only: `--opcode-tracking` (an EVM inspector; the upstream
docs warn it inflates cycle counts substantially) and the SP1 profiler that
the same `profiling` feature enables (`TRACE_FILE`, `TRACE_SAMPLE_RATE`;
Gecko format), which this apparatus has not exercised.
