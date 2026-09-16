# On-chain verification, Arbitrum Sepolia (421614)

Date: 2026-09-16. View calls only, no transaction.

| Call | Target | Result |
| --- | --- | --- |
| `VERIFIER_HASH()` | V6.1.0 Groth16 verifier `0xb69f2584CBcFf99a58C4e7002E8b89Af54a6f4e2` | `0x4388a21c…` matches proof selector |
| `routes(0x4388a21c)` | gateway `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` | `0xb69f2584…`, frozen = false |
| `verifyProof(vkey, publicValues, proof)` | gateway | returns, no revert |
| `verifyProof(vkey, publicValues, proof)` | verifier directly | returns, no revert |
| same, last proof byte +1 | gateway | reverts `0x7fcdd1f4` (ProofInvalid) |
| same, vkey last byte +1 | gateway | reverts `0x7fcdd1f4` (ProofInvalid) |

Inputs: `out/vkey.txt`, `out/public-values.hex`, `out/proof.hex` in this directory.

```text
vkey       0x00b22d4bb5487743bd048fde7fdbd7b048b37bc93bafce13610f2d633465bfba
proof      356 bytes, selector 0x4388a21c
publics    765 bytes (guest-committed block header of 20600066)
```
