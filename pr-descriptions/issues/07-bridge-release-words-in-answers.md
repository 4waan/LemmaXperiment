# bridge: fewer release-chosen words in agent answers

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

Answers carry bundle paths, which the release chooses. They are validated and capped (100 characters each, 40 per segment, 120 in all), so a release can still put a few short phrases in front of the model through file names.

## Proposal

- Find out from benchmark traces whether agents use the paths at all.
- If not, show counts only; if so, show paths only from the base probe the preview already checked, or with segments reduced to a fixed vocabulary.

## Done when

- A decision recorded in `docs/security-model.md`, with a test that holds the answer to it.
