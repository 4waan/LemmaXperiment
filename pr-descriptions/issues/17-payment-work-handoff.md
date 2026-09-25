# Tracking: payment work handoff asks

**Open after:** the payment work starts on the seams in `HANDOFF-protocol-phase2.md`.
**Lane:** payment work.

## Problem

The payment lane's seams are specified in `HANDOFF-protocol-phase2.md`: the paid tool (`registerPaidTools`, `markPending` with the release digest, `ctx.recover()` after a lost response), receipt signing and signature verification, `SpendLedger.entriesFor`, draft bundles for the probe, release payload content, `economics.json`, and key custody in a signer that runs as another user.

## Proposal

- Open one issue per ask when the teammate picks it up; this issue only tracks them.

## Done when

- Every ask in the handoff document is either done or has its own issue.
