# The proof dependency graph: what position is worth, what it is not, and where it leads

Research note, 15 September 2026. Companion to [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md) (value as marginal contribution), [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) sections 10 to 12 (typed edges, no centrality-minted rewards, recursion limits), [BLUEPRINT.md](BLUEPRINT.md) sections 5 and 8 (package DAG, payee flattening, flaws F4, F5, F9), [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md) section 12 (composition) and [QUEUEING_THEORY.md](QUEUEING_THEORY.md) section 10.3 (deadline value). Nothing here is implemented or measured. Every number below comes from `proof_graph_sim.py`, a stdlib-only simulator over a synthetic ecosystem scaled from the one recorded execute run (block 18884864, 108.5 M PGU), and is labeled synthetic. Reproduce with `python3 proof_graph_sim.py tables`.

## 0. Findings first

The brief proposes four things: model the ecosystem as a directed graph `G = (V, E)`; measure reuse centrality; measure marginal contribution `MC_j = C(G − {j}) − C(G)`; combine them into `PCS_j = usage_j × marginal_speedup_j × success_j × dependency_reach_j` as a core feature of the market. It also says this is "far more interesting than token price", and that part is right. The findings, in the order a reader most likely needs them:

1. **The object is right; the product is wrong.** The ecosystem is a graph, and the removal counterfactual `MC_j` is the correct value quantity: it is the graph form of the per-job `ΔC_jk` in PROOF_MODULE_VALUE section 1 and of the VCG externality in its section 3. The `PCS` product is not. It multiplies unlike units (jobs × fraction × fraction × nodes), counts descendants twice (usage and reach both count them), presupposes what it multiplies (a module with no successful jobs has no measured speedup either), and amplifies whichever factor is cheapest to inflate. The blueprint (section 8, "avoid the study's multiplicative utility score as a pricing oracle") and EIP8025 section 11 ("do not multiply these unlike units into one universal truth score") already reject this shape. In the simulation, `PCS` ranks a shared codec first and the settlement wrapper second; neither is what anyone pays for, and the wrapper is not for sale. Section 5.

2. **It is not one graph.** The project has three artifact kinds (theorem, package, runtime proof) and six edge kinds (EIP8025 section 10). "Removing `j`" means something different in each layer: a theorem's removal costs a gate and some risk (PROOF_MODULE_VALUE section 6); a package's removal costs substitution to the best alternative; a runtime proof's removal costs inline recomputation, and that edge only exists under recursive aggregation. A single centrality run across layers ranks plumbing at the top. That is the documented result on the Mathlib graph, where `Eq.refl` is the second most cited declaration and PageRank and betweenness pick foundational plumbing rather than important theorems. Section 2.

3. **`MC_j` on a graph is an AND/OR problem, and the cascade is the whole point.** `C(G)` is the cheapest way to serve every settled job from the available modules: AND edges for dependencies, OR edges for alternative implementations. Finding a minimum-cost AND/OR solution is NP-hard in general (even with unit weights and OR out-degree at most two), but this market's graph will have dozens of packages, at most eight payees per job and one to four optimization modules per job, so exact computation is trivial: the simulator solves every single-node removal on a 60-job ecosystem in well under a second. What matters is the cascade: removing a node removes everything that transitively depends on it. In the simulation a shared codec that no program names directly has `MC = 0` without the cascade and `MC = 711 M PGU` with it. Section 3, table T2.

4. **Reach measures exposure; it does not measure value. Both are useful, for different jobs.** Reach and `MC` diverge exactly where alternatives exist. The npm literature makes the same point from the risk side: an average package implicitly trusts 79 packages and 39 maintainers, and a handful of maintainer accounts reach most of the ecosystem. That is why `left-pad` mattered, not because `left-pad` was valuable. Use reach (money-weighted, over settled jobs) to prioritize audits and redundancy; use `MC` and Shapley to defend fees. Section 4.

5. **The one thing the graph gives the market that the ledger does not is a demand signal.** A node with no alternative for some job class and large money-weighted reach is a single point of failure whose value is undefined: every job using it falls to the buyer's willingness to pay, so `MC` explodes, and the enabling surplus cannot be attributed (all required modules are symmetric complements: stand-alone `MC` gives each the whole surplus, Shapley gives each an arbitrary `1/n`). The correct response is not to pay it more but to fund an alternative: post a redundancy bounty through the existing commission flow (AGENT_MARKETPLACE section 2), capped at `min(exposure, recreation cost)`. Once an alternative exists, `MC` becomes finite and measurable and the fee band of PROOF_MODULE_VALUE section 9 applies. The graph metric becomes a generator of Experiment-01-shaped demands. Section 7, table T7.

6. **Attribution inside a job is the Shapley value of the saving game; on this graph shape it is cheap, and it is not split-proof.** Per job, players are the optional market modules, `v(T)` is the measured PGU saving with `T` available (execute mode, tier 2), and Shapley sums to the job's saving and gives null players zero; the simulation confirms `Σ Shapley + enabling surplus = total saving` exactly. This is "game-theoretic centrality" in the sense of Michalak et al., which is the rigorous version of what the brief calls a centrality score. On tree-shaped dependency structures Shapley is linear time (Megiddo 1978; the airport rule of Littlechild and Owen). But Knudsen and Østerdal show Shapley is not split-proof in general, and the simulation shows it: republishing one module as two required halves raises the pair's Shapley share by 18 percent. The fix is to attribute to payees, not to nodes: with creators as players the split changes nothing (table T6). Section 6.

7. **Plumbing is over-credited by every short-run measure, including Shapley; the long-run cap fixes it.** The shared codec in the simulation has a higher Shapley total (133.9 M PGU) than the cache built on it (103.9 M) because it is a complement to every optimization. That is the correct short-run answer and the wrong long-run one: dependents could be re-based on the upstream codec for a fraction of that. Cumulative claimable value is bounded by `min(attributed saving, recreation or re-basing cost)`, which is the supply-side ceiling of Hoffmann, Nagle and Zhou and the `D(i)` term in Kaliszyk and Urban's lemma metric. With the cap the codec drops to 60 M and the cache becomes the most valuable market asset. Section 3.4.

8. **Every free-to-extend graph metric has been farmed; here, the edge types differ in what they cost to forge.** Registry edges (package depends on package) cost curation only; job edges cost an escrowed fee, of which `(1 − r)` is lost to a washer; recursive-proof edges cost proving. In the simulation, 20 sybil packages raise reach and `PCS` by 1.53× and `MC` by 1.00×; 20 wash jobs raise `MC` by 1.5× but leave independent-payer `MC` unchanged and cost the attacker 47 PROVE per PROVE of ledger value fabricated. The attack the graph framing newly exposes is witness gerrymandering (funding jobs on inputs where `j` shines); the sealed holdout and payer-independence weighting are the defenses. Section 8, tables T4 to T6.

