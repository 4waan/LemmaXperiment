# catalog: measured chain cost and price floor

**Open after:** `catalog/loader-and-fixtures` (P6), with HANDOFF item 4 merges.
**Lane:** waits on the payment work.

## Problem

`economics.json` holds placeholder chain cost, price floor and ETH price. Pricing (`maxPriceFor`), the stage-4 verdict and the dashboard's all-in numbers all read it.

## Proposal

- Fill it from measured testnet settlements (gas per settlement, ETH/USD at a dated source), and set the price floor with the owner.

## Done when

- `economics.json` has `status: "measured"` with dated sources, and `catalog:check` passes with prices at or below `maxPriceFor`.
