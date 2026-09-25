# bridge: run acceptance tests on the Node major the package pins

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

Acceptance tests run on the Node that runs the bridge. When a package pins another major (`.nvmrc`, `.node-version`), verify refuses and records nothing, because a receipt would claim a result for a Node the tests never ran on. A user whose bridge runs Node 22 cannot verify a Node 24 package without restarting the bridge on 24.

## Proposal

- Look for a Node of the pinned major where version managers keep them (nvm, fnm, Volta, asdf, mise), or take an explicit `LEMMA_NODE_<major>` path.
- Run the acceptance command with that Node first on the acceptance PATH.
- Keep refusing, with the same answer, when none is found.

## Done when

- A package pinned to another supported major verifies with a Node of that major when one is installed.
- The receipt's run used that Node (a test asserts `process.version` in the run).
- Without one, the answer and the no-receipt behaviour are unchanged.
