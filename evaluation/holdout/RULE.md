# Holdout selection rule, set 1

EXPERIMENT.md section 4 step 4. This rule is frozen before any randomness
is drawn; `holdout.py` implements it and `commitment.json` records the
public side of the commitment. The chosen blocks are known only to the
evaluator until the final evaluation is signed.

## 1. Domain

- Chain: Ethereum mainnet, `chainId` 1.
- Supported range S = [19426587, 22431083], the Cancun era: from the
  Cancun activation block to the block before Prague activation (22431084).
  This is the range the pinned host reproduces in full
  (`apparatus/pins.json` `fixtures.forkSupport.supportedRange`,
  `apparatus/FAILURES.md` #10).
- A holdout set is a window of ten consecutive block numbers
  [start, start + 9] with both ends inside S. There are
  M = |S| - 9 = 3004488 possible starts.
- Exclusion set X: every block the apparatus or the public development
  corpus executed, widened by 1000 blocks on each side:
  18884864, 20600000, 20600066, 22441128, 23945771, 23985839, 25988970,
  25988980. A window that contains any block of X is rejected. Only
  20600000 and 20600066 lie inside S; the others are listed so the rule
  does not depend on the range.

## 2. Salt

The salt has two parts so that nobody can grind it after the rule is public.

- `preSalt`: 32 bytes from the evaluator machine's CSPRNG. Its sha256 is
  published in `commitment.json` (phase `precommit`) and pushed to the
  public repository before the beacon block exists.
- `beacon`: the canonical hash of mainnet block `beaconBlock`. The block
  number is published in the same precommit and is at least ten blocks above
  the chain head observed at precommit time; the pushed precommit triggers
  `.github/workflows/holdout-commitment.yml`, which logs the chain head at
  that moment from a public endpoint. The hash is read only after the block
  is finalized, from two providers that must agree.
- `salt = sha256(preSalt || beacon)` over the raw 64 bytes.

## 3. Derivation

For k = 0, 1, 2, ...:

```text
r_k     = sha256(b"lemma-holdout/1" || salt || k as 4-byte big-endian)
start_k = 19426587 + (int(r_k, big-endian) mod M)
```

The first k whose window [start_k, start_k + 9] does not intersect X is
accepted. The modulo bias is below 2^-200 and is ignored.

## 4. Manifest

The sealed manifest (`lemma-holdout-manifest/1`) lists, for each of the ten
blocks, the header fields two providers agree on: number, hash, parentHash,
stateRoot, transactionsRoot, receiptsRoot, withdrawalsRoot, timestamp,
gasUsed, gasLimit, baseFeePerGas, blobGasUsed, excessBlobGas and
transaction count. It also carries `preSalt`, the beacon, the salt, the
derivation trace, the sha256 of this file and of `holdout.py`, and the
sealing time. It is written as canonical JSON (sorted keys, no whitespace,
no trailing newline) so that the sha256 of the file is the commitment.

- Commitment: `sha256(manifest bytes)`, published as
  `sealed.commitment` in `commitment.json` and as
  `sealedHoldoutCommitment` in `demand/spec.json`, signed by the evaluator
  key (EIP-191 personal message `lemma-holdout/1 commitment <hex>`).
- Storage: the manifest and `preSalt` live in the evaluator environment,
  outside the repository and outside the creator workspace. They are not
  in any GitHub secret, because a workflow the creator can edit could read
  one.

## 5. Use and reveal

- The evaluator runs every manifest block through the frozen harness
  (`apparatus-execute`, `input_source=rpc`) for the baseline and the
  candidate, after the candidate's final submission is immutable. Failures
  and timeouts are retained; no block is replaced.
- After the final evaluation is signed, the manifest and `preSalt` are
  published under `evaluation/holdout/revealed/` and anyone can run
  `holdout.py verify`, which recomputes the commitment, the salt, the
  derivation and the headers.
- One evaluation per sealed set. Any later attempt needs set 2: a new
  precommit under this rule, or a revised rule with a new set id.

## 6. What the commitment does not claim

The blocks are public history. Committing them prevents silent replacement
and stops the creator from tuning to them; it does not show that a model
never saw them. The exclusion margin of 1000 blocks keeps the window off
the executed blocks, not off their state: popular contracts appear in
every block of the era.
