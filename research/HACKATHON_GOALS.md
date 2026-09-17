# Hackathon competitiveness and achievement goals

Assessment for Arbitrum Open House Singapore. Saved September 16, 2026.

This captures the project assessment and goals from the discussion. It is not an official judging score or a claim that the goals have been achieved. Implementation details remain governed by the experiment and its acceptance policy.

Related documents: [Experiment](EXPERIMENT.md), [agent economy review](AGENT_ECONOMY_REVIEW.md), [asset certification](ASSET_SCOPE_AND_CERTIFICATION.md), [reuse plan](REUSE_PLAN.md), and [recorded experiment results](LemmaXperiment/results/report.md).

## 1. Competitiveness

This can be a competitive submission if we demonstrate one complete economic loop with real verification and measured benefit. The strongest differentiator is the combination of artifact certification, agent procurement and paid reuse.

We have recorded proof infrastructure progress. We have not yet demonstrated that an agent-created asset is useful enough for another agent to acquire and reuse economically. That is the gap to close.

### Assessment against the published criteria

- **Innovation:** promising. Agents purchasing data already have precedents such as Fangorn. Our distinguishing achievement must be evaluating and reusing capabilities under explicit compatibility and cost constraints.
- **Technical execution:** a useful foundation exists. The recorded baseline proof and verifier checks support the build, but the marketplace loop remains to be demonstrated.
- **Real problem solving:** plausible. We need evidence that procurement avoids meaningful work.
- **Product-market fit:** weakest today. We need an identifiable operator with a recurring task and a reason to pay.

A credible prize contender demonstrates working agents, enforced settlement, meaningful rejection cases, measured reuse and an independent pilot user.

A weaker submission consists of an impressive architecture, several asset categories, token listings and simulated savings. Prioritize proving the complete loop. Public winner descriptions do not support assigning a probability of winning.

