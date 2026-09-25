# benchmark: find the Cursor key in any of the user's shells

**Open after:** `benchmark/harness-and-probe` (P10) merges.
**Lane:** non-chain.

## Problem

Commands that run agents refuse to start while their environment, or an ancestor's, holds anything that looks like a credential. A shell that started the harness in the background, or another terminal of the same user, keeps its own copy, which the agent's shell tool could read through `/proc`.

## Proposal

- Scan the environments of every process of the user that `/proc` shows, not only ancestors, and refuse while any holds a credential.

## Done when

- A harness started while another terminal of the user has `CURSOR_API_KEY` exported refuses to run, and says which process holds it.
