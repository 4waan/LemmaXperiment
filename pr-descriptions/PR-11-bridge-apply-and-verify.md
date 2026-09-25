# bridge: apply and verify, adoption receipts

Branch `bridge/apply-and-verify` → `main`. **Stacked on the bridge scan PR** (`bridge/scan-and-tools`): review after it merges, or read only the eight commits after it. Each commit is one change, builds, and passes the whole suite on its own.

## What and why

A bought resolution becomes a working change in the buyer's repository, with evidence of whether it works. This PR does three things:

- It applies the patch all or nothing, surviving crashes and concurrent bridges.
- It installs dependency changes without running package code.
- It runs the release's acceptance tests and records an adoption receipt only when the test run is real evidence about the resolution.

Receipts feed compatibility history (lever 7) once the payment work verifies their signatures.

## Commits

1. **catalog: check a profile against a bare release manifest.**
   - `checkReleaseProfile` is the resolver's `checkProfile` for a client that holds a manifest but not the index.
   - A property test holds the two equal.
2. **server: serve a release manifest by digest.**
   - `GET /api/v1/releases/:digest` serves from the catalog, or from the store once a redeploy dropped the release.
   - The response is immutable. The bridge checks the digest.
3. **bridge: crash-safe apply journal, one per repository** (`apply.ts`).
   - There is one journal per repository (the lockfile's directory), taken before anything is planned. A second apply there gets BUSY.
   - An unfinished earlier apply is undone first and reported.
   - Copies and the journal are flushed before the workspace changes.
   - Added files are linked into place, which fails if something appeared there. A replaced file must still hold what the bundle was built against.
   - A rollback restores only what still holds the apply's content and keeps the original of anything it leaves.
   - package.json and lockfiles are put back after an interrupted install. A kept journal retries only its failed steps.
   - Startup recovery claims dead journals in place (`claim.<n>`), so a live apply is never moved.
   - A process is recognized by pid and start time (`/proc`, else `ps` in UTC and the C locale), within its namespaces and boot. A holder in other namespaces is judged by a heartbeat.
   - A recorded install is killed only when verified. A leaderless group is left alone.
4. **bridge: dependency installs without package code or wallet secrets** (`install.ts`, `secrets.ts`).
   - Scripts, pnpmfiles and yarn builds are off, and exact pins are saved exactly.
   - The environment has neither wallet secrets nor the bridge's settings, using one shared list of secret names.
   - Installs are killed when the bridge exits.
5. **bridge: acceptance runs that count only as evidence** (`acceptance.ts`).
   - There is no shell. Each run gets its own process group, a minimal `PATH`, a fresh `HOME` and the user's corepack cache with downloads off.
   - The package manager is found on the bridge's PATH, checked, and run by that path.
   - Output is capped and digested, and the duration is monotonic.
   - Offline mode (Linux) reports its own progress on fd 3, so its failures never count as test results.
6. **bridge: purchase records, receipt sending and release manifests.**
   - The inbox keeps each preview's package and capability, links from purchases to packages, adapt markers per package, release manifests and receipts.
   - A package is identified by directory, workspace path and `package.json` name.
   - The preview offers no second purchase of a release this package already owns, and tells a purchase that is bought from one still settling.
   - Receipts are posted as `{ receipt, previewId }`; `NOT_SETTLED` and `TOO_EARLY` are retried.
7. **bridge: apply and verify tools with adoption receipts** (`adoption.ts`, `text.ts`, `main.ts`), described below.
8. **docs:** bridge README (apply, verify, receipts, key custody), security model (acceptance preconditions, the corepack cache, limits on release-chosen text).

## The tools

- **`lemma_apply_resolution({ capability, package?, mode? })`**
  - `mode: "preview"`, the default, reports what would change and writes nothing.
  - Drift answers `adapt` and exports the files to merge by hand. Content already in place answers "already applied".
  - `mode: "apply"` takes the repository's journal first, then plans and writes through it.
  - **Which purchase it uses:**
    1. One for this package still settling: recovered first, never passed over for an older one.
    2. Else the newest for this package: previewed here, or chosen for it before. A moved repository keeps it.
    3. Else the newest bought for its current profile.
  - The package must still fit the profile the purchase was made for, or nothing is applied or recorded.
- **`lemma_verify_adoption({ capability, package?, adapted? })`** runs the recipe only when the run is evidence about the resolution. Nothing runs, and nothing is recorded, when:
  - its files are not in place, unless apply answered `adapt` here and the agent says it merged;
  - an apply is running or unfinished in the repository;
  - the package pins another Node major than the bridge's;
  - the recipe's script is missing (or only npm's placeholder);
  - the package manager does not run;
  - a wallet secret is in the bridge's environment.

  The first run's receipt is signed by the payment work's hook (never sent unsigned) and retried when the answer allows. Later runs only retry it, and every answer says so.
