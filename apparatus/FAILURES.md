# Apparatus failure log

Every failed run, its cause and its fix. Kept separate from the plan so the
plan stays readable and the failures stay countable.

| # | Run | Stage | Symptom | Cause | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | [34937991050](https://github.com/4waan/LemmaXperiment/actions/runs/34937991050) | build | `Could not find protoc` from `sp1-prover-types` build script | runner image lacks `protobuf-compiler`; RSP's own CI installs it | added an apt install step |
| 2 | [34938739219](https://github.com/4waan/LemmaXperiment/actions/runs/34938739219) | build | `couldn't read .../sp1-core-executor-runner-6.8.0/target/sp1-native-bins/release/...` | `sp1-core-executor-runner`'s build script spawns a nested cargo build and embeds the result by absolute path; the restored `target/` cache marked the script fresh while the registry source dir was re-extracted without the binary | removed `Swatinem/rust-cache`; build runs once per pin anyway |
| 3 | [34941010909](https://github.com/4waan/LemmaXperiment/actions/runs/34941010909) | prove | exit 143 (SIGTERM) 38 s after `starting proof generation` | SP1 6.8.0 CPU prover defaults (2^24-cycle shards, ~400M-element trace threshold, 4 core workers x 4 buffers, 8 recursion workers) exceed the runner's 16 GB; the hosted-runner watchdog kills the VM | one worker and one-deep buffer per stage, 2^20 shards, 64M-element threshold via env vars |
| 4 | [34941602366](https://github.com/4waan/LemmaXperiment/actions/runs/34941602366) | prove | exit 143 after 21 min of proving; artifact and post steps skipped | still over 16 GB. The 16 GB swap file was never created: `fallocate /swapfile` failed with `Text file busy` because that path is the runner's stock 2 GB swap, and a failure inside an `&&` chain does not trip `bash -e`. The memory log died with the VM | swap at `/swapfile2` (24 GB) with one command per line; memory sampler also streams into the job log; 2^19 shards, 32M-element threshold, normalize cache 1 |

| 5 | [34944035840](https://github.com/4waan/LemmaXperiment/actions/runs/34944035840) | prove | cancelled at 5 h 56 min by the 355 min job cap, still proving | working set ~27 GB (peak RSS 15.9 GB + 11.5 GB swap) against 16 GB RAM: the run swapped for six hours. Memory cannot go much lower through env vars; the rest is recursion proving keys. No shard progress visible because the pinned host pins `sp1_prover=warn` | `lemma-prove` honors `SP1_LOG` for shard progress; prove the smallest block (20600066, 0.96M gas) first to measure throughput before choosing between block size and host |

| 6 | [35048872659](https://github.com/4waan/LemmaXperiment/actions/runs/35048872659) | build | `unresolved module or unlinked crate tracing` in `wrap.rs` | `lemma-wrap` used `tracing::info!` without listing `tracing` as a dependency; every SP1 import resolved | added `tracing = "0.1"`; next build green |
| 7 | [35058394157](https://github.com/4waan/LemmaXperiment/actions/runs/35058394157) | build (standard) | `sp1up` step: `Fetching GitHub releases failed after 4 attempts: HTTP 403 ... API rate limit exceeded` | `cargo prove install-toolchain` queries the GitHub releases API unauthenticated; hosted runners share one IP quota, and the first job of the new two-variant matrix drew a runner whose quota was spent (the sibling job on another runner passed) | `sp1up --token "${{ github.token }}"`, which sp1up forwards to `install-toolchain` |
| 8 | [35060195042](https://github.com/4waan/LemmaXperiment/actions/runs/35060195042), [35060203750](https://github.com/4waan/LemmaXperiment/actions/runs/35060203750), [35060212541](https://github.com/4waan/LemmaXperiment/actions/runs/35060212541) | execute | `lemma-prove` printed its usage text and exited; the step then wrote `run.txt` with `wall_seconds: 0` and only failed at `cat run/report.csv` | operator dispatch error: the inputs were built in a zsh loop that does not word-split, so `block` arrived as `20600066 cycle-tracking` and `variant` as empty. The step masked the binary's exit status because its output goes through `tee` and the job shell has no `pipefail` | re-dispatched with quoted inputs; `set -o pipefail` at the top of the execute, prove and wrap steps so a binary failure fails the step before any record is written |
| 9 | [35078569391](https://github.com/4waan/LemmaXperiment/actions/runs/35078569391), [35078576105](https://github.com/4waan/LemmaXperiment/actions/runs/35078576105) | execute | host `failed to fetch storage ... Max retries exceeded HTTP error 429` five minutes into block execution | six execute jobs dispatched at once against one archive-provider key; the pinned provider layer retries 429 only three times with a one second initial backoff, and two of the six ran out of retries. The four others (two cache hits, two fresh) passed | dispatch RPC-backed executions one at a time; the offline `input_source=fixture` path avoids the provider entirely once a block is in the corpus. Block 23985839 (BPO1 era) was not retried once failure 10 explained the era |
| 10 | [35079926409](https://github.com/4waan/LemmaXperiment/actions/runs/35079926409) | execute | host `Failed to validate post execution state: block gas used mismatch: got 27639202, expected 27674793` on block 25988980 (BPO2 era, 2026-09-16), before any client input was written | per-transaction comparison against the chain's receipts: only three of the block's five EIP-7702 (type 4) transactions differ, by 12,500 gas each before the refund cap, and exactly those whose authority did not exist at the parent block (nonce 0, balance 0, `codeHash` zero in `eth_getProof`). The pinned host's `proofs` backend (`crates/storage/rpc-db/src/basic.rs:179`) returns `Some(AccountInfo)` for every address, so revm (`revm-handler` 18.1.0 `apply_eip7702_auth_list`, which refunds unless the account is empty *and* `is_loaded_as_not_existing_not_touched()`) grants the 12,500 gas refund the chain does not. The guest's `TrieDB::basic_ref` returns `None` for absent accounts and would compute the right gas, but the host rejects the block first. Upstream issue succinctlabs/rsp#181 reports the symptom with a different diagnosis (a revm version); the pin already carries reth v2.2.0 and still fails | pin left unpatched (it is the baseline). Supported range recorded: Cancun era fully; Prague and Osaka rules execute (blocks 22441128 and 23945771 pass) except any block with a 7702 authorization for a nonexistent authority, which is most current blocks (110 of 120 sampled carry type 4 transactions). Holdout blocks come from the Cancun era |

## Open

- Failure 10 is a pinned-host bug. Reporting the corrected diagnosis on
  succinctlabs/rsp#181 is the operator's call; the one-line fix (return
  `None` from `basic_ref` when nonce, balance and code hash are all zero)
  would change the host, not the guest, and stays out of this experiment.
- Apparatus step 1 closed on 2026-09-16: compressed proof of block
  20600066 in 4 h 09 min, Groth16 wrap in 31 min, verified on Arbitrum
  Sepolia through the SP1 gateway. Measured throughput about 5.5M cycles
  per hour, so proof-requiring blocks stay under about 30M cycles.
- If it still exceeds memory with swap in place, the next lever is SP1's fixed
  `ProverSemaphore::new(4)` in `cpu_worker_builder`, which is not an env var.
  It would need a custom worker builder in `lemma-prove`, still outside the
  pinned guest and executor crates.

## Patterns

- Three of seven failures were runner-environment gaps (missing package,
  wrong cache, unauthenticated GitHub API). The first two are what RSP's own
  CI already handles; mirror it first. The third only shows on shared
  hosted-runner IPs.
- Two of six were memory, one was the time cap. GitHub's hosted runner kills the whole VM on
  memory exhaustion, which also loses `if: always()` artifacts. Anything
  diagnostic must stream to the job log.
- A failing command inside `a && b && c` does not fail a `bash -e` step.
  One command per line in workflow `run:` blocks.
- A failing command on the left of `| tee` does not fail the step either
  unless `set -o pipefail` is on. Every run step now sets it.
- Parallel RPC-backed jobs share one provider key and one rate limit. Fixed
  inputs (the development corpus) remove the provider from every later run;
  anything that still needs the provider runs alone.
- Fork support is a property of the host as much as of the guest: the
  chain spec and the EVM were current, the state-fetching layer was not.
  Check support with blocks that contain the fork's new transaction types,
  not just blocks from the fork's era.
