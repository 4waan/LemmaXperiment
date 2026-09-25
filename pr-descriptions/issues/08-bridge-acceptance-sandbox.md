# bridge: confine acceptance runs beyond the network

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

Acceptance tests are the release's and the buyer's code running as the user. Offline mode takes the network away on Linux, but writes are not confined to the package and the real home is readable. Offline mode also needs unprivileged user namespaces and the `ip` tool, and runs the tests as mapped root.

## Proposal

- Where available, run the tests under a sandbox (bubblewrap, or Landlock on Linux 5.13+): the package and a temporary directory writable, the rest of the filesystem read-only, the home directory hidden except the package manager's caches.
- Keep the current behaviour where no sandbox is available, and say so in the answer.

## Done when

- A test that writes outside the package, or reads a file in the real home, fails in the sandbox.
- The sandbox's own failures count as not started, as offline mode's do.
