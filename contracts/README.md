# contracts/

Owner: operator. Solidity, Foundry. Target: Arbitrum Sepolia, testnet ETH.
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

Confirm or deploy a pinned SP1 verifier on Arbitrum Sepolia before building
UsageEscrow. Record the address and version in `demand/spec.json`.

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
