# formal/

Owner: creator agent. Reviewed by the evaluator.

## Standard

A checked Lean 4 model-level theorem that the optimized operation agrees with
the unoptimized specification under stated assumptions, plus independently
checked Rust behavior. This does not establish compiler correctness or full
verification of Ethereum.

## Expected contents

```text
formal/
  lean-toolchain         pinned toolchain
  lakefile.*             build config
  Model/                 the abstract model of the operation
  Theorem/               the optimization property
  axiom-report.md        output of #print axioms per theorem, checked against policy
  model-to-code.md       which Rust items each Lean definition models, and the gap
```

## Rules

- No `sorry`, no unfinished placeholders.
- Axioms limited to those allowed in `evaluation/policy.json`.
- The theorem must not assume the desired result.
- If the agent picks trie-node reuse, the theorem covers cache-hit soundness:
  a hit returns only a node previously authenticated for the same reference
  and bytes under the same decoder rules.
