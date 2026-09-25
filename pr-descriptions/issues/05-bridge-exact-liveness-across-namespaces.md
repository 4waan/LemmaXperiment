# bridge: exact liveness for journal holders in other namespaces

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

A journal holder is recognised by pid and start time within its pid and time namespaces and boot. A holder in other namespaces (a container or a sandbox that shares the state directory) is judged by how recently its owner file was refreshed: running within a minute of the last refresh, and its install counted as ended 15 minutes after. A holder that is stalled for more than a minute, or an install that outlives its bridge by more than 15 minutes, is misjudged.

## Proposal

- Hold a lock the kernel releases on exit: an `flock` or `fcntl` lock on the owner file through a small helper process, or a lock held by the bridge itself if Node gains the API.
- Keep the heartbeat as the fallback where locks are unavailable (some network filesystems).

## Done when

- A live apply in another pid namespace is never rolled back, however long it stalls.
- A dead one is recovered at the next start without waiting a minute.
