# Optional candidate protocol: authenticated trie-node reuse

Status: proposed technical protocol. No implementation or results exist.

Use this only if the creation agent selects trie-node reuse after profiling. [EXPERIMENT.md](EXPERIMENT.md) defines the funded demand, agent workflow, evaluation limits and payment rules. This appendix does not predetermine the asset or override that experiment. Its cache-specific claims apply only to this candidate.

Source context: [Alloy trie tooling](https://alloy.rs/reference/protocol-and-rpc-types/) and [RSP block proving](https://succinctlabs.github.io/rsp/Generating-proofs).

## 5. Define the module precisely

### Interface contract

Conceptual interface, to adapt to the actual upstream types after the feasibility screen:

```text
resolve_node(expected_reference, immutable_witness, cache)
    -> authenticated_decoded_node or verification_error
```

- Hashed references must resolve to bytes whose Keccak digest equals the expected reference.
- Embedded child references must follow Ethereum's inline-node rules; they must not be treated as hashed references.
- RLP canonicality, compact-path decoding and node validity use the unchanged upstream semantics.
- A cache hit returns only a node previously authenticated for that exact reference and immutable byte content under the same decoder rules.
- An untrusted witness dictionary index is never itself evidence of authentication.
- Structural node caching does not cache a key's membership result. Each root/path traversal still checks its own path and node relationships.
- Cache lifetime is one job. Newly written trie nodes are immutable objects with new identities; no old cached object is mutated in place.
- All supplied hash-to-bytes mappings are authenticated in the guest before reuse. Host deduplication is an optimization, not a trust assumption.

Proposed resource bounds: a configurable byte cap and deterministic fallback to ordinary resolution. Select the cap on development fixtures, then freeze it before holdout measurement. Do not silently omit verification when the cache fills.

### Versions and controls

**A, primary baseline:** the pinned upstream prover with its existing optimizations intact.

**B, treatment:** the same prover with the candidate module enabled. The intended variable is node authentication/decoding reuse.

**C, diagnostic ablation:** the same module integration with cache reuse disabled. This helps isolate the mechanism but cannot replace A as the primary comparator.

Keep guest input encoding identical for A and B in the first pass if possible. If integration requires a changed witness format, treat it as a combined cache-plus-encoding optimization, include preprocessing costs, and label the result accordingly.

## 6. What Lean proves

Prove a refinement theorem over a small model of node resolution:

```text
For a fixed immutable witness and valid cache invariant,
resolving any finite reference sequence through the cache
has the same accepted results and rejection behavior
as resolving that sequence through the uncached model.
```

Supporting obligations:

1. An empty cache satisfies the invariant.
2. A miss authenticates and decodes before inserting.
3. An insertion preserves the invariant.
4. A hit returns the value associated with the requested authenticated node.
5. Capacity fallback preserves observable results.
6. Different roots or paths do not permit bypassing traversal checks.

Use an abstract deterministic authenticator/decoder in this first theorem. State that its Ethereum correctness, Keccak collision resistance where relied upon, and faithful Rust implementation are outside this theorem. Model hash-keyed reuse either under an explicit no-collision assumption for accepted node bytes or with exact-byte identity sufficient for the invariant. Do not leave that assumption implicit.

Run the Lean kernel check with a pinned toolchain. Publish theorem statements, dependency/axiom reports, and build logs. Reject unfinished proof placeholders and additional axioms that merely assume the desired result.

**Allowed description:** a module whose cache algorithm has a machine-checked refinement proof, with Rust behavior checked independently.

**Not established:** a fully formally verified Rust module, verified compiler, complete Ethereum semantics, or end-to-end formally verified execution prover.

Lean is not on the runtime proving path. The optimization changes the work; formal verification supplies evidence about its safety.

## 7. Independent correctness checks

Do not use A-versus-B agreement as the only oracle: both versions share the upstream parser and verifier.

### Three layers

1. **Regression:** A, B and C produce identical semantic outputs on identical valid fixtures and reject the same malformed fixtures within the declared input domain.
2. **Independent trie fixtures:** build small tries and verify lookups with a separately implemented Ethereum trie library, such as a pinned Python Ethereum trie implementation. Confirm it does not import the Rust implementation under test. Commit fixture bytes and expected outcomes.
3. **Block integration:** A and B validate the same block and computed post-state result against the frozen expected header using the upstream block-proving checks. Preserve all existing block validation rules.

### Required adversarial cases

- Empty trie and absent key; account and storage paths.
- Branch, extension and leaf nodes; odd/even compact paths.
- Inline and hashed child references, including their encoding boundary.
- Shared prefixes and disjoint paths.
- Wrong expected hash, malformed/noncanonical RLP, truncated node and wrong path.
- Missing witness node and conflicting mappings for one purported reference.
- A forged cache handle pointing at an unauthenticated node.
- Cache capacity at zero, one node, just below capacity and full capacity.
- Reordered lookups and repeated keys; identical bytes reached through different traversal contexts.
- A new root or modified witness after a previous job; no stale job cache allowed.
- Trie updates within block execution, preserving immutable-node identity.

Cache capacities are correctness configurations, not opportunities to tune on holdout performance. Publish case counts, configurations, failures and uncovered behavior. A single unexplained correctness mismatch blocks payment-demo approval of that module version.

## 8. Corpus and measurement protocol

### Freeze before optimizing

Create a manifest with chain ID, block numbers and hashes, parent roots, fork, witness hashes, expected outputs, input provenance and selection rule. Use historical finalized data in a fork supported by the pinned pipeline. RPC responses supply fixtures; this experiment does not implement a light client proving their canonicality.

**Development set:** three representative block fixtures for implementation and cap selection.

**Holdout set:** ten consecutive supported blocks selected by a fixed recorded rule before tuning. Keep them separate until the candidate version is frozen. Never replace an expensive or slow holdout block because it weakens the result.

**Diagnostic set:** synthetic trie workloads spanning high sharing, little sharing and malformed input. These explain mechanisms and do not estimate typical Ethereum savings.

If a pipeline rejects a block because the fork is unsupported, report that setup limitation and choose the supported range before benchmarking begins. If resources cannot cover the full holdout, label the result preliminary instead of reducing the success criteria after seeing results.

### Execution protocol

1. Run correctness checks before measuring performance.
2. Use the same hardware allocation, prover version, compiler settings, proof mode, security settings and external acceleration patches for A and B.
3. Build and perform one unmeasured toolchain warmup. Keep per-job module caches empty in every measured run.
4. Measure three paired runs per holdout block. Randomize A/B order with a published seed; do not run them concurrently on shared hardware.
5. Preserve all 60 planned proof runs, including failures, out-of-memory events and timeouts. Set a common timeout before starting.
6. Prove diagnostic C only on development fixtures unless a specific mechanism question remains unresolved.
7. Re-run after changes only as a new explicitly versioned candidate. Do not overwrite old observations.

The full plan is compute intensive. Obtain hardware access and a cost estimate during setup. No expenditure is authorized by this design document itself.

### Record for every run

- Candidate, commit, guest key, fixture ID, execution order and timestamps.
- CPU/GPU model, allocated resources, RAM, proof backend and configuration.
- Host witness preparation time, input bytes and guest cycles.
- Authentications, decodes, hits, misses and peak cache bytes in diagnostic instrumentation.
- Proving time, wrapping/compression time and final proof size.
- Local verification outcome and verification time.
- Fixed-resource compute charge or disclosed cost model.
- Failure category and timeout threshold, if applicable.

Measure final performance without diagnostic logging. If instrumentation is needed for cycles, keep that measurement distinct from the uninstrumented timing result.

**Primary latency:** host preparation plus proof generation plus wrapping on fixed resources. Report input acquisition, provider queue and onchain settlement separately, then also show buyer-observed total latency when available.

**Primary cost:** comparable complete-job cost, including preprocessing, proving, wrapping and settlement. If only a fixed-machine runtime proxy exists, say so; provider quotes are commercial prices, not direct evidence of computational efficiency.

### Analysis

For each block, take the median of its three A runs and three B runs. Report the median paired percentage change across blocks, every block-level result and aggregate baseline-versus-treatment cost over the corpus. Use a paired bootstrap over blocks for a 95% interval; do not pretend repeated runs are independent blocks.

Avoid tail-latency claims from ten blocks. Report observed regressions and failures directly. An interval crossing zero means the performance evidence is inconclusive, even if the point estimate looks favorable.

