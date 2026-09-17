# The agent economy loop, reviewed against the notes

Research note, 16 September 2026. Reviews the "machine-native economy" text of the same date (agent species, evaluation market, asset registry, emergent valuation, the ten-proofs argument, the Protocol Foundry name, the live-loop demo). Companions: [EXPERIMENT.md](EXPERIMENT.md) (the build), [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md) (blocks, channels, invariants, the nineteen-day plan), [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md) (value and gaming), [PROOF_GRAPH.md](PROOF_GRAPH.md) (graph metrics and what they must not become), [ASSET_SCOPE_AND_CERTIFICATION.md](ASSET_SCOPE_AND_CERTIFICATION.md) (claim families and the certificate), [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md) (identities, composition). Nothing here is implemented or measured.

## 0. Findings first

1. **The thesis is right and about half of it is already in the notes in a stronger form.** The traded unit is demonstrated usefulness; selection under competition is the answer to cheap generation; the role decomposition maps one-to-one onto Experiment 01's blocks. Section 2.
2. **The other half contradicts positions the notes took for documented reasons.** Capital allocation on `V_i(t)` is the tea protocol failure that [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md#L178) section 10 and invariant I-L2 forbid; "active buyers: 127" and "independent evaluators: 14" cost nothing to fake when identities are wallets; the loop diagram has no loss arrows; the asset card prints figures where it should print signed claims; Ethereum is drawn as the demand source that BLUEPRINT correction 1 says it is not. Section 3.
3. **Cheap generation undermines the asset-value premise, not just the scarcity premise.** If a replacement costs thirty seconds, the forward value of the code tends to the bounty floor. What is not cheaply regenerable is the evidence: the evaluation record, the sealed holdout results, the integration into a pinned pipeline, the settled usage history. The asset is the evidence. Evaluation cost, not generation cost, is the entry barrier and therefore the churn rate of the whole market. Section 3.2.
4. **The demo stays Experiment 01.** One real turn of the loop, every claim labeled, beats a simulated live economy on three of the four judging criteria and does not violate I-X2. The vision is the thesis slide and the roadmap. Section 8.
5. **Both proposed names collide with `forge`.** Defer naming; it is not on the critical path. Section 7.

## 1. The vision, restated

The text proposes: agents as producers, evaluators, buyers, sellers and capital allocators; humans set the protocol and constraints. Eight species (builder, verifier, adversary, benchmark, buyer, prover/executor, capital, composer). A loop from creation through an evaluation market, an asset registry, a market, a real Ethereum workload and usage data that "feeds valuation". Value as `V_i(t) = E[future economic contribution of asset i | I_t]`, discovered by the market rather than declared. A machine-readable asset card (correctness, utility, demand, composability, trust, economic). The claim that when an agent can produce ten proofs in thirty seconds the market evaluates all ten and the worse ones lose capital, so what is valuable is accumulated demonstrated usefulness. A stack of Ethereum (workload), Arbitrum (market), agents (production, evaluation, trade), zkVM/Lean/RISC-V (execution and verification). And a hackathon demo showing agents creating, attacking, evaluating, pricing, buying and upgrading an asset in a live loop.

## 2. What holds

**The asset is demonstrated usefulness, not the artifact.** [ASSET_SCOPE_AND_CERTIFICATION.md](ASSET_SCOPE_AND_CERTIFICATION.md#L7) section 1: a certificate is worth reduced evaluation work, integration uncertainty and supplier risk, and cannot create demand or make public information exclusive. The vision restates this correctly and its "accumulated demonstrated economic usefulness" line is the right slogan.

**Selection under competition is the right frame for cheap generation.** With the correction in 3.2 about who pays for the selection.

**The species are the right decomposition.** Five of eight already exist as blocks in [ROBINHOOD_CHAIN_PROD.md](ROBINHOOD_CHAIN_PROD.md#L85) section 2. Section 6 gives the mapping.

**Composer agents are the one species with defensible economics.** Composition creates value the parts do not have, so it is not subject to the hazard in 3.2 to the same degree, and attribution is already handled: [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md#L221) section 12 (flattened payout schedule, composite guest key) and [PROOF_GRAPH.md](PROOF_GRAPH.md#L236) section 6 (Shapley on the saving game, capped at total saving).

**It is a capital market, not an NFT protocol.** The notes dropped token-per-category in AGENT_MARKETPLACE section 2 for the same reason.

## 3. Where it breaks

### 3.1 Valuation feeding capital allocation

The vision's capital agents "allocate capital toward assets with expected future demand", and "agents update valuation" from usage data. That converts the ledger quantity `V_i` into money. [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md#L178) section 10, point 3, states when washing becomes profitable: the moment `V_j` feeds a token price, a retroactive grant or a ranking that unlocks external money. The three precedents (tea protocol, Unity Runtime Fee, RetroPGF) are documented there and in [PROOF_GRAPH.md](PROOF_GRAPH.md#L313) section 7.3. Invariant I-L2: nothing pays out on any ledger metric; settlement reads only the snapshotted schedule.

The agent setting makes this worse, not better. In a human market a wash trade costs at least a human's time. In an agent market a buyer is a wallet and a loop; the marginal cost of a fake buyer is a faucet claim. The only cost a wash job carries is the one the protocol imposes: the escrowed fee (PROOF_MODULE_VALUE 10, point 1) and the `(1 - r)` loss per self-funded job (point 3). Those survive only while nothing pays on the aggregate.

**Design consequence.** Capital agents are out of scope, and the reason is written into the thesis slide rather than hidden. If a later system wants a price for control of an asset, the price is set by bilateral trade in the control token with the ledger published as evidence (PROOF_MODULE_VALUE section 9: realized value is evidence, forward value prices the asset, neither is paid out). No protocol function reads the ledger.

### 3.2 Cheap generation and the hazard rate

The vision's argument: an agent produces ten proofs in thirty seconds, the market evaluates all ten, the worse ones lose capital, so the surviving asset's value is its demonstrated usefulness. Correct about selection, silent about what it does to the survivor's value.

PROOF_MODULE_VALUE section 3 defines value against the best alternative, so the second-best in a niche is worth about zero and value concentrates on the best. Forward value (section 9) is then

```text
V_i^fwd = sum over t of  E[jobs_t] * E[dC_t] * p * S(t)
S(t)    = P(i is still the best registered alternative at t)
```

If competitors arrive at rate `lambda` and each beats `i` with probability `q`, `S(t) = exp(-lambda * q * t)` and the forward value of the *code* is roughly `E[jobs] * E[dC] * p / (lambda * q)`. When generation is thirty seconds, `lambda` is whatever the market's entry barrier allows, and for the code alone that value approaches the bounty floor. A capital agent holding "productive assets" holds something whose expected life is `1 / (lambda q)`.

What does not decay at that rate: evidence. A competitor's evidence must be produced fresh, at evaluation cost `E`, on the same frozen policy and a new sealed holdout. So the entry barrier is `E` plus any submission stake, not generation cost, and `lambda` is set by `E`. Cheaper evaluation means more churn, lower asset values and better infrastructure; more expensive evaluation means the reverse. The project already sits on both sides of this: execute-mode PGU is minutes and third-party reproducible (I-E8), a real proof is hours on a runner and is the live critical path (G0). That is the correct place for the trade to be made explicit rather than a problem to hide.

**Design consequence.** State the asset as `(artifact digest, evidence record, usage ledger)` and price the evidence record. The thesis sentence becomes: the asset is the evidence, and evidence is expensive to fake only while evaluation is expensive and independent. A fee band at a share of per-job saving (PROOF_MODULE_VALUE section 9) scales down automatically when a better alternative appears, which is the right behavior under a high hazard rate; a fixed per-job fee is not.

### 3.3 No loss arrows, and who pays to evaluate ten candidates

Every arrow in the vision's loop carries value upward. A selection mechanism needs channels through which capital leaves: failed bounties, forfeited stakes, evaluation fees, expired escrow. Section 4 redraws the loop with them.

The specific gap is evaluation cost. Let `G` be the cost to generate a candidate, `E` the cost to evaluate one, `N` the candidates a demand attracts. If submission is free, `N` is bounded only by `G`, and someone pays `N * E`. If that is the buyer, spam creation is an attack on buyers (the Unity pattern: a metric a hostile party can move against the payer). If it is the evaluator, honest evaluation stops. [EXPERIMENT.md](EXPERIMENT.md#L339) section 15 lists "full proof evaluation may dominate cost and elapsed time" as a known flaw; the vision does not mention it.

**Design consequence.** Three rules, all cheap to implement on the existing contracts:

1. **Submission stake.** A candidate posts `s >= E_admission` at submission. Forfeited on Fail to the evaluator's credit, refunded on Pass, refunded on Inconclusive (I-E7: insufficient compute is the evaluator's problem, not the creator's). Then `N * E` is paid by the candidates that fail.
2. **Tiered evaluation.** Cheap admission checks first (ASSET_SCOPE section 5, step 3: schemas, signatures, limits, rights), then execute-mode PGU on the holdout (minutes, deterministic, I-E8), then one real proof for the accepted candidate only. This is already implied by the plan's three real proofs; write it as a rule so the count does not grow with `N`.
3. **One decision per demand version** (I-E3). A retry is a new demand with a new sealed holdout and a new stake, so the flood cannot recycle a leaked holdout.

### 3.4 The asset card prints figures where it should print claims

The card reads `formal verification: 100%`, `adversarial tests: passed`, `independent evaluators: 14`, `active buyers: 127`, and the text says "no human needs to interpret that, an agent can."

`formal verification: 100%` is not a number. It is a claim about a statement under declared assumptions, and the statement is where the value and the risk both live (I-E5: `#print axioms` on the exported theorem, reviewer confirms the theorem addresses the implemented optimization; I-X3: model-level, the model-to-Rust gap written into the evidence panel). `adversarial tests: passed` is a lower bound on brokenness at one adversary's budget, comparable across assets only if the budget and method are pinned. `independent evaluators: 14` and `active buyers: 127` are counts of wallets (3.1) unless independence is a disclosed, costed property (I-L4: effective payers and top-payer share published with every value sentence). `demand growth: +23%` is the tea metric.

Interpretation is not removed by machine-readability; it moves into the reading agent's issuer policy (ASSET_SCOPE section 7, "who certifies the certifier"). What the card can do is make every line verifiable rather than merely parseable.

**Design consequence.** Every line on the card is a signed claim with provenance: who produced it, under which frozen policy hash, on which inputs, at what cost, and with which label from I-L3. Section 5 gives the shape. The defensible sentence is then "an agent can verify each claim's provenance," not "an agent can interpret the score."

### 3.5 Ethereum is not the demand source

The vision draws `REAL ETHEREUM WORKLOAD -> USAGE DATA -> feeds valuation` and "Ethereum creates the workload". [BLUEPRINT.md](BLUEPRINT.md) correction 1 and [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) section 1: EIP-8025 is a draft with opt-in proofs and no protocol payment. The workload exists; a paying workload does not, yet. A sponsor sits at the bottom of the diagram, and I-X1 requires saying so: sponsored demand is never called customer validation.

**Design consequence.** The stack slide reads: Ethereum supplies the *workload* (real mainnet blocks through RSP and SP1), a sponsor supplies the *demand* (the funded specification), Arbitrum coordinates settlement. Three different words for three different things.

### 3.6 Identity is free

Runs through 3.1 and 3.4 but deserves its own line because it is the property that separates an agent market from a human one. [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md#L81) section 4: a wallet address does not establish competence; independent machines and wallets alone do not establish independent economic actors; the same operator running several roles must disclose it. In an agent economy every role can be sybil-instantiated at faucet cost. Any metric that counts identities (buyers, evaluators, dependents) is therefore free to inflate, and [PROOF_GRAPH.md](PROOF_GRAPH.md#L317) section 8 measures exactly that for packages, wash jobs and witness gerrymandering.

**Design consequence.** Count money, not identities. Publish payer independence (I-L4) as a disclosure. Where an identity count is unavoidable (evaluator quorum), require stake per identity so the count has a floor cost.

### 3.7 Adversary agents are an evidence class, not a verdict

For a Lean-verified refinement the attack surface is not the theorem; it is the statement's scope and the trusted base. Useful adversary work here: search the permitted input domain for inputs where the model and the Rust implementation diverge (the I-X3 gap); attempt to reconstruct holdout blocks from public commitments (I-E2 independence); feed malformed witnesses through the integration (I-E6 oracle). Each has a budget in compute hours and a method hash, and each produces a lower bound.

**Design consequence.** An adversary lane is a second evaluator in B3 with its own frozen policy hash and its own signed report. Its card line reads `adversarial: 0 findings at budget B under method M`, never `passed`. Section 6 says when to add it.

## 4. The loop, redrawn with loss arrows

Solid arrows carry value or work. Arrows marked `$-` carry capital out of the loop; a market without them is not a selection mechanism. Sponsor at the bottom, labeled.

```text
                    SPONSOR / BUYER  (funded specification, frozen policy, sealed holdout)
                    label: sponsored demand (I-X1)
                          │  bounty + usage escrow
                          v
  ┌───────────────────────────────────────────────────────────┐
  │  CREATOR AGENTS  (reuse | compose | create | decline)     │
  │  stake s posted at submission                             │
  └────────┬──────────────────────────────────────────────────┘
           │ candidate + manifest + hypothesis hash
           v
  ┌───────────────────────────────────────────────────────────┐
  │  EVALUATION, tiered                                       │
  │   1. admission checks       (seconds)   ── Fail ──> $- stake forfeited
  │   2. execute-mode PGU       (minutes)   ── Fail ──> $- stake forfeited
  │      on the sealed holdout, vs best registered alternative │
  │   3. adversary lane         (budget B)  ── findings ─────> report, lower bound
  │   4. one real proof         (hours)     ── Fail ──> $- bounty returns to sponsor
  │  verdict: Pass | Fail | Inconclusive (stake refunded on Inconclusive)
  └────────┬──────────────────────────────────────────────────┘
           │ Pass: register version + credit bounty, one transaction (I-S11)
           v
  ┌───────────────────────────────────────────────────────────┐
  │  REGISTRY + LEDGER  (evidence record, usage rows, labels) │
  │  reads nothing into settlement; pays nobody (I-L2)        │
  └────────┬──────────────────────────────────────────────────┘
           │ discovery by interface, version, trust, budget
           v
  ┌───────────────────────────────────────────────────────────┐
  │  JOBS  (worker fetches witness, runs approved guest)      │
  │   proof valid  ──> settle once, pull payments (I-S2, I-S12)│
  │   deadline miss ──> $- escrow refunds to buyer (I-S5)     │
  │   fee = share of measured per-job saving, inside (0, dC)  │
  └────────┬──────────────────────────────────────────────────┘
           │ settled job rows (payer, dC vs alternative, PGU model version)
           v
  ┌───────────────────────────────────────────────────────────┐
  │  USAGE LEDGER  ──> evidence, published with labels        │
  │   NOT a price. NOT a payout. NOT an input to settlement.  │
  │   criticality ──> redundancy bounty ──> new demand (C12)  │
  └───────────────────────────────────────────────────────────┘
           │
           └──> back to a sponsor, who funds the next demand or does not.

  Hazard: a new candidate that beats the registered best on the same holdout
  policy replaces it as the counterfactual; the old asset's fee band shrinks to
  zero automatically. Its evidence record and settled rows remain.
```

What changed against the vision's diagram: four exits for capital, the sponsor named, the ledger explicitly severed from settlement, the replacement hazard drawn, and "capital agents allocate" removed.

## 5. The asset card, redrawn as a provenance card

Builds on the `asset-claim/v1` certificate in [ASSET_SCOPE_AND_CERTIFICATION.md](ASSET_SCOPE_AND_CERTIFICATION.md#L233) section 6 and the labels in I-L3. The card is a list of claims; each claim is independently signed and independently verifiable. No line is a bare number. Illustrative, not a standard.

```json
{
  "schema": "asset-card/v1",
  "subject": {
    "moduleId": "registry id",
    "version": "immutable version",
    "payloadDigest": "digest of delivered bytes",
    "dependencyLockDigest": "digest of exact closure"
  },
  "claims": [
    {
      "family": "correctness",
      "statement": "theorem name and exported statement digest",
      "result": "kernel-checked under {propext, Classical.choice, Quot.sound}",
      "method": "formally-checked-under-assumptions",
      "gap": "model-level; model-to-Rust gap described at evidenceURI",
      "producer": "evaluator identity",
      "policyHash": "workflow file hash",
      "evidenceDigest": "...",
      "costToProduce": {"unit": "runner-minutes", "value": 0},
      "label": "formal evidence (I-X3)"
    },
    {
      "family": "performance",
      "statement": "PGU saving vs best registered alternative on sealed holdout H",
      "result": {"dPGU": 0, "relative": 0.0, "blocks": 0, "runsPerVariant": 2},
      "method": "independent-reproduction",
      "counterfactual": "registry-chosen (I-E9)",
      "pgUModelVersion": "pinned",
      "producer": "evaluator identity",
      "policyHash": "...",
      "holdoutCommitment": "revealed preimage",
      "costToProduce": {"unit": "runner-minutes", "value": 0},
      "label": "measured (I-X4)"
    },
    {
      "family": "adversarial",
      "statement": "findings against the implemented optimization",
      "result": {"findings": 0, "budgetHours": 0, "methodHash": "..."},
      "method": "bounded-search",
      "producer": "adversary lane identity",
      "label": "lower bound at stated budget"
    },
    {
      "family": "usage",
      "statement": "settled jobs using this version",
      "result": {
        "jobs": 0,
        "feesReceived": "wei",
        "attributedSaving": "PGU at quoted rate",
        "effectivePayers": 0,
        "topPayerShare": 0.0,
        "sponsoredShare": 0.0
      },
      "method": "observed-in-live-jobs",
      "producer": "indexer, rebuildable from chain state (I-L1)",
      "label": "receipts = contractual; saving = measured; independence = disclosure (I-L3, I-L4)"
    },
    {
      "family": "composition",
      "statement": "registered composites that pin this version",
      "result": {"composites": 0},
      "method": "registry-observed",
      "label": "exposure, not value (PROOF_GRAPH 14)"
    },
    {
      "family": "identity",
      "statement": "who built, evaluated, and paid; disclosed relationships",
      "result": {"creator": "...", "evaluator": "...", "sharedOperator": false},
      "method": "producer-declared",
      "label": "disclosure"
    }
  ],
  "omitted_on_purpose": [
    "reputation score",
    "demand growth",
    "active buyers count",
    "current bid",
    "any scalar that combines families (ASSET_SCOPE 4.3)"
  ]
}
```

Rendered for a human, the same card is a table with one row per claim and a label column. Rendered for an agent, it is the JSON above, and the agent's issuer policy decides which producers and methods it accepts. The `omitted_on_purpose` list is not decoration; it is the set of fields whose presence would make the card a payout target.

## 6. Species mapped to the build

| Vision species | Block in ROBINHOOD_CHAIN_PROD | Status | Decision |
| --- | --- | --- | --- |
| Builder | B2 creator agent, disposition in {reuse, compose, create, decline} (I-A6) | in plan, G3 | keep |
| Verifier | B3 evaluator: rebuild, correctness oracle, Lean axioms (I-E5, I-E6) | in plan, G4 | keep |
| Benchmark | B3 PGU matrix on sealed holdout vs registry-chosen alternative (I-E8, I-E9) | in plan, G4 | keep |
| Buyer | B1 demand, sponsor-funded, labeled (I-X1) | in plan, G2 | keep; say "sponsor" |
| Prover / executor | B5 worker, reuse job, single settlement (I-S2) | in plan, G5 | keep |
| Registry | `ModuleRegistry` written only from the acceptance path (I-S8); B6 ledger | in plan, G4 and G5 | keep |
| "Creator agents improve assets" | redundancy bounty loop, C12 (PROOF_GRAPH 7) | design only | roadmap; already drawn |
| Adversary | second lane in B3 with its own policy hash and signed report (3.7) | not in plan | add only if the G0 proof lands and G4 has slack; otherwise roadmap, listed in the report as a gap |
| Composer | AGENT_MARKETPLACE 12, PROOF_GRAPH 6 | design only | first post-hackathon item |
| Capital | none | excluded | out of scope by I-L2 and 3.1; stated on the thesis slide with the reason |

Six of the nine rows are Experiment 01. The vision is a description of what one turn of Experiment 01 generalizes into, which is the correct relationship between a pitch and a build.

## 7. Naming

Protocol Foundry and VeriForge both collide with `forge`. Foundry (`forge`, `cast`, `anvil`) is the Solidity toolchain every Arbitrum judge uses daily and the toolchain in this project's own contracts (ROBINHOOD_CHAIN_PROD section 5.2, "Foundry configuration"). A judge reading "Protocol Foundry" will think of the tool first. The other candidates in the text are generic (AgentFoundry, VeriMarket), abstract (Ethry), narrowing (Proofsmith) or heavily used (Machina).

Position: defer. Naming is not on the critical path and the submission form accepts whatever is in the repo. Rule out anything containing `forge` or `foundry`. The working names in the notes (ProofMarket in BLUEPRINT, LemmaXperiment for the repo) are not wrong.

## 8. The demo

The vision's demo is "agents autonomously creating, attacking, evaluating, pricing, buying, upgrading an asset in a live loop, with an actual Ethereum-related workload underneath."

Constraints as of today: eighteen days to the 4 October 15:59 close; GitHub Actions is the only compute; the first real proof is the critical path and was still in flight at the last plan revision (G0); the hard rule is no simulated proof, and I-X2 requires a recording or a mock to be labeled as such. A live loop with multiple agent roles, adversary attacks, pricing and upgrades cannot be real in that window. Shown simulated, it is a video of a loop, and every frame carries a label that says so.

Judging criteria (ROBINHOOD_CHAIN_PROD finding 3): smart contract quality, product-market fit, innovation, real problem solving. One real turn of Experiment 01 scores on contract quality (fourteen settlement invariants with tests), real problem solving (a real mainnet block, a real PGU saving on a sealed holdout, a real verified settlement), and innovation if the thesis is framed as section 3.2 (the asset is the evidence; the evaluation cost sets the churn rate; the market's edges cost money to create). Product-market fit is capped by I-X1 either way; a simulated economy does not raise it. Judges have seen enough autonomous-agent-economy demos to discount anything without a real proof under it.

**Position.** The demo is Experiment 01, unchanged: funded demand, creator disposition, frozen evaluation, atomic registration and bounty, paid reuse with a verified proof. The thesis slide is the loop from section 4 with the one completed turn highlighted as done, real and labeled, the adversary lane marked added or gap, and composer and capital marked roadmap and excluded respectively, each with its one-line reason. The stack slide uses the three words from 3.5.

## 9. Positions taken

- The asset is `(artifact digest, evidence record, usage ledger)`; the evidence record carries the value; the code's forward value decays at a rate set by evaluation cost.
- Nothing pays out on `V_i`. Capital agents are excluded, and the exclusion is stated with its reason. Control-token prices, if any, come from bilateral trade with the ledger as published evidence.
- Submission is staked; evaluation is tiered; one decision per demand version. Candidates that fail pay for their own evaluation.
- Count money, not identities. Identity counts that cannot be avoided carry a stake per identity.
- Every card line is a signed claim with producer, policy hash, inputs, cost and label. No scalar combines families. The omitted fields are listed on the card.
- Adversarial results are lower bounds at a stated budget, from a separate lane with its own policy hash.
- Ethereum supplies the workload, a sponsor supplies the demand, Arbitrum settles. Three words, not one.
- The demo is one real turn. The vision is the thesis slide and the roadmap.
- Naming deferred; nothing containing `forge` or `foundry`.

## 10. Flaws in this note

- The hazard-rate expression in 3.2 treats competitor arrivals as Poisson with a fixed win probability. Real arrivals cluster after a toolchain release, when the PGU model changes and every old reading is stale (PROOF_MODULE_VALUE section 9).
- The submission stake in 3.3 assumes an evaluator that cannot fail candidates for its own gain. With one evaluator that is a disclosure; with several it needs the quorum rules this note does not write.
- The adversary lane is described, not costed. On GitHub Actions its budget competes with the real proofs for runner hours.
- The provenance card has not been checked against a consuming agent's actual issuer policy. It is a schema proposal.
- One turn of Experiment 01 does not establish a market (I-X5). This note does not change that.
