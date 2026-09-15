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
