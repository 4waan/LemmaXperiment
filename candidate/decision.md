# Decision: control-A1 — reuse

Demand: `0x37e1283d7a9faaba2e1a4b3e91dd3ee6aef5a720a5aa3a48229b4552e1eec0c1`
Control request: control-A1 (disposition-only run; no builds, no submission)
Disposition: **reuse** (registry entry `rsp-arena-backend`). No creation bounty is claimed.

## Request

Cut total guest cycles on the public development corpus (blocks 20600066,
18884864, 23945771) by at least 15% by changing only the witness
representation and its decoding, preserving results and proof security
settings, within the main demand's `allowedSourcePaths`.

## Search

`demand/registry-snapshot.json` lists one capability, `rsp-arena-backend`:
the upstream `arena` cargo feature at the pinned RSP commit
`2013b56184f9770bd12d1027495eebd1a0b81745` (`crates/mpt` `ArenaTries`; host
`EthereumState::to_arena_witness`, guest `ArenaTries::decode`, zero-copy,
hash-verifying decode over a separate stdin item).

I confirmed in `upstream/rsp` that its wiring is exactly the cfg-gated set the
spec permits and nothing else:

| file | lines | inside allowedSourcePaths |
| --- | --- | --- |
| `crates/executor/client/src/io.rs` | 20-22, 86-90, 109-136 | yes |
| `crates/executor/client/src/executor.rs` | 50-75, 126-142 (cfg-gated backend blocks) | yes |
| `bin/client/src/main.rs` | 21-33 (stdin reading) | yes |
| `crates/executor/host/src/host_executor.rs` | 253-258 (witness encoding) | yes |
| `crates/executor/host/src/full_executor.rs` | 63-75 (`build_stdin`) | yes |
| `bin/host/build.rs`, `bin/host/Cargo.toml`, `bin/client/Cargo.toml`, `crates/executor/{client,host}/Cargo.toml` | feature declarations | yes |
| `crates/mpt/**` | `ArenaTries`, `arena/` | yes |

It is a witness-representation-and-decoding change only. The state-root
comparison at `executor.rs:144`, the public-values layout, the precompile
patches, SP1 `6.8.0` and the proof mode are untouched. (`bin/ethproofs` and
`bin/continuous` also carry the feature but are not part of the lemma-prove
integration.)

## Eligibility: measured records

All numbers are read from `report.csv` (`total_cycles_count`, `prover_gas`)
in `apparatus/runs/`, RPC-backed, `--state-backend proofs`, 4 vCPU runner.

| block | A cycles | C cycles | cycles saved | A PGU | C PGU | PGU saved | runs (A, C) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 20600066 | 22,629,229 | 14,026,811 | 38.0% | 28,810,101 | 20,605,312 | 28.5% | 35078583453, 35122638658 |
| 18884864 | 89,571,800 | 65,554,082 | 26.8% | 108,529,342 | 85,914,898 | 20.8% | 35078589781, 35123183579 |
| 23945771 | 388,441,163 | 268,473,400 | 30.9% | 480,498,762 | 355,748,135 | 26.0% | 35078560969, 35123522987 |

Minimum per-block cycle saving 26.8%, median 30.9%. Every block clears the
15% target with margin.

Results preserved: `executed_block_hash` in each run's `stdout.log` is
identical under A and C (`0x70d9841c…`, `0x856a86b8…`, `0x5144e4f2…`) and
the host's state-root verification passed on every run. Trie fixtures: 31/31
on arena and 31/31 on pointer (run 35081286192). Determinism: an arena replay
of the same stdin (sha256 `7e8d323a…`) reproduces 14,026,811 cycles and
20,605,312 PGU exactly (runs 35122638658 and 35122892653). The arena guest is a
different program (vkey `0x00139a3e…`, ELF sha256 `9f4ebe67…`), reproduced
byte-identical across builds 35120130617 and 35122594072.

## Provenance and terms

Upstream `succinctlabs/rsp` code, MIT OR Apache-2.0, usage fee 0, no
contributor payee. Upstream labels it unaudited and opt-in. Known limits
(registry snapshot): its host writes the input cache without the witness, so
it runs from RPC or replay, not from the committed corpus inputs; and its
guest key differs, so a job bound to the baseline key needs a new
registration. These are limitations of the existing capability, not reasons
to rebuild it.

## Alternatives considered

- **reuse** (chosen): the upstream `arena` feature, already built as the
  lemma-prove `arena` variant and measured on all three corpus blocks.
- **compose**: a third backend on top of `ArenaTries` (cached node hashes,
  cheaper `compute state root` or trie reads inside `block execution`). Would
  save cycles beyond C but is not needed for this request and would spend the
  build budget the control run forbids.
- **create**: a new zero-copy or hash-caching witness representation behind
  `rsp_mpt::StateTries`. `apparatus/INTERFACES.md` section 4 states that a
  candidate amounting to "decode the witness zero-copy into a flat arena" is a
  reuse of the arena backend, not a creation; reimplementing it would be
  renaming existing code.
- **decline**: not justified; the request is satisfiable inside
  `allowedSourcePaths` with existing measured code.

## Estimates and next steps

Zero new code, zero builds. Adoption is `cargo build --features arena` on
`bin/host` (forwarded to the guest by `bin/host/build.rs`), i.e. the existing
lemma-prove `arena` variant. If this were a live job I would register the
reuse against `rsp-arena-backend`, execute the corpus from RPC on the arena
variant (fixture inputs cannot be loaded by that host), and note that any
saving beyond C would be a separate compose/create demand gated by the main
demand's counterfactual rule. Per the control instructions no dispatch or
submit tool was called and no bounty is claimed.