9. **Runtime proofs have graph value only under aggregation, and only with at least two parents.** For a child proof reused by `n` parents, `MC(n) = n·i − (c + n·v)` with `i` the inline cost, `c = i + o` the cost of proving it separately and `v` the in-guest verification cost; break-even is `n* = (i + o)/(i − v)`, always above one. Succinct's documentation says one combined program is generally cheaper than aggregating. The brief's "Proof P depends on Proof Q" edge is real but rare, and the apparatus `report.csv` already carries the `verify_sp1_proof` column that would record it. Section 9, table T8.

10. **The graph is a temporal DAG of immutable versions.** Content addressing makes cycles impossible and edges always point to older nodes, so raw counts favor old nodes (the citation-network age bias). Score lineages, not versions; age-normalize; record upstream absorption as an edge that zeroes forward `MC` for jobs pinned to the new upstream. Section 10.

11. **What to build: a Proof Graph Ledger with five labeled metrics and three consumers, and no payout on any of them.** Metrics: receipts (contractual flow), reach (exposure), attributed saving (Shapley, tiered, capped), exposure without alternative (criticality), payer independence. Consumers: the package explorer, a redundancy-bounty generator, audit sampling. Money-flow precedents exist (Deep Funding's fractional-credit edges; Drips' recursive dependency splits), and the blueprint's flattened payee schedule is the same idea truncated to depth one; keep it contractual and snapshotted. Sections 11 and 12.

## 1. The brief against the existing positions

| Brief | Existing position | Resolution |
| --- | --- | --- |
| `V` = theorem/proof modules, one node type | Three artifact kinds stay separate (BLUEPRINT §8; PROOF_MODULE_VALUE §6: "never add them into one number") | Typed multilayer graph; per-layer removal semantics; no cross-layer centrality |
| `E` = dependency relationships, one edge type | Six edge kinds, "not interchangeable" (EIP8025 §10) | Typed edges with different attestation strength and forge cost (§2.2) |
| Reuse centrality: "how many successful proofs depend on this module" | Receipts are not causal contribution (F5); only escrow-settled jobs count (PROOF_MODULE_VALUE §10) | Keep as money-weighted reach over settled jobs; label it exposure, not value |
| `MC_j = C(G − {j}) − C(G)` | `ΔC_jk` against the best alternative (PROOF_MODULE_VALUE §3); Shapley for interaction (§5) | Adopt, with `C` defined as an AND/OR minimum, cascade included, tier-labeled, capped by recreation cost |
| `PCS = usage × speedup × success × reach` | "Avoid the multiplicative utility score" (BLUEPRINT §8); "do not multiply unlike units" (EIP8025 §11) | Reject as a score; publish a vector of labeled metrics; if one number is needed for ranking, use independent attributed saving (§5.3) |
| "Core feature of your market" | "Graph centrality may help discovery. It should not directly mint rewards" (EIP8025 §10) | Core feature as explorer, demand generator and audit sampler; never as a payout basis |
| "Far more interesting than token price" | "Nothing pays out on the ledger total" (PROOF_MODULE_VALUE §14) | Agreed, and precisely because it is not a price |

The brief allows that it "could perhaps be inconsistent". The inconsistency is in one place: it treats position in the graph as value. Position is exposure. Value is what disappears when the node does and the best alternative takes over. The graph lets you compute that; position alone does not.

## 2. What the graph actually is

### 2.1 The brief's picture, typed

The brief draws lemmas feeding modules feeding proofs. In this project's vocabulary each arrow is a different relation with a different source of truth:

```text
THEOREM LAYER     T-cache-refinement          T-multiproof-equiv        T-codec-canonical
(kernel-checked;        | assures                    | assures                 | assures
 edge declared)         v                            v                         v
PACKAGE LAYER     witness-cache@1 ──depends──>  codec@1  <──depends──  multiproof@1
(manifests; DAG         |                            ^
 by content hash)       |                            └──depends── arena-backend@1, fork-adapter@1
                        | executed-in  (program key recorded in the settled job)
RUNTIME LAYER     job P (payer p1, fee, PGU with, PGU without)      job Q (payer p2, ...)
(escrow-attested)       | verifies-child  (only under aggregation; parent commits child vkey + digest)
                  child proof R
```

"Lemma A and Lemma B feed Module X" is two `assures` edges. "Module X feeds Proof P and Proof Q" is two `executed-in` edges from settled jobs. "Proof P also depends on Module Y" means P's program is a composite package whose closure contains both X and Y; the blueprint's PackageRegistry already models that as a flattened, deduplicated dependency set. "Proof P depends on Proof Q" (a runtime proof depending on a runtime proof) exists only when P's guest verified Q with `verify_sp1_proof(vkey, public_values_digest)` and committed to it; it is the one edge the chain can vouch for cryptographically (section 9).

### 2.2 Nodes and edges, with where each comes from

Nodes:

- theorem statement: `theoremStatementHash`, toolchain, axiom report (manifest `theoremStatements`);
- package version: manifest hash, artifacts, `dependencyVersions`, proposed payees (PackageRegistry or ModuleRegistry);
- program version: guest key, verifier version, `workloadRelationId` (ProgramRegistry);
- settled job: `jobId`, payer, worker, program used, fee, `pguWith`, `pguWithout` (ProofMarket events plus the tier-2 replay of PROOF_MODULE_VALUE section 11);
- payee address (snapshotted payout schedule);
- upstream release: pinned commit of RSP/SP1, a non-market node that everything hangs from.

Edges:

| Edge | From, to | Source | What vouches for it | Cost to forge one |
| --- | --- | --- | --- | --- |
| assures | theorem → package | manifest reference | kernel check of the theorem; the reference itself is declared | one evaluation |
| depends | package → package | `dependencyVersions` | declared, curated | registry curation |
| implements | program → package | ProgramRegistry | curated | curation |
| substitutes | program ↔ program | same `workloadRelationId` | registry | curation |
| executed-in | job → program | settlement event | escrow and verifier | the job's fee |
| verifies-child | proof → proof | parent's public values | the proof itself | a proving run |
| pays | job → payee | settlement event | escrow | the job's fee |
| absorbed-by | upstream release → package | curator | declared | curation |

The chain vouches for exactly three edge types: `executed-in`, `pays`, `verifies-child`. Any metric is only as trustworthy as its weakest edge. Reach over `depends` edges is a claim; usage over `executed-in` edges is a fact about payments; `MC` over settled jobs with tier-2 replays is a reproducible measurement.

### 2.3 Structural facts that shape every algorithm

