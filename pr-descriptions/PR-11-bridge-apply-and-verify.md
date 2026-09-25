# bridge: apply and verify, adoption receipts

Branch `bridge/apply-and-verify` → `main`. **Stacked on the bridge scan PR** (`bridge/scan-and-tools`): review after it merges, or read only the last commit. One commit.

## What and why

A bought resolution becomes a working change in the buyer's repository, with evidence of whether it works. This PR does three things:

- It applies the patch all or nothing, surviving crashes and concurrent bridges.
- It installs dependency changes without running package code.
- It runs the release's acceptance tests and records an adoption receipt only when the test run is real evidence about the resolution.

Receipts feed compatibility history (lever 7) once the payment work verifies their signatures.

## Changes

- **`lemma_apply_resolution({ capability, package?, mode? })`**
  - `mode: "preview"`, the default, reports what would change and writes nothing.
  - Drift, or a link anywhere on a bundle path, answers `adapt`. Nothing is written, and the files are exported to the state directory to merge by hand.
  - **Which purchase it uses:** one bought from a preview of this package or applied here. Otherwise it uses one bought for the same repository profile (a moved repository, a second worktree), which is exactly what the preview's "already bought" answer matches on.
  - **The journal** (`apply.ts`):
    - It is created fully formed and renamed into place, so of two applies only one gets it. Recovery claims a journal by renaming it, so two bridges never undo the same one.
    - Copies, digests and the journal are flushed to disk before the workspace changes. Staged content is flushed and renamed over each target.
    - A rollback restores a bundle file only if it still holds what apply wrote. A file edited since is left as it is, and its original is kept in `<state>/recovered/`.
    - package.json and every lockfile are put back as they were before an interrupted install; what they held is kept and reported.
    - One journal that cannot be undone is kept and reported, and never stops the bridge. The next apply of that resolution retries it.
    - A recorded install is killed before a rollback, but only when its identity can be verified by pid and start time (`/proc`, else `ps`). Otherwise the journal is kept rather than undone under a running install.
  - **Installs** (`install.ts`):
    - Lifecycle scripts, pnpmfiles and yarn builds are disabled: `--ignore-scripts`, `--ignore-pnpmfile`, and `--mode=skip-build` with `YARN_ENABLE_SCRIPTS=false`.
    - Exact pins are saved exactly on npm too.
    - The environment has no wallet keys or Lemma settings. Everything else passes, because registry configuration reads tokens from other variables.
    - No install outlives the bridge, and a group that cannot be recorded is stopped before the failure is reported.
- **`lemma_verify_adoption({ capability, package?, adapted? })`**
  - Runs the recipe (core `acceptanceArgv`) without a shell, in its own process group, with a minimal `PATH` (including the package manager's directory), a fresh `HOME` and only the variables the recipe lists. It stops at the recipe's timeout, and output is digested, never shown.
  - The package manager is checked first. One that is missing or does not run there records nothing, and neither does a run that did not start.
  - A receipt is recorded only when:
    - the resolution is applied here, or
    - apply answered `adapt` here and the agent says it merged by hand.
  - It refuses to run tests while the bridge's environment, or the one it started with, holds a wallet key, because tests run as the user and can read `/proc/<bridge>/environ`.
  - `LEMMA_ACCEPTANCE_OFFLINE=1` (Linux): a new network namespace with loopback brought up and checked first; where that is unavailable, nothing runs.
- **Receipts:**
  - Signed by the payment work's hook. When the hook fails, the receipt is kept and never sent unsigned, and it is signed at the next verify.
  - Posted as `{ receipt, previewId }`. `recordedAt` is never earlier than the resolution's creation.
  - `NOT_SETTLED` and `TOO_EARLY` are retried at the next start. `UNKNOWN_RESOLUTION` and `MISMATCH` are final and reported. A retried send says it recorded the first run's receipt, not this run's.
- **Server:** `GET /api/v1/releases/:digest`, the manifest by digest (the bridge checks the digest).
- **Startup:** journals are recovered and reported; pending purchases and unsent receipts are retried; a stray error in one tool call never takes the server down.
- **Answers** stay within 600 characters of enums, numbers, codes and validated paths. Recipe arguments never reach the model; at most a short plain test script name does.
- **Docs:** bridge README (apply, verify, receipts, key custody), security model (acceptance gaps, key custody), architecture.

## Verification

```
npm run verify          # typecheck, test typecheck, 436 tests, build: all pass
```

- **Journal:**
  - all-or-nothing apply, rollback on a write or install failure, recovery after a crash
  - a live apply left alone by recovery, and a second apply answered BUSY
  - later edits never overwritten, manifests put back and reported
  - an undo that cannot finish reported and retried
  - an install that cannot be identified never signalled
  - a recovery another bridge died in finished
  - an orphaned install killed
  - unreadable journals kept

  Each of these tests fails on the code before the fix.
- **Installs:** flags per package manager (npm, pnpm, yarn classic and berry), exact pins (`1.2.3`, `=1.2.3`, `v1.2.3`), the environment denylist, and an install stopped when its group cannot be recorded.
- **Acceptance:** the environment allowlist, capped and digested output, timeouts, a command or package manager that does not start, the offline argv, and texts that never echo recipe prose.
- **End to end,** from the bridge to the real server app in-process:
  - preview, buy, apply and verify, with the receipt recorded through the real bridge client
  - adapt, and adapted-by-hand verification only after an adapt answer
  - no receipt before apply
  - signing failure and retry
  - retryable answers
  - a moved repository
  - the wallet-key refusal

Reviewed in three rounds with independent reviewers who reproduced every finding before it counted. Among the fixes:

- journals without a lock, or with a non-atomic one
- rollbacks overwriting later edits
- a journal that stopped the bridge from starting
- installs seeing the wallet key, and yarn berry and pnpmfile hooks running
- installs outliving the bridge
- pid reuse leading to a kill of the wrong process group
- receipts from untested or unapplied changes, and receipts sent unsigned
- final answers retried forever, and retryable ones dropped
- the purchase used in a monorepo or a moved repository not matching the one the preview blocked

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (bundles, release manifests by digest, server answers).
- [x] No secret can reach browser code, model context, logs, or committed fixtures. The wallet key is kept out of installs and tests, and tests refuse to run while it is in the environment.
- [x] Paid paths remain idempotent and recoverable (one receipt per resolution, retries only where the server allows).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- Acceptance tests are the release's and the buyer's code running as the user:
  - the network is on unless offline mode is used
  - writes are not confined to the package
  - the real home is readable

  The buyer key belongs with a signer that runs as another user, or on a hardware or remote signer (handoff ask 9).
- Offline mode needs Linux, unprivileged user namespaces and the `ip` tool, and runs the tests as mapped root.
- A rollback cannot tell an interrupted install's change to package.json from an edit made after a crash. It puts the manifest back and keeps and reports what it held.
