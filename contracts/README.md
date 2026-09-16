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
