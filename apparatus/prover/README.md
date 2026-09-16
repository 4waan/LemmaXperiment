# lemma-prove

A thin wrapper over the pinned RSP host. The guest ELF, executor crates and
CSV report are the pinned upstream ones; this binary only adds `--stdin-dir`,
`--out-dir` and `--proof-mode`, because the upstream CLI discards proof bytes
and does not expose the executor's stdin dump.

It is not built standalone. `apparatus-build.yml` copies this directory into
the pinned RSP checkout as `bin/lemma-prove`, copies `bin/host/src/cli.rs` and
`bin/host/src/execute.rs` next to it, appends the member to the workspace,
and builds. The build record lists the workspace edit and both binary hashes.

Outputs per block under `--out-dir`:

```text
vkey.txt                 program key of the embedded guest, every mode
{block}.execution.json   cycles, syscalls, prover gas, execution seconds,
                         build variant, per-phase cycle_tracker map
{block}.proving.json     vkey, proof length, proving seconds   (with --prove)
{block}.proof.bin        bincode SP1 proof                     (with --prove)
{block}.vk.bin / .txt    verifying key, bincode and bytes32    (with --prove)
```

## Build variants

`apparatus-build.yml` builds the crate twice from the same sources:

| variant | cargo features | SP1 executor | use |
| --- | --- | --- | --- |
| `standard` | none | native (x86_64 linux) | proofs, PGU, every timing that counts |
| `cycle-tracking` | `rsp/cycle-tracking,lemma-prove/cycle-tracking` (= `sp1-sdk/profiling`) | portable interpreter | per-phase cycle attribution only |

The guest ELF is identical in both (the feature is host-side; `build.rs`
forwards nothing to the guest), so `vkey.txt` must match across variants and
so must `total_instruction_count` and `prover_gas`. What differs: SP1 6.8.0
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
