# Handoff to the protocol lane, phase 2 (appends to HANDOFF-protocol.md)

The non-chain half of the product loop now exists on branches: catalog, resolver and free preview (server), persistence and `ResolutionService`, the bridge's scan and tools, apply and verify, the benchmark harness, and the dashboard. This note lists the seams your work plugs into and what the non-chain lane needs from you. Every seam is typed with `@lemma/core` schemas.

## Server: `ResolutionService` (`apps/server/src/service.ts`)

The server builds a new `McpServer` for every request (stateless Streamable HTTP; the SDK refuses to reuse a stateless transport). So the paid tool can be registered per request with terms from the preview the request names. The registrar `(server, service, { message })` gets the request's parsed JSON-RPC message: read `previewId` from it, call `quote`, and build `accepts` from the result. The registrar may be async. The server awaits it before dispatching, answers 500 if it throws, and never dispatches a call once the request has timed out. Every store failure reaches you as a `StoreError` carrying only a code (SQLSTATE or a connection code), safe to log as it is.

| Call | When | Contract |
| --- | --- | --- |
| `quote(previewId)` | Building `accepts` for the paid tool | `{ ok, terms: PaymentTerms, preview }`, or `NOT_FOUND`, `NO_OFFER`, `QUOTE_EXPIRED`. Use `terms` unchanged: they are x402 v2 `PaymentRequirements` fields. |
| `prepare(previewId, { payer, nonce, validBefore })` | Inside the paid tool's handler, before settlement | Values from the **verified x402 payload**, never from tool arguments. Writes one `prepared` row with a conditional insert. Returns `{ ok, resolution, bundle }`, or `IN_FLIGHT`, `ALREADY_SETTLED`, `PAYMENT_REUSED` (this authorization already backs another resolution), `QUOTE_EXPIRED`, `NOT_FOUND`, `NO_OFFER`, `PAYLOAD_MISSING`. **Answer every `ok: false` with `isError`**, which makes x402 cancel that settlement. Nonces are compared case-insensitively. |
| `commit(resolutionId, { nonce, settlementRef })` | In `hooks.onAfterSettlement` | Settles only the row that still holds that authorization, and one settlement settles one row. Never throws. **Do not throw anywhere in `onAfterSettlement`**: x402 runs it inside its `try`, so a throw tells a buyer who already paid that settlement failed. |
| `listUnsettled(before)` | The settlement reconciler | Prepared rows whose `validBefore` passed, with their payer and nonce. |
| `expire(resolutionId, nonce)` | The reconciler, once USDC `authorizationState` shows that authorization can no longer settle | Changes nothing unless the row still holds that nonce and its window has closed, so a stale decision never lands on a re-armed row. If the chain shows it **did** settle, call `commit` instead. |

The free `lemma_recover_resolution` tool is always registered: a buyer whose paid response was lost gets the delivery back with the preview id and the buyer address.

Paid results: return the `ResolutionDelivery` (`{ resolution, bundle }`) as **JSON text** in `content`, because the x402 MCP client returns only `content`, `isError` and `paymentResponse`. The bridge parses it with core schemas. Do not declare an `outputSchema` on the paid tool.

`PAID_TOOLS=on` makes `main.ts` refuse to start until your registrar is wired in (`createApp({ registerPaidTools })`).

## Bridge

- **`registerPaidTools(server, ctx: PaidToolContext)`** (`apps/bridge/src/bridge.ts`): register `lemma_buy_resolution` there.
  - `ctx.latestOffer(capability)` returns the latest preview with a still-open offer (expiry is tracked on a monotonic clock). Buy only that offer.
  - Store the delivery with `ctx.inbox.put(delivery)`. It refuses a bundle whose digest is not the resolution's `payloadDigest`, and clears the pending mark.
  - Answer the agent in at most 600 characters, built from enums and numbers only (see `text.ts`), with no `outputSchema`.
  - Call `ctx.inbox.markPending(previewId, buyer, now, releaseDigest)` **before** signing: the release digest makes the bridge hold back any new offer for that release while the purchase is pending or stored.
  - After a lost or failed paid response, call `await ctx.recover()`. **Never pay again**; recovery is free.
