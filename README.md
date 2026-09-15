# Experiment 01: Demand triggers an agent-created proof asset

Status: outline only. Nothing here is implemented, run or benchmarked.

Authoritative plan: [EXPERIMENT.md](../EXPERIMENT.md). It takes priority over
[BLUEPRINT.md](../BLUEPRINT.md). [TRIE_MODULE_PROTOCOL.md](../TRIE_MODULE_PROTOCOL.md)
is an optional candidate protocol the agent may or may not select.

## Layout

| Path | Owner | Contents |
| --- | --- | --- |
| `apparatus/` | operator | pins, environment record, setup and baseline scripts, baseline run records |
| `demand/` | buyer / operator | frozen requirement, terms and registry snapshot |
| `agent/runner/` | operator | funded trigger, tool limits, workspace restrictions, run log |
| `candidate/` | creator agent | module code, adapter, tests, build recipe, asset manifest |
| `formal/` | creator agent | Lean model, theorem, axiom report, model-to-code map |
| `evaluation/` | evaluator | frozen policy, evaluator image hash, signed reports |
| `contracts/` | operator | CreationBounty, ModuleRegistry, UsageEscrow (Arbitrum Sepolia) |
| `reuse/` | clean worker | fresh-job integration of the accepted version and its proof |
| `results/` | operator | final outcome, cost accounting, intervention log |

Private holdout fixtures never live in this tree. They stay in the evaluator's
separate environment; only their commitment is recorded here.

## Build order

1. Apparatus: baseline proof, fixtures, evaluator image, verifier check, budgets.
2. Demand-to-agent runner: schema, funded trigger, restricted workspace, run log.
3. Creation run: search, hypothesis, bounded revisions, code and formal evidence.
4. Evaluation: reproduction, independent correctness, formal review, holdout, verdict.
5. Acceptance and reuse: bounty payment, registry entry, fresh proof job, report.

## Fixed decisions carried over from the plan

- Integration target: pinned RSP/SP1 pipeline. Exact commits pinned in `demand/spec.json` during setup.
- Settlement: Solidity on Arbitrum Sepolia, testnet ETH, labeled as such.
- Formal evidence: Lean 4 model-level theorem plus independently checked Rust behavior.
- One creator agent, one evaluator with a separate signing identity.
- Three local candidate revisions, then one holdout submission.
- Ten holdout blocks, three paired A/B runs each: 60 planned proof runs.

## Stage gates

Each stage directory has a README stating what it consumes, what it produces and
what must be true before the next stage starts. A stage that cannot run records
a blocker in `results/report.md` instead of a simulated result.
