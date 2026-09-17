# Queueing theory for the proof marketplace: deadlines, provers, and the 99% question

Research note, 15 September 2026. Companion to [BLUEPRINT.md](BLUEPRINT.md), [EXPERIMENT.md](EXPERIMENT.md), [AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md), [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) and [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md). Every simulated number below is produced by [queueing_sim.py](queueing_sim.py) in this folder (standard-library Python, no dependencies; `python3 queueing_sim.py grid` regenerates every table in about two minutes on an 8-core laptop). Published figures are cited; modelled figures are labelled as such. Nothing here is a measurement of this project's own provers, because none exist yet.

## 0. Findings first

The system is: proof jobs arrive, compete for a finite pool of provers, each has a deadline, and a job either has a valid proof by its deadline or it does not. That is a multi-server queue with impatient customers, and the quantity that matters is

```text
P(T <= D)   with   T = W + S
```

where `W` is the time a job waits for a prover, `S` is the proving time once started, and `D` is the deadline measured from the job's arrival. The results, in the order a reader is most likely to need them:

1. **Where the deadline actually comes from.** EIP-8025 defines no deadline at all: proofs are optional, provers are "altruistic", and validators "must not delay block validation or attestation production while waiting for a proof". The number comes from the Ethereum Foundation's realtime-proving definition: proving latency at or below 10 s for 99% of mainnet blocks, because "with the current slot time of 12 seconds and maximum time to propagate data across the network of ~1.5 seconds, realtime means 10 seconds or less". The 12 s slot stays: EIP-7782 (6 s slots) was declined for Glamsterdam. So model both D = 10 s (protocol-meaningful) and D = 12 s (the number in the question). Section 2.

2. **With mean 7 s and p95 11 s, no number of provers reaches 99% at a 12 s deadline.** Response time can never beat service time, so `P(T <= D) <= P(S <= D)`. Fitting a lognormal to (mean 7 s, p95 11 s) gives `P(S <= 12) = 0.973` and `P(S <= 10) = 0.908`; gamma and Weibull fits give 0.976 to 0.981 at 12 s. The simulation confirms the plateau: at 5 jobs/s, 50 provers already deliver 0.9728 and 300 provers deliver 0.9730. Adding provers removes waiting; it cannot remove the tail of the proving time itself. Sections 4 and 5.