- **Acyclic by construction.** A manifest hash covers its dependency hashes, so a cycle would need a hash fixpoint. The registry's acyclicity requirement (BLUEPRINT section 5) is therefore structural, not a policy. Cycle detection is a sanity check, not a defense.
- **Temporal.** Every edge points from a newer node to an older one. The package layer is a citation network, with the citation network's known bias: older nodes accumulate more in-edges regardless of quality (section 10).
- **Bipartite between packages and jobs.** Jobs point at programs; programs at packages. HITS-style hubs (jobs and composites that use many modules) and authorities (modules used by many jobs) are the natural pair, and both are just counts over settled jobs.
- **Small.** Dozens of packages, hundreds to thousands of jobs, at most eight payees and a handful of optional modules per job. Every algorithm below is exact. The NP-hardness results in section 3 matter only as a reason not to design for the general case.
- **Versioned.** `witness-cache@2` does not inherit `@1`'s dependents; dependents must republish to move. Metrics live at version level and aggregate to lineage level, which is what the optional ERC-721 controls (AGENT_MARKETPLACE section 5).

## 3. Removal semantics: what `C(G − {j})` means

The brief writes `MC_j = C(G − {j}) − C(G)` without saying what `C` is or what happens to `j`'s descendants. Both choices change the answer by orders of magnitude.

### 3.1 `C(G)` is a minimum-cost AND/OR solution

Each job class `k` has a set of feasible program configurations (OR choices). Each configuration is a set of modules, and each module requires the closure of its dependencies (AND). Given the set `A` of available modules, the job's cost is

```text
cost_k(A) = min( none_k,  min over configurations c with closure(c) ⊆ A of PGU_k(c) )
C(G)      = Σ over settled jobs k of cost_k(V)
MC(j)     = Σ_k [ cost_k(V − {j} − dependents(j)) − cost_k(V) ]
```

`none_k` is the buyer's fallback when no configuration is feasible: the direct onchain check for small membership jobs (BLUEPRINT flaw F6), or the funded `maxReward` when the proof is the only option (PROOF_MODULE_VALUE section 7). `PGU_k(c)` is the tier-2 execute-mode reading of configuration `c` on job `k`'s committed witness. The ledger already records `pguWith` and `pguWithout`; the graph version needs the reading for every feasible configuration of the class, which is the "counterfactual matrix" of section 12.

Finding a minimum-cost solution of an AND/OR graph is NP-hard in general (Sahni 1974; Dantas da Silva, Protti and Souza show it stays NP-hard with unit weights and OR out-degree at most two). None of that bites here: with four optional modules per class there are at most sixteen subsets, and the simulator evaluates every removal on 58 settled jobs in milliseconds. The existing EIP8025 section 10 warning stands: use bounded enumeration, not a general planner.

### 3.2 The cascade is not optional

`dependents(j)` in the formula is the set of every module whose closure contains `j`. Drop it and `MC` silently becomes "the configurations that name `j` directly", which for shared infrastructure is none of them:

```text
T2. Cascade: removing a node removes everything that depends on it
node             dependents                                                                MC local M  MC short M
---------------  ------------------------------------------------------------------------  ----------  ----------
codec@1          ['arena-backend@1', 'fork-adapter@1', 'multiproof@1', 'witness-cache@1']         0.0       711.0
witness-cache@1  -                                                                              158.5       158.5
arena-backend@1  -                                                                               49.2        49.2
fork-adapter@1   -                                                                              481.4       481.4
telemetry@1      -                                                                                0.0         0.0
```

Synthetic. `M` is millions of PGU-equivalents. A ledger that only looks at program manifests assigns the codec nothing; the cascade assigns it every saving in the ecosystem. Neither is the number to pay on (section 3.4), but the second is the number that describes exposure. This is the same computation as DebtRank in financial networks: the systemic loss triggered by one node's failure, propagated along edges, and it is a risk measure there too.

### 3.3 Three horizons of "without `j`"

The formula hides a time scale. There are three defensible readings, and the ledger needs all three under different labels.

| Horizon | "Without `j`" means | What it measures | Label |
| --- | --- | --- | --- |
| Instant | `j` and its dependents vanish; only nodes that exist today remain | What breaks now; exposure | risk |
| Substitution | Jobs move to the best registered alternative at the same `workloadRelationId` | Value against the best alternative (PROOF_MODULE_VALUE §3) | measured, tier 2 or 3 |
| Long run | The ecosystem re-bases dependents on an alternative or recreates `j` | Ceiling on cumulative claimable value | cap |

