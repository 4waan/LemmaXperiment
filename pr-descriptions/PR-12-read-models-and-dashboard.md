# web: read models and dashboard

Branch `web/read-models-dashboard` → `main`. **Stacked on the persistence PR** (`server/persistence-and-resolution-service`): review after it merges, or read only the last commit. One commit. It does not depend on the bridge PRs.

## What and why

Buyers, reviewers and the team need to see what Lemma sells, why a profile can or cannot be sold, what a resolution did, and what demand Lemma cannot serve yet. This PR adds typed read models in core, server read routes built on them, and a static dashboard that renders only from those models.

## Changes

- **Core read models** (`packages/core/src/read.ts`):

  | Model | What it holds |
  | --- | --- |
  | `ReleaseSummary` | Per profile: sellable, or its blocker; an evidence label (benchmarked, provisional, none); the all-in reduction at the list price after chain cost; `maxPriceFor`. |
  | `CatalogView` | The catalog as the dashboard shows it. |
  | `ResolutionView` | A resolution as anyone may see it: never the preview id, the buyer, the bundle or the settlement reference. |
  | `DemandKey`, `DemandView` | Demand buckets with distinct repositories and distinct client addresses; only buckets with at least five of each are published. |
  | `StatusView` | What the status view reports. |

  `rankUnmetDemand` builds the "what to build next" list from `DemandView`.
- **Server:**
  - `GET /api/v1/catalog`.
  - `GET /api/v1/status`, which reports `degraded` when the store does not answer.
  - Demand served as parsed keys.
  - Failures and 404s are never cached.
  - The server serves the built dashboard: only regular files with Vite's hashed names and an allowlisted extension, never through a link.
  - The page's CSP allows scripts, styles, fonts, images and API calls from this origin only, with no inline code, framing, forms or base URI.
- **Dashboard** (`apps/web`):
  - Views: overview and setup, capability catalog with per-profile evidence, resolution detail, benchmark evidence, unmet demand, status.
  - Every response is parsed with the core schemas before it is rendered.
  - Rendering uses React escaping only, with allowlisted links and testnet, provisional and probe labels.
  - zod runs without code generation, so the CSP needs no `unsafe-eval`, and assets are never inlined.
  - `check-dist` refuses a build with inline script, `eval`, source maps or unexpected files.
- **Docs:** web and server READMEs, architecture, deployment (the image copies `apps/web/dist`).

## Verification

```
npm run verify          # typecheck, test typecheck, 382 tests, build (with check-dist): all pass
```

- Read models: summaries at list price with and without evidence, expired releases, provisional labels, and the unmet-demand ranking.
- Server:
  - catalog, status (including degraded) and demand as parsed keys
  - unreadable demand keys left out
  - no caching of failures
  - dashboard serving: hashed names only, no links, the exact CSP
- Dashboard: views render from fixtures parsed with the core schemas, and switching views never mixes data.
- Checked in a browser against the built page: every view renders under the CSP with no violations.

Reviewed with independent reviewers who reproduced every finding before it counted. All findings are fixed in this commit.

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (every API response is parsed in the browser).
- [x] No secret can reach browser code, model context, logs, or committed fixtures. Read models never carry preview ids, buyers or bundles.
- [x] Paid paths remain idempotent and recoverable (n/a; read-only).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- The warranty, voucher and contract-link panes belong to the payment work.
- Benchmark evidence shows once the first frozen report exists.
