# web: benchmark evidence and payment panes

**Open after:** `web/read-models-dashboard` (P12) merges.
**Lane:** non-chain for evidence; payment panes belong to the payment work.

## Problem

The dashboard's benchmark view has nothing to show until the first frozen report exists. The warranty, voucher and contract-link panes belong to the payment work.

## Proposal

- Show the first frozen report's verdicts and evidence as soon as it is committed.
- Leave the payment panes to the payment work, with read models it can extend.

## Done when

- The benchmark view renders a real report under the page's CSP, with no layout for missing data left in place.
