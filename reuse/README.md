# reuse/

Owner: clean worker. The decisive test after acceptance.

## Procedure

1. Pick a supported input outside both development and holdout sets. Done
   before any measured use: block 20600928, recorded in `input.json` by
   `input.py` (lowest gasUsed of the 1000 blocks after the baseline, inside
   the holdout rule's exclusion margin, so disjoint from set 1 without opening
   sealed material). 20600066 is a development block and is not eligible.
2. Fund a fresh UsageEscrow job.
3. In a clean worker process/account, install the immutable accepted release
   using only its `integrationInstructions`.
4. Generate a new runtime proof, submit it on Robinhood Chain testnet
   (chain 46630), collect worker compensation and contributor fee in one
   settlement.

## Rules

- No source edits and no human-written replacement implementation.
- New code means a new version and a new evaluation.
- Log any installation assistance.
- Run the baseline on the same input if claiming continued savings.
- Report regressions even when payment succeeds.
- Disclose if creator and worker share an operator.

## Expected contents

```text
reuse/
  input.py            selection rule for the fresh input
  input.json          identity of the fresh input, recorded before use
  install-log.md      steps taken, assistance logged
  job.json            escrow job snapshot and tx hashes
  proof/              public values and proof bytes
  baseline-run.md     optional comparison on the same input
```