- **Answers** stay within 600 characters of counts, codes and short bundle paths. Paths are capped at 100 characters each and 120 in all, since the release chooses them. Recipe arguments never reach the model.
- **Startup:**
  - Journals are recovered and reported, with manifests put back counted apart from files left alone.
  - Pending purchases and unsent receipts are retried.
  - A stray error in one tool call never takes the server down.

## Verification

```
npm run verify          # typecheck, test typecheck, 470 tests, build: all pass (at every commit)
```

The bridge has 111 tests in four files, one per module, plus the existing scan and bridge tests.

- **Journal** (`apply.test.ts`):
  - all or nothing, drift checked with the journal held, and a file changed or created between the check and the write never overwritten
  - crash recovery; live applies left alone
  - applies in one repository serialized, across resolutions
  - later edits never overwritten; manifests put back and reported, including by a rollback that crashed
  - no restore temp files left behind
  - an unfinished undo retried first and reported, only in its own repository, and never repeating a done step
  - an unverifiable install and a leaderless group never signalled
  - start times compared only when read the same way, the same in every time zone
  - holders in other namespaces judged by their heartbeat; one from another boot counted as gone
  - a race test: 150 applies while two other processes recover, every one ok
- **Installs:** flags per package manager, exact pins, the environment, and one secret-name list shared with verify.
- **Acceptance:**
  - the environment, including the corepack cache
  - the manager run by its path
  - a missing script or npm's placeholder
  - offline mode end to end (loopback works, the network is gone, the wrapper's own failures not recorded)
  - a wall-clock step back
- **End to end,** from the bridge to the real server app in-process:
  - buy, apply, verify and the receipt
  - adapt and adapted-by-hand
  - a moved repository, with and without a profile change
  - a second worktree after a merge
  - sibling packages sharing a purchase
  - a pending purchase recovered first
  - no second offer for an owned release
  - an unrelated project at a reused path
  - a release the server lost
  - the running and unfinished answers
  - a missing test script, a profile that no longer fits, a Node pin mismatch
  - signing failure and retry, and retryable answers
  - the wallet-key refusal
- New tests were checked to fail on the code before each fix.

Reviewed in four rounds by independent reviewers who reproduced every finding before it counted; the fourth round's findings are fixed in these commits. Among the fixes:

- journals without a lock, with a racy claim, or undone under a live apply from another time zone or namespace
- rollbacks overwriting later edits, or repeating a done step
- a kept undo retried in the wrong package
- applies of different resolutions sharing manifests
- installs seeing wallet keys or running package code
- receipts from untested, unapplied, or no-longer-fitting changes, from a missing test script, or sent unsigned
- a pending purchase sending the agent back to preview
- offline mode recording its own failures as tests

gitleaks: no leaks (every commit).

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (bundles, release manifests by digest, server answers, journals and inbox records read back).
- [x] No secret can reach browser code, model context, logs, or committed fixtures. Wallet secrets are kept out of installs, and tests refuse to run while one is in the environment.
- [x] Paid paths remain idempotent and recoverable (one receipt per resolution, retries only where the server allows, a pending purchase recovered before anything else).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

Each has an issue draft in `pr-descriptions/issues/`, to open once this PR merges.

- Acceptance tests are the release's and the buyer's code running as the user. The network is on unless offline mode is used, writes are not confined to the package, and the real home is readable (issue 08). The buyer key belongs with a signer that runs as another user (handoff ask 9).
- Offline mode needs Linux, unprivileged user namespaces and the `ip` tool, and runs the tests as mapped root (issue 08).
- Tests run on the bridge's Node. A package pinned to another major is refused rather than tested (issue 01). Version-manager shims that need the user's HOME do not run (issue 02).
- A release manifest the server lost makes its purchase unusable here (issue 03).
- A moved repository is matched by package name and path, not its history (issue 04).
- Holders in other namespaces are judged by a heartbeat (issue 05).
- A bridge killed with SIGKILL leaves its install to the next start's recovery (issue 06).
- A few short release-chosen file names still reach the model (issue 07).
- A rollback cannot tell an interrupted install's change to package.json from an edit made after a crash. It puts the manifest back, and keeps and reports what it held.
