# server: persistence, ResolutionService and demand

Branch `server/persistence-and-resolution-service` → `main`. **Stacked on the resolver and preview server PR**: review after it merges, or read only the last commit. One commit.

## What and why

The free path already works in memory. This PR makes it durable and gives the payment work a narrow, crash-safe seam to wrap x402 around, so neither lane blocks the other. It also starts counting demand, including the demand Lemma cannot serve yet, as the input for what to build next.

## Changes

- **Postgres through drizzle** (`apps/server/src/db`), with postgres.js in production and PGlite in tests. Every hashed object is stored as canonical JSON next to its digest and re-parsed with its core schema when read.

  | Table | Rule |
  | --- | --- |
  | `releases`, `bundles`, `catalog_snapshots` | Immutable copies keyed by digest, upserted at startup, so a redeploy never strands an offer or a recovery. |
  | `previews` | Offer-bearing previews only, purged a day after expiry unless a settled resolution needs them. |
  | `resolutions` | One row per `deriveResolutionId(previewId, payer)`: `prepared → settled`, or `expired` by the reconciler, then re-armable. One authorization (payer and nonce) backs one row and one settlement settles one row (unique indexes). |
  | `adoption_receipts` | One per settled resolution, submitted by the buyer, `verified: false` until the payment work checks its signature. |
  | `demand_seen`, `demand_salts`, `demand_daily` | Salted profile digests and salted client addresses per bucket and day, collapsed to counts when the day closes; the salt is discarded. |

- **`ResolutionService`**, the seam for the payment work:
  - `quote(previewId)`: the stored offer's exact `PaymentTerms`.
  - `prepare(previewId, { payer, nonce, validBefore })`: one conditional insert. A second payment for the same resolution gets `IN_FLIGHT` or `ALREADY_SETTLED`, and an authorization that already backs another resolution gets `PAYMENT_REUSED`; the wrapper answers `isError`, so x402 cancels that settlement.
  - `commit(resolutionId, { nonce, settlementRef })`: settles only the row that still holds that authorization, and never throws.
  - Store failures reach the payment work as a `StoreError` that carries only a code (SQLSTATE or a connection code), never SQL, parameters or a connection string.
  - `listUnsettled(before)` and `expire(resolutionId, nonce)` for the reconciler; a stale decision never lands on a re-armed row.
  - `recover(previewId, buyer)`: settled resolutions only, for the free recovery tool.
  - `registerPaidTools(server, service, { message })` runs per request with the parsed message, so the payment work can quote the preview a paid call names. It may be async: the server awaits it before dispatching, answers 500 if it fails, and never dispatches a call after the request timed out.
- **Read API**: `GET /api/v1/resolutions/:id` (a public view without the preview id, buyer or bundle), `POST /api/v1/adoption-receipts` (`{ receipt, previewId }`: only the buyer can submit; `TOO_EARLY` and `NOT_SETTLED` are retryable, and five minutes of clock skew is allowed either way), `GET /api/v1/demand` (buckets with at least five repositories from at least five client addresses).
- **Demand**: every preview is counted, offer or not. Recording never fails or stalls a preview (bounded to 250 ms). Client addresses are keyed with `DEMAND_SOURCE_KEY` (required in production, never stored in the database) before they are salted, so a database backup cannot recover them. Recording and closing a day serialize on a per-day advisory lock: nothing is counted twice, and a closed day never gets a new salt. Each day closes on its own, with a five-minute statement limit.
- **Operations**:
  - Migrations are generated into `apps/server/drizzle/` and applied by `node apps/server/dist/migrate.js` (deployment step 3). The server refuses to start while the schema is behind, and reports an unreachable or unreadable database as that.
  - `DATABASE_URL` accepts any `postgres://` or `postgresql://` string and is never printed. Connecting times out after 10 s and Postgres cancels request statements after 5 s; a partitioned database is not bounded by either (documented), though the request still answers 504.
  - Errors are logged by name and code only (SQLSTATE, or a connection code such as `ECONNREFUSED`), never by message, because drizzle's messages carry query parameters. Startup names an unreachable database, an unparseable `DATABASE_URL`, an unreadable migration journal and a failed catalog save as such.
  - Housekeeping closes demand days and purges expired offers hourly, each step on its own.
  - A new CI job runs the race and migration tests on a real Postgres service container, pinned by digest.
- **Docs**: server README (tables, seam, routes), architecture (the seam), deployment (migration step, database behavior), security model (receipts, payment binding, k-anonymous demand and its limit), economic gates (demand threshold).

## Verification

```
npm run verify          # typecheck, test typecheck, 358 tests, build: all pass
LEMMA_TEST_DATABASE_URL=... npx vitest run apps/server/test/postgres.test.ts   # 5 tests on Postgres 16
```

- One contract suite runs against the memory store and PGlite: quotes, one prepare per resolution, `PAYMENT_REUSED` (including nonce case), re-arm after expiry, stale expire and settlement refused, one settlement per resolution, `commit` never throwing, receipts only from the buyer and only once, demand counts and thresholds (a single caller's made-up profiles stay hidden), late writes after a close, and purge rules.
- Real Postgres: 20 concurrent payments for one resolution leave exactly one `prepared` row; one authorization across 10 concurrent resolutions backs exactly one; closes racing late writes of already-counted pairs count a day exactly once and leave no salt, ten times over; sixteen concurrent first writes of a day are all kept; a rolled-back first write never makes a profile count twice; migrations apply to an empty database. Each of these fails on the code before the fix.
- HTTP: receipts (404 for a wrong preview id, 400 for a malformed body, 500 when the store fails, 403 from a browser, 425 for a future-dated receipt), a stalled demand write not delaying a preview, recovery answering fixed text when the store fails, an async registrar, and no dispatch after a timeout.

Reviewed in three rounds, each with independent reviewers who reproduced every finding before it counted, and a check of each round's fixes:

- receipt slots anyone could take with a public resolution id
- one authorization able to back two resolutions
- a stale reconciler decision landing on a re-armed row
- demand closes that double-counted under concurrency or with late writes, and could publish buckets below five
- made-up profiles defeating the five-repository threshold
- client addresses recoverable from the database by brute force
- a demand salt cached before its transaction committed (dropped writes, double counts)
- a stalled database failing free previews
- query parameters and connection strings reaching logs, callers and the payment work
- a paid-tool registrar that was not awaited
- receipts from a buyer with a skewed clock being refused for good

Not fixed, documented: a demand day too large to close in five minutes would fail on every hourly run and needs batching.

gitleaks: no leaks.

## Checklist (CONTRIBUTING.md)

- [x] The change stays within the MVP boundary.
- [x] New input is validated at its trust boundary (receipts, environment, stored rows are re-parsed).
- [x] No secret can reach browser code, model context, logs, or committed fixtures.
- [x] Paid paths remain idempotent and recoverable.
- [x] Unsupported profiles remain free.
- [x] Tests cover success, failure, expiry and no-match behavior.
- [x] Documentation describes new assumptions and limitations.

## Limitations and follow-ups

- Receipt signatures are verified by the payment work; until then every receipt stays unverified and counts for nothing in compatibility history.
- Demand thresholds count distinct client addresses; a prober with many addresses can still inflate counts, so demand is a roadmap signal only.
- The MVP runs one replica; the database removes the in-memory limits, and the day close and payment state are safe under concurrency.
- `drizzle/0000_initial.sql` is the first migration; any local database built from an earlier draft of this branch needs a reset.