- **Receipts** (`apps/bridge/src/adoption.ts`):
  - `adoptionTools({ signReceipt })` takes your signing hook, `(receipt) => Promise<signature | null>`. Sign `adoptionReceiptDigest(receipt)` with the typed-data layout you define (EOA, ERC-1271 or ERC-6492 bytes all fit `SignatureBytes`).
  - If the hook throws, the bridge keeps the receipt and never sends it unsigned, because the first write wins on the server. It tries signing again at the next verify.
  - The bridge posts `{ receipt, previewId }` to `POST /api/v1/adoption-receipts`; the preview id proves the submitter is the buyer. The server stores it with `verified: false`.
  - `NOT_SETTLED` and `TOO_EARLY` answers are retried.

## What the non-chain lane needs from you

1. **Map every `prepare` refusal to `isError`**, and pass the verified payer, nonce and `validBefore` to `prepare`.
2. **Never throw in `onAfterSettlement`**; call `commit(resolutionId, { nonce, settlementRef })` there.
3. **A reconciler** over `listUnsettled` that checks each authorization on chain and calls `expire(resolutionId, nonce)` or `commit`.
4. **Decide the nonce strategy, and do not make the nonce the resolution id itself.** A deterministic nonce per resolution lets USDC refuse a second payment for it. But the resolution id is public (the server's resolution view is keyed by it), and USDC publishes the nonce next to the payer's address, so the two together would let anyone join a wallet to the release it bought and its adoption outcome. Derive the nonce from the resolution id and the preview id (a secret the bridge and the server share), for example `keccak256(resolutionId, previewId)` under its own digest kind. With random nonces instead, the server's `PAYMENT_REUSED` check and the reconciler still prevent double delivery, but two authorizations for one resolution could both reach the chain.
5. **Build `accepts` per request from `quote`**, and return paid results as JSON text.
6. **Receipt verification.** Verify a stored receipt's signature against the resolution's payer and mark it verified. The store needs a small `markReceiptVerified(resolutionId, receiptDigest)`; add it with your verifier, or ask and we will. Compatibility history (lever 7) counts only verified receipts.
7. **Export `SpendLedger.entriesFor(resolutionId)`** (amount, gas, transaction). The benchmark harness fills `RunRecord.payment` from it through its `PaymentSource` seam (`packages/benchmark/src/runner.ts`).
8. **Draft bundles for the stage-4 probe.** The two catalog releases (`mcp-server-payment-gating`, `mcp-client-paying-client` at `0.1.0-skeleton`) carry placeholder payloads. A draft bundle for either lets us run `benchmark probe` and get a go or kill verdict with the price to pre-register.
9. **Keep the buyer key out of the bridge's environment.** The bridge runs repository code as descendants (dependency installs with scripts disabled, and acceptance tests, which are the release's and the buyer's own test code). Any process of the same user can read the environment a process started with from `/proc/<pid>/environ`, so a `BUYER_PRIVATE_KEY` environment variable is readable by those descendants however clean their own environment is. A key file the user can read does not help either, because acceptance tests run as that user and can read it. Keep the key with a signer process that runs as another user (the bridge asks it to sign `adoptionReceiptDigest` and payment authorizations), or on a hardware or remote signer. **This is enforced:** `lemma_verify_adoption` refuses to run tests while the bridge's environment, or the one it started with, holds a wallet secret, and installs never receive one. The names are one list, `WALLET_SECRET` in the bridge's `secrets.ts`: private and signing keys, mnemonics, seed and recovery phrases, and the key, secret, password, passphrase, seed or private key of a wallet, signer, buyer or deployer. Name the key so that it matches, and never pass it under another name.
10. **Fill `packages/catalog/economics.json`**: chain cost `g` per resolution (every on-chain action, whoever pays), the price floor, and ETH/USD for gas accounting. While it says `placeholder`, `catalog:check` refuses any evidence, so nothing can be sold.

## Facts checked in the installed packages

- x402 2.27.0: an `isError` handler result cancels settlement; `onAfterSettlement` runs inside the `try`; the stock EVM client picks a random nonce; `initialize()` fetches the facilitator's `/supported`.
- MCP SDK 1.30.1: a client validates `structuredContent` against a declared `outputSchema`, even on errors; a bare union as `outputSchema` is dropped.