The Singapore listing names smart contract quality, product-market fit, innovation and creativity, and real problem solving. It requires deployment on an Arbitrum chain. [Singapore listing](https://www.hackquest.io/ja/hackathons/Arbitrum-Open-House-Singapore-Online-Buildathon)

Fangorn's agent data-commerce submission and its second-place NYC online Buildathon award establish a relevant precedent. They do not establish that our additional certification and procurement behavior is already solved. [Fangorn submission](https://www.hackquest.io/projects/Fangorn), [NYC results](https://blog.arbitrum.foundation/open-house-nyc-buildathon-concludes-meet-the-winning-teams/)

## 2. Core achievement goal

**A funded need causes an agent to acquire or create a reusable capability, which passes scoped evaluation and is independently reused in a fresh paid job.**

The demonstration must establish all five steps:

1. **Demand:** a buyer specifies an actual task, budget and acceptance conditions.
2. **Production:** the agent chooses reuse, composition, creation or decline.
3. **Certification:** evaluation accepts the exact artifact version for specific claims.
4. **Reuse:** a separate worker uses that unchanged release on fresh input.
5. **Settlement:** contracts pay according to verified acceptance and agreed terms.

The baseline execution proof establishes part of the infrastructure. The core product achievement is the completed cycle above.

## 3. Economic goals

**Show when acquisition is a rational decision.**

The buyer compares:

```text
Cost to buy and use
  = price + retrieval + checking + integration + execution

Cost to build and use
  = generation + failed attempts + checking + integration + execution
```

Both options must satisfy the deadline and acceptance requirements. Include allocated settlement costs where relevant, and account for failed acquisition attempts as well as failed generation attempts.

### Measurements

- Buyer's total cost and completion time.
- Creator's development, inference and evaluation costs.
- Certification cost and how repeated buyers share that cost.
- Actual acquisition or invocation fees.
- Number of future uses needed to recover the creation cost.

**Success:** at least one reported workload shows a defensible benefit from external reuse against a credible baseline, including free alternatives.

The agent must also decline a purchase when it is more expensive or incompatible. Testnet payments demonstrate settlement mechanics; they do not establish willingness to pay with real money.

Keep formal-development savings separate from runtime execution-proving savings. A successful lemma purchase does not by itself demonstrate faster zkVM proving.

## 4. Marketplace goals

**Make useful work discoverable, purchasable and deliverable.**

The minimum marketplace needs:

- A funded demand with frozen acceptance criteria.
- Listings tied to immutable artifact versions.
- Compatibility and certificate filters.
- Explicit prices, rights and delivery modes.
- Acceptance, rejection, expiry and refund paths.
- A record of downstream use and agreed contributor payments.

**Success:** an agent can discover an eligible offer, acquire it, receive the correct material and complete settlement without a human manually coordinating each step.

For the hackathon, fixed quotes and a small catalog are enough. Liquidity, speculative asset trading and algorithmic valuation are later questions.

## 5. Agentic layer goals

**The agent must make consequential decisions that we can inspect.**

It should:

1. Translate the demand into capability requirements.
2. Search existing and free resources.
3. Reject incompatible candidates.
4. Compare acquisition against creation.
5. Act within a fixed spending and execution budget.
6. Submit its artifact and evidence.
7. Stop or recover appropriately after failure.

**Success:** its choice changes with the circumstances.

- Compatible and cheaper asset available: **reuse**.
- Useful dependencies available: **compose**.
- Missing capability within budget: **create**.
- No viable option: **decline**.

A scripted purchase followed by an LLM explanation does not establish this goal. Log the inputs, alternatives, decision, tool actions and actual costs. Label human interventions.

## 6. Security goals

**Prevent invalid work and unauthorized actions from causing payment or trusted adoption.**

### Artifact correctness

The delivered bytes must match the evaluated release. Proofs must bind the intended inputs, program and outputs.

### Certification integrity

Certificates must identify the claim, assumptions, evaluator and applicable profile. A valid signature establishes who issued the claim; it does not independently establish the claim's truth.

### Agent authority

The creator cannot change the evaluator's policy, access holdouts, use evaluator keys or spend beyond its authorization.

### Settlement integrity

Wrong-demand submissions, replayed receipts, unauthorized signers and invalid proofs must fail. Expired work follows explicit refund rules.

**Success:** demonstrate an accepted job and deliberate failures, including a wrong artifact digest, incompatible profile, invalid proof and repeated payment attempt.

Public artifacts are sufficient initially. Confidential delivery would add another security objective.

## 7. Final achievement statement

Target statement, to use only after the evidence supports it:

> We demonstrated an agent choosing external reuse over recreation, completing fresh verified work, and settling payment on Arbitrum under explicit certification and spending policies.

Support it with:

- One complete creation/procurement-to-reuse trace.
- Reproducible cost and timing results.
- Deployed contracts and settlement receipts.
- Rejection and refund evidence.
- An independent operator's test or feedback.

The priority order is: complete the loop, establish its benefit, enforce its boundaries, then expand the market. This gives judges a concrete product achievement and a credible reason for the broader vision.

## 8. Cases to map through the build next

Build mapping: [BUILD_CASE_MAP.md](BUILD_CASE_MAP.md) now defines components, milestones, failure cases, acceptance checks and evidence for these five cases.

The next planning step is to trace these five cases through implementation, acceptance checks and evidence collection:

1. **Working agents.** Observable decisions and actions, budgets, logs and intervention records.
2. **Enforced settlement.** Acceptance-linked registration/payment and explicit failure/refund transitions.
3. **Meaningful rejection cases.** Invalid artifacts, incompatible profiles, unauthorized actions and replay attempts.
4. **Measured reuse.** Fresh downstream work compared against credible creation and free-reuse alternatives.
5. **Independent pilot user.** An operator outside the development team tries a real task and provides attributable results or feedback. Interest, completed use and willingness to pay are separate evidence levels.

For each case, the build map should identify the starting state, responsible component, trigger, expected transition, failure behavior, measurable outcome and saved evidence. This document records the goals; that build map is the next deliverable.
