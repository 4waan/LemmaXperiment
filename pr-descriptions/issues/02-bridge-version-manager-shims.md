# bridge: package managers behind version-manager shims

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

Acceptance runs get a fresh `HOME`. Corepack shims work because the bridge points `COREPACK_HOME` at the user's cache. Volta, asdf and mise shims also find their tools through the user's home, so under a fresh `HOME` they fail: verify reports the manager as unusable and suggests putting a real one on the bridge's PATH.

## Proposal

- Pass each version manager's own setting when it is set, or its default under the real home, as with `COREPACK_HOME`: `VOLTA_HOME`, `ASDF_DATA_DIR`, `MISE_DATA_DIR`.
- Or resolve a shim to the binary it would run, once, before the run.
- Document which managers are supported.

## Done when

- With a Volta, asdf or mise shim first on the bridge's PATH, the manager check passes and the tests run.
- The tests can read no more of the real home than the version manager's own data directory.
