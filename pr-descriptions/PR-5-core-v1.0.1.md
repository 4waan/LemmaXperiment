# core v1.0.1: fix MCP schema conversion; add price bound, evidence binding and apply planning

Branch `core/v1.0.1-mcp-and-helpers` → `main`. One commit. No hashed shape changes: every frozen vector is unchanged, and one derived vector is added.

## What and why

`tools/list` fails today for any MCP tool that takes a `RepositoryProfile`, which includes `lemma_preview`. MCP clients read tool input schemas as draft-7 JSON Schema converted from the input side, and the dependency cap was written as `z.custom().pipe()`, which cannot be represented. The call fails with `-32603 Custom types cannot be represented in JSON Schema`.

This PR fixes that. It also adds the pure helpers the next PRs build on:

| Helper | Used by |
| --- | --- |
| `maxPriceFor` | catalog prices and the stage-4 probe |
| `baseReleaseDigest` | evidence binding |
| `planApply` | the bridge and the probe |
| `RecoverInput` / `ResolutionDelivery` | recovery |

## Changes

- **MCP fix.** The dependency cap is now a `z.preprocess` step. It still runs before any entry is parsed (a test proves an oversized map yields exactly one issue), and it publishes `maxProperties: 500`. A regression test converts `PreviewInput` exactly as the SDK does (`io: "input"`, `target: "draft-7"`) and lists and calls the tool through a real `McpServer` and `Client`.
- **`maxPriceFor(evidence, { chainCostAtomic, targetBps })`.** Returns `min(floor(3S/10), S - g - ceil(target * C / 10^4))`, floored at 0.
  - It is the highest price that is sellable and still leaves the buyer the 25% all-in target after chain cost.
  - `g` has no default.
  - A fast-check property (2,000 runs) pins it as exactly the largest valid price.
- **`allInReductionBps` rounds toward negative infinity.** The property test found that truncation reported a -0.9999 bps cost increase as 0. It now reads -1.
- **`baseRelease` / `baseReleaseDigest`** (new digest kind `release-base`).
  - The release without evidence, build metadata, price or dates.
  - Evidence ships as a new version `X+<benchmark>`, and `X`, `X+provisional-N` and `X+bench-1` share one base, so evidence stays bound to what was measured while the price may follow the evidence.
- **`catalogDigestOf(releaseDigests)`** gives the same catalog digest from precomputed release digests.
- **`planApply(bundle, state)`** is a pure drift planner.
  - An add needs an empty path whose parents are directories.
  - A modify or delete needs the file its `baseDigest` names.
  - Everything else is reported as drift, with nothing planned.
- **Recovery seam.**
  - `LEMMA_TOOLS.recoverResolution` names the free tool.
  - `RecoverInput` is `{ previewId, buyer }`: the preview id is the bearer secret, and a public resolution id recovers nothing.
  - `ResolutionDelivery` is `{ resolution, bundle }`, and the bundle must be the one the resolution names.
- **Digestible text.** `SafeText` and patch content refuse lone UTF-16 surrogates, so every value that parses can be digested. `ResolutionDelivery.safeParse` never throws.
- **Docs.** `packages/core/README.md`. `docs/architecture.md`: recovery by preview id and buyer. `docs/economic-gates.md`: the stage-4 gate uses `maxPriceFor`.

## Verification

```
npm run verify    # typecheck, test typecheck, 230 tests, build: all pass
```

- Reproduced the bug first: `tools/list` returned `-32603` with the old schema. The new round-trip test lists and calls the tool.
- The frozen vectors are unchanged. The new `baseReleaseDigest` vector was recomputed independently in Python (pycryptodome keccak over sorted-key JSON): `0x1dc49fab…1188`.
- The fast-check property for `maxPriceFor` holds over 2,000 random cases, checking both that the returned price works and that price + 1 does not.
- Reviewed by four independent lenses (arithmetic, zod/MCP interop, semantics, tests and docs), with each finding checked by three adversarial verifiers. All confirmed findings are fixed in this commit:
  - `baseRelease` excluding commercial terms
  - lone surrogates making `safeParse` throw
  - parent-path drift in `planApply`
  - doc accuracy
- gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (`RecoverInput` is strict; `ResolutionDelivery` checks the bundle digest).
- [x] No secret can reach browser code, model context, logs, or committed fixtures.
- [x] Paid paths remain idempotent and recoverable (the recovery key is defined here).
- [x] Unsupported profiles remain free (unchanged).
- [x] Tests cover success, failure and edge cases (price bound at every boundary, drift, lone surrogates, oversized maps).
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- `ResolutionDelivery` parsing hashes the bundle, which takes about 170 ms for a 2 MB bundle. That is fine for the rare recovery path.
- The catalog (next PR) uses `maxPriceFor`, `baseReleaseDigest` and `catalogDigestOf`. The resolver and server use the recovery seam. The bridge and the benchmark probe share `planApply`.

## Update: follow-up commit

`core: refuse patches to install-steering files; do not advise the resolution id as the payment nonce`

- `PatchPath` also refuses `npm-shrinkwrap.json`, `pnpm-workspace.yaml` (its overrides steer pnpm) and bun's lockfiles, so a bundle cannot change what the install that applies its dependency changes resolves.
- The resolution id keys a public view, so using it as the EIP-3009 nonce would let anyone link a wallet to what it bought. The docs now advise a nonce derived from the resolution id and the preview id instead.
