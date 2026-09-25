# bridge: stop installs when the bridge is killed

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

Installs run in their own process group and are killed when the bridge exits or is stopped by a signal. A bridge killed with SIGKILL leaves its install running until the next start's recovery kills it (only when it can be verified). Meanwhile the install can keep changing `node_modules` and the manifests.

## Proposal

- Run each install under a tiny supervisor that dies with its parent and takes the group with it (Linux `PR_SET_PDEATHSIG` through a helper, or a watcher that polls the parent pid on other systems).

## Done when

- Killing the bridge with SIGKILL during an install stops the install within a second, on Linux and macOS.
