# resolver and server preview path

Branch `resolver/preview-server` → `main`. **Stacked on the catalog PR** (`catalog/loader-and-fixtures`): review after it merges, or read only the last commit. One commit.

## What and why

Economic gate 3, "Free preview", works end to end on the server. Given a typed task and a privacy-safe repository profile, the resolver returns a free, deterministic decision (reuse, build or decline) with its reasons, and an offer only when the matched profile can be sold. The server exposes it over stateless MCP for the bridge, with the read API the bridge and dashboard need.

## Changes

- **`resolve()`** in `@lemma/catalog`, so `catalog:check`, the server and the benchmark share one implementation. It is pure: the clock, preview id and payment settings are injected.
  1. No release for the capability: `build` with `NO_RELEASE_FOR_CAPABILITY`. The task is in scope, and demand records it.
  2. Every supported profile of every candidate is checked in a fixed order, collecting codes: expiry, language, runtime, package manager, module system, dependencies, frameworks.
  3. Matches are ranked by a published total order: sellable now, then expected net saving `S − P`, then semver precedence, release id, release digest and profile index. **This amends lever 8 in `docs/economic-gates.md`.**
  4. The top match is `reuse`. Its offer carries the release's price and `payTo`, the evidence's saving, the configured network and asset, and `validUntil = min(now + ttl, expiresAt, evidence.staleAfter)`. When a sale blocker applies, there is no offer and the blocker is the reason.
  5. Without a match, the nearest candidate (fewest distinct codes, then a supported platform first, then identity order) gives the reasons. Any `UNSUPPORTED_*` code means `decline`; otherwise `build`.
  6. The result is validated with `Preview.parse`, failing closed. The resolver never emits `adapt`: the bridge decides that from drift.
- **Golden replay.** `catalog:check` runs every fixture through the resolver at its pinned instant and reports any mismatch.
- **Server** (`apps/server`):
  - `config.ts`: zod-validated environment. Addresses are normalized, the chain must be Arbitrum Sepolia, TTL and timeout are bounded, `PAID_TOOLS` is off by default, and `DATABASE_URL` is required in production.
  - `createApp(deps)`: every dependency injected and tested through `app.request()`. `main.ts` is the new entry point, and the Dockerfile and `railway.toml` start it.
  - `POST /mcp`: a new stateless `McpServer` and transport per request, with JSON responses. `GET` and `DELETE` return 405. Batches (400, -32600), parse errors (-32700) and browser-originated requests (any `Origin`) are refused.
  - Tools: `lemma_preview` (`PreviewInput` → `PreviewResult`), stored before it is returned when it carries an offer; and the free `lemma_recover_resolution`, registered even with paid tools off. Errors are text only.
  - Read API: `/api/v1/releases`, `/api/v1/interest` (`ETag` = catalog digest), `/api/v1/releases/:digest/base-probe` (immutable), `/healthz`.
  - Middleware: 256 KB body limit, security headers, CORS limited to the dashboard origin (before the limiter, so a 429 is readable), a request timeout that answers 504, and a token-bucket rate limit keyed on the trusted proxy hop's address (IPv6 per /64).
  - Startup refuses a failing `catalog:check`, a release that pays anyone but the configured provider, and `PAID_TOOLS=on` without the payment work's registrar. SIGTERM closes the server cleanly.
  - The in-memory offer store is bounded: expired offers are swept when it fills, and beyond the cap a preview says so instead of growing the process.
- **Docs**: server README (interfaces and environment), architecture (stateless MCP, single replica for now), deployment (start command, `PAID_TOOLS`), security model (preview ids as bearer secrets), economic gates (lever 8).

## Verification

```
npm run verify          # typecheck, test typecheck, 320 tests, build: all pass
npm run catalog:check   # ok: 2 releases, 27 fixtures, 0 problems
```

- Golden: every catalog fixture replays to its expected decision.
- fast-check properties: determinism, catalog-order independence, a dependency outside the interest set never changes the decision, an offer exists exactly when there is no sale blocker, and no failing check ever yields `reuse`.
- Cost: each dependency range is tested at most once per candidate profile, and nothing is parsed per call (an operation-count test, not a timing test).
- HTTP: `tools/list` and `tools/call` through a real MCP client, 405 on `GET /mcp`, batch and parse-error answers, 413, 429 with CORS headers, 504 on a slow store, a failed store giving a text-only error, proxy-address handling, and startup refusing a foreign `payTo`.

Reviewed by two lenses (resolver semantics, HTTP surface) with adversarial verification. Every confirmed finding is fixed in this commit:

- nearest-candidate choice flipping decline and build on tie-breaks
- JSON-RPC batches multiplying the rate limit
- an unbounded memory offer store
- IPv6 clients evading the limit, and client-supplied forwarding entries
- CORS headers missing on 429
- timeouts answering 500 instead of 504
- no SIGTERM handling
- an unparseable version crashing the golden replay
- a doc claim that did not match the code

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (MCP arguments, environment, catalog).
- [x] No secret can reach browser code, model context, logs, or committed fixtures (preview ids are never logged).
- [x] Paid paths remain idempotent and recoverable (recovery is free and always registered).
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Needs the owner's decision

- **Lever 8's ranking order** in `docs/economic-gates.md`: sellable first, then expected net saving, then version and identity. Pass rate slots in after "sellable" once verified receipts exist.

## Limitations and follow-ups

- Offers live in process memory in this PR; the persistence PR stores them in Postgres. Until then the MVP runs one replica.
- Paid tools are the payment work's; the server refuses `PAID_TOOLS=on` without them.
