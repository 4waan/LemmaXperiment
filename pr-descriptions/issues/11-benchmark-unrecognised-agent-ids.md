# benchmark: runs whose agent id the provider never recognises

**Open after:** `benchmark/harness-and-probe` (P10) merges.
**Lane:** non-chain.

## Problem

A run stays pending until billing for its agent id settles. An id the provider never recognises stays pending forever, which blocks the report. This fails closed on purpose.

## Proposal

- Add `benchmark abandon <version> <run>`: a person marks a run as failed with no cost, which the report shows and counts against the treatment or control as the protocol says.

## Done when

- A report with an abandoned run completes, lists it, and passes or fails by the protocol's rules.
