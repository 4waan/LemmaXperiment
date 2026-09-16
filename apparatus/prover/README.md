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
{block}.execution.json   cycles, syscalls, prover gas, execution seconds
{block}.proving.json     vkey, proof length, proving seconds   (with --prove)
{block}.proof.bin        bincode SP1 proof                     (with --prove)
{block}.vk.bin / .txt    verifying key, bincode and bytes32    (with --prove)
```

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
