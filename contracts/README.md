# contracts/

Owner: operator. Solidity, Foundry. Target: Robinhood Chain testnet, chain 46630, testnet ETH
(`demand/spec.json` `settlement`). Arbitrum Sepolia is never a settlement venue;
its SP1 gateway is used read-only to cross-check proof bytes.
Three logical components; one deployment is acceptable for the prototype.

## CreationBounty

```text
FUNDED -> SUBMITTED -> ACCEPTED
   |          |
   |          +-> REJECTED
   +----------+-> EXPIRED
```

- Funding fixes demandHash, creator, evaluator, policyHash, amount, submitBy, evaluateBy.
- Require evaluateBy > submitBy. One submission at or before submitBy.
- Evaluator signature binds: chainId, contract, demandId, candidateDigest,
  policyHash, reportHash, derivedGuestKey, recipient, verdict, validUntil.
- Acceptance registers the version in ModuleRegistry and credits the creator once.
- Rejection, expiry or creator decline credits the sponsor.
- Pull withdrawals with solvency accounting.

## ModuleRegistry

Immutable accepted versions with evidence references, guest key, compatibility
and contributor terms. Only the bounty-acceptance path may create an entry.

## UsageEscrow

- Fund a proof job: snapshot module version, verifier, guest key, worker,
  contributor, amounts, statement, deadline.
- Settle once on a verified SP1 proof with exact public bindings; any relayer
  may submit; stored recipients are paid.
- Refund only after the deadline.

Guest public values commit: settlement chainId, contract, jobId, source domain,
input/block commitments, computed result, success flag.

## Setup dependency

Deploy `SP1VerifierGroth16` v6.1.0 from `sp1-contracts` on Robinhood Chain
testnet before building UsageEscrow (no upstream deployment exists for 46630).
Source-verify it on the explorer and record address, version and
`VERIFIER_HASH()` in `demand/spec.json` `settlement.sp1Verifier` and
`apparatus/pins.json`. Cross-check the same proof triple read-only against the
Arbitrum Sepolia gateway.

## Planned layout

```text
contracts/
  foundry.toml
  src/CreationBounty.sol
  src/ModuleRegistry.sol
  src/UsageEscrow.sol
  test/
  script/
```

## Deployed (Robinhood Chain testnet, 46630, 2026-09-17)

| contract | address | source |
| --- | --- | --- |
| SP1VerifierGroth16 v6.1.0 | `0x2d67d20E250A439a826c77C432E5E9C481e8cB9E` | vendored `src/sp1/` from sp1-contracts v6.1.0, unmodified, hashes in the deployment file |
| ModuleRegistry | `0x92695F85f4e595C413C766eE3d4AF4568C1D5188` | `src/ModuleRegistry.sol` |
| CreationBounty | `0x2C920C76751fCBf080f0443e6A85813A5B3f798E` | `src/CreationBounty.sol` |
| UsageEscrow | `0xC5cf835118B0476d5c938E7788959ca98E627ea7` | `src/UsageEscrow.sol` |

Evidence: `deployments/46630-lemma.json` (deployer, blocks, tx hashes, code
hashes, `VERIFIER_HASH`, explorer verification GUIDs). All four are
source-verified on the explorer. The deployed verifier returns for the real
proof of block 20600066 and reverts `ProofInvalid` on a mutated one, the
same result the Arbitrum Sepolia gateway gave in step 1.

Tests (`forge test`, 37 tests): verifier identity and the real proof;
bounty state machine, deadlines at and after the boundary, EIP-712 replay
across demands, contracts and chains, expired verdicts, nonce reuse, wrong
signer, pause scope, reentrancy, direct registry writes; escrow term
snapshots, every public-values field mutated, wrong length, wrong chain,
invalid proof, relayer cannot redirect, deadline boundary, pause scope, the
real verifier rejecting a foreign proof; and the solvency invariant over
random call sequences (I-S1).

Not implemented, by design: a general payee schedule (I-S13; jobs have
exactly a worker and a contributor) and the `witnessCommitment` public value
of ROBINHOOD_CHAIN_PROD.md 3.2 (hashing the whole witness inside the guest
would cost a large share of the cycles the demand is trying to save; the
witness is bound by the guest's checks against `parentStateRoot`, and its
sha256 is a ledger field).

## Funded demand

`demand/funding.json`: demandId
`0x5aa24f989335d1795c40c561af98d83f666a4f65d9ddd17ce42f4caf4e5158b2`,
tx `0x8f1e3be9…`, block 120638142, 0.05 testnet ETH escrowed, submitBy
2026-09-21T05:00Z, evaluateBy 2026-09-26T05:00Z.
