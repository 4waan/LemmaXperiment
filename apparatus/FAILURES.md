# Apparatus failure log

Every failed run, its cause and its fix. Kept separate from the plan so the
plan stays readable and the failures stay countable.

| # | Run | Stage | Symptom | Cause | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | [34937991050](https://github.com/4waan/LemmaXperiment/actions/runs/34937991050) | build | `Could not find protoc` from `sp1-prover-types` build script | runner image lacks `protobuf-compiler`; RSP's own CI installs it | added an apt install step |
| 2 | [34938739219](https://github.com/4waan/LemmaXperiment/actions/runs/34938739219) | build | `couldn't read .../sp1-core-executor-runner-6.8.0/target/sp1-native-bins/release/...` | `sp1-core-executor-runner`'s build script spawns a nested cargo build and embeds the result by absolute path; the restored `target/` cache marked the script fresh while the registry source dir was re-extracted without the binary | removed `Swatinem/rust-cache`; build runs once per pin anyway |
| 3 | [34941010909](https://github.com/4waan/LemmaXperiment/actions/runs/34941010909) | prove | exit 143 (SIGTERM) 38 s after `starting proof generation` | SP1 6.8.0 CPU prover defaults (2^24-cycle shards, ~400M-element trace threshold, 4 core workers x 4 buffers, 8 recursion workers) exceed the runner's 16 GB; the hosted-runner watchdog kills the VM | one worker and one-deep buffer per stage, 2^20 shards, 64M-element threshold via env vars |
| 4 | [34941602366](https://github.com/4waan/LemmaXperiment/actions/runs/34941602366) | prove | exit 143 after 21 min of proving; artifact and post steps skipped | still over 16 GB. The 16 GB swap file was never created: `fallocate /swapfile` failed with `Text file busy` because that path is the runner's stock 2 GB swap, and a failure inside an `&&` chain does not trip `bash -e`. The memory log died with the VM | swap at `/swapfile2` (24 GB) with one command per line; memory sampler also streams into the job log; 2^19 shards, 32M-element threshold, normalize cache 1 |

## Open

- Run [34944035840](https://github.com/4waan/LemmaXperiment/actions/runs/34944035840): in progress with the fix for #4.
- If it still exceeds memory with swap in place, the next lever is SP1's fixed
  `ProverSemaphore::new(4)` in `cpu_worker_builder`, which is not an env var.
  It would need a custom worker builder in `lemma-prove`, still outside the
  pinned guest and executor crates.

## Patterns

- Two of four failures were runner-environment gaps (missing package, wrong
  cache). Both are what RSP's own CI already handles; mirror it first.
- Two of four were memory. GitHub's hosted runner kills the whole VM on
  memory exhaustion, which also loses `if: always()` artifacts. Anything
  diagnostic must stream to the job log.
- A failing command inside `a && b && c` does not fail a `bash -e` step.
  One command per line in workflow `run:` blocks.
