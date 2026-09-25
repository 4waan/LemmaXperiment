# bridge: recognise a moved repository by its history

**Open after:** `bridge/apply-and-verify` (P11) merges.
**Lane:** non-chain.

## Problem

A purchase is matched to a package by directory, or, once that directory is gone, by the same `package.json` name at the same path in the workspace, and the package must still fit the profile it was bought for. Two unrelated projects with the same package name and layout (template names such as `web` or `api`) can still match after the first is deleted.

## Proposal

- Record the repository's root commit (the first commit of `git rev-list --max-parents=0 HEAD`, read from `.git` without running git if possible) with each package reference.
- Require it to match, when both sides have one, before a moved package inherits a purchase.

## Done when

- A clone or a moved copy of the same repository keeps its purchases.
- An unrelated repository with the same package name and path does not.
