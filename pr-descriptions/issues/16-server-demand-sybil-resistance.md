# server: demand counts that one prober cannot inflate

**Open after:** `server/persistence-and-resolution-service` (P8) merges.
**Lane:** non-chain.

## Problem

Unmet-demand buckets are published once they have five distinct repositories and five distinct client addresses. A prober with many addresses and made-up profiles can still inflate a bucket, so demand is a roadmap signal only.

## Proposal

- Weigh demand by bridges that have bought before, or by previews followed by a purchase, and publish the weighted and raw counts apart.

## Done when

- The ranking used for "what to build next" cannot be moved by previews from addresses that never bought.