3. **What does reach 99%, and what each costs.** Four levers, all quantified in Section 6:
   - run two independent copies of every job and take the first (ceiling 0.9993 at 12 s; consumes 11.6 prover-seconds per job instead of 7);
   - start a second copy if the first has not finished after `t_h` seconds (a hedge): the trigger must satisfy `t_h <= D - q(S)`, which for this distribution means 4 s at the latest with no queueing (ceiling 0.9926) and 3 s with a margin (ceiling 0.9957, 10.5 prover-seconds per job); at 5 s or later the hedge no longer reaches 99%;
   - make every proving run at least 11.2% faster (p99 falls from 13.5 s to 12 s); 15% gives a margin (ceiling 0.9932);
   - relax the deadline: at D = 15 s the single-attempt ceiling is 0.9962.
   Retrying after the assigned prover misses its deadline (the Succinct Prover Network's slash-and-retry path) adds nothing at a 12 s deadline: a retry that starts at the deadline is too late by construction.

4. **How many provers once a policy is chosen.** For arrival rate `lambda` (jobs/s) the offered load is `R = lambda * w` prover-seconds per second, where `w` is the work per job (7 s single, 11.6 s two copies, 10.5 s hedge at 3 s, 5.95 s at 15% faster). The simulated minimal `N` for 99% at D = 12 s is `N* ~ R + beta * sqrt(R)` with `beta` between about 0.5 (large pools) and 1.0 (small pools), the square-root staffing rule of Halfin and Whitt. Concretely (Table T3): at 5 jobs/s, 63 provers with two-copy redundancy, 60 with a 3 s hedge, 35 if provers are 15% faster, 40 if provers behave like Brevis's published Pico Prism 1.0 numbers. At 20 jobs/s: 236, 218, 125 and 143. Section 7.

5. **The N = 100 scenario.** With 100 provers of the stated speed and single assignment, the pool sustains about 13 jobs/s before queueing collapses, but at 97.3% success, never 99%. With two-copy redundancy the same 100 provers sustain about 8 jobs/s at 99.5%; with 15% faster provers about 14 jobs/s at 99.3%. Table T2.

6. **Redundancy only removes the part of the tail that is idiosyncratic to a prover.** If slow blocks are slow for every prover (large gas, pathological opcodes: the "prover stunners" tracked by Ethproofs), running two copies does not help. With half the log-variance block-intrinsic, two-copy redundancy still clears 99% (0.9952); with three quarters it no longer does (0.9897); the hedge policy fails at 99% once more than about a third of the variance is intrinsic. This is why the EF's definition says the tail is "mitigated in future hard forks" rather than by more hardware, and why a module that shortens the tail (the [EXPERIMENT.md](EXPERIMENT.md) deliverable) is worth more than its median saving suggests. Table T5, Section 10.3.

7. **For real-time work there is no room for a per-job auction.** The matching budget is `D - q99(S) - t_settle`. It is negative for the stated distribution at both deadlines and +0.8 s for a Pico-class prover at 12 s. Boundless ramps its Dutch auction over 300 s and Succinct's default timeout is 300 s: those markets serve minute-to-hour deadlines. A real-time supplier must be pre-assigned (standing assignment, service-level agreement, subscription) with the auction moved from the job to the capacity commitment. Section 9.

8. **Today the dominant failure on the live real-time tracker is availability, not speed.** On 15 September 2026 the Ethproofs real-time cohort page shows 38.7% of evaluated slots proven under 10 s, 3.11% "stunned" (over 10 s), 0.02% "paralyzed", and 58.2% offline. Conditional on being online, 92.6% of proofs land under 10 s. Ten independent provers of that reliability would be needed for 99% coverage of a slot; the arithmetic is in Section 8.3.

9. **For this project's own hackathon regime** (CPU proofs that take hours, one to three workers, deadlines of hours), the same model says: with three workers at 50% utilisation, a `proveBy` of three mean proving times gives 98.8% on-time settlement and four gives 99.8%; with one worker at 80% utilisation and a deadline of two mean times it is 40%. Set `proveBy` from a measured `q99(S)` plus settlement time, not from a round number. Table T7, Section 10.1.

## 1. The marketplace as a queue

### 1.1 Notation

| Symbol | Meaning | Unit |
|---|---|---|
| `lambda` | proof-job arrival rate | jobs/s |
| `S` | proving time of one job on one prover (random) | s |
| `mu = 1/E[S]` | completion rate of one prover | jobs/s |
| `N` | active provers (clusters, not GPUs) | count |
| `rho = lambda / (N mu) = lambda E[S] / N` | utilisation | dimensionless |
| `R = lambda E[S]` | offered load, mean number of busy provers (Little's law) | Erlangs |
| `W` | waiting time from arrival to first proving start | s |
| `T = W + S` | response time | s |
| `D` | deadline after arrival | s |
| `F(x) = P(S <= x)` | service-time distribution | |
| `q_p` | p-quantile of `S` (`q99` is the 99th percentile) | s |
| `w` | prover-seconds actually consumed per job under a policy | s |
| `phi` | share of the log-variance of `S` that is intrinsic to the job (shared by every prover that proves it) | 0 to 1 |

The metric is `P(T <= D)`. Everything else (mean wait, utilisation, cost) is instrumental.

### 1.2 Mapping the ProofMarket lifecycle onto queue stages

[BLUEPRINT.md](BLUEPRINT.md) section 7 defines `OPEN -> RESERVED -> ASSIGNED -> SETTLED` with deadlines `acceptBy`, `activateBy`, `proveBy`. In queueing terms it is a tandem of three stations:

```text
arrival (createJob)            OPEN      waiting for an acceptable quote          -> W_match
requester accepts a quote      RESERVED  waiting for the worker to activate       -> W_activate (a chain tx)
worker activates and proves    ASSIGNED  service S = witness fetch + prove + wrap -> S
submitProof + verification     SETTLED   settlement latency                       -> t_settle
```

`T = W_match + W_activate + S + t_settle` and the deadline that matters to the consumer is `proveBy` (submission at or before it is permitted; expiry only after it). The Succinct network has the same shape with an off-chain auctioneer in the `OPEN` stage; Boundless has it with a Dutch-auction ramp in the `OPEN` stage and a lock in the `RESERVED` stage. In every case the `OPEN` stage delay is a matching delay that comes straight out of the proving window.

### 1.3 Three clocks

[BLUEPRINT.md](BLUEPRINT.md) flaw F7 already separates proof delivery, L2 settlement and L1 finality. The queueing model uses only the first clock: `D` is measured from the moment the job exists to the moment a valid proof exists at the consumer. Settlement and finality are added afterwards as constants (`t_settle`) and never inside `S`.

### 1.4 Little's law

`L = lambda * E[T]` for jobs in the system and `R = lambda * E[S]` for provers busy. At 5 jobs/s with 7 s proofs, 35 provers are busy on average whatever `N` is; two-copy redundancy raises it to 58. A worker console that displays a queue length is displaying `lambda * E[W]`, so a growing queue at constant `lambda` means `E[W]` is growing, which is the one early warning a marketplace can read directly from its own indexer ([BLUEPRINT.md](BLUEPRINT.md) screen 5). Ethproofs already splits each proof's time into "queue" and "prove" and instructs readers: "If orange (queue) grows disproportionately, investigate infrastructure bottlenecks."

## 2. Where the deadline comes from

### 2.1 EIP-8025 has no latency window

The draft ([EIP-8025: Optional Execution Proofs](https://eips.ethereum.org/EIPS/eip-8025), created 17 September 2025) is explicit on three points that constrain any model:

- Proof generation is asynchronous and event-driven: "A prover reacts to a new beacon block, constructs the corresponding `NewPayloadRequest`, and calls `proof_engine.request_proofs(...)`".
- Attestation never waits: "Validators must not delay block validation or attestation production while waiting for a proof; if a proof is missing or late, the node attests using the fork choice determined by the execution engine's re-execution of payloads."
- There is no reward: "This EIP does not introduce incentives for proof-generating nodes; for that reason, they are considered altruistic and the mechanism is opt-in."

It bounds proof size (`MAX_PROOF_SIZE = 409600`, 400 KiB, marked provisional in the linked consensus snapshot per [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) section 1) and it references "the execution-validation window introduced by EIP-7732, which defers execution validation until the next beacon block and provides additional time for proof generation". It leaves the number of sufficient proofs `k` open. So a queueing model of EIP-8025 as it stands has a soft deadline (a late proof is simply useless for that slot) and a consumer that wants `k` distinct proof types, not one proof.

### 2.2 The number: 10 s for 99% of blocks

The EF's working definition ([Shipping an L1 zkEVM #1: Realtime Proving](https://blog.ethereum.org/2025/07/10/realtime-proving), 10 July 2025):

| Requirement | Value |
|---|---|
| Latency | `<=10s for P99 of mainnet blocks` |
| On-prem CAPEX | `<=100k USD` |
| On-prem power | `<=10kW` |
| Code | fully open source |
| Security | `>=128 bits` (100 accepted initially) |
| Proof size | `<=300KiB with no trusted setups` |

The rationale is the slot arithmetic quoted in the findings, and the 99% is a P99 over blocks "with the tail end (as well as synthetic DOS vectors) mitigated in future hard forks". The December 2025 follow-up ([#2: The Security Foundations](https://blog.ethereum.org/2025/12/18/zkevm-security-foundations)) reports that "proving latency dropped from 16 minutes to 16 seconds" over 2025 and that "zkVMs now prove 99% of all Ethereum blocks in under 10 seconds on target hardware", and sets milestones of 600 KiB / 100-bit for end of May 2026 and 300 KiB / 128-bit for end of 2026. The Ethproofs 2026 roadmap draft discusses tightening the P99 target to under 8 s and adds a reliability floor of 90% uptime for the real-time cohort ([Ethproofs 2025 Review and 2026 Roadmap](https://hackmd.io/@willcorcoran/S1A840ZMZg)).

Two consequences for modelling. First, "P99 of blocks under 10 s" is a statement about the service-time distribution `S` of one prover on one block, with no queue in front of it: it is `q99(S) <= 10`. Second, the deadline is per block and blocks are independent trials, so a slot-level miss is not carried forward: a prover that abandons a late block and starts the next one behaves like a queue with deadline-triggered abandonment. Section 8.1 shows that the work-conserving alternative (finish the late proof anyway) costs measurable success probability.

### 2.3 Slot time and fork timing

- The slot stays 12 s for planning purposes: "A proposal to shorten slot times to 6 seconds (EIP-7782) was declined for Glamsterdam" ([Chainstack Glamsterdam overview](https://chainstack.com/ethereum-glamsterdam-upgrade/)). Contemporary summaries of the core-dev decision list interference with real-time proving among the reasons; that attribution was not verified against call notes here. A 6 s slot would halve the window: `P(S <= 6)` for the stated distribution is 0.36, so it would require roughly a two-fold prover speedup, not a bigger pool.
- ePBS (EIP-7732) is a Glamsterdam headliner, and the EF's 7 September 2026 priorities target "Shipping Glamsterdam in December 2026". The same post places mandatory proofs several forks out ("Under the current Strawmap ordering, mandatory proofs arrive in K*", with a reordering to L* under review) and describes the arc as "from available and optional, to expected, to mandatory" ([Current and Emerging Priorities](https://blog.ethereum.org/2026/09/07/protocol-priorities)). Under ePBS the proof window is longer than 10 s because execution validation is deferred to the next slot; the exact figure depends on attestation timing and is left as a sensitivity in Table A1 (D = 15 s).

### 2.4 What this means for the question as posed

The question used a 12 s window. The protocol-meaningful number is 10 s today and somewhat above 12 s after ePBS. The document therefore reports D = 10, 12 and 15 s wherever the deadline matters, and treats 12 s as the primary case to match the question.

## 3. The arrival process

### 3.1 One chain is periodic, many chains are Poisson

A single L1 stream is deterministic: one block every 12 s, `lambda = 1/12 = 0.083` jobs/s. That is a `D/G/N` queue (deterministic arrivals, general service, `N` provers), and with `E[S] = 7 s` one prover cluster runs at `rho = 0.58`. The only way a queue forms is a proof overrunning into the next slot; Section 8.1 quantifies it.

A marketplace that serves many chains, rollups and applications sees the superposition of many independent, individually sparse streams. By the Palm-Khintchine theorem the superposition of many independent renewal processes converges to a Poisson process ([Palm-Khintchine theorem](https://en.wikipedia.org/wiki/Palm%E2%80%93Khintchine_theorem)), which is why `M/G/N` (Poisson arrivals) is the right model for the market and `D/G/N` for a single chain. Fifty rollups at 2 s blocks each give `lambda = 25` jobs/s in aggregate, just above the top of the range simulated in Section 7 (20 jobs/s).

### 3.2 What the live markets' parameters say about their regime

- Succinct Prover Network: requests carry a deadline and a maximum fee; the quickstart's default timeout is 300 s, and the walkthrough example uses "a deadline of 10 minutes for the proof" ([SPN overview](https://docs.succinct.xyz/docs/provers/how-it-works/overview), [quickstart](https://docs.succinct.xyz/docs/sp1/prover-network/quickstart)).
- Boundless: the documented example offer has "Length of ramp-up period: 300 seconds", "Lock Timeout: 2700 seconds" and "Timeout: 3600 seconds" ([Boundless proof lifecycle](https://docs.boundless.network/developers/proof-lifecycle)).

Those are deadlines of minutes to an hour with service times of similar order. The 12 s real-time regime is a different operating point of the same model: `D/E[S]` of about 1.5 instead of 5 to 50. Every conclusion below states which regime it belongs to.

### 3.3 Batching changes the arrival process seen by the prover

Boundless provers "batch submissions rather than prove individually", aggregating many requests into one Merkle tree under a single Groth16 proof to amortise on-chain verification. A batch server waits for a batch to fill or a timer to fire before starting; that waiting is pure `W` added to every job in the batch. It is efficient for throughput and cost and hostile to tight deadlines, which is one more reason the real-time regime cannot reuse the batch market's mechanics unchanged.

## 4. Calibrating the service time

### 4.1 Published proving-time data

| Source | Hardware | Blocks | Mean | Share under 10 s | Share under 12 s |
|---|---|---|---|---|---|
| Succinct SP1 Hypercube, May 2025 (as reported by [Aligned](https://blog.alignedlayer.com/the-year-of-zkvm-real-time-proving-milestones-present-and-future/) and [Brevis](https://blog.brevis.network/2025/10/15/pico-prism-99-6-real-time-proving-for-45m-gas-ethereum-blocks-on-consumer-hardware/)) | about 160 RTX 4090 | mainnet | 10.3 s | | 93% |
| Brevis Pico Prism 1.0, 15 Oct 2025 ([blog](https://blog.brevis.network/2025/10/15/pico-prism-99-6-real-time-proving-for-45m-gas-ethereum-blocks-on-consumer-hardware/)) | 64 RTX 5090, 128k USD MSRP | every block of 1 Sep 2025, 45M gas limit | 6.9 s | 96.8% | 99.6% |
| ZisK, Nov 2025 (as reported by [Aligned](https://blog.alignedlayer.com/the-year-of-zkvm-real-time-proving-milestones-present-and-future/)) | 24 RTX 5090 | mainnet | 6.56 s | | 99.74% |
| Brevis Pico Prism 2.0, 12 May 2026 ([blog](https://blog.brevis.network/2026/05/12/pico-prism-2-0-a-5-3x-efficiency-leap-in-real-time-ethereum-proving/)) | 16 RTX 5090 | 60M gas limit | 6.1 s | | |
| Ethproofs live page, 15 Sep 2026 ([blocks](https://ethproofs.org/blocks)) | RTP cohort clusters (ZisK 8x5090, Axiom 16x5090 eligible) | recent blocks, e.g. 41.7M gas in 4.1 s, 34.3M gas in 2.8 s, 23.1M gas in 2.2 s | individual proofs mostly 1.8 to 2.9 s | | |

The question's premise (mean 7 s, p95 11 s) sits between Pico Prism 1.0 and SP1 Hypercube in speed and has a heavier tail than either. Both are plausible for a market that includes provers below the frontier.

### 4.2 Fitting a distribution to (mean 7 s, p95 11 s)

Two moments do not pin down a tail, and the 99% question lives entirely in the tail beyond the 95th percentile. Three common families fitted to the same two numbers:

| Family | Parameters | `P(S <= 10)` | `P(S <= 12)` | `P(S <= 15)` | `q99` | `q99.9` |
|---|---|---|---|---|---|---|
| lognormal | `mu = 1.900, sigma = 0.303` (CV 0.31) | 0.908 | 0.973 | 0.996 | 13.5 s | 17.0 s |
| gamma | `k = 9.97, theta = 0.702` (CV 0.32) | 0.903 | 0.976 | 0.998 | 13.2 s | 15.9 s |
| Weibull | `k = 3.21, lambda = 7.81` | 0.890 | 0.981 | 0.9997 | 12.6 s | 14.3 s |

All three agree that 99% is out of reach at 12 s for a single attempt, and disagree by a factor of two on how far (1.9 to 2.7 points). The lognormal is used from here on because it also reproduces the published data with one free parameter: fitted to Pico Prism 1.0's mean 6.9 s and 99.6% under 12 s, it predicts 96.5% under 10 s against the reported 96.8%. The calibrated parameters:

| Calibration | `mu` | `sigma` | `P(S <= 10)` | `P(S <= 12)` | `q95` | `q99` | `q99.9` |
|---|---|---|---|---|---|---|---|
| question ("spec"): mean 7, p95 11 | 1.900 | 0.303 | 0.908 | 0.973 | 11.0 s | 13.5 s | 17.0 s |
| Pico Prism 1.0 ("pico"): mean 6.9, 99.6% under 12 | 1.908 | 0.218 | 0.965 | 0.996 | 9.6 s | 11.2 s | 13.2 s |
| SP1 Hypercube (May 2025): mean 10.3, 93% under 12 | 2.326 | 0.107 | 0.412 | 0.930 | 12.2 s | 13.2 s | 14.3 s |
| ZisK (Nov 2025): mean 6.56, 99.74% under 12 | 1.856 | 0.225 | 0.976 | 0.997 | 9.3 s | 10.8 s | 12.8 s |

The practical instruction for this project: when measuring your own provers, record enough runs to estimate `q99` directly, and report `q99` alongside the median. [EXPERIMENT.md](EXPERIMENT.md) already forbids tail-latency claims from ten blocks, which is correct: `q99` needs hundreds of blocks.

### 4.3 PGU as the predictor of `S`

[LemmaXperiment/evaluation/policy.json](LemmaXperiment/evaluation/policy.json) makes SP1 prover gas units (PGU) the funded metric because PGU is deterministic for a given guest and input and is what the Succinct network bills (0.2 PROVE base plus up to 2 PROVE per billion PGU in the quickstart). For queueing, PGU is the natural job-size variable: `S = s_0 + s_1 * PGU + noise` on fixed hardware, with `s_1` the seconds-per-PGU calibration that [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md) section 2 asks the experiment to fit from its real proofs. Block gas ranges from under 1M (block 20600066, 0.96M gas) to over 41M on current mainnet, so the job-size distribution is wide and the proving-time distribution inherits that width: this is the intrinsic component of `S`.

### 4.4 Intrinsic versus idiosyncratic variance

Write `ln S = mu + sigma * (sqrt(phi) Z_job + sqrt(1 - phi) Z_prover)`. `Z_job` is shared by every prover that proves the same block (gas, opcode mix, witness size); `Z_prover` is specific to one run (GPU contention, memory pressure, network, a straggling shard). `phi` is the share of variance that redundancy cannot remove. Nobody has published `phi` for Ethereum block proving. The paired A/B design in [TRIE_MODULE_PROTOCOL.md](TRIE_MODULE_PROTOCOL.md) section 8 (three runs per block per variant on fixed hardware) estimates it as a by-product: the between-block variance of block medians divided by the total variance is `phi`. Record it.

## 5. Result 1: adding provers cannot beat the service-time ceiling

Since `T = W + S` and `W >= 0`,

```text
P(T <= D) <= P(S <= D) = F(D)
```

for any `N`, any queue discipline, any arrival process, as long as each job is proven once by one prover. For the question's distribution `F(12) = 0.973` and `F(10) = 0.908`. Simulation (Table T1, 5 jobs/s, single assignment, FCFS, D = 12 s):

| N | `rho` | `P(W > 0)` | mean wait | p99 wait | `P(T <= 12)` |
|---|---|---|---|---|---|
| 36 | 0.972 | 0.814 | 3.63 s | 19.5 s | 0.703 |
| 38 | 0.921 | 0.488 | 0.73 s | 5.7 s | 0.940 |
| 40 | 0.875 | 0.302 | 0.28 s | 2.9 s | 0.964 |
| 45 | 0.778 | 0.068 | 0.04 s | 1.0 s | 0.972 |
| 50 | 0.700 | 0.010 | 0.00 s | 0.0 s | 0.9728 |
| 60 | 0.583 | 0.000 | 0 | 0 | 0.9730 |
| 100 | 0.350 | 0.000 | 0 | 0 | 0.9730 |
| 300 | 0.117 | 0.000 | 0 | 0 | 0.9730 |

Between 36 and 50 provers the pool goes from collapse to the ceiling; beyond 50 (utilisation 70%) the 51st prover buys nothing. **The direct answer to "how many provers for 99%" under the stated assumptions is: there is no such number.** A second answer follows once the assumptions are changed, and that is the useful engineering result.

## 6. Result 2: what reaches 99%, and at what cost in prover-seconds

All ceilings below are analytic for the "spec" lognormal at D = 12 s with independent copies (`phi = 0`) unless stated, and each was reproduced by simulation at light load (Table T2, first rows).

### 6.1 Redundant dispatch (k copies from t = 0, first to finish wins, others cancelled)

`P(min(S_1..S_k) <= D) = 1 - (1 - F(D))^k`:

| k | ceiling at 12 s | prover-seconds per job (simulated) |
|---|---|---|
| 1 | 0.9733 | 7.0 |
| 2 | 0.9993 | 11.6 |
| 3 | 0.99998 | 15.9 |

Two copies cost 1.66x the work of one, not 2x, because the loser is cancelled at the winner's completion. This is the "redundancy-d" model of Gardner, Zbarsky, Doroudi, Harchol-Balter, Hyytiä and Scheller-Wolf ([Reducing Latency via Redundant Requests: Exact Analysis](https://dl.acm.org/doi/10.1145/2796314.2745873), SIGMETRICS 2015) and the older systems intuition of Vulimiri et al. ([Low latency via redundancy](https://doi.org/10.1145/2535372.2535392), CoNEXT 2013). push0 (Section 9) implements exactly this as optional "k-of-n dispatch".

### 6.2 Hedged dispatch (second copy only if the first is still running at `t_h`)

With the second copy started at `t_h` on an idle prover, `P = F(D) + (1 - F(D)) * F(D - t_h)`:

| `t_h` | ceiling at 12 s | share of jobs that spawn a hedge `1 - F(t_h)` | prover-seconds per job (simulated) |
|---|---|---|---|
| 2 s | 0.9976 | 1.000 | |
| 3 s | 0.9957 | 0.996 | 10.5 |
| 4 s | 0.9926 | 0.955 | 9.7 |
| 5 s | 0.9883 | 0.832 | 9.0 |
| 6 s | 0.9829 | 0.640 | |

The trigger constraint is `t_h <= D - q_target(S)` where `q_target` is the quantile the hedge must reach in the remaining time. At a 12 s window with a 7 s mean there is almost no room: a hedge at 3 s fires on 99.6% of jobs, so it is nearly full duplication at a 10% discount. Hedging is the cheap tail cure of Dean and Barroso's [The Tail at Scale](https://doi.org/10.1145/2408776.2408794) (CACM 2013) when `D` is many multiples of the median, which is the minute-scale marketplace regime, not the real-time one.

### 6.3 Reassignment after a lock timeout (the Boundless pattern) and slash-and-retry (the Succinct pattern)

Two variants, depending on whether the first prover's late proof still counts:

```text
A: late proof still accepted, second prover starts at t_L:   P = F(D) + (1 - F(D)) * F(D - t_L)
B: first prover cancelled at t_L (slash, retry):              P = F(t_L) + (1 - F(t_L)) * F(D - t_L)
```

| `t_L` | A | B |
|---|---|---|
| 4 s | 0.9926 | 0.736 |
| 6 s | 0.9829 | 0.591 |
| 8 s | 0.9745 | 0.736 |
| 10 s | 0.9733 | 0.908 |
| 12 s (= D) | 0.9733 | 0.9733 |

Variant A is the hedge of 6.2 under another name. Variant B is strictly worse than doing nothing unless the retry has a full proving window left, so at a 12 s deadline Succinct's "if Bob does not submit a proof ... within 10 minutes, the proof request is canceled and Bob's stake is slashed. Alice can retry her request" is an accounting mechanism, not a latency mechanism ([Succinct network architecture](https://blog.succinct.xyz/network/introducing-the-succinct-network-architecture-and-the-prove-token/)). Boundless's documented split (lock 2700 s, expiry 3600 s) leaves a 900 s second-chance window: in that regime, with proving times of minutes, `F(900 s)` is high and variant A works as designed ("Slashed collateral is used to incentivize other provers to fulfill the request in the case where the locker fails to deliver the proof").

### 6.4 Faster provers

A uniform speedup `delta` turns `F(D)` into `F(D / (1 - delta))`:

| Calibration | D | `F(D)` | 5% faster | 10% | 15% | 25% | speedup for `q99 = D` |
|---|---|---|---|---|---|---|---|
| spec | 10 s | 0.908 | 0.933 | 0.953 | 0.969 | 0.989 | 26.0% |
| spec | 12 s | 0.973 | 0.982 | 0.989 | 0.993 | 0.998 | 11.2% |
| spec | 15 s | 0.996 | 0.998 | 0.999 | 0.999 | 1.000 | (already met) |
| pico | 10 s | 0.965 | 0.980 | 0.989 | 0.995 | 0.999 | 10.6% |
| pico | 12 s | 0.996 | 0.998 | 0.999 | 1.000 | 1.000 | (already met) |

Read against [EXPERIMENT.md](EXPERIMENT.md) acceptance criterion 3 (at least 5% median improvement): a 5% module moves 0.9 points of blocks across a 12 s deadline for the spec prover (one third of its misses) and 2.5 points across a 10 s deadline (27% of its misses). It does not, alone, take a spec prover to 99% at either deadline; 11.2% does at 12 s and 26% at 10 s. For a Pico-class prover at 10 s, 5% removes 42% of the misses. This is the quantitative form of [PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md) section 8 ("latency is worth a step function"): the value of a speedup is the mass of blocks it moves across `D`, `F(D/(1 - delta)) - F(D)`, and that mass depends on where the prover's tail sits relative to `D`, not on the median.

### 6.5 Correlated tails: what redundancy cannot fix

Simulated with 150 provers at 5 jobs/s (no queueing), varying `phi` (Table T5):

| `phi` | two copies: `P(T <= 12)` | prover-s per job | hedge at 3 s: `P(T <= 12)` | prover-s per job |
|---|---|---|---|---|
| 0 | 0.9994 | 11.6 | 0.9957 | 10.5 |
| 0.25 | 0.9980 | 11.9 | 0.9911 | 10.6 |
| 0.5 | 0.9952 | 12.3 | 0.9849 | 10.8 |
| 0.75 | 0.9897 | 12.8 | 0.9772 | 10.9 |
| 1 | 0.9738 | 14.0 | 0.9738 | 11.0 |

At `phi = 1` the second copy finishes at the same time as the first: it costs double and buys nothing. Two-copy redundancy survives `phi` up to about 0.7 at the 99% target; the hedge survives only up to about 0.3. The block-intrinsic share for Ethereum proving is probably high (proving time is close to linear in cycles, and cycles are a property of the block), which argues for measuring `phi` before buying redundancy and for treating tail-shortening modules as the primary lever, in agreement with the EF's decision to handle the tail "in future hard forks" rather than by hardware.

### 6.6 Summary of levers at D = 12 s, spec prover

| Lever | ceiling | prover-seconds per job | needs |
|---|---|---|---|
| single assignment | 0.973 | 7.0 | |
| two copies, independent | 0.9993 | 11.6 | `phi <~ 0.7` |
| hedge at 3 s | 0.9957 | 10.5 | `phi <~ 0.2` |
| 15% faster prover | 0.9932 | 5.95 | a module or hardware |
| 20% faster prover | 0.9962 | 5.6 | |
| deadline 15 s | 0.9962 | 7.0 | ePBS-style window |

## 7. Result 3: how many provers once the policy is fixed

### 7.1 Erlang C, Halfin-Whitt and the square-root rule

For Poisson arrivals and exponential service, the probability that an arriving job waits is Erlang's C formula, a function of `N` and `R` only ([Erlang C](https://en.wikipedia.org/wiki/Erlang_(unit)#Erlang_C_formula)). Halfin and Whitt showed that when `N = R + beta * sqrt(R)` and `R` grows, `P(W > 0)` converges to `[1 + beta * Phi(beta) / phi(beta)]^-1`, so a fixed quality of service costs a fixed `beta`, and the safety capacity grows only with the square root of the load ([Heavy-Traffic Limits for Queues with Many Exponential Servers](https://doi.org/10.1287/opre.29.3.567), Operations Research 1981). Garnett, Mandelbaum and Reiman extended the rule to impatient customers ([Designing a Call Center with Impatient Customers](https://doi.org/10.1287/msom.4.3.208.7753), M&SOM 2002), which is the proof-with-deadline setting. For non-exponential service the delay probability is close to the M/M/N value while mean waits scale with `(1 + CV^2)/2`, which for CV = 0.31 is 0.55: proving is a low-variance service compared with the exponential benchmark, so Erlang C is slightly conservative. Simulation check (Table T6, single assignment, spec, D = 12 s):

| R | `beta` | N | Erlang C `P(W>0)` | simulated `P(W>0)` | Halfin-Whitt limit | simulated `P(T <= 12)` |
|---|---|---|---|---|---|---|
| 35 | 0.5 | 38 | 0.518 | 0.496 | 0.505 | 0.940 |
| 35 | 1.0 | 41 | 0.240 | 0.214 | 0.223 | 0.969 |
| 35 | 1.5 | 44 | 0.099 | 0.088 | 0.085 | 0.9715 |
| 35 | 2.0 | 47 | 0.035 | 0.033 | 0.027 | 0.9723 |
| 35 | 2.5 | 50 | 0.011 | 0.010 | 0.007 | 0.9724 |
| 70 | 0.5 | 75 | 0.450 | 0.419 | 0.505 | 0.962 |
| 70 | 1.0 | 79 | 0.211 | 0.198 | 0.223 | 0.970 |
| 70 | 1.5 | 83 | 0.088 | 0.076 | 0.085 | 0.9720 |
| 70 | 2.0 | 87 | 0.032 | 0.029 | 0.027 | 0.9722 |
| 70 | 2.5 | 91 | 0.010 | 0.011 | 0.007 | 0.9725 |

Two readings. Erlang C predicts the simulated delay probability within about 10% across the range, so it can be used for back-of-envelope sizing without running the simulator. And the deadline loss from queueing is much smaller than `P(W > 0)`: at `beta = 1.5`, 9% of jobs wait but the success rate is within 0.2 points of the ceiling, because most waits are short relative to the 5 s of slack that a median job has. This is why the sizing rule below has a small `beta`.

### 7.2 Minimal `N` for 99% at D = 12 s

Bisection over `N` with 100,000 simulated jobs per point (Monte Carlo resolution about 0.0003 on the success probability, so the reported `N*` may be off by one). Spec distribution unless noted; the last column is the Pico-calibrated prover with single assignment (Table T3).

| `lambda` (jobs/s) | `R = 7 lambda` | single | two copies `phi=0` | two copies `phi=0.5` | hedge 3 s `phi=0` | hedge 3 s `phi=0.5` | 15% faster | 20% faster | pico, single |
|---|---|---|---|---|---|---|---|---|---|
| 1/12 | 0.6 | none (0.973) | 4 | 5 | 4 | none (0.985) | 3 | 2 | 3 |
| 0.5 | 3.5 | none | 10 | 11 | 10 | none | 6 | 5 | 7 |
| 1 | 7 | none | 16 | 19 | 16 | none | 10 | 9 | 11 |
| 2 | 14 | none | 28 | 32 | 27 | none | 16 | 14 | 18 |
| 5 | 35 | none | 63 | 69 | 60 | none | 35 | 31 | 40 |
| 10 | 70 | none | 121 | 133 | 114 | none | 65 | 60 | 74 |
| 20 | 140 | none | 236 | 256 | 218 | none | 125 | 115 | 143 |

Expressed as `N* = R_eff + beta * sqrt(R_eff)` with `R_eff = lambda * w` (measured work per job):

| policy | `w` (s) | `beta` at 1 job/s | at 5 jobs/s | at 20 jobs/s |
|---|---|---|---|---|
| two copies, `phi = 0` | 11.6 | 1.29 | 0.64 | 0.24 |
| hedge at 3 s | 10.5 | 1.74 | 1.11 | 0.70 |
| 15% faster | 5.95 | 1.66 | 0.96 | 0.54 |
| 20% faster | 5.6 | 1.44 | 0.57 | 0.29 |
| pico, single | 6.9 | 1.56 | 0.94 | 0.42 |

`beta` shrinks with scale because the queueing loss allowed is fixed (ceiling minus 0.99) while waits, conditional on waiting, shrink like `1/sqrt(N)` in the Halfin-Whitt regime. A working rule for this deadline: **`N* ~ lambda * w + (0.5 to 1.0) * sqrt(lambda * w)`, plus whatever margin availability requires (Section 8.3).** For 99% at 10 s the ceiling of even the Pico-class prover (0.965) is below target, so Table T3b reports the 95% target instead: 40 provers at 5 jobs/s, 145 at 20 jobs/s.

### 7.3 The question's scenario: N = 100, D = 12 s, spec prover

Success probability by arrival rate and policy (Table T2; "overload" marks cells where `lambda * w >= N`, where the queue is unstable and the steady-state success is zero):

| `lambda` | `R = 7 lambda` | single | single, abandon at deadline | two copies `phi=0` | two copies `phi=0.5` | hedge 3 s | 15% faster |
|---|---|---|---|---|---|---|---|
| 1/12 | 0.6 | 0.9735 | 0.9735 | 0.9991 | 0.9944 | 0.9956 | 0.9932 |
| 1 | 7 | 0.9735 | 0.9735 | 0.9991 | 0.9944 | 0.9957 | 0.9932 |
| 2 | 14 | 0.9735 | 0.9735 | 0.9991 | 0.9944 | 0.9960 | 0.9932 |
| 5 | 35 | 0.9735 | 0.9735 | 0.9991 | 0.9944 | 0.9955 | 0.9932 |
| 8 | 56 | 0.9735 | 0.9735 | 0.9946 (load 93) | 0.755 (load 98.5) | 0.9952 (load 84) | 0.9932 |
| 10 | 70 | 0.9736 | 0.9735 | overload | overload | overload (load 99) | 0.9932 |
| 12 | 84 | 0.9732 | 0.9733 | overload | overload | overload | 0.9932 |
| 13 | 91 | 0.9713 | 0.9709 | overload | overload | overload | 0.9932 |
| 14 | 98 | 0.8997 | 0.9532 | overload | overload | overload | 0.9930 |

So 100 provers of the stated speed are enough capacity for about 13 jobs/s with single assignment (at the 97.3% ceiling), about 8 jobs/s at 99.5% with two copies, and about 14 jobs/s at 99.3% if the provers are 15% faster. "Abandon at deadline" (stop proving a job whose deadline has passed and release the prover) matters only near saturation, where it rescues 5 points at 14 jobs/s; it is free and every real-time prover should do it.

## 8. The L1 real-time regime specifically

### 8.1 One chain, one cluster: `D/G/1` and the case for abandoning late proofs

A single prover cluster proving every block sees deterministic arrivals every 12 s. If it finishes the current block late, the next block has already arrived and waits, so one slow block can spoil the next one. Simulated (Table T4):

| prover | D | clusters | policy | `P(proof by D)` | share of blocks that waited | mean wait |
|---|---|---|---|---|---|---|
| spec | 12 s | 1 | finish late proofs | 0.9706 | 2.9% | 0.046 s |
| spec | 12 s | 1 | abandon at deadline | 0.9729 | 0 | 0 |
| spec | 12 s | 2 (alternate) | either | 0.9729 | 0 | 0 |
| spec | 10 s | 1 | finish late proofs | 0.9035 | 2.9% | 0.046 s |
| spec | 10 s | 1 | abandon at deadline | 0.9080 | 0 | 0 |
| pico | 12 s | 1 | finish late proofs | 0.9959 | 0.4% | 0.003 s |
| pico | 10 s | 1 | finish late proofs | 0.9645 | 0.4% | 0.003 s |
| pico | 10 s | 1 | abandon at deadline | 0.9648 | 0 | 0 |

The cascade costs 0.2 to 0.5 points for a heavy-tailed prover and nothing measurable for a Pico-class one. Abandoning at the deadline makes every block an independent trial with success exactly `F(D)`, which is what the EF's per-block P99 assumes. Note that abandoning is the opposite of what a payment-per-proof market rewards if late proofs are still paid; the market's rules and the protocol's needs diverge here, and [BLUEPRINT.md](BLUEPRINT.md)'s boundary rule (submission permitted at or before `proveBy`, expiry after) already aligns the market with abandonment.

### 8.2 `k` of `n` proof types

EIP-8025 leaves open how many distinct proofs a node should require. If `n` independent proof systems each meet the deadline with probability `p` (and the same block is not pathological for all of them), the chance that at least `k` do is a binomial tail:

| prover | D | `p` | 1 of 2 | 2 of 2 | 1 of 3 | 2 of 3 | 3 of 3 | 2 of 4 | 3 of 4 |
|---|---|---|---|---|---|---|---|---|---|
| spec | 10 s | 0.908 | 0.992 | 0.825 | 0.999 | 0.976 | 0.749 | 0.997 | 0.955 |
| spec | 12 s | 0.973 | 0.9993 | 0.947 | 1.000 | 0.998 | 0.922 | 0.9999 | 0.996 |
| pico | 10 s | 0.965 | 0.9988 | 0.932 | 1.000 | 0.996 | 0.899 | 0.9998 | 0.993 |
| pico | 12 s | 0.996 | 1.000 | 0.992 | 1.000 | 1.000 | 0.988 | 1.000 | 0.9999 |

`k = 1` is the redundancy of Section 6.1 across proof systems (diversity for free); `k = n` multiplies the misses. A "2 of 3" rule with Pico-class provers keeps 99.6% of blocks proven at 10 s; "3 of 3" drops to 90%. Whatever `k` the protocol chooses sets the per-system latency target for suppliers, and block-intrinsic slowness (Section 6.5) makes the systems more correlated than this table assumes, so treat these as upper bounds.

### 8.3 Availability dominates today

The Ethproofs real-time cohort page on 15 September 2026 shows, over 351,463 evaluated block slots and 7 evaluated provers (2 eligible: ZisK on 8x5090, Axiom on 16x5090, at 0.0040 to 0.0048 USD per proof): sub-10 s success 38.7% against a 70% target, "stunned" (over 10 s) 3.11%, "paralyzed" 0.02%, offline 58.2% ([ethproofs.org](https://ethproofs.org/)). Read as per-(prover, slot) frequencies, that is `P(online) = 0.42` and `P(under 10 s | online) = 0.926`. The 2026 roadmap adds a 90% uptime floor for cohort membership for this reason.

For a consumer that needs at least one proof per slot from `n` independent provers of that reliability, `P(at least one) = 1 - (1 - 0.387)^n`: 0.62 at n = 2, 0.77 at 3, 0.91 at 5, 0.98 at 8, 0.9925 at 10. The lesson for a supplier marketplace is that in the current state of the ecosystem, uptime is worth more than the last second of proving speed, and a market that measures and pays for availability (a standing assignment with a liveness bond) addresses the actual bottleneck. Both numbers are cohort-wide and include provers that are not eligible on hardware grounds; the page does not publish per-prover uptime, so this is an order-of-magnitude reading.

### 8.4 Inside one cluster: fork-join and stragglers

A multi-GPU prover is itself a queueing system: the block is split into `G` shards proven in parallel, then aggregated. Its latency is the slowest shard plus the aggregation tree, so it is an order statistic: `P(max <= t) = F_shard(t)^G`. For lognormal shards with dispersion `sigma_s`, the median of the slowest of `G` shards relative to one shard's median:

| `sigma_s` | G = 4 | G = 16 | G = 64 |
|---|---|---|---|
| 0.2 | 1.22x | 1.41x | 1.58x |
| 0.3 | 1.35x | 1.68x | 1.99x |
| 0.5 | 1.65x | 2.37x | 3.16x |

This is why the Ethproofs roadmap standardises on a small number of RTX 5090s per cluster and why push0 offers speculative re-execution of straggling shards. It is also why proving latency does not fall linearly with GPU count: doubling `G` halves the work per shard and raises the straggler multiplier. The one-prover `S` used throughout this document already includes the effect; a marketplace that sells sub-block work (shards, witness pieces) would need the fork-join model explicitly.

## 9. Existing markets through the queueing lens

| Market or system | Arrival and matching | Assignment | Deadline handling | Queueing reading |
|---|---|---|---|---|
| Succinct Prover Network ([architecture](https://blog.succinct.xyz/network/introducing-the-succinct-network-architecture-and-the-prove-token/), [docs](https://docs.succinct.xyz/docs/provers/how-it-works/overview)) | requests to an off-chain auctioneer; "a simple reverse auction to allocate the request to the lowest bidding prover"; stake bounds concurrent auctions per prover | one prover, exclusive | missed deadline: request cancelled, stake slashed, requester retries; users may bypass auctions with "off-chain service level agreements with provers" | variant B of Section 6.3: retry adds nothing to on-time delivery; per-prover concurrency cap is a per-server `c_i` so `N = sum c_i`; SLAs are the standing-assignment path |
| Boundless ([proof lifecycle](https://docs.boundless.network/developers/proof-lifecycle)) | reverse Dutch auction: price rises linearly from min to max over a ramp-up (300 s in the example); provers preflight-execute to estimate cycles before bidding | first bidder locks; collateral required; unlocked requests can be fulfilled directly at the current price | lock timeout (2700 s) before expiry (3600 s); slashed collateral funds fulfilment by others | the price ramp is a load-dependent matching delay: idle provers lock at min price immediately, loaded ones wait for the price; lock-then-expiry is variant A hedging with `t_L = 2700 s`; batching adds `W` |
| push0 orchestration ([arXiv 2602.16338](https://arxiv.org/abs/2602.16338)) | persistent priority queues (NATS JetStream), at-least-once | dispatchers pull tasks; priority `(block_num, retry_count, enqueue_time)` with a starvation-freedom theorem | bounded retries after ACK timeout; optional k-of-n speculative dispatch; partition-affine routing for aggregation barriers | an intra-prover job shop: oldest-block-first is EDF for a chain; measured orchestration overhead 5 ms (P99 8.5 ms) against 7 s proofs, so orchestration is not the bottleneck; 14M Zircuit blocks in production |
| Prooφ ([arXiv 2404.06495](https://arxiv.org/abs/2404.06495)) | tasks with a fee, provers with capacity `s` and unit cost `p`, cleared in rounds | allocate the highest-fee tasks to the lowest-cost provers up to cumulative capacity; second-price payments | none: no time dimension | mechanism design without a clock; capacity misreporting is the only queueing-adjacent concern; it answers "who proves" and not "when" |

None of these publishes `P(T <= D)` or a latency distribution for its own network, and none of the general-purpose markets is built for a 12 s window. The consistent design signal is that the closer the deadline is to the proving time, the more the market moves the auction off the job and onto the capacity: Succinct's SLAs, Boundless's option to disable locking, push0's pre-provisioned dispatcher pool. The matching budget makes this quantitative:

| prover | D | `q99(S)` | budget for auction + dispatch + settlement |
|---|---|---|---|
| spec | 10 s | 13.5 s | negative (3.5 s short) |
| spec | 12 s | 13.5 s | negative (1.5 s short) |
| pico | 10 s | 11.2 s | negative (1.2 s short) |
| pico | 12 s | 11.2 s | +0.8 s |

Even the best published prover leaves under a second at a 12 s deadline for everything that is not proving, so any real-time supply arrangement must have the prover already assigned, warm and holding the witness when the block appears. This is what [EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md) section 4 calls the execution market ("assets are prefetched, environments are warm ... before a block arrives") and what its section 9 recommends ("reserve capacity and use standing quotes with bounded validity").

## 10. Applying the model to this project's plans

### 10.1 ProofMarket deadlines ([BLUEPRINT.md](BLUEPRINT.md))

- **Set `proveBy` from a measured quantile, not a round number.** `proveBy - activation >= q99(S_prep + S_prove + S_wrap) + t_submit + margin`, where the quantile is taken from the benchmark protocol's raw observations (cold and warm runs separately). For the hackathon's CPU proving, [LemmaXperiment/apparatus/SETUP_PLAN.md](LemmaXperiment/apparatus/SETUP_PLAN.md) expects hours per compressed proof under a 6 h runner cap; that cap is itself a hard deadline on `S`, so choose blocks whose `q99(S)` sits well under 6 h, which the plan already does by restricting real proofs to blocks under about 2M to 5M gas.
- **The long-deadline regime in numbers.** Table T7 (time unit = one mean proving run, p95 = 2 units, FCFS, Poisson arrivals):

  | workers | `rho` | `D = 2` | `D = 3` | `D = 4` |
  |---|---|---|---|---|
  | 1 | 0.2 | 0.892 | 0.975 | 0.994 |
  | 1 | 0.5 | 0.727 | 0.883 | 0.949 |
  | 1 | 0.8 | 0.395 | 0.566 | 0.692 |
  | 2 | 0.5 | 0.876 | 0.974 | 0.994 |
  | 3 | 0.2 | 0.948 | 0.993 | 0.999 |
  | 3 | 0.5 | 0.919 | 0.988 | 0.998 |
  | 3 | 0.8 | 0.697 | 0.880 | 0.954 |

  Two or three workers with a `proveBy` of three to four mean proving times deliver 97% to 99.8% on time at half utilisation. A single worker at 80% utilisation misses a third of jobs even with a generous deadline. The demo's two or three workers are therefore not decoration: they are what makes the expiry path rare enough to be shown as an exception rather than the norm.
- **Add a lock timeout if reassignment is wanted.** [BLUEPRINT.md](BLUEPRINT.md) flaw F11 notes that an assigned worker can stall and "deposits only limit the economic damage". In the hour-scale regime, a Boundless-style `lockTimeout < proveBy` with `proveBy - lockTimeout >= q99(S)` of a fallback worker turns the bond into a latency mechanism (variant A of Section 6.3); in the real-time regime it cannot, and only upfront redundancy or standing assignment can. Whether to add the field is a product decision; the arithmetic for choosing it is above.
- **Abandon at `proveBy`.** A worker should stop proving a job whose `proveBy` has passed (it cannot be paid) and take the next one; Table T2's last row shows what that is worth under load.
- **Log arrival, start and finish per job.** `W` and `S` are then observable per job, `phi` is observable from repeated blocks, and the worker console's queue display becomes `lambda * E[W]` with a meaning.

### 10.2 LemmaXperiment ([EXPERIMENT.md](EXPERIMENT.md))

- The funded metric is PGU, which predicts `S` on fixed hardware (Section 4.3). A 5% PGU reduction is a 5% shift of the whole `S` distribution if `S` is proportional to PGU; its deadline value is the `F(D/0.95) - F(D)` mass of Section 6.4, which the report should state alongside the median saving. It is small at 12 s for an already-fast prover and large at 10 s for a slow one.
- The paired A/B holdout design estimates `phi` for free (Section 4.4). Publishing it would be a first, since no prover network publishes the intrinsic share of its latency variance.
- Real proofs run on shared GitHub runners: their wall time is a `W + S` sample with an unknown `W`, which is why the plan is right to label it "network latency, never used as a gate". If a wall-clock number is reported at all, report the runner's queue time separately, exactly as Ethproofs splits "queue" from "prove".

### 10.3 The value of a tail-shortening module ([PROOF_MODULE_VALUE.md](PROOF_MODULE_VALUE.md))

Section 8 of that document models latency value as a step at the deadline. This note supplies the step's height: for a buyer with deadline `D` and a prover with distribution `F`, a module with speedup `delta` moves `F(D/(1 - delta)) - F(D)` of jobs from missed to met. That quantity is the number to put in the evidence sentence, and it is largest exactly when the prover's `q99` is just above `D`. A module that only reduces the median of an already-compliant prover has near-zero deadline value and only cost value; a module that trims the tail of a borderline prover has deadline value on a few percent of jobs, each worth the whole job. Because redundancy cannot remove the block-intrinsic tail (Section 6.5) while a module can, tail-shortening modules and redundancy are complements, not substitutes.

### 10.4 Agent procurement ([AGENT_MARKETPLACE.md](AGENT_MARKETPLACE.md))

- The buyer's loop (search, reject incompatible, request quotes, fund, invoke) is synchronous matching. For any job whose deadline is within a few multiples of `S`, that loop has to run before the job exists: the marketplace sells standing capacity with bounded-validity quotes, and the per-job step is a single authenticated invoke. The document's "Retry limits and backoff are bounded" is compatible with the model only when `D - t_retry >= q99(S)`; otherwise the retry is variant B and should be skipped in favour of a parallel copy.
- The restricted signer's "maximum concurrency" is the per-worker `c_i`; the pool's `N` in this note is `sum c_i`, and a worker that accepts more concurrent jobs than its hardware proves in parallel is not adding capacity, it is adding queue.
- Idempotency keys make a retried request join the same queue position instead of creating a second job; without them a client retry is an unintended (and unpaid-for) redundancy that can double the load exactly when the system is slowest.

### 10.5 Supplying EIP-8025 proofs ([EIP8025_AGENT_ECONOMY_RESEARCH.md](EIP8025_AGENT_ECONOMY_RESEARCH.md))

Because the protocol will not pay and will not wait, a supplier's product is a probability: `P(a proof of type X for slot s exists by t)` for a sponsor who values it. Sections 6 to 8 give the levers, and Section 8.3 says that in September 2026 the cheapest probability to buy is uptime. A sponsored-supply contract can be written directly in these terms: coverage (`P(online)`), latency (`q99(S)` on named hardware), and a redundancy factor, with the bond sized to the miss rate the contract promises.

## 11. Economics of capacity

### 11.1 Cost of a prover-second

Illustrative, not a quote: a 16x RTX 5090 cluster at 45k USD amortised over three years plus 10 kW at 0.10 USD/kWh costs about 0.00075 USD per second, 2.7 USD per hour, or 0.0053 USD per 7 s proof. That is consistent with the 0.0040 to 0.0048 USD per proof shown for the eligible Ethproofs clusters and with the Ethproofs 2025 review's fall from 1.69 USD to under 4 cents per proof ([review](https://hackmd.io/@willcorcoran/ry16VMmfbx)). Two-copy redundancy raises the cost per job by 1.66x; a 15% faster prover lowers it by 15%.

### 11.2 Sizing by the critical ratio

Let `c_p` be the cost of one prover per second and `c_miss` the value lost per missed job (forfeited fee plus slashed bond plus reputational loss, or for a sponsor the value of a covered slot). Total cost per second is `N c_p + lambda c_miss (1 - P_N)`, so a prover is worth adding while

```text
lambda * c_miss * (P_(N+1) - P_N)  >  c_p
```

With the Table T1 curve at 5 jobs/s, going from 40 to 45 provers raises `P` from 0.964 to 0.972 (0.0016 per prover), so each added prover saves 0.008 missed jobs per second, worth it while `c_miss > 0.00075 / 0.008 = 0.094 USD`. Beyond 50 provers `P_(N+1) - P_N` is zero and no `c_miss` justifies the 51st: at that point the money goes to redundancy (if `phi` is low), to faster provers (if `phi` is high), or to the deadline (a longer window). The same inequality prices the redundancy decision: two copies cost `0.66 * 7 * c_p = 0.0035 USD` extra per job and buy 2.6 points of success at 12 s (`phi = 0`), so they pay when `c_miss > 0.13 USD`.

### 11.3 The market clears on prover-seconds, not on proofs

Because `w` (prover-seconds per job) differs by policy, a market that prices per proof (Succinct's base fee plus PGU price, Boundless's per-cycle Dutch price) is pricing the single-assignment `w`. A buyer who wants 99% at 12 s from provers with a 97% single-attempt ceiling is buying 1.5x to 1.7x the prover-seconds and should expect to pay for them, which is another reason the real-time product is an SLA on a distribution rather than a spot price on a proof.

## 12. Assumptions, limits and what would replace them with measurements

- Service times are lognormal, calibrated to two published numbers; the tail beyond p99 is extrapolated. Replace with the empirical distribution from hundreds of measured blocks.
- Provers are homogeneous; a real pool mixes speeds and the FCFS assumption then leaves value on the table (fastest-available assignment does better; slowest-first hurts).
- FCFS, no preemption, no priority. Earliest-deadline-first is optimal on one server for feasibility (Liu and Layland, [Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment](https://doi.org/10.1145/321738.321743), JACM 1973) and a good multi-server heuristic; push0's oldest-block-first is EDF for a single chain. Lehoczky's real-time queueing theory ([Real-time queueing theory](https://doi.org/10.1109/REAL.1996.563715), RTSS 1996) covers the heavy-traffic analysis of deadline-aware disciplines and is the natural next tool if a marketplace wants to schedule rather than merely dispatch.
- Copies are independent unless `phi` says otherwise; `phi` is unmeasured for Ethereum proving.
- Settlement latency, witness acquisition and network propagation are zero inside the model and must be subtracted from `D` outside it.
- Arrivals are Poisson (market) or exactly periodic (one chain); bursts from correlated demand (many rollups posting at once, a reorg) would need a batch-arrival model.
- Availability is treated as a separate multiplicative factor; a prover that is online but degraded is not modelled.
- The Ethproofs cohort figures are a screenshot of a live page on one day and are cohort-wide, not per prover.

The measurements that would replace the assumptions are cheap and mostly already planned in this folder: per-job arrival, start and finish timestamps (gives `W`, `S`, `rho`); repeated blocks (gives `phi`); cold and warm separation (gives the two `S` distributions); uptime per worker (gives availability).

## Appendix A. Reproducing the numbers

```text
python3 queueing_sim.py run  --N 100 --lam 5 --D 12                          # one configuration, JSON out
python3 queueing_sim.py run  --N 100 --lam 5 --D 12 --policy redundant --k 2
python3 queueing_sim.py run  --N 100 --lam 5 --D 12 --policy hedge --t-h 3 --phi 0.5
python3 queueing_sim.py find --lam 5 --D 12 --policy redundant --k 2 --target 0.99
python3 queueing_sim.py grid                                                   # every table, ~2 min on 8 cores
```

`grid` writes `queueing_results.json` (every run's raw metrics) and `queueing_tables.md` (the tables above, in the same order) next to the script. Seeds are fixed, so a rerun reproduces the tables exactly; changing `--jobs` or a seed moves individual cells within the stated Monte Carlo resolution.

The simulator is an event-driven `M/G/N` (or `D/G/N`) queue with FCFS dispatch, optional k-copy redundancy with cancel-on-first-completion, optional hedging with head-of-line priority for the hedge copy, optional abandonment at the deadline, a job-intrinsic variance share `phi`, a uniform speedup, and warm-up discard. It was validated against an exact heap-of-free-times FCFS implementation (success and delay probabilities agree to Monte Carlo precision) and against Erlang C (Table T6). Distribution fits use closed forms for the lognormal and Weibull and a regularised incomplete gamma for the gamma family; the fitting code is reproduced in the script's helpers.

## Appendix B. Formulas used

```text
lognormal from (mean m, quantile x at p):  sigma = z_p - sqrt(z_p^2 - 2 ln(x/m)),  mu = ln m - sigma^2 / 2
single attempt:                            P = F(D)
k independent copies:                      P = 1 - (1 - F(D))^k
hedge at t_h (late first copy counts):     P = F(D) + (1 - F(D)) F(D - t_h)
cancel-and-retry at t_L:                   P = F(t_L) + (1 - F(t_L)) F(D - t_L)
uniform speedup delta:                     P = F(D / (1 - delta))
k of n proof types, independent:           P = sum_{i >= k} C(n, i) p^i (1 - p)^(n - i)
n provers with availability a, speed q:    P(at least one) = 1 - (1 - a q)^n
offered load:                              R = lambda * w    (w = prover-seconds per job under the policy)
Erlang C:                                  P(W > 0) = [R^N / N! * N / (N - R)] / [sum_{k<N} R^k / k! + R^N / N! * N / (N - R)]
square-root staffing:                      N = R + beta sqrt(R),  P(W > 0) -> [1 + beta Phi(beta) / phi(beta)]^-1
fork-join over G shards:                   P(max <= t) = F_shard(t)^G
Little's law:                              L = lambda E[T],  busy provers = lambda E[S]
critical ratio for the (N+1)th prover:     add while lambda c_miss (P_(N+1) - P_N) > c_p
```

## Sources

Protocol and roadmap

- Ethereum EIPs. [EIP-8025: Optional Execution Proofs](https://eips.ethereum.org/EIPS/eip-8025). Draft, created 17 September 2025. Accessed 15 September 2026.
- Ethereum Foundation. [Shipping an L1 zkEVM #1: Realtime Proving](https://blog.ethereum.org/2025/07/10/realtime-proving). 10 July 2025.
- Ethereum Foundation. [Shipping an L1 zkEVM #2: The Security Foundations](https://blog.ethereum.org/2025/12/18/zkevm-security-foundations). 18 December 2025.
- Ethereum Foundation Protocol Cluster. [Current and Emerging Priorities](https://blog.ethereum.org/2026/09/07/protocol-priorities). 7 September 2026.
- Chainstack. [Ethereum Glamsterdam: What Changes for Infrastructure](https://chainstack.com/ethereum-glamsterdam-upgrade/). Accessed 15 September 2026 (EIP-7782 declined for Glamsterdam; ePBS headliner).

Prover performance data

- Ethproofs. [Real-time proving cohort](https://ethproofs.org/) and [blocks](https://ethproofs.org/blocks). Live pages read 15 September 2026; figures quoted are as displayed that day.
- W. Corcoran. [Ethproofs 2025 Review and 2026 Roadmap](https://hackmd.io/@willcorcoran/S1A840ZMZg) and [Post 1](https://hackmd.io/@willcorcoran/ry16VMmfbx). HackMD drafts, accessed 15 September 2026.
- Brevis. [Pico Prism: 99.6% Real-Time Proving for 45M Gas Ethereum Blocks on Consumer Hardware](https://blog.brevis.network/2025/10/15/pico-prism-99-6-real-time-proving-for-45m-gas-ethereum-blocks-on-consumer-hardware/). 15 October 2025.
- Brevis. [Pico Prism 2.0: A 5.3x Efficiency Leap in Real-Time Ethereum Proving](https://blog.brevis.network/2026/05/12/pico-prism-2-0-a-5-3x-efficiency-leap-in-real-time-ethereum-proving/). 12 May 2026.
- Aligned. [The year of zkVM real-time proving: milestones, present and future](https://blog.alignedlayer.com/the-year-of-zkvm-real-time-proving-milestones-present-and-future/). Accessed 15 September 2026 (SP1 Hypercube, ZisK and Pico figures as reported there).

Markets and orchestration

- Succinct. [Introducing the Succinct Network Architecture and the $PROVE Token](https://blog.succinct.xyz/network/introducing-the-succinct-network-architecture-and-the-prove-token/); [Prover network overview](https://docs.succinct.xyz/docs/provers/how-it-works/overview); [Quickstart](https://docs.succinct.xyz/docs/sp1/prover-network/quickstart). Accessed 15 September 2026.
- Boundless. [Proof Lifecycle](https://docs.boundless.network/developers/proof-lifecycle). Accessed 15 September 2026.
- push0 authors. [push0: Scalable and Fault-Tolerant Orchestration for Zero-Knowledge Proof Generation](https://arxiv.org/abs/2602.16338). arXiv, February 2026.
- W. Wang, L. Zhou et al. [Prooφ: A ZKP Market Mechanism](https://arxiv.org/abs/2404.06495). arXiv, revised March 2025.

Queueing theory

- S. Halfin and W. Whitt. [Heavy-Traffic Limits for Queues with Many Exponential Servers](https://doi.org/10.1287/opre.29.3.567). Operations Research 29(3), 1981.
- O. Garnett, A. Mandelbaum and M. Reiman. [Designing a Call Center with Impatient Customers](https://doi.org/10.1287/msom.4.3.208.7753). Manufacturing and Service Operations Management 4(3), 2002.
- K. Gardner, S. Zbarsky, S. Doroudi, M. Harchol-Balter, E. Hyytiä and A. Scheller-Wolf. [Reducing Latency via Redundant Requests: Exact Analysis](https://dl.acm.org/doi/10.1145/2796314.2745873). ACM SIGMETRICS 2015.
- A. Vulimiri, P. B. Godfrey, R. Mittal, J. Sherry, S. Ratnasamy and S. Shenker. [Low Latency via Redundancy](https://doi.org/10.1145/2535372.2535392). ACM CoNEXT 2013.
- J. Dean and L. A. Barroso. [The Tail at Scale](https://doi.org/10.1145/2408776.2408794). Communications of the ACM 56(2), 2013.
- J. P. Lehoczky. [Real-time queueing theory](https://doi.org/10.1109/REAL.1996.563715). IEEE Real-Time Systems Symposium, 1996.
- C. L. Liu and J. W. Layland. [Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment](https://doi.org/10.1145/321738.321743). Journal of the ACM 20(1), 1973.
- J. D. C. Little. [A Proof for the Queuing Formula: L = λW](https://doi.org/10.1287/opre.9.3.383). Operations Research 9(3), 1961.
- M. Harchol-Balter. [Performance Modeling and Design of Computer Systems: Queueing Theory in Action](https://doi.org/10.1017/CBO9781139226424). Cambridge University Press, 2013 (M/G/N approximations, Kingman's formula, redundancy chapters).
- Wikipedia. [Erlang C formula](https://en.wikipedia.org/wiki/Erlang_(unit)#Erlang_C_formula) and [Palm-Khintchine theorem](https://en.wikipedia.org/wiki/Palm%E2%80%93Khintchine_theorem). Reference statements only.
