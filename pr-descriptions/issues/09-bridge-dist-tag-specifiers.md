# bridge scan: range-check dist-tag specifiers

**Open after:** `bridge/scan-and-tools` (P9) merges.
**Lane:** non-chain.

## Problem

A dependency declared with a dist-tag (`latest`, `next`) is looked up like any registry range, and the version the lockfile installed is used with no check against the declared specifier, because a tag has no range.

## Proposal

- Treat a dist-tag specifier as resolved only through the lockfile, and note it in the profile notes, as other unresolved cases are.

## Done when

- A scan fixture with `"latest"` gives a noted, lockfile-backed version, and the preview says the profile was read with a note.
