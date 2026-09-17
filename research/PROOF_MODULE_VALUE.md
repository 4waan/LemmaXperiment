# Proof-module value: what a reusable proof component is worth

Research note, 15 September 2026. Companion to [EXPERIMENT.md](EXPERIMENT.md), [BLUEPRINT.md](BLUEPRINT.md) and [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md). Graph extension: [PROOF_GRAPH.md](PROOF_GRAPH.md) computes the marginal contribution on the typed dependency graph (cascade, AND/OR alternatives, payee-level Shapley, criticality) and audits the proposed centrality score against it. Nothing here is implemented or measured beyond the single execute run already recorded in `LemmaXperiment/apparatus/runs/`. Arithmetic on that run is illustrative and labeled as such.

## 0. The question and the answer in one paragraph

The question is what a theorem, lemma or module `j` is worth. The proposed answer is that its value is its measured marginal contribution: for every job `k` that could use it, the cost and latency the job would have incurred without `j`, minus what it incurred with `j`, weighted by how much the buyer cares about each, summed over jobs. That definition is sound and has good precedent (Shapley value, VCG payments, Data Shapley, Kaliszyk and Urban's lemma-usefulness metrics). Three things have to be true for it to produce evidence rather than marketing: the counterfactual must be defined against the best alternative and not the naive baseline; the per-job difference must be reproducible by someone who does not own the module; and the jobs that count must be jobs someone unaffiliated actually paid for. In this project's setting all three are achievable, because SP1 execute mode makes the cost counterfactual deterministic and cheap, and escrowed settlement on Arbitrum makes "a job happened" a fact rather than a claim. The parts of the value that cannot be measured this way (the formal theorem, enabling modules that make a job possible at all, latency near a deadline) need separate treatment and are covered in sections 6 to 8.

## 1. The formula and what it commits you to

Starting point, as proposed:

```text
ΔC_jk = C_k(without j) − C_k(with j)
ΔT_jk = T_k(without j) − T_k(with j)

V_j = Σ_k  P(job_k uses j) · ( w_C · ΔC_jk + w_T · ΔT_jk )
```

Read literally, this makes five commitments that each need a decision.

1. **`j` is a thing a job can run with or without.** That is true of an executable module version. It is not directly true of a Lean theorem, which never executes. Section 6 handles the theorem.
2. **"Without j" is a specific counterfactual.** Naive baseline, or the best alternative the buyer would actually have chosen? These differ, and the difference is where most inflated claims hide. Section 3.
3. **`C` and `T` have units and prices.** For this project, `C` should be prover gas units (PGU) priced at a quoted rate, and `T` should be modeled from PGU or measured on fixed hardware, never mixed. Section 2.
4. **`P(job_k uses j)` is either observed or forecast.** Ex post it is 0 or 1 from the settlement ledger. Ex ante it is a forecast used to price the asset. Keep two ledgers: realized value and forward value. Section 9.
5. **`w_C` and `w_T` are buyer-specific and not constant.** Latency is worth almost nothing far from a deadline and a great deal near one. Section 8.

The sentence the system should be able to emit at the end is:

> Module `X` v1.2 reduced prover gas by `N` PGU (`p`% median, paired 95% interval `[a, b]`) across `n` jobs funded by `m` distinct unaffiliated payers, worth `Y` PROVE at the prices those jobs actually cleared at. Wall-clock latency saving is modeled at `Z` seconds per job from the PGU calibration and was measured on `s` audited jobs.

Every number in that sentence has a defined provenance. That is the whole point.

## 2. Units: what `C` and `T` are in this project

### Cost is PGU, priced at the clearing rate

The frozen evaluation policy already chooses this: `primaryMetric` is "prover gas units (PGU) per holdout block from SP1 execute mode", deterministic, with wall-clock proving explicitly not a gate. That is the right choice for a value ledger too, for three reasons.

- **PGU is a cost model, not a wall-clock reading.** Succinct defines prover gas as a linear regression over per-shard trace heights that predicts core GPU proving time, calibrated to be of similar magnitude to cycle count but much better at predicting proving time (ECDSA recovery takes more than twice as long as a keccak workload with fewer cycles). It is what the prover network actually bills against.
- **PGU is available without proving.** It comes from execute mode. The one recorded run in this repo executed mainnet block 18884864 in 3.95 s and reported 108,529,239 PGU over 89,571,530 cycles. Proving the same block takes minutes to hours depending on hardware. So the counterfactual "execute the baseline guest on the same witness" costs seconds, not a second proof.
- **PGU is reproducible by third parties.** Given the committed witness and the two guest ELFs, anyone can rerun execute mode and get the same PGU. Wall-clock cannot be audited this way.

Price: the Succinct network quickstart shows a request with a 0.2 PROVE base fee and a maximum of 2.0 PROVE per billion PGU (bPGU), settled by reverse auction among staked provers. Boundless uses the same shape (per-cycle work measured inside the proof, reverse Dutch auction). So `w_C` has a natural unit: the PROVE-per-bPGU rate the job actually cleared at, or a disclosed fixed-machine cost model when jobs run on owned hardware.

### Latency is modeled from PGU, or measured on pinned hardware, never both silently

`T` on shared or unknown hardware is noise. The apparatus notes already say wall time on a GitHub runner "is not a benchmark". Two honest options:

- **Modeled latency:** `ΔT_modeled = ΔPGU × s`, where `s` is seconds per PGU calibrated once on the pinned proving host. This inherits PGU's reproducibility and is labeled modeled.
- **Measured latency:** paired A/B runs on the pinned box, randomized order, fresh caches, as the experiment's evaluation protocol already specifies. Expensive, so sampled.

Report both with their labels. Never present modeled latency as observed.

### Illustrative arithmetic on the recorded run

Labeled: illustrative, one block, list price not a cleared price, PROVE not converted to ETH.

```text
Block 18884864:           108,529,239 PGU = 0.1085 bPGU
At 2.0 PROVE / bPGU:      0.217 PROVE variable + 0.2 PROVE base fee = 0.417 PROVE cap

5% PGU improvement:       5.43 M PGU saved  -> 0.0109 PROVE per job  (2.6% of the job cap)
20% PGU improvement:      21.7 M PGU saved  -> 0.0434 PROVE per job  (10.4% of the job cap)

5% module, 18,421 jobs of this size: about 200 PROVE of realized saving
```

Two lessons fall out of this before any experiment runs.

1. **The base fee is invariant to the module.** A per-request fee of 0.2 PROVE dwarfs the saving from a 5% improvement on a 4.3 M gas block. A module's realized value is small per job unless the improvement is large, the blocks are large, or volume is large. The value statement must always be in absolute PGU and cleared price, never only in percent.
2. **Break-even is volume-driven.** With the experiment's own formula, `break-even jobs = ceil((bounty + integration cost) / net saving per job)`, a bounty of even a few PROVE needs hundreds of jobs at 5% on blocks this size. That is the honest answer to "is a 5% module worth a bounty": only with volume, or only if latency near a deadline is what is being bought (section 8).

## 3. The counterfactual: "without j" means "with the best alternative"

This is the single most important correction to the formula.

The naive reading sets `C_k(without j)` to the unmodified upstream pipeline. The correct reading, from mechanism design, sets it to the cost of the best allocation that excludes `j`. In VCG terms, an agent's contribution is the welfare with the agent present minus the maximum welfare achievable without it; the payment is the externality it imposes, and this is what makes truthful reporting a dominant strategy. Applied here:

```text
ΔC_jk = min over alternatives a ≠ j of C_k(a) − C_k(j)
```

Consequences:

- If a competing module `k` achieves 4.8% and `j` achieves 5.0%, `j`'s marginal value is 0.2%, not 5.0%. Its usage receipts are still 100% of jobs that chose it, but its value is small. Usage and value diverge exactly here.
- If upstream RSP merges an equivalent optimization, `ΔC_j` goes to zero for every job pinned to the new upstream, even though old receipts remain. This is the main depreciation mechanism for a proof module and it is discontinuous, not a smooth decay. Section 9.
- The buyer's "best alternative" includes not proving at all, or checking directly on chain. BLUEPRINT flaw F6 already notes small membership jobs may be cheaper to verify directly. For those jobs `ΔC_j` is negative and the ledger should say so.

The registry snapshot in `demand/registry-snapshot.json` is the right place to enumerate alternatives. A value computation that does not name the alternative it compared against is a claim, not a measurement.

## 4. Estimating ΔC per job without doubling the cost of every job

Running "with" and "without" as full proofs for every production job doubles spend and is only acceptable in evaluation. Four estimation tiers, from strongest to weakest evidence, each with a label.

| Tier | How | Cost | Reproducible by others | Label |
| --- | --- | --- | --- | --- |
| 1 | Paired A/B proofs on pinned hardware | 2× proving | No (hardware-bound) | measured latency and cost |
| 2 | Execute mode both guests on the job's committed witness | seconds per job | Yes, from witness + ELFs | measured PGU |
| 3 | Holdout regression: apply the evaluation's paired estimate and interval to new jobs of the same class | free | Yes, from the signed report | modeled from holdout |
| 4 | Self-reported by the worker | free | No | claimed |

Tier 2 is the workhorse. It is cheap enough to run on every job, and anyone holding the witness can replay it. It requires the ledger to store, per settled job, the witness commitment, both guest keys (the module's and the alternative's), both PGU readings and the execute-mode toolchain version. The counterfactual guest must be the registered alternative, not a straw man the worker picked.

Tier 3 is what the experiment's ten-block, sixty-run evaluation produces: a paired median and bootstrap interval. It is honest to extrapolate it to jobs whose blocks fall in the same fork and gas range, and dishonest outside that range. Record the validity domain with the estimate.

Tier 4 should never enter `V_j`. It may be displayed as a quote estimate, which the blueprint already separates from observed durations.

Auditing: a fraction of tier-2 or tier-3 jobs is periodically re-run at tier 1 by the evaluator. Disagreement beyond the interval flags the calibration, not the module.

## 5. Several modules in one job: interaction, Shapley, and why the sum cannot exceed the saving

If a job uses modules A and B that both reduce hashing, `ΔC_A` measured alone plus `ΔC_B` measured alone exceeds `ΔC_{A,B}` measured together. Paying each its solo marginal contribution overpays.

The standard fix is the Shapley value: each module's average marginal contribution over all orderings of the module set. Data Shapley applied exactly this to training points, with Monte Carlo approximation because the subset count is exponential. Here the module count per job is tiny (one to four) and each subset evaluation is a tier-2 execute run of a few seconds, so exact Shapley is affordable: `2^m` execute runs per job, or per job class if using tier 3.

Two properties matter for a payout system:

- **Efficiency:** Shapley values sum to the total saving. Payouts derived from them cannot exceed what the job actually saved. The flattened payee schedule in BLUEPRINT section 5 and AGENT_MARKETPLACE section 12 should be read as a contractual split, not a value measurement; Shapley is the measurement.
- **Null player:** a module that changes nothing gets zero. A bundled dependency that is present but not on the hot path earns receipts but not value. This is the formal version of the blueprint's warning that receipts do not establish causal contribution (flaw F5).

Practical rule for the experiment: with one module and one baseline, Shapley collapses to `ΔC_j`. Do not build the general machinery until a second accepted module exists. Do record enough per job (witness commitment, module set, guest keys) that it can be computed later.

## 6. What the theorem is worth, separately from the module

A Lean theorem never runs inside SP1 (TRIE_MODULE_PROTOCOL section 6: "Lean is not on the runtime proving path"). Its `ΔC` is zero by construction. Its value is of a different kind, and pretending otherwise produces nonsense like "Lemma #712 reduced proving cost".

What the theorem actually does in this system:

1. **Gate value.** The demand requires it (`leanTheoremRequired: true`). Without it the module is not accepted and earns nothing. So the theorem's value is at least the module's value times the probability the module would have been rejected without it. This is an option, not a cost saving.
2. **Risk reduction.** A cache or multiproof optimization that silently accepts a wrong node would produce an invalid statement that still verifies as a proof of the wrong program. The theorem lowers the probability of that class of defect within its stated scope. Expected loss avoided is `P(defect) × loss`, where loss includes every job settled on a bad module and any downstream consumer that acted on the result. Neither factor is directly observable; both can be bounded. The bug log during creation (defects the theorem attempt exposed before submission) is the one direct observation available, and the experiment already requires logging revisions.
3. **Reusability of the statement.** A refinement theorem over an abstract authenticator and decoder can be reused by the next cache-shaped module with a different implementation. That reuse has the shape of Kaliszyk and Urban's lemma value (next paragraph) and can be tracked through `theoremStatements` references in later manifests.

The formal-mathematics literature gives a warning and a usable metric.

- **Warning: citation count is not value.** In the Mathlib dependency graph (308,129 declarations, 8.4 M premise edges), `Eq.refl` ranks second by in-degree with 69,580 citations. PageRank and betweenness pick out foundational plumbing, and mathematically important results such as the Chinese Remainder Theorem do not appear in the top 100. A naive "most used lemma" ledger would pay `Eq.refl`.
- **Usable metric:** Kaliszyk and Urban score lemma usefulness as `Q1(i) = U(i) × D(i) / S(i)`: recursive uses times recursive proof effort it encapsulates, divided by the size of its statement. Their justification is that a lemma with large `D` is expensive to re-derive when needed, so it is worth remembering. Evaluated by adding the top-scored lemmas to the ATP premise pool, this raised Flyspeck proving success from 36.4% to 44.2%. That evaluation design (with versus without, measured on a downstream task) is the same shape as `V_j`. Their `D(i)` is the formal analog of `ΔC`: the work you avoid by having the lemma.

So the honest decomposition is:

```text
V_module    = Σ_k  w_C ΔC_jk + w_T ΔT_jk          (measured, section 2 to 5)
V_theorem   = gate option + expected loss avoided   (bounded, not measured)
            + Σ over later modules that reuse the statement  (tracked by reference)
```

Report them on separate lines. Never add them into one number.

## 7. Enabling modules: when "without j" is "no job"

Some modules do not reduce cost; they make a job possible. A witness-format adapter for a fork the pipeline did not support, or a wrapper that commits the settlement bindings, has `C(without j) = ∞` and the formula explodes.

Replace infinity with the buyer's willingness to pay: `ΔC_jk ≤ maxReward_k`, the funded ceiling already in `JobSpec`. This is the same move Hoffmann, Nagle and Zhou make for open source: supply-side value (cost to recreate once, about 4 billion dollars in their sample) versus demand-side value (what every user would spend to replace it, about 8.8 trillion), with the further finding that 96% of demand-side value comes from 5% of developers. Demand-side value capped at willingness to pay is the right notion for enabling modules; supply-side value is the right floor for the creation bounty.

Label enabling-module value as "capped at funded reward" and keep it out of the PGU ledger.

## 8. Latency is worth a step function, not a line

`w_T · ΔT` treats a second saved as equally valuable everywhere. Buyers do not experience it that way.

- A batch attestation with a day-long `proveBy` values a two-minute saving at roughly zero.
- Real-time block proving (the EIP-8025 direction the blueprint keeps as future scope) values the same two minutes at the full job if it moves the proof from after the slot deadline to before it.

Model `w_T` per job as a function of slack: `w_T(k) = value_k · 1[T_with ≤ deadline_k < T_without]` plus a small linear term for buyers who state one. The quote already carries `proveBy`; the ledger can compute slack after the fact. This also means a module's latency value is concentrated in a subset of jobs, and the summary should say how many jobs it moved across a deadline, not only average seconds saved.

## 9. From realized value to an asset price

`V_j` as a sum over settled jobs is a realized ledger: what the module has already saved buyers. It is evidence. It is not a price. Three further quantities matter for anyone deciding what to pay for the module, its bounty, or its control token.

**Forward value.** `V_j^fwd = Σ over future periods of E[jobs] · E[ΔC per job] · price, discounted`, with `P(job uses j)` now a genuine forecast. Two decay sources dominate and both are discontinuous: upstream absorption (section 3) and toolchain drift (a new SP1 release changes the PGU model, so old `ΔPGU` readings are not comparable to new ones; re-measure on the new toolchain rather than carrying the number over). Pin every ledger entry to the toolchain and PGU model version.

**Fee band.** The contributor fee per job must sit strictly inside `(0, net saving per job)`, or the buyer is worse off using the module. The experiment's `buyer net saving per future job` formula already subtracts the fee; the value ledger supplies the other terms. A fee set at a fixed share of `ΔC_jk` (say 10 to 30%) is self-limiting: it cannot exceed the saving and it scales down automatically when a better alternative appears. A fixed per-job fee does not have that property and can go negative-value silently.

**Bounty floor.** The creation bounty is a supply-side number: what it costs to make the module once (agent inference, proving budget during development, evaluation). It should be compared against forward value, not realized value, because at funding time realized value is zero. The experiment's `creator experiment margin` formula is the creator's side of this.

Contractual splits (the snapshotted payee schedule) stay as they are. The value ledger's job is to make those splits defensible or to show they are not.

## 10. Gaming: what breaks usage-weighted value, with evidence

Every usage-weighted reward system that has been deployed at scale has been farmed. The formula must be designed against these cases, and the blueprint's one-line warning ("self-funded jobs can inflate it") deserves the full treatment.

**tea protocol, 2024 to 2025.** teaRank scored packages by position in the npm dependency graph, PageRank-style, with token rewards. Farmers published spam packages to inflate dependent counts; at the peak, roughly 70% of all new npm packages over six months (about 613,000 to 667,000 of 890,000) were tea spam, later evolving into scripts publishing hundreds of packages per hour linked into circular dependency graphs. Up to 150,000 packages were taken down. The lesson: a value signal derived from a graph that participants can extend for free will be extended until it is worthless.

**Unity Runtime Fee, 2023.** A per-install fee on a metric (installs) that third parties could inflate at no cost to themselves ("install bombing", pirated copies, reinstalls) produced enough backlash that the policy was withdrawn within a year. The lesson: a metric that a hostile party can move against the payer is not a billing basis.

**Optimism RetroPGF.** Formal analysis of its quadratic, mean and median voting rules found exploitable vulnerabilities validated by simulation; builders reported that not knowing how impact is measured made the funding unreliable. The lesson: the measurement rule must be frozen and public before the work, which is exactly what the experiment's frozen acceptance criteria do.

Design consequences for `V_j`:

1. **Only escrow-settled jobs count**, and each job's saving is capped by what its payer actually paid. A job that cost nothing contributes nothing. This makes a fake job cost at least the proving fee.
2. **Weight by payer independence.** Track `m` distinct payers and the share of `V_j` from the top payer. A module whose value is 90% from one address affiliated with its creator has a disclosed value, not an established one. The blueprint already requires disclosing creator and worker relationships; extend that to payers.
3. **Wash economics.** If the contributor receives fraction `r` of a job's fee, a self-funded job costs the full fee and returns `r` of it, a loss of `(1 − r)` per job. Washing is unprofitable as long as the value ledger is not itself converted to money at a rate above `(1 − r)` times job cost. It becomes profitable the moment `V_j` feeds a token price, a retroactive grant or a ranking that unlocks external money. So: the ledger can be published as evidence, but nothing in the protocol should pay out on the ledger total directly. Payouts stay per job, on verified settlement, at snapshotted terms.
4. **The counterfactual guest is chosen by the registry, not the worker.** Otherwise the worker measures against a deliberately slow alternative. Section 3.
5. **The PGU model version is pinned.** Otherwise a toolchain upgrade that shrinks everything looks like module value.
6. **Baseline ownership.** Whoever profits from `ΔC` must not control the baseline (TRIE_MODULE_PROTOCOL: do not disable an upstream optimization to manufacture a baseline). The registry snapshot, taken before creation, fixes the alternatives.

## 11. What to record per job so `V_j` is computable later

Minimum ledger row, written by the indexer from settlement events plus one execute-mode replay:

```text
jobId, settlementTx, payer, worker, contributorPayees
moduleVersion (guest key), alternativeVersion (guest key), registrySnapshotHash
witnessCommitment, blockNumber, gasUsed, fork
pguWith, pguWithout, cyclesWith, cyclesWithout, executeToolchain, pguModelVersion
clearedPricePerBPGU, baseFee, feePaid, contributorFeePaid
proveByDeadline, observedProvingSeconds (if pinned hardware, else null)
evidenceTier (1..4), auditRunRef (if any)
```

From this the summary in section 1 is a query, and every figure in it is either reproducible (tier 2) or references a signed report (tier 1, tier 3).

Per module, additionally keep: accepted evaluation report hash, holdout interval and its validity domain (fork, gas range, toolchain), theorem statement references and the list of later manifests that cite them, and the date any upstream release absorbed the optimization.

## 12. Worked shape of the evidence sentence, using only what exists today

Nothing below is a result. It shows the sentence the system would produce if Experiment 01 accepts a module at exactly the 5% threshold and ten reuse jobs settle on blocks like 18884864.

> Module `witness-cache` v1.0.0 (guest key `…`) reduced prover gas by a median 5.0% (paired 95% interval [3.1%, 6.8%], 10 holdout blocks, SP1 6.8.0 PGU model) against upstream RSP `2013b56` with its arena backend enabled. Across 10 settled reuse jobs from 1 payer (the project team, disclosed as sponsored), measured PGU saving was 54.3 M PGU, worth 0.109 PROVE at a 2.0 PROVE/bPGU list price. Latency saving is modeled only. Contributor fees paid: `…`. Payer-independence: 0 external payers; value labeled sponsored.

The last clause is the one that keeps this honest, and it is the same standard the experiment already applies to demand: sponsored is not external.

## 13. What Experiment 01 can test about the value model itself

Beyond the experiment's existing gates, three cheap additions would validate the ledger design rather than just the module.

1. **Tier-2 replay agreement.** After the evaluator's holdout run, replay execute mode on the same witnesses from a different machine and confirm identical PGU. This establishes that the counterfactual is reproducible, which is the premise of the whole ledger.
2. **PGU-to-seconds calibration.** From the three planned real proofs, fit `s` (seconds per PGU) on the pinned host and report the residual. This is what makes modeled latency a defensible label.
3. **Alternative-aware ΔC.** Compute `ΔC` against both the naive upstream and the arena backend already listed in `existingCapabilities`. If the module's advantage over the arena backend is much smaller than over the naive baseline, the value sentence must use the smaller number. This is the one place the experiment as written could produce an inflated value claim by accident.

## 14. Summary of positions taken

- Value is marginal contribution against the best alternative, not against the naive baseline. VCG framing.
- Cost is PGU priced at cleared rates; latency is modeled from PGU or measured on pinned hardware, labeled either way.
- The counterfactual is computed in execute mode per job, cheap and third-party reproducible. This is the project's structural advantage over every prior usage-reward system.
- Multiple modules per job are attributed by Shapley, which caps total attributed value at total saving.
- The theorem's value is gate, risk and statement reuse; it is bounded and tracked, never added to the PGU number.
- Enabling modules are valued at funded willingness to pay, not infinite savings.
- Latency value is a deadline step, not a line.
- Realized value is evidence; forward value prices the asset; fees are a share of per-job saving; bounties are compared to forward value.
- Nothing pays out on the ledger total. Payouts remain per verified job at snapshotted terms, because every deployed usage-reward system that paid on an inflatable aggregate was farmed.

## Sources

- SP1 prover gas definition and regression model: [Prover Gas, Succinct docs](https://docs.succinct.xyz/docs/sp1/optimizing-programs/prover-gas)
- Base fee and price per bPGU example, auction strategy: [Prover network quickstart, Succinct docs](https://docs.succinct.xyz/docs/sp1/prover-network/quickstart)
- Network architecture, PROVE reverse auction and staking: [Introducing the Succinct Network Architecture and the PROVE Token](https://blog.succinct.xyz/network/introducing-the-succinct-network-architecture-and-the-prove-token/)
- Proof aggregation and the note that single proofs are usually cheaper than aggregation: [Proof Aggregation, Succinct docs](https://docs.succinct.xyz/docs/sp1/writing-programs/proof-aggregation)
- Boundless reverse Dutch auction and proof of verifiable work: [Proof Lifecycle, Boundless docs](https://docs.boundless.network/developers/proof-lifecycle)
- Data Shapley: [Ghorbani and Zou, ICML 2019](https://proceedings.mlr.press/v97/ghorbani19c/ghorbani19c.pdf)
- VCG payments as externality / marginal contribution: [Levin, Stanford Econ 285 notes](https://web.stanford.edu/~jdlevin/Econ%20285/Vickrey%20Auction.pdf), [Brown CSCI 1440 lecture](https://cs.brown.edu/courses/csci1440/lectures/2024/vcg_mechanism.pdf)
- Lemma usefulness metrics `Q1 = U·D/S` and with/without evaluation: [Kaliszyk and Urban, Learning-assisted theorem proving with millions of lemmas](https://pmc.ncbi.nlm.nih.gov/articles/PMC4599631/)
- Mathlib dependency graph, `Eq.refl` in-degree, centrality picking plumbing: [The Network Structure of Mathlib](https://arxiv.org/html/2604.24797v2)
- Supply-side versus demand-side value of open source: [Hoffmann, Nagle and Zhou, The Value of Open Source Software, HBS working paper 24-038](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4693148)
- tea protocol reward design: [What is Proof of Contribution, tea docs](https://docs.tea.xyz/tea/i-want-to.../learn-about-proof-of-contribution/what-is-proof-of-contribution-technical)
- tea protocol npm spam scale: [devclass, 70% of new npm packages](https://devclass.com/2024/08/07/npm-overflowing-with-tea-spam-spills-out-from-70-of-all-new-packages-research/), [Sonatype](https://www.sonatype.com/blog/devs-flood-npm-with-10000-packages-to-reward-themselves-with-tea-tokens), [Socket](https://socket.dev/blog/tea-protocol-spam-floods-npm-but-its-not-a-worm), [Wyss et al., Spilling the Tea](https://ldklab.github.io/assets/papers/scored25-teaspam.pdf), [tea's response](https://tea.xyz/blog/owning-the-fallout-fixing-the-incentives-how-tea-is-responding-to-the-npm-token-farming-campaign)
- Unity Runtime Fee and install bombing: [The Register, Unity apologizes](https://www.theregister.com/software/2023/09/23/unity-apologizes-announces-revised-runtime-fee-criteria/325218), [Yahoo Finance, fee scrapped](https://finance.yahoo.com/news/unity-software-scraps-runtime-fee-165652555.html)
- RetroPGF impact = profit and reliability concerns: [Optimism governance forum](https://gov.optimism.io/t/retropgf-impact-profit-framework/7034); voting vulnerabilities: [Evaluating Voting Design Vulnerabilities for Retroactive Funding, arXiv 2505.16068](https://arxiv.org/pdf/2505.16068)
- Internal: recorded execute run `LemmaXperiment/apparatus/runs/execute-18884864-proofs-34940610488/`, frozen policy `LemmaXperiment/evaluation/policy.json`, pins `LemmaXperiment/apparatus/pins.json`
