# lemma-prove

A thin wrapper over the pinned RSP host. The executor crates and measured
guest are the pinned upstream ones. This binary adds `--stdin-dir`,
`--out-dir`, `--proof-mode`, `--stdin-file` and `--guest settlement`, because
the upstream CLI discards proof bytes, does not expose the executor's stdin
dump, cannot execute a saved stdin again and does not commit the reuse escrow
context.

It is not built standalone. `apparatus-build.yml` copies this directory into
the pinned RSP checkout as `bin/lemma-prove`, copies `bin/host/src/cli.rs` and
`bin/host/src/execute.rs` next to it, appends the member to the workspace,
and builds. The build record lists the workspace edit and both binary hashes.

## Settlement guest

`--guest settlement` selects the evaluator-owned `lemma-client`. It executes
the same pinned RSP client and preserves every upstream validation, then
commits the nine static ABI words consumed by `UsageEscrow`: settlement chain,
market, job ID, source domain, block number, block hash, parent state root,
computed state root and success. The dynamic context is supplied with
`--job-chain-id`, `--job-market` and `--job-id` and is part of the saved stdin.

Candidate backend features are forwarded to both `rsp-client` and
`lemma-client`. Evaluation measures and proves the settlement guest, and the
accepted version records its independently derived key. The upstream guest
key remains diagnostic because its block-header public values cannot settle a
reuse job.

Outputs per block under `--out-dir`:

```text
vkey.txt                 program key of the embedded guest, every mode
{block}.execution.json   cycles, syscalls, prover gas, execution seconds,
                         build variant, per-phase cycle_tracker map
{block}.proving.json     vkey, proof length, proving seconds   (with --prove)
{block}.proof.bin        bincode SP1 proof                     (with --prove)
{block}.vk.bin / .txt    verifying key, bincode and bytes32    (with --prove)
```

## Replay: `--stdin-file`

`lemma-prove --block-number N --chain-id 1 --cache-dir cache --stdin-file N.bin ...`
executes the stdin a previous run saved (`--stdin-dir`) through the
executor's own validation path (guest execution, header check, the same
hooks), without the RPC provider or the input cache. Two executions of one
stdin file are executions of identical bytes, which is what the evaluation
policy's determinism check needs: a fresh host run re-serializes the witness
in HashMap order and moves cycles by about 0.01% (apparatus/INTERFACES.md
section 7). Execute only; `--prove` with `--stdin-file` is refused.

## Build variants

`apparatus-build.yml` builds the crate three times from the same sources:

| variant | cargo features | guest ELF | SP1 executor | use |
| --- | --- | --- | --- | --- |
| `standard` | none | pinned default MPT | native (x86_64 linux) | proofs, PGU, every timing that counts; evaluation baseline A |
| `cycle-tracking` | `rsp/cycle-tracking,lemma-prove/cycle-tracking` (= `sp1-sdk/profiling`) | same as standard | portable interpreter | per-phase cycle attribution only |
| `arena` | `rsp/arena,lemma-prove/arena` (forwarded to the guest by `build.rs`, as `bin/host/build.rs` does) | upstream arena MPT backend, unaudited | native | the registered existing capability; evaluation counterfactual C (`evaluation/policy.json`) |

The arena host writes its input cache without the witness (`parent_state` is
`serde(skip)` under that feature at the pin), so the arena variant never
shares the actions cache and cannot load the committed corpus inputs: it
runs from RPC, or replays a stdin it produced.

Standard and cycle-tracking share each corresponding guest ELF (the feature
is host-side), so `vkey.txt` must match between them and so must
`total_instruction_count` and `prover_gas`. What differs: SP1 6.8.0
only parses the guest's `cycle-tracker-report-*` lines under its `profiling`
feature (`sp1-core-executor/src/minimal/write.rs`), and that feature also
selects the portable executor over the native one (`sp1-core-executor/src/build.rs`
`detect_executor`). So the standard build leaves the six per-phase columns of
`report.csv` at 0, and the cycle-tracking build fills them at the cost of a
slower execute. The cycle-tracking build is never used with `--prove` and its
wall-clock is not a measurement. `execution.json` also carries `validate
header`, which the upstream CSV omits.

## lemma-wrap

`lemma-wrap --compressed-proof {block}.proof.bin --stdin {block}.bin --out-dir wrap-out`

Re-executes the guest for public values, verifies the compressed proof
against the pinned vkey, runs shrink and wrap, then Groth16 through gnark
(docker), verifies the bundle with the SDK and writes:

```text
groth16.bin          SP1ProofWithPublicValues, bincode
proof.hex            on-chain proof bytes (4 byte selector + groth16 proof)
public-values.hex    on-chain public values bytes
vkey.txt             program vkey (bytes32)
wrap.json            timings and lengths
```
