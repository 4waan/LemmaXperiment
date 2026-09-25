# benchmark: harness and stage-4 probe

Branch `benchmark/harness-and-probe` → `main`. **Stacked on the catalog PR** (`catalog/loader-and-fixtures`): review after it merges, or read only the last commit. One commit. It does not depend on the resolver, server or bridge PRs.

## What and why

Nothing is sold without evidence that it saves the buyer money (`docs/benchmark-protocol.md`, `docs/economic-gates.md`). This PR adds the harness that produces that evidence:

- the frozen paired benchmark, which produces run records and reports
- the stage-4 probe: a cheap go or kill test per release family, which also gives the price to pre-register

## Changes

- **Commands** (`npm run benchmark -- <command> <version> ...`):

  | Command | What it does |
  | --- | --- |
  | `freeze` | Checks the fixtures, the Lemma rule and `LEMMA_BENCHMARK_MODEL`, then does a smoke run that must be priced per token. Writes `experiments/<v>.json`. Refuses a version that is already frozen or has runs, and a freeze with no matched task. |
  | `run` | Runs the paired matrix with the arms interleaved. Each run is logged before its agent starts, so an interrupted or crashed run is recorded rather than re-rolled. It resumes from its logs. The version is bound to its freeze and locked while in use. |
  | `reconcile` | Turns attempts into core `RunRecord`s once billed cost has settled. A failing usage lookup leaves only that attempt pending. |
  | `probe` | Three controls and one treatment with the draft bundle pre-applied through core `planApply`. Decides go or kill with `maxPriceFor`. A verdict on placeholder economics is marked provisional. The version is bound to its task, fixture, bundle and model. |
  | `report` | Writes scrubbed verdicts and evidence. Any frozen task or slot without a result fails, and a report needs at least one matched task to pass. Each evidence entry names the release the paired treatments adopted and its base. |

- **Adapters.** `CursorAdapter` runs `@cursor/sdk` in a child process. The SDK is loaded lazily, and the key goes over stdin, never through the environment. `FakeAdapter` serves the tests.
- **Arms.**
  - Local runtime, no sandbox, project settings only.
  - Each run gets a fresh fixture copy outside the repository, with nothing above it that carries agent settings.
  - The treatment differs from the control only by the Lemma rule and the bridge.
- **Isolation.**
  - Every child gets an allowlisted environment and a fresh home per run.
  - The harness owns each run's deadline.
  - When a run ends, every process whose environment carries the run's home is killed, in repeated passes.
  - Commands that run agents refuse to start while their environment, or one an ancestor started with, holds anything that looks like a credential. The patterns are listed in the README.
- **Measurement.**
  - Tokens are mapped so the totals match Cursor's.
  - Cost is micro-USD from settled billing only, never estimated. A run that did work, or that was interrupted after it started, is never recorded at zero cost.
  - Startup failures are kept apart and retried once. A treatment whose agent ignored Lemma is a real result.
- **Installs** for pre-applied bundles run without lifecycle scripts: npm and pnpm with `--ignore-scripts`, yarn classic with `--ignore-scripts`, yarn berry with `--mode=skip-build`.
- **Docs:** benchmark README and protocol (arms, token mapping, reconcile, interrupted runs, credentials).

## Verification

```
npm run verify          # typecheck, test typecheck, 327 tests, build: all pass
```

- Fake-adapter tests cover:
  - token mapping and cost conversion
  - settled billing, and zero cost only for a run that did nothing
  - interrupted runs recorded, not re-run
  - the run-log lock (including a stale or half-written lock) and version binding
  - overlapping reconciles producing one record
  - report completeness and the adopted release
  - probe verdicts on measured and placeholder economics
  - credential patterns, both flagged and harmless
  - ancestor environments
  - process cleanup (a detached orphan, the SDK child's own fatal error without the key)
  - workspace removal and run-directory checks
  - install flags for every package manager
- Checked by hand: yarn 1.22.22 with `--ignore-scripts` and yarn 4.5.0 with `--mode=skip-build` do not run a dependency's postinstall.
- No real Cursor run happens in CI. The probe is run by hand with a key on a pipe.

Reviewed in three rounds, each with independent reviewers who reproduced every finding before it counted. Among the fixes:

- runs lost or re-rolled after an interruption
- agent processes surviving their run
- secrets readable by the agent from an ancestor's environment
- zero-cost records for runs whose billing had not landed
- reports passing with tasks missing
- evidence naming the wrong release
- a freeze smoke run outside the run-directory checks
- yarn installs running scripts
- two commands writing one version's logs at once

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (fixtures, the SDK child's output, billing reads).
- [x] No secret can reach browser code, model context, logs, or committed fixtures. The key goes over a pipe, never the environment, and raw run output stays in the ignored `runs/` directory.
- [x] Paid paths remain idempotent and recoverable (n/a; the payment ledger plugs in through `PaymentSource`).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- The credential check covers the harness and its ancestors only. A shell that started it in the background keeps its own copy, so run the harness from a session that never held the key.
- An agent id the provider never recognises stays pending, which blocks the report. This fails closed.
- The probe needs a draft bundle from the payment work (HANDOFF ask 8), and treatment payments need `SpendLedger.entriesFor` (ask 7).
