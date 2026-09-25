# benchmark: first probe run with a real draft bundle

**Open after:** `benchmark/harness-and-probe` (P10), with a draft bundle from the payment work (HANDOFF ask 8) merges.
**Lane:** non-chain, waits on the payment work.

## Problem

The stage-4 probe decides go or kill per release family from three control runs and one pre-applied treatment. It has only run against fake adapters. Treatment payments also need `SpendLedger.entriesFor` (HANDOFF ask 7).

## Proposal

- Run the probe by hand with a real key on a pipe, for `mcp-server.add-payment-gating`, and commit the verdict and its provisional price.

## Done when

- A committed probe verdict with its runs, and the pre-registered price in the catalog's provisional overlay.
