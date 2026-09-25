# catalog: loader, index, pack and check, fixtures, and release skeletons

Branch `catalog/loader-and-fixtures` → `main`. **Stacked on #P5** (`core/v1.0.1-mcp-and-helpers`): review after it merges, or read only the last commit. One commit.

## What and why

Economic gate 2, "Catalog and fixtures", becomes checkable. The catalog now loads, indexes, packs and validates releases, and one command, `npm run catalog:check`, refuses anything that must never be served. The resolver and preview server (next PR) and the benchmark harness build on this index, and the server runs the same check before it listens.

## Changes

- **`loadCatalog` / `loadCatalogResult`**
  - Manifests and bundles parse with the core schemas, and each release lives at `<releaseId>/<version>`.
  - The bundle digest must equal the manifest's `payloadDigest`, and no version appears twice.
  - One bad release does not hide problems in the others.
- **`buildIndex`** precomputes what the resolver and read API need:
  - the catalog digest
  - releases by capability, with semver ranges parsed once
  - per-capability interest sets, the only package names the bridge will send (lever 6)
  - base probes of every path a bundle touches, so the bridge can predict drift before paying without ever seeing content
- **`checkCatalog`** is read-only and independent of the clock. It checks:
  - `bundle.json` equals what `payload/` packs to, and the whole tree is scanned for links, special files and non-UTF-8 text.
  - Every range, in profiles and in bundle dependency changes, parses and is bounded above. Dist-tags such as `latest` and open ranges such as `*` are refused.
  - **Evidence ships as a new version** `X+<benchmarkVersion>` with the same `baseReleaseDigest` as `X`, so only evidence, price and dates may differ.
  - Reserved `probe-` and `provisional-` evidence never appears in `releases/`. Public evidence is refused until benchmark reports can be verified (they arrive with the harness).
  - Evidenced prices need measured economics, a non-zero `payTo`, and a price in `[price floor, maxPriceFor(evidence, g)]`.
  - Fixtures cover every release family and capability, and each fixture's reasons must be an answer the resolver can give.
- **`releases.provisional/`**: a testnet-only overlay of `X+provisional-N` versions. Stage 5 needs an offer and stage 6's treatment arm must buy one before frozen evidence exists. The server loads it only when explicitly allowed, and never in production.
- **`economics.json`**: dated inputs for chain cost `g`, the price floor and ETH/USD. It is marked `placeholder` until the payment work sets them. While it is a placeholder, no release may carry evidence.
- **Two skeleton releases**, `mcp-server-payment-gating` and `mcp-client-paying-client` at `0.1.0-skeleton`:
  - Placeholder payloads for the payment work to replace.
  - No evidence, a zero price and a zero `payTo`, so they can be previewed but never sold.
  - Provenance pinned to `coinbase/x402@dd927a26…` (Apache-2.0).
- **27 fixtures**: exact, boundary, near-miss (including prerelease and expiry), several unsupported cases (including multi-reason and above the Node range), and a no-release case for the facilitator capability.
- **Commands**
  - `catalog:check` and `catalog:pack` build first, then run.
  - `pack --write` replaces `bundle.json` through a temp file and a rename, never writing through a link.
  - `.gitattributes` stops line-ending conversion of hashed files.
- **Docs**: the catalog README, the fixtures, releases and overlay READMEs, and `docs/economic-gates.md` (price bound and the overlay).

## Verification

```
npm run verify          # typecheck, test typecheck, 261 tests, build: all pass
npm run catalog:check   # ok: 2 releases, 27 fixtures, 0 problems
```

Every rule has a test that breaks a copy of the catalog and expects the exact problem, including:

- a tampered bundle
- a stale payload
- unreferenced payload files
- symlinks anywhere in the tree
- a missing `releases/` directory
- an unbounded or unparseable range
- evidence on a base version
- an overlay that differs in more than price, dates and evidence
- reserved prefixes
- a price above `maxPriceFor` or below the floor
- placeholder economics
- a zero `payTo`
- missing fixture coverage
- impossible fixture answers
- BOM preservation
- writes through links

Reviewed by four lenses (rule bypasses, filesystem safety, fixture semantics, index and docs) with adversarial verification. Every finding is fixed in this commit, including the three that were confirmed:

- bundle ranges not checked
- `pack --write` following a link
- weak fixtures

A second pass checked the fixes. gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (catalog files are untrusted until checked).
- [x] No secret can reach browser code, model context, logs, or committed fixtures.
- [x] Paid paths remain idempotent and recoverable (n/a; nothing here can be sold).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Needs the owner's decision

- `packages/catalog/releases/README.md` gains a **testnet-only exception** to "no release may become purchasable until its measured savings evidence is frozen", for the provisional overlay that stages 5 and 6 need. The public service never loads it, and the `+provisional-N` suffix is visible in every preview.

## Limitations and follow-ups

- The payloads are placeholders. The payment work replaces them before any probe or benchmark.
- `economics.json` waits on HANDOFF item 4 (chain cost and price floor).
- Verifying public evidence against benchmark reports is wired up once the first frozen benchmark exists. Until then `catalog:check` refuses public evidence.

## Update: follow-up commits

1. `catalog: judge binary base files as bytes and report bad entries without hiding siblings`
2. `catalog: report payload faults once and completely, name bad entry names, hold the no-release rule while releases fail`
   - `packPayload(root, releaseDir)` names every fault by its path from the catalog root, as the scan does, so a fault that both see is reported once.
   - Only `payload/base/` is exempt from the UTF-8 scan, because base files are hashed as bytes. Every file in `payload/files/` that is not valid UTF-8 is reported.
   - The "no releases, so its only case is no-release" rule waits until `releases/` loads cleanly.
   - Each entry name that is not valid UTF-8 is reported under its own name.
3. A merge of the core follow-up (`core/v1.0.1-mcp-and-helpers`), so the stack above builds on it.

Verification: `npm run verify` (271 tests) and `npm run catalog:check` (2 releases, 27 fixtures, 0 problems) pass. Each new test fails on the previous commit.