The graph computes the first two directly. The third needs one declared number per package: the cheaper of re-basing its dependents on an existing alternative or recreating it (the supply-side value of Hoffmann, Nagle and Zhou; for a lemma, Kaliszyk and Urban's `D(i)`, the proof effort the lemma encapsulates). For public code the recreation cost of an identical copy is near zero, which is BLUEPRINT flaw F4 restated: ongoing fees on public modules are contractual, enforced by settlement, not by scarcity. The cap therefore matters most for plumbing that is cheap to route around.

### 3.4 The plumbing problem, in numbers

The full node table of the synthetic ecosystem. Columns: direct dependents (`in`), transitive reach (packages plus settled jobs), settled jobs using the node (`usage`), fees of those jobs, minimum number of feasible alternatives across the jobs using it (`alt`, 0 means enabling for some job), `MC` split into the substitution part and the enabling part, Shapley over the saving game, declared recreation cost, Shapley capped by it, and the brief's `PCS` in two readings (section 5).

```text
T1. Synthetic ecosystem: every metric per node (M = million PGU-equivalents)
    settled jobs: 58, failed: 2, C(G) = 3,956.8 M PGU
node                 in  reach  usage  money PROVE  alt  MC subst M  MC enable M  Shapley M  recreate M  capped M  PCS(job)  PCS(MC)
-------------------  --  -----  -----  -----------  ---  ----------  -----------  ---------  ----------  --------  --------  -------
codec@1               4     62     58        19.51    0       229.6        481.4      133.9        60.0      60.0     509.1    584.0
bindings-wrapper      0     58     58        19.51    0         0.0      2,408.5        0.0         inf       0.0     476.3   1850.6
upstream-rsp          0     38     38        15.39    0         0.0      2,334.0        0.0         inf       0.0     176.3    770.7
witness-cache@1       0     38     38        15.39    1       158.5          0.0      103.9     1,500.0     103.9     176.3     52.3
arena-backend@1       0     30     30        12.13    3        49.2          0.0       27.3     1,000.0      27.3      54.8     12.7
multiproof@1          0     20     20         4.12    1        16.5          0.0        8.3       800.0       8.3      72.2     84.5
telemetry@1           0     13     13         5.17    5         0.0          0.0        0.0        50.0       0.0      10.2      0.0
fork-adapter@1        0      8      8         3.26    0         0.0        481.4        0.0       600.0       0.0      23.5     35.2
upstream-codec        1      1      0         0.00  n/a         0.0          0.0        0.0         inf       0.0       0.0      0.0
membership-baseline   0      0      0         0.00  n/a         0.0          0.0        0.0         inf       0.0       0.0      0.0

    efficiency check: sum of Shapley 273.4 M + enabling surplus 437.6 M = 711.0 M; total saving vs upstream-only = 711.0 M
    Shapley by creator (payee-level): alice 240.6 M, bob 24.6 M, carol 8.3 M, erin 0.0 M
```

Synthetic; parameters chosen so each phenomenon is visible. Four things to read off it.

- **`codec@1` tops reach, both `PCS` readings and even Shapley over nodes** (133.9 M against the cache's 103.9 M), because every optimization is hard-wired to it and complements share credit. Its declared re-basing cost is 60 M, so its capped value is 60 M and the cache (103.9 M, far below its 1,500 M creation cost) is the most valuable market asset. This is the `Eq.refl` result reproduced with money: plumbing wins every position-based ranking and loses to the long-run cap.
- **`bindings-wrapper` and `upstream-rsp` are not for sale and have the largest exposure.** Every job needs them; their `MC enable` is the sum of every buyer's willingness to pay. The brief's `PCS(MC)` reading ranks them first and second. A score that puts unpriced infrastructure at the top of an asset ranking has answered the wrong question.
- **`telemetry@1` is the null player:** bundled into thirteen settled jobs, positive reach, positive `PCS`, zero `MC`, zero Shapley. This is flaw F5 (receipts do not establish causal contribution) in one row.
- **`fork-adapter@1` has zero Shapley and 481 M of enabling exposure.** It saves nothing; it makes eight jobs possible. Its value is capped at those buyers' willingness to pay and belongs in the criticality table (section 7), not in the saving ledger.

## 4. Centrality: what each standard measure means here, and what it costs to fake

| Measure | What it computes on this graph | What the literature found | Cost to move it | Legitimate use |
| --- | --- | --- | --- | --- |
| In-degree | direct dependent packages | `Eq.refl` is second in Mathlib by in-degree (69,580 citations) | one manifest per unit | display only |
| Transitive reach | all descendant packages and settled jobs | npm: a package implicitly trusts 79 packages and 39 maintainers; `left-pad` | one manifest per package unit; a fee per job unit | exposure, audit priority |
| PageRank, Katz | attenuated reach on the reversed DAG | tea farmed npm to about 70 percent spam; on a DAG it favors old nodes | free at the registry | discovery, age-normalized |
| HITS | hubs: composites and jobs using many modules; authorities: modules used by many jobs | fits the bipartite package-job layer | mixed | discovery |
| Betweenness | brokerage between layers | Mathlib: picks plumbing, not theorems | free | none |
| Money-weighted reach | fees of settled jobs downstream | receipts are not value (F5) | a fee per unit | exposure in PROVE |
| `MC` (removal counterfactual) | AND/OR recomputation with cascade | VCG externality; DebtRank | needs a slower registered alternative (registry-controlled) or wash jobs | value, tier-labeled |
| Shapley over the saving game | game-theoretic centrality (Michalak et al.) | efficiency and null player hold; not split-proof (Knudsen and Østerdal) | wash jobs; splitting (defeated at payee level) | attribution within a job |
| OR-degree, articulation | number of registered alternatives per job class | supply-chain single points of failure | none, it is structural | redundancy bounties |

Two general observations. First, every measure in the top half is computed over declared edges and is therefore a claim; every measure in the bottom half is computed over settled jobs and is therefore about money that moved. Second, the measures that are hardest to fake (`MC`, Shapley) are exactly the ones that need the tier-2 counterfactual matrix, which only this project's execute-mode design makes cheap. That is the structural advantage PROOF_MODULE_VALUE section 14 identifies, and it transfers to the graph unchanged.

## 5. Six properties a payout-safe score must have, and how `PCS` does

### 5.1 The properties

1. **Null player.** A node whose removal changes no settled job's cost scores zero.
2. **Bounded.** The sum of scores over nodes does not exceed the total measured saving of settled jobs (Shapley's efficiency axiom, or a weaker upper bound).
3. **Free-action invariant.** No action that costs the actor nothing (publishing a package, creating an address, declaring a dependency) changes any score.
4. **Split-monotone.** Republishing one node as several does not raise the total score of the set.
5. **Registry-chosen counterfactual.** The alternative that "without `j`" is measured against is fixed by the registry snapshot, not by whoever benefits.
6. **Pinned.** Scores are comparable only within one PGU model and toolchain version.

### 5.2 The audit

| Score | 1 null | 2 bounded | 3 free-action | 4 split | 5 registry | 6 pinned | Simulation evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| In-degree | fails | fails | fails | fails | n/a | n/a | T4: 0 → 20 for free |
| Reach | fails | fails | fails | fails | n/a | n/a | T4: ×1.53 for free; T6: ×2.00 |
| PageRank | fails | fails | fails | fails | n/a | n/a | tea protocol |
| Usage receipts | fails | fails | holds (costs a fee) | fails | n/a | n/a | T1: telemetry 13 jobs, zero value |
| `PCS` product | fails | fails | fails | fails | fails | fails | T1, T4, T5, T6 |
| Stand-alone `MC` | holds | fails on complements | holds | fails | holds if enforced | holds if enforced | T6: ×2.00 |
| Shapley over nodes | holds | holds | holds | fails | holds if enforced | holds if enforced | T6: ×1.18 |
| Shapley over payees, capped | holds | holds | holds | holds | holds if enforced | holds if enforced | T6: ×1.00 |

`PCS` fails all six. Three of the failures are structural rather than parametric:

- **Units.** `usage` counts jobs, `dependency_reach` counts nodes and jobs again, `marginal_speedup` and `success` are fractions. The product is in jobs squared. No fee, price or bounty is denominated in jobs squared, so nothing can be paid on it without an arbitrary conversion, and an arbitrary conversion is where every farmed system put its exploit.
- **Double counting and presupposition.** Reach contains usage. Speedup measured on settled jobs already conditions on success, so `success` multiplies in a factor of one on the settled graph; the only place it carries information is as a forward reliability estimate for quotes, where the queueing note already handles it as `P(T ≤ D)`.
- **Amplification.** A product raises the reward for moving the cheapest factor. In T4 the free factor (reach) moves `PCS` by 1.53×; in T5 a paid factor (usage) plus the free factor together move it by 1.97×.

Both readings of `marginal_speedup` were tested. `PCS(job)` credits each module used with the whole job-level saving, which is how an observational implementation would read it. `PCS(MC)` uses the module's own `MC` as the speedup fraction, which is the honest reading. The honest reading makes things worse: it ranks the wrapper and the upstream pipeline first and second, because their `MC` is the entire willingness to pay of every buyer.

### 5.3 If one number is required

Rankings need a scalar. The scalar that survives the audit is independent attributed saving:

```text
IAS_j = min( Σ over settled jobs k with unaffiliated payers of  φ_jk ,  R_j )
```

with `φ_jk` the payee-level Shapley share of job `k`'s tier-2 measured saving and `R_j` the declared recreation or re-basing cost. Publish next to it, never inside it: money-weighted reach (exposure), effective number of payers (`1 / Herfindahl` of fee shares; T5 shows it halving under wash trading), and the enabling exposure from section 7. `IAS_j` may order a listing. It must not pay anyone; payouts stay per job at snapshotted terms (PROOF_MODULE_VALUE section 14).

## 6. Attribution within a job: Shapley on this graph

### 6.1 The saving game

For job `k`, let the fixed set be the non-market modules (upstream pipeline, wrapper, baseline guest) plus the enabling set `E_k` (market modules present in every feasible configuration's closure). The players are the remaining market modules in the class. The characteristic function is

```text
v_k(T) = cost_k(fixed ∪ E_k) − cost_k(fixed ∪ E_k ∪ T)
```

which is a tier-2 execute-mode reading per subset. Shapley over the players attributes `v_k(all)` exactly; the enabling surplus `none_k − cost_k(fixed ∪ E_k)` is reported separately against every member of `E_k` and never split. In T1, `273.4 M + 437.6 M = 711.0 M` is this identity holding over 58 jobs.

Three consequences match PROOF_MODULE_VALUE section 5 and extend it:

- **Sub-additivity is handled.** In the synthetic block class the cache alone saves 5 percent, the arena backend alone 3 percent, both together 6.5 percent. Crediting each with its saving when added alone to the baseline pays 8 percent of a 6.5 percent saving; crediting each with the loss when removed from the full set pays 5. Shapley averages over orderings and pays exactly 6.5.
- **The codec is a player.** Because the optimizations depend on it, `v({cache}) = 0` and `v({codec, cache}) = 5%`: the two are complements, and Shapley gives the codec a share of every optimization's saving. That is what the cap in section 3.4 is for.
- **Tree structure gives closed forms.** When each job's configuration closure is a chain or a tree (which the eight-payee, deduplicated-dependency rule of BLUEPRINT section 5 makes likely), the Shapley value is the airport rule: each segment's saving is shared equally among the players on it, computable in linear time (Littlechild and Owen 1973; Megiddo 1978). The general exponential enumeration is only needed for genuinely interacting modules, and there are at most a handful of those per job.

### 6.2 Shapley is not split-proof; payee-level attribution is

```text
T6. Split: one module republished as two complementary halves (both required)
metric                                one module  two halves  ratio
------------------------------------  ----------  ----------  -----
reach (sum)                                38.00       76.00  x2.00
PCS (sum)                                 176.29      352.58  x2.00
MC short (sum, M PGU)                     158.52      317.05  x2.00
Shapley over nodes (sum, M PGU)           103.88      123.00  x1.18
Shapley over creators: alice (M PGU)      240.56      240.56  x1.00
```

Synthetic. Reach, `PCS` and stand-alone `MC` double on a split because both halves are required and each is credited with the whole. Shapley over nodes rises 18 percent: with two complementary halves there are more orderings in which the pair completes a coalition with the codec and the arena backend, and the extra share comes out of those two. This is the impossibility result of Knudsen and Østerdal: no efficient rule of this family is both merge-proof and split-proof in general.

The defense follows from what actually gets paid. Settlement credits payees, not nodes. Define the players as payees (creators, or the addresses on the snapshotted schedule) and let all of a payee's modules enter a coalition together. Splitting a module changes nothing (last row). What is left is sybil payees, which is the affiliated-payer problem of section 8 with the same disclosure defense. The blueprint's limit of eight unique payees per job is also, in this light, a bound on the number of players.

### 6.3 The dual game: who pays for shared infrastructure

The saving game attributes value to modules. The dual question, how a shared module's fixed cost should be recovered from the jobs that use it, is the classical airport cost-sharing game, and its Shapley solution is equal division of each shared segment among its users. Applied to a creation bounty `B_j` recovered over the jobs that use `j`, the fair per-job contributor fee is `B_j / (number of jobs that will use j)`, which requires forecasting that number. That is the forward-value problem of PROOF_MODULE_VALUE section 9 seen from the cost side, and the graph's contribution to it is a base rate: the reach-growth history of comparable lineages (section 10).

## 7. Where this is headed: the graph as a demand generator

The brief's instinct that this "could become a core feature of your market" is right, but the feature is not a price. It is the loop that a supply-chain map makes possible.

### 7.1 Criticality, and what to do about it

```text
T7. Criticality: nodes with no alternative, ranked by exposure (redundancy bounty candidates)
    exposure = what settled buyers would have lost had the node not existed (cascade included)
node              jobs w/o alt  fees PROVE  exposure M  recreate M  action
----------------  ------------  ----------  ----------  ----------  --------------------------------------------
bindings-wrapper            58       19.51     2,408.5         inf  outside market
upstream-rsp                38       15.39     2,334.0         inf  outside market
codec@1                      8        3.26       481.4        60.0  redundancy bounty <= min(exposure, recreate)
fork-adapter@1               8        3.26       481.4       600.0  redundancy bounty <= min(exposure, recreate)
```

Synthetic. The top two rows are the honest answer to "what is most critical": the upstream pipeline and the settlement wrapper, neither of which the market prices. The next two are actionable. Eight settled jobs on the newer fork have no program that avoids `fork-adapter@1`, and `codec@1` is critical for the same jobs only because the adapter depends on it. The market's response is a commission (AGENT_MARKETPLACE section 2) for an independent adapter, or for an adapter re-based on the upstream codec, with the bounty ceiling `min(exposure, recreation cost)`: 481 M PGU-equivalents, about 0.96 PROVE at the quickstart price, against a declared 600 M recreation cost for the adapter and 60 M for re-basing off the codec. The cheaper fix is the codec re-base, and the table says so.

The loop this closes:

```text
critical node (no alternative, exposure E)
    → redundancy bounty ≤ min(E, R)          (commission flow, EXPERIMENT.md shape)
    → accepted alternative registered        (substitutes edge appears)
    → MC of the original becomes finite      (best-alternative counterfactual now exists)
    → contributor fee falls into (0, ΔC)     (fee band, PROOF_MODULE_VALUE §9)
    → fees decline as alternatives improve   (depreciation, §10)
```

Every step uses a mechanism the project already has. The graph's job is to fire the first one, and to compute the ceiling on the second.

### 7.2 Three other consumers, none of them a payout

- **Explorer.** The package explorer of BLUEPRINT section 10 shows the dependency graph. Add, per node, the five labeled metrics of section 12 and, critically, two numbers side by side: contractual flow (fees actually credited through snapshotted schedules) and attributed saving (Shapley, tiered, capped). Where the first exceeds the second the split is generous; where the second exceeds the first the module is underpaid. Both are useful to the next requester deciding what split to approve. Neither changes an existing job.
- **Audit sampling.** PROOF_MODULE_VALUE section 4 re-runs a fraction of tier-2 jobs at tier 1. Sample proportional to money-weighted reach: a wrong reading on a node that 58 jobs pass through matters more than one that 8 pass through. Exposure is exactly the right sampling weight, and exactly the wrong payout weight.
- **Graph-aware quotes.** A quote already names `programId` and `packageVersion`. The indexer can show the requester, next to each quote, the registered alternatives at the same relation and their tier-3 expected PGU. This is the substitution graph made visible at the moment of choice, which is where the best-alternative counterfactual is actually decided.

### 7.3 What it must not become

A token whose price tracks centrality (tea), a retroactive pool that pays on a graph score (the RetroPGF vulnerability analysis), or a fee that a third party can inflate against the payer (Unity). PROOF_MODULE_VALUE section 10 documents all three failures; the graph framing does not escape them, it inherits them, and the only reason this project can use graph metrics at all is that its important edges cost money to create.

## 8. Gaming, measured

### 8.1 Sybil packages

```text
T4. Sybil packages: 20 empty packages declare a dependency on witness-cache@1 (cost to attacker: registry curation only)
metric                before         after  ratio
--------------  ------------  ------------  -----
in-degree                  0            20      -
reach                     38            58  x1.53
usage                     38            38  x1.00
PCS                   176.29        269.07  x1.53
MC short (PGU)  158523090.91  158523090.91  x1.00
```

Synthetic. This is the tea attack in miniature: at its peak roughly 70 percent of new npm packages over six months were spam published to move a graph score. The registry's curation step (BLUEPRINT section 5: "MVP registration is curator controlled") is the only thing that makes it cost anything here, and curation does not scale. Metrics over `depends` edges should be displayed with that caveat and never used for anything that unlocks money.

### 8.2 Wash jobs

```text
T5. Wash jobs: 20 self-funded settled jobs on witness-cache@1 by an affiliated payer
metric                         before   after  ratio
-----------------------------  ------  ------  -----
usage                           38.00   58.00  x1.53
PCS                            176.29  346.68  x1.97
MC short (M PGU)               158.52  237.48  x1.50
MC independent payers (M PGU)  124.31  124.31  x1.00
effective payers (1/HHI)         6.75    3.44  x0.51
    attacker outlay: 7.40 PROVE net of the 10% contributor share (20 jobs) to add 0.158 PROVE of measured
    saving to the ledger: 47 PROVE spent per PROVE of ledger value.
```

Synthetic. Wash jobs are real jobs with real execute-mode savings, so `MC` over all settled jobs rises. Three things contain it. The independent-payer `MC` (excluding disclosed affiliates) does not move. The effective payer count halves, which the explorer shows. And the price is 47 PROVE per PROVE of fabricated saving at a 10 percent contributor share, because a wash job pays the whole fee to recover `r` of it. The attack pays only if something external pays on `MC` at more than 47 to 1, which is the precise statement of PROOF_MODULE_VALUE section 10, point 3: the ledger is evidence, and the moment it feeds a token price or a grant, washing becomes rational.

### 8.3 Witness gerrymandering

The graph framing exposes one attack the per-job ledger does not name. `MC_j` sums over settled jobs, and a payer chooses which inputs to fund. A module that saves 20 percent on blocks with heavy trie access and nothing elsewhere can have its `MC` inflated by funding only the first kind, at full price, with a real independent-looking payer. Nothing about the jobs is fake. Two defenses exist already and a third is cheap:

- the tier-3 holdout estimate is over blocks chosen by a sealed rule (EXPERIMENT section 4), so the evidence sentence's percentage cannot be gerrymandered even if the realized ledger can;
- payer independence weighting discounts any single funder;
- publish `MC` per job class (fork, gas band) rather than pooled, so a module whose value is concentrated in one input class shows it.

### 8.4 Registry politics

The best-alternative counterfactual is only as good as the alternatives the registry admits. A creator who can delay a competitor's registration keeps their own `MC` high. This is governance risk, not a graph property; the registry snapshot rule (taken before creation, PROOF_MODULE_VALUE section 10, point 6) and the curator's disclosed role (flaw F10) are the current mitigations. The redundancy-bounty loop of section 7 pushes in the right direction, since it pays for the alternatives that incumbents would rather not see.

## 9. Runtime proofs: when a proof has dependents

The brief's picture puts proofs at the leaves, and in this system's MVP that is exactly right: a settled runtime proof is consumed once by its consumer contract and has no dependents. The only way a runtime proof acquires an in-edge is recursive aggregation, where a parent guest calls `verify_sp1_proof(vkey, public_values_digest)` and commits to the child. Then the child has marginal value to the parents:

```text
T8. Recursive aggregation: when does a reused child proof have positive marginal value?
    MC(n) = n*i - (c + n*v): i = inline cost of the subcomputation, c = i + o cost of proving it
    separately (o = per-proof overhead), v = cost of verifying the child inside each parent.
    Break-even parents n* = (i + o) / (i - v). All quantities as fractions of i.
o/i   v/i    n*  min n  MC n=1  MC n=2  MC n=3  MC n=5
---  ----  ----  -----  ------  ------  ------  ------
0.0  0.05  1.05      2   -0.05   +0.90   +1.85   +3.75
0.0  0.20  1.25      2   -0.20   +0.60   +1.40   +3.00
0.0  0.50  2.00      2   -0.50   +0.00   +0.50   +1.50
0.1  0.05  1.16      2   -0.15   +0.80   +1.75   +3.65
0.1  0.20  1.38      2   -0.30   +0.50   +1.30   +2.90
0.1  0.50  2.20      3   -0.60   -0.10   +0.40   +1.40
0.3  0.05  1.37      2   -0.35   +0.60   +1.55   +3.45
0.3  0.20  1.62      2   -0.50   +0.30   +1.10   +2.70
0.3  0.50  2.60      3   -0.80   -0.30   +0.20   +1.20
```

Closed form; `o` and `v` are unmeasured. Succinct's documentation is explicit that "proving a single program is faster and more cost-effective than generating multiple proofs and aggregating them, since there is some small overhead to each proof and aggregation", which is the `n = 1` column: always negative. A child proof is an asset only when at least two parents consume it, or when it was already paid for by someone else (a block-level proof reused by two applications that each need a sub-statement of it). Two further conditions from EIP8025 section 12 stand: the parent must bind the child's public values into its own logic, not merely check that some proof verifies; and a proof about yesterday's state has no parents tomorrow.

What the graph needs to record this edge honestly: the parent's committed `(child vkey, public values digest)` pairs, taken from its public values rather than from the worker's claim, and the `verify_sp1_proof` count from the execute report (the apparatus `report.csv` already has the column; it read zero for block 18884864). The `o` and `v` in the table are the two numbers Experiment 01 could measure with one extra proof (section 13).

## 10. Time: versions, lineages, depreciation

- **Age bias.** Every `depends` edge points to an older node, so in-degree and reach grow with age regardless of merit. Citation analysis corrects this with time-rescaled rankings (CiteRank and successors); the equivalent here is reach per month since registration, or an exponentially decayed usage count. Show both raw and normalized.
- **Lineages.** `witness-cache@2` starts with zero dependents. Metrics roll up from version to lineage (sum of settled jobs across versions) because the lineage is what the optional control token governs and what a requester recognizes. Payee schedules stay at version level because that is what each job snapshotted.
- **Depreciation as an edge.** When upstream RSP merges the equivalent optimization, add an `absorbed-by` edge from the upstream release to the package. Forward `MC` for jobs pinned to the new upstream goes to zero on that date, discontinuously (PROOF_MODULE_VALUE section 9); realized `MC` on old jobs is unchanged. A lineage's forward value is its expected reach growth times expected per-job saving, and the absorbed-by edge is the event that ends it.
- **Toolchain drift.** A new SP1 release changes the PGU model. Metrics are comparable within one `pguModelVersion` only; the ledger row carries it, and the explorer should refuse to sum across it.

## 11. Money-flow precedents, and what to borrow

Two live systems route money down a dependency graph.

**Deep Funding** (Ethereum, launched with an initial sponsorship from Vitalik Buterin) builds a dependency graph of repositories (v2: 31 seed repositories, 5,024 dependencies, 14,927 edges) where "the weight of an edge source → target represents the portion of the credit for source that belongs to target", weights out of a node sum to less than one, and the remainder stays with the node. Weights are proposed by competing models and spot-checked by a human jury. Funding then flows along the weighted edges.

**Drips** implements the same flow contractually: a Drip List assigns percentage shares to up to 200 repositories or addresses; when a project claims funds it can forward a percentage upstream to its own dependencies, so a single grant reaches the transitive closure (ENS's list of seven projects reaches over 40 two degrees out).

The blueprint's flattened payee schedule (BLUEPRINT section 5: deduplicate, flatten, at most eight payees, snapshot per job) is Deep Funding's edge weighting truncated to depth one and made contractual. Three things to borrow and one not to:

- borrow the fractional-credit edge as the data model for `pays` and for proposed composite splits: a share out of each node, shares sum to less than one, remainder stays;
- borrow "weights are proposals, spot-checked": Shapley over the counterfactual matrix is the model that proposes; the requester who approves a split is the jury; the tier-1 audit is the spot check;
- borrow Drips' recursion for the proposal, then flatten before snapshot, exactly as the blueprint says, so settlement never traverses a graph;
- do not borrow model-proposed weights as the payout basis. Deep Funding distributes grant money that has no other claimant. This market distributes a buyer's fee, and the buyer approved a specific split for a specific job. Graph-derived weights inform the next approval; they never rewrite a settled one.

## 12. The Proof Graph Ledger: what to record and what to publish

Extends the per-job row of PROOF_MODULE_VALUE section 11. Written by the indexer from chain events, manifests and one tier-2 replay per feasible configuration.

```text
nodes
  nodeId, layer (theorem | package | program | job | payee | upstream)
  contentHash or address, registeredAt, lineageId, pguModelVersion (for job rows)

edges
  edgeId, type (assures | depends | implements | substitutes | executed-in |
                verifies-child | pays | absorbed-by)
  from, to, source (manifest | registry | settlement event | public values | curator)
  attested (kernel | escrow | proof | declared), settlementTx (if any)

counterfactual matrix (per settled job)
  jobId, witnessCommitment, registrySnapshotHash
  for each feasible configuration c of the job's class:
      configurationHash, closure, pgu (tier 2), executeToolchain
  noneOption: kind (direct-check | maxReward), pguEquivalent

metrics (per node, per pguModelVersion, recomputed by the indexer)
  receipts            fees credited through pays edges                       label: contractual
  reach               descendants; money-weighted over settled jobs           label: exposure
  attributedSaving    Σ_k φ_jk, payee-level Shapley, tier, capped by R_j     label: measured / modeled
  enablingExposure    Σ over jobs with no alternative of (none_k − cost_k)   label: at risk
  independence        effective payers (1 / HHI), share from top payer        label: disclosure
```

Consumers: the explorer (all five, labeled), the redundancy-bounty generator (enabling exposure ranked, bounty ceiling `min(exposure, R_j)`), audit sampling (money-weighted reach as the sampling weight). Non-consumers: settlement, which reads only the snapshotted schedule; any token; any retroactive pool.

Staging, consistent with PROOF_MODULE_VALUE section 5 ("do not build the general machinery until a second accepted module exists"): record nodes, edges and the counterfactual matrix from the first job onward, because they cannot be reconstructed later without the witnesses; compute the metrics only when there are at least two market modules to attribute between.

## 13. What Experiment 01 can test about the graph model

Additions to PROOF_MODULE_VALUE section 13, all cheap relative to the planned sixty runs.

1. **Record the full counterfactual matrix on the holdout.** The evaluation already executes A (upstream) and B (candidate) on ten blocks. Executing the arena backend as a third configuration, and B with the arena backend as a fourth, gives the two-player saving game per block: `v({cache})`, `v({arena})`, `v({cache, arena})`. That is enough to compute the first real Shapley split and to show whether the interaction is sub-additive, as assumed in the simulation.
2. **Compute `MC` with the cascade on the real graph.** The real graph after acceptance has one market module and its declared dependencies. Publish `MC local` and `MC short` side by side, as in T2, for every node in the candidate's closure. If any dependency is a hard-wired fork of an upstream crate, its short-run `MC` will equal the module's, and the re-basing cost declared in the manifest becomes the number that matters.
3. **Measure `o` and `v` once.** One additional real proof that verifies one of the three planned proofs as a child gives the per-proof overhead and the in-guest verification cost as PGU, from execute mode, on the pinned toolchain. Table T8 then stops being a closed form with unmeasured parameters.
4. **Declare `R_j` in the manifest.** Add a `recreationCostEstimate` field with its basis (agent inference spend, proving budget, evaluation cost). It is a claim, labeled as such, and it is the only input to the cap that the ledger cannot compute.
5. **Publish the explorer with labels.** Five metrics, five labels, the counterfactual matrix downloadable, and the sentence "no payout is derived from this page" on the page.

## 14. Positions taken

- The ecosystem is a typed, multilayer, temporal DAG. Metrics are computed per layer over typed edges and inherit the attestation strength of the weakest edge they use.
- `C(G)` is a minimum-cost AND/OR solution over settled jobs; `MC_j` includes the cascade; both are exact at this scale.
- Reach is exposure. `MC` against the best registered alternative is value. Recreation cost caps cumulative claimable value. Enabling surplus is contractual and unattributable.
- Attribution within a job is the Shapley value of the tier-2 saving game, computed over payees, capped, and offered to the requester as a proposal before the job, never applied at settlement.
- `PCS` is rejected. If a scalar is required for ranking, it is independent attributed saving, published beside exposure and payer independence.
- The graph's core market feature is the redundancy-bounty loop: critical node → commission → alternative → measurable `MC` → fee band → depreciation.
- Runtime proofs enter the graph only through `verifies-child` edges committed in public values, and have positive marginal value only with two or more parents.
- Nothing pays out on any graph metric. The edges that matter cost money to create, and that, not any formula, is what keeps the metrics honest.

## Appendix. Reproducing the tables

`python3 proof_graph_sim.py tables` prints T1 to T8 with seed 1; `--seed` changes the synthetic job draws. The ecosystem is defined at the top of the script (`MODULES`, `CLASSES`); the cost multipliers, willingness-to-pay fallbacks and recreation costs are the illustrative choices discussed above. Removal, Shapley over nodes, Shapley over creators and the three attacks are each under a hundred lines and use nothing outside the standard library.

## Sources

- Myerson, R. B. (1977), Graphs and Cooperation in Games, Mathematics of Operations Research 2(3): [INFORMS](https://pubsonline.informs.org/doi/abs/10.1287/moor.2.3.225)
- Michalak, Aadithya, Szczepański, Ravindran, Jennings (2013), Efficient Computation of the Shapley Value for Game-Theoretic Network Centrality, JAIR 46: [JAIR](https://jair.org/index.php/jair/article/view/10810), [arXiv](https://arxiv.org/abs/1402.0567)
- Tarkowski, Michalak, Rahwan, Wooldridge (2018), Game-theoretic Network Centrality: A Review: [arXiv 1801.00218](https://arxiv.org/pdf/1801.00218)
- Littlechild and Owen (1973), A Simple Expression for the Shapley Value in a Special Case: [Semantic Scholar](https://www.semanticscholar.org/paper/A-Simple-Expression-for-the-Shapley-Value-in-a-Case-Littlechild-Owen/fc40e3b266ce8dfc71bc91d5268559cc6ce274a7); airport problem overview: [Wikipedia](https://en.wikipedia.org/wiki/Airport_problem)
- Megiddo (1978), Computational Complexity of the Game Theory Approach to Cost Allocation for a Tree: [PDF](http://theory.stanford.edu/~megiddo/pdf/cost_tree.pdf)
- Knudsen and Østerdal (2012), Merging and Splitting in Cooperative Games: Some (Im)Possibility Results, International Journal of Game Theory 41(4): [Springer](https://link.springer.com/article/10.1007/s00182-012-0337-7)
- Dantas da Silva, Protti, Souza (2012), Revisiting the Complexity of And/Or Graph Solution: [arXiv 1203.3249](https://arxiv.org/abs/1203.3249); original NP-hardness: Sahni (1974), Computationally related problems, SIAM Journal on Computing 3(4)
- Battiston, Puliga, Kaushik, Tasca, Caldarelli (2012), DebtRank: Too Central to Fail?, Scientific Reports 2:541
- Zimmermann, Staicu, Tenny, Pradel (2019), Small World with High Risks: A Study of Security Threats in the npm Ecosystem, USENIX Security: [PDF](https://www.usenix.org/system/files/sec19-zimmermann.pdf)
- Decan, Mens, Grosjean (2019), An empirical comparison of dependency network evolution in seven software packaging ecosystems, Empirical Software Engineering 24
- Walker, Xie, Yan, Maslov (2007), Ranking scientific publications using a model of network traffic (CiteRank), Journal of Statistical Mechanics
- Kivelä, Arenas, Barthelemy, Gleeson, Moreno, Porter (2014), Multilayer networks, Journal of Complex Networks 2(3)
- Deep Funding: [deepfunding.org](https://www.deepfunding.org/), dependency graph data and edge-weight definition: [GitHub deepfunding/dependency-graph](https://github.com/deepfunding/dependency-graph), mechanism overview: [Gitcoin](https://gitcoin.co/mechanisms/deep-funding)
- Drips dependency funding: [Drips](https://www.drips.network/solutions/dependency-funding), Drip Lists: [docs](https://docs.drips.network/support-your-dependencies/overview/), ENS example: [ENS blog](https://ens.domains/blog/post/supporting-software-dependencies-with-drips)
- SP1 proof aggregation and the single-program cost warning: [Succinct docs](https://docs.succinct.xyz/docs/sp1/writing-programs/proof-aggregation)
- Mathlib dependency graph, `Eq.refl` in-degree, centrality picking plumbing: [The Network Structure of Mathlib, arXiv 2604.24797](https://arxiv.org/html/2604.24797v2)
- Kaliszyk and Urban, lemma usefulness `Q1 = U·D/S`: [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4599631/)
- Hoffmann, Nagle and Zhou, The Value of Open Source Software: [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4693148)
- tea protocol npm spam scale: [devclass](https://devclass.com/2024/08/07/npm-overflowing-with-tea-spam-spills-out-from-70-of-all-new-packages-research/), [Wyss et al., Spilling the Tea](https://ldklab.github.io/assets/papers/scored25-teaspam.pdf)
- RetroPGF voting vulnerabilities: [arXiv 2505.16068](https://arxiv.org/pdf/2505.16068); Unity Runtime Fee reversal: [The Register](https://www.theregister.com/software/2023/09/23/unity-apologizes-announces-revised-runtime-fee-criteria/325218)
- Data Shapley: [Ghorbani and Zou, ICML 2019](https://proceedings.mlr.press/v97/ghorbani19c/ghorbani19c.pdf)
- Internal: recorded execute run `LemmaXperiment/apparatus/runs/execute-18884864-proofs-34940610488/` (108,529,239 PGU; `verify_sp1_proof` = 0), frozen policy `LemmaXperiment/evaluation/policy.json`, simulator `proof_graph_sim.py`
