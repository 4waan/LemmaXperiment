# catalog: check public evidence against frozen benchmark reports

**Open after:** `catalog/loader-and-fixtures` (P6), after the first frozen benchmark merges.
**Lane:** non-chain.

## Problem

`catalog:check` refuses public evidence until a frozen benchmark report exists to back it. Checking evidence against reports (the same base release digest and the same derived numbers) is wired but has nothing to check yet.

## Proposal

- Once the first frozen report is committed, enable the check, and add the first evidenced release version (`X+<benchmarkVersion>`).

## Done when

- `catalog:check` passes with the first evidenced release and fails when its evidence differs from the report by any number.
