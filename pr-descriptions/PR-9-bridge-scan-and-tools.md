# bridge: workspace scan, server client, preview tool, inbox and rule

Branch `bridge/scan-and-tools` → `main`. **Stacked on the persistence PR** (`server/persistence-and-resolution-service`): review after it merges, or read only the last commit. One commit.

## What and why

Stage 3 (a free preview) becomes usable from a coding agent. The bridge runs next to the agent over stdio. It describes the repository without sending any code, asks the server for a preview, and checks locally whether a matching release would apply before anything is bought. It also holds the seams the payment work plugs its paid tool into, so neither lane blocks the other.

## Changes

- **Scan** (`apps/bridge/src/scan`):
  - Reads the nearest `package.json` and the nearest lockfile above it: allowlisted names, size-capped, never through a link.
  - Exact versions come from npm (v1 to v3), pnpm (v5.4, v6, v9) and yarn (v1, berry) lockfiles, without a YAML dependency.
  - Only registry ranges are looked up; `npm:` aliases, git, file, link and workspace installs are not.
  - Left out and noted, never guessed:
    - a version outside the declared range
    - conflicting lockfiles when `packageManager` does not choose one
    - anything else unresolved
  - Dependencies are filtered by the catalog's interest set (lever 6).
  - Frameworks, module system, language and the Node major complete the profile. The Node major comes from `.nvmrc` or `.node-version`, versions and LTS codenames, nearest pin first.
  - Results are cached by file stat.
- **Server client** (`LemmaRemote`):
  - One stateless MCP connection.
  - The interest set is refetched only when the catalog digest changes; base probes are cached per release.
  - Base-probe paths must be safe relative paths (core `PatchPath`).
  - Every request has a timeout, so a stalled server ends in "build it yourself".
- **`lemma_preview`**:
  - One server round trip.
  - Runs the drift probe locally before any purchase, sending no file content.
  - A named `package` must be a real package directory; otherwise the preview says so rather than scanning a parent.
- **Budgets:** tool answers are at most 600 characters built from enums and numbers, with no `outputSchema`. Tool definitions plus instructions stay under 3,000 characters. Tests enforce both.
- **Paid-tool seam** (`PaidToolContext`):
  - `latestOffer` hands out only the latest preview's offer, and only while it has no drift, has not expired by the monotonic or the wall clock, and is not already pending or bought.
  - An earlier preview never replaces a later one's answer.
  - `recover()` recovers after a lost paid response.
- **Inbox:**
  - Paid resolutions live in a private state directory, absolute and outside the workspace, compared as real paths.
  - Pending marks name their release.
  - A lost paid response is recovered for free, at startup or on request, and never bought twice.
- **The Lemma rule** (`lemma-mcp install-rule`): the rule file the benchmark treatment gets.
- **Trace** (optional, for the benchmark): one line per initialize and per tool call, including calls rejected for their arguments. Tool names only.
- **Docs:** bridge README (tools, budgets, recovery, scan rules) and architecture.

## Verification

```
npm run verify          # typecheck, test typecheck, 399 tests, build: all pass
```

- Scanner fixtures:
  - npm, pnpm and yarn in single-project and monorepo layouts
  - this repository's own lockfile
  - aliases and protocol specifiers
  - pnpm 5.4 peer suffixes
  - conflicting lockfiles
  - LTS codenames and the nearest pin
  - links refused at every level
- End to end, from the bridge to the in-process server: every catalog fixture's expected decision in one round trip. Budget tests cover characters and requests.
- Offers:
  - drift, a failed base probe, or a later failed preview leaves no offer
  - a pending or bought release gets no new offer
  - an offer expires by the wall clock
  - recovery on request works
- Remote: unsafe or oversized probe paths, a stalled server, and an older server's interest set.
- State directory: empty, relative, inside the workspace, and a link into it.

Reviewed in two rounds, each with independent reviewers who reproduced every finding before it counted. The second round's findings are fixed in this commit.

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (lockfiles, the server's answers, tool arguments).
- [x] No secret can reach browser code, model context, logs, or committed fixtures. No file content leaves the machine, and no catalog prose reaches the model.
- [x] Paid paths remain idempotent and recoverable (pending marks, free recovery, no second offer).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- `lemma_buy_resolution` belongs to the payment work. It must pass the release digest to `markPending` and call `ctx.recover()` after a lost response, never pay again.
- A dist-tag specifier such as `latest` resolves with no range check, because it is still a registry install.
