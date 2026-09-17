#!/usr/bin/env python3
"""Proof-market queueing simulator: M/G/N and D/G/N with deadlines.

Pure Python 3 standard library (no numpy). Models proof jobs arriving at a
pool of N provers, each job needing one proving run whose duration S is
lognormal, fitted to a (mean, p95) pair or to a (mean, P(S <= x)) pair.
A job succeeds if a valid proof exists by arrival + D.

Dispatch policies
  single     one copy per job, FCFS
  redundant  k copies on k provers from t=0, first to finish wins, others cancelled
  hedge      one copy; if not finished t_h seconds after it started, a second
             copy is queued at the head of the line; first to finish wins

Options
  --phi      share of log-variance that is job-intrinsic (shared by all copies
             of the same job); 0 = copies independent, 1 = copies identical
  --speedup  uniform multiplicative speedup of every proving run (0.05 = 5%)
  --kill     abandon a job at its deadline and free its provers (non-work-conserving)
  --arrival  poisson (marketplace) or periodic (one L1 chain, one block per slot)

Usage examples
  python3 queueing_sim.py run --N 100 --lam 5 --D 12
  python3 queueing_sim.py run --N 100 --lam 5 --D 12 --policy redundant --k 2
  python3 queueing_sim.py find --lam 5 --D 12 --policy hedge --t-h 3 --target 0.99
  python3 queueing_sim.py grid            # regenerates every table in QUEUEING_THEORY.md (~2 min, all cores)
"""
import argparse
import heapq
import json
import math
import random
import sys
from collections import deque

SQRT2 = math.sqrt(2.0)


# ----------------------------------------------------------------------------
# distribution helpers
# ----------------------------------------------------------------------------
def Phi(z):
    return 0.5 * (1.0 + math.erf(z / SQRT2))


def Phi_inv(p):
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if Phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def lognormal_from_mean_quantile(mean, x, p):
    """(mu, sigma) of a lognormal with E[S] = mean and P(S <= x) = p."""
    z = Phi_inv(p)
    a = math.log(x / mean)
    disc = z * z - 2 * a
    if disc < 0:
        raise ValueError("no lognormal has that mean and quantile")
    s = z - math.sqrt(disc)
    mu = math.log(mean) - s * s / 2
    return mu, s


def ln_cdf(x, mu, s):
    return Phi((math.log(x) - mu) / s)


def ln_q(p, mu, s):
    return math.exp(mu + Phi_inv(p) * s)


# ----------------------------------------------------------------------------
# Erlang C and Halfin-Whitt (M/M/N reference values)
# ----------------------------------------------------------------------------
def erlang_c(N, A):
    """P(wait > 0) in M/M/N with offered load A = lambda * E[S] Erlangs."""
    if A >= N:
        return 1.0
    # compute via log-sum to avoid overflow
    terms = []
    for k in range(N):
        terms.append(k * math.log(A) - math.lgamma(k + 1))
    last = N * math.log(A) - math.lgamma(N + 1) + math.log(N / (N - A))
    m = max(max(terms), last)
    denom = sum(math.exp(t - m) for t in terms) + math.exp(last - m)
    return math.exp(last - m) / denom


def halfin_whitt_pwait(beta):
    """Limit of P(wait>0) when N = A + beta*sqrt(A), A -> infinity."""
    phi = math.exp(-beta * beta / 2) / math.sqrt(2 * math.pi)
    return 1.0 / (1.0 + beta * Phi(beta) / phi)


def erlang_c_wait_tail(N, A, mean_s, t):
    """P(W > t) in M/M/N (exponential service, FCFS)."""
    pw = erlang_c(N, A)
    mu = 1.0 / mean_s
    return pw * math.exp(-(N * mu - A * mu) * t)


# ----------------------------------------------------------------------------
# simulation
# ----------------------------------------------------------------------------
ARR, DONE, HEDGE, KILL = 0, 1, 2, 3


class Job(object):
    __slots__ = ("arr", "deadline", "zj", "done", "completion", "running",
                 "first_start", "idx", "copies")

    def __init__(self, arr, deadline, zj, idx):
        self.arr = arr
        self.deadline = deadline
        self.zj = zj
        self.done = False
        self.completion = float("inf")
        self.running = {}
        self.first_start = None
        self.idx = idx
        self.copies = 0


def simulate(N, lam, D, mu, sigma, policy="single", k=1, t_h=3.0, phi=0.0,
             speedup=0.0, kill=False, arrival="poisson", n_jobs=100000,
             warmup=0.05, seed=1):
    rng = random.Random(seed)
    sq_phi = math.sqrt(phi)
    sq_1phi = math.sqrt(1.0 - phi)
    scale = 1.0 - speedup

    def service(job):
        zi = rng.gauss(0.0, 1.0)
        return scale * math.exp(mu + sigma * (sq_phi * job.zj + sq_1phi * zi))

    events = []
    seq = [0]

    def push(t, typ, job, cid):
        seq[0] += 1
        heapq.heappush(events, (t, seq[0], typ, job, cid))

    free = [N]
    waitq = deque()
    busy = [0.0]
    jobs_created = [0]
    n_warm = int(n_jobs * warmup)
    stats = {"n": 0, "success": 0, "waited": 0, "wait_sum": 0.0, "waits": [],
             "work": 0.0, "resp_sum": 0.0}
    t_measure_start = [None]
    t_measure_end = [None]

    def start_copy(job, cid, t):
        free[0] -= 1
        S = service(job)
        job.running[cid] = t
        if job.first_start is None:
            job.first_start = t
        push(t + S, DONE, job, cid)
        if policy == "hedge" and cid == 0:
            push(t + t_h, HEDGE, job, 0)

    def try_dispatch(t):
        while free[0] > 0 and waitq:
            job, cid = waitq.popleft()
            if job.done:
                continue
            if kill and t >= job.deadline:
                continue
            start_copy(job, cid, t)

    def release_all(job, t):
        for cid, t0 in job.running.items():
            free[0] += 1
            if job.idx >= n_warm:
                busy[0] += t - max(t0, t_measure_start[0] if t_measure_start[0] is not None else t0)
        job.running.clear()

    def finalize(job, t, ok):
        if job.idx < n_warm:
            return
        stats["n"] += 1
        if ok:
            stats["success"] += 1
            stats["resp_sum"] += t - job.arr
        w = (job.first_start - job.arr) if job.first_start is not None else (job.deadline - job.arr)
        if w > 1e-9:
            stats["waited"] += 1
        stats["wait_sum"] += w
        stats["waits"].append(w)

    # first arrival
    if arrival == "poisson":
        t_next = rng.expovariate(lam)
    else:
        t_next = 0.0
    push(t_next, ARR, None, 0)

    finished = 0
    while events:
        t, _, typ, job, cid = heapq.heappop(events)
        if typ == ARR:
            idx = jobs_created[0]
            jobs_created[0] += 1
            if idx == n_warm:
                t_measure_start[0] = t
            job = Job(t, t + D, rng.gauss(0.0, 1.0), idx)
            ncopies = k if policy == "redundant" else 1
            for c in range(ncopies):
                waitq.append((job, c))
            if kill:
                push(t + D, KILL, job, 0)
            try_dispatch(t)
            if jobs_created[0] < n_jobs:
                if arrival == "poisson":
                    push(t + rng.expovariate(lam), ARR, None, 0)
                else:
                    push(t + 1.0 / lam, ARR, None, 0)
        elif typ == DONE:
            if cid not in job.running:
                continue  # cancelled copy
            t0 = job.running.pop(cid)
            free[0] += 1
            if job.idx >= n_warm:
                busy[0] += t - max(t0, t_measure_start[0])
            if not job.done:
                job.done = True
                job.completion = t
                release_all(job, t)
                finalize(job, t, t <= job.deadline)
                if job.idx >= n_warm:
                    finished += 1
                    if finished == n_jobs - n_warm:
                        t_measure_end[0] = t
            try_dispatch(t)
        elif typ == HEDGE:
            if not job.done:
                waitq.appendleft((job, 1))
                try_dispatch(t)
        elif typ == KILL:
            if not job.done:
                job.done = True
                release_all(job, t)
                finalize(job, t, False)
                if job.idx >= n_warm:
                    finished += 1
                    if finished == n_jobs - n_warm:
                        t_measure_end[0] = t
                try_dispatch(t)

    n = stats["n"]
    waits = sorted(stats["waits"])
    span = (t_measure_end[0] or t) - (t_measure_start[0] or 0.0)
    return {
        "N": N, "lam": lam, "D": D, "policy": policy, "k": k, "t_h": t_h,
        "phi": phi, "speedup": speedup, "kill": kill, "arrival": arrival,
        "n": n,
        "success": stats["success"] / n,
        "p_wait": stats["waited"] / n,
        "mean_wait": stats["wait_sum"] / n,
        "p99_wait": waits[int(0.99 * (n - 1))] if n else 0.0,
        "util": busy[0] / (N * span) if span > 0 else 0.0,
        "work_per_job": busy[0] / n,
        "offered_load": lam * math.exp(mu + sigma * sigma / 2) * (1 - speedup),
    }


def fast_single_fcfs(N, lam, D, mu, sigma, n_jobs=200000, warmup=0.05, seed=1,
                     arrival="poisson", speedup=0.0):
    """Exact FCFS M/G/N via a heap of server free times (single copy, no kill)."""
    rng = random.Random(seed)
    heap = [0.0] * N
    heapq.heapify(heap)
    t = 0.0
    n_warm = int(n_jobs * warmup)
    ok = 0
    waited = 0
    n = 0
    for i in range(n_jobs):
        if arrival == "poisson":
            t += rng.expovariate(lam)
        else:
            t += 1.0 / lam
        f = heapq.heappop(heap)
        start = max(t, f)
        S = (1 - speedup) * rng.lognormvariate(mu, sigma)
        heapq.heappush(heap, start + S)
        if i >= n_warm:
            n += 1
            if start + S <= t + D:
                ok += 1
            if start > t + 1e-9:
                waited += 1
    return {"success": ok / n, "p_wait": waited / n, "n": n}


def find_min_N(target, lam, D, mu, sigma, n_jobs=100000, N_max=2000, **kw):
    """Smallest N with P(success) >= target, or None with the value at N_max."""
    hi_res = simulate(N_max, lam, D, mu, sigma, n_jobs=n_jobs, **kw)
    if hi_res["success"] < target:
        return None, hi_res
    lo = 1
    hi = N_max
    best = hi_res
    while lo < hi:
        mid = (lo + hi) // 2
        r = simulate(mid, lam, D, mu, sigma, n_jobs=n_jobs, **kw)
        if r["success"] >= target:
            hi = mid
            best = r
        else:
            lo = mid + 1
    if best["N"] != lo:
        best = simulate(lo, lam, D, mu, sigma, n_jobs=n_jobs, **kw)
    return lo, best


# ----------------------------------------------------------------------------
# experiment grid: regenerates every simulated table in QUEUEING_THEORY.md
# (writes queueing_results.json and queueing_tables.md next to this file;
#  about two minutes on an 8-core laptop)
# ----------------------------------------------------------------------------
import os
import time
from multiprocessing import Pool

SPEC = lognormal_from_mean_quantile(7.0, 11.0, 0.95)        # user's spec: mean 7 s, p95 11 s
PICO = lognormal_from_mean_quantile(6.9, 12.0, 0.996)       # Pico Prism 1.0 calibration
LONG = lognormal_from_mean_quantile(1.0, 2.0, 0.95)         # long-deadline regime: mean 1 unit, p95 2 units
DISTS = {"spec": SPEC, "pico": PICO, "long": LONG}

POLICIES = {
    "single": dict(policy="single"),
    "single+kill": dict(policy="single", kill=True),
    "redundant2 phi=0": dict(policy="redundant", k=2, phi=0.0),
    "redundant2 phi=0.5": dict(policy="redundant", k=2, phi=0.5),
    "hedge3 phi=0": dict(policy="hedge", t_h=3.0, phi=0.0),
    "hedge3 phi=0.5": dict(policy="hedge", t_h=3.0, phi=0.5),
    "single 15% faster": dict(policy="single", speedup=0.15),
    "single 20% faster": dict(policy="single", speedup=0.20),
}


def job_run(args):
    tag, dist, N, lam, D, kw, n_jobs, seed = args
    mu, s = DISTS[dist]
    r = simulate(N, lam, D, mu, s, n_jobs=n_jobs, seed=seed, **kw)
    r.update(tag=tag, dist=dist)
    return r


def job_find(args):
    tag, dist, lam, D, kw, n_jobs, target, N_max = args
    mu, s = DISTS[dist]
    N, r = find_min_N(target, lam, D, mu, s, n_jobs=n_jobs, N_max=N_max, **kw)
    r.update(tag=tag, dist=dist, minN=N, target=target)
    return r


def fmt(x, nd=4):
    return ("%." + str(nd) + "f") % x


def run_grid():
    t0 = time.time()
    out = {}
    tables = []
    pool = Pool()

    # ------------------------------------------------------------------ T1
    T1 = [("T1", "spec", N, 5.0, 12.0, POLICIES["single"], 200000, 11)
          for N in (36, 38, 40, 45, 50, 60, 80, 100, 150, 300)]
    # ------------------------------------------------------------------ T2
    lams2 = [1 / 12, 0.5, 1, 2, 5, 8, 10, 12, 13, 14]
    pols2 = ["single", "single+kill", "redundant2 phi=0", "redundant2 phi=0.5",
             "hedge3 phi=0", "single 15% faster"]
    T2 = [("T2|%s|%g" % (p, lam), "spec", 100, lam, 12.0, POLICIES[p], 150000, 21)
          for p in pols2 for lam in lams2]
    # ------------------------------------------------------------------ T4 (single L1 chain, periodic)
    T4 = []
    for dist in ("spec", "pico"):
        for D in (10.0, 12.0):
            for N in (1, 2):
                for p in ("single", "single+kill"):
                    T4.append(("T4|%s|D%g|N%d|%s" % (dist, D, N, p), dist, N, 1 / 12, D,
                               dict(POLICIES[p], arrival="periodic"), 150000, 31))
    # ------------------------------------------------------------------ T5 (correlation)
    T5 = []
    for phi in (0.0, 0.25, 0.5, 0.75, 1.0):
        T5.append(("T5|redundant2|%g" % phi, "spec", 150, 5.0, 12.0,
                   dict(policy="redundant", k=2, phi=phi), 150000, 41))
        T5.append(("T5|hedge3|%g" % phi, "spec", 150, 5.0, 12.0,
                   dict(policy="hedge", t_h=3.0, phi=phi), 150000, 41))
    # ------------------------------------------------------------------ T6 (Erlang C check, beta staffing)
    T6 = []
    for R in (35.0, 70.0):
        lam = R / 7.0
        for beta in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            N = int(math.ceil(R + beta * math.sqrt(R)))
            T6.append(("T6|R%g|b%g" % (R, beta), "spec", N, lam, 12.0, POLICIES["single"], 150000, 51))
    # ------------------------------------------------------------------ T7 (long-deadline hackathon regime)
    # time unit = 1 mean service (e.g. one CPU proof hour); p95 = 2 means
    T7 = []
    for N in (1, 2, 3):
        for rho in (0.2, 0.5, 0.8):
            for D in (2.0, 3.0, 4.0):
                T7.append(("T7|N%d|rho%g|D%g" % (N, rho, D), "long", N, rho * N, D,
                           POLICIES["single"], 150000, 61))

    runs = T1 + T2 + T4 + T5 + T6 + T7
    print("running %d fixed-N simulations" % len(runs), flush=True)
    res_runs = pool.map(job_run, runs, chunksize=1)
    out["runs"] = res_runs
    print("fixed-N done in %.0fs" % (time.time() - t0), flush=True)

    # ------------------------------------------------------------------ T3 (min N for 99%)
    lams3 = [1 / 12, 0.5, 1, 2, 5, 10, 20]
    pols3 = ["single", "redundant2 phi=0", "redundant2 phi=0.5", "hedge3 phi=0",
             "hedge3 phi=0.5", "single 15% faster", "single 20% faster"]
    finds = [("T3|%s|%g" % (p, lam), "spec", lam, 12.0, POLICIES[p], 100000, 0.99, 1500)
             for p in pols3 for lam in lams3]
    finds += [("T3|pico single|%g" % lam, "pico", lam, 12.0, POLICIES["single"], 100000, 0.99, 1500)
              for lam in lams3]
    finds += [("T3b|pico single D10|%g" % lam, "pico", lam, 10.0, POLICIES["single"], 100000, 0.95, 1500)
              for lam in lams3]
    print("running %d minimal-N searches" % len(finds), flush=True)
    res_finds = pool.map(job_find, finds, chunksize=1)
    out["finds"] = res_finds
    print("searches done in %.0fs" % (time.time() - t0), flush=True)
    pool.close()
    pool.join()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "queueing_results.json"), "w") as f:
        json.dump(out, f, indent=1)

    # ------------------------------------------------------------------ tables
    by_tag = {r["tag"]: r for r in res_runs}
    L = tables.append

    L("### T1. Adding provers cannot beat the service-time ceiling (spec, lambda = 5 jobs/s, D = 12 s, single assignment)\n")
    L("| N | rho = 7*lambda/N | P(wait > 0) | mean wait (s) | p99 wait (s) | P(proof by 12 s) |")
    L("|---|---|---|---|---|---|")
    for r in res_runs:
        if r["tag"] == "T1":
            L("| %d | %.3f | %.4f | %.3f | %.2f | %.4f |" % (r["N"], 35.0 / r["N"], r["p_wait"], r["mean_wait"], r["p99_wait"], r["success"]))
    L("")

    L("### T2. N = 100 provers, D = 12 s, spec distribution: P(proof by deadline) by arrival rate and policy\n")
    L("| lambda (jobs/s) | offered load 7*lambda | " + " | ".join(pols2) + " |")
    L("|---|---|" + "---|" * len(pols2))
    for lam in lams2:
        cells = []
        for p in pols2:
            r = by_tag["T2|%s|%g" % (p, lam)]
            cells.append("%.4f" % r["success"])
        L("| %s | %.1f | %s |" % (("1/12" if lam < 0.1 else "%g" % lam), 7 * lam, " | ".join(cells)))
    L("")
    L("Work per job (prover-seconds actually consumed, N = 100, lambda = 5): " + ", ".join(
        "%s = %.1f" % (p, by_tag["T2|%s|5" % p]["work_per_job"]) for p in pols2) + "\n")

    L("### T3. Smallest N with P(proof by 12 s) >= 0.99 (spec distribution unless noted)\n")
    L("| lambda (jobs/s) | offered load 7*lambda | " + " | ".join(pols3 + ["pico single"]) + " |")
    L("|---|---|" + "---|" * (len(pols3) + 1))
    fb = {r["tag"]: r for r in res_finds}
    for lam in lams3:
        cells = []
        for p in pols3 + ["pico single"]:
            r = fb["T3|%s|%g" % (p, lam)]
            if r["minN"] is None:
                cells.append("none (%.4f at N=1500)" % r["success"])
            else:
                cells.append("%d (%.4f)" % (r["minN"], r["success"]))
        L("| %s | %.1f | %s |" % (("1/12" if lam < 0.1 else "%g" % lam), 7 * lam, " | ".join(cells)))
    L("")
    L("### T3b. Smallest N with P(proof by 10 s) >= 0.95, Pico-calibrated distribution, single assignment\n")
    L("| lambda (jobs/s) | offered load 6.9*lambda | min N | P(success) at that N |")
    L("|---|---|---|---|")
    for lam in lams3:
        r = fb["T3b|pico single D10|%g" % lam]
        L("| %s | %.1f | %s | %.4f |" % (("1/12" if lam < 0.1 else "%g" % lam), 6.9 * lam,
                                         ("none" if r["minN"] is None else str(r["minN"])), r["success"]))
    L("")

    L("### T4. One L1 chain, one block every 12 s, N clusters (periodic arrivals)\n")
    L("| distribution | D (s) | N clusters | policy | P(proof by D) | P(block waited) | mean wait (s) |")
    L("|---|---|---|---|---|---|---|")
    for r in res_runs:
        if r["tag"].startswith("T4|"):
            _, dist, Dt, Nt, p = r["tag"].split("|")
            L("| %s | %s | %s | %s | %.4f | %.4f | %.3f |" % (dist, Dt[1:], Nt[1:], p, r["success"], r["p_wait"], r["mean_wait"]))
    L("")

    L("### T5. Redundancy only removes the idiosyncratic part of the tail (spec, lambda = 5, N = 150, D = 12)\n")
    L("| phi (job-intrinsic share of log-variance) | redundant k=2: P(success) | work/job (s) | hedge at 3 s: P(success) | work/job (s) |")
    L("|---|---|---|---|---|")
    for phi in (0.0, 0.25, 0.5, 0.75, 1.0):
        a = by_tag["T5|redundant2|%g" % phi]
        b = by_tag["T5|hedge3|%g" % phi]
        L("| %g | %.4f | %.1f | %.4f | %.1f |" % (phi, a["success"], a["work_per_job"], b["success"], b["work_per_job"]))
    L("")

    L("### T6. Square-root staffing check: N = R + beta*sqrt(R), spec distribution, single assignment, D = 12\n")
    L("| R (Erlangs) | beta | N | Erlang C P(wait) (M/M/N) | simulated P(wait) (M/G/N) | Halfin-Whitt limit | simulated P(proof by 12 s) |")
    L("|---|---|---|---|---|---|---|")
    for R in (35.0, 70.0):
        for beta in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            r = by_tag["T6|R%g|b%g" % (R, beta)]
            L("| %g | %g | %d | %.4f | %.4f | %.4f | %.4f |" % (R, beta, r["N"], erlang_c(r["N"], R), r["p_wait"],
                                                                halfin_whitt_pwait(beta) if beta > 0 else 1.0, r["success"]))
    L("")

    L("### T7. Long-deadline regime (time unit = one mean proving run; p95 = 2 units; e.g. hours of CPU proving)\n")
    L("| N workers | rho | D = 2 units | D = 3 units | D = 4 units |")
    L("|---|---|---|---|---|")
    for N in (1, 2, 3):
        for rho in (0.2, 0.5, 0.8):
            cells = ["%.4f" % by_tag["T7|N%d|rho%g|D%g" % (N, rho, D)]["success"] for D in (2.0, 3.0, 4.0)]
            L("| %d | %g | %s |" % (N, rho, " | ".join(cells)))
    L("")

    # analytic tables
    L("### A1. Single-attempt ceilings P(S <= D) and what a uniform speedup moves across the deadline\n")
    L("| distribution | D (s) | P(S <= D) | +5% faster | +10% faster | +15% faster | +25% faster | p99 (s) | p99.9 (s) |")
    L("|---|---|---|---|---|---|---|---|---|")
    for name in ("spec", "pico"):
        mu, s = DISTS[name]
        for D in (10.0, 12.0, 15.0):
            cells = ["%.4f" % ln_cdf(D / (1 - d), mu, s) for d in (0.05, 0.10, 0.15, 0.25)]
            L("| %s | %g | %.4f | %s | %.2f | %.2f |" % (name, D, ln_cdf(D, mu, s), " | ".join(cells), ln_q(0.99, mu, s), ln_q(0.999, mu, s)))
    L("")

    md = "\n".join(tables)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "queueing_tables.md"), "w") as f:
        f.write(md)
    print(md)
    print("total %.0fs" % (time.time() - t0))



# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def add_common(p):
    p.add_argument("--lam", type=float, default=5.0, help="arrival rate, jobs/s")
    p.add_argument("--D", type=float, default=12.0, help="deadline after arrival, s")
    p.add_argument("--mean", type=float, default=7.0)
    p.add_argument("--p95", type=float, default=11.0)
    p.add_argument("--policy", choices=["single", "redundant", "hedge"], default="single")
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--t-h", dest="t_h", type=float, default=3.0)
    p.add_argument("--phi", type=float, default=0.0)
    p.add_argument("--speedup", type=float, default=0.0)
    p.add_argument("--kill", action="store_true")
    p.add_argument("--arrival", choices=["poisson", "periodic"], default="poisson")
    p.add_argument("--jobs", type=int, default=100000)
    p.add_argument("--seed", type=int, default=1)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p_run = sub.add_parser("run")
    add_common(p_run)
    p_run.add_argument("--N", type=int, default=100)
    p_find = sub.add_parser("find")
    add_common(p_find)
    p_find.add_argument("--target", type=float, default=0.99)
    p_find.add_argument("--N-max", dest="N_max", type=int, default=2000)
    sub.add_parser("grid")
    args = ap.parse_args(argv)

    if args.cmd == "grid":
        run_grid()
        return

    mu, s = lognormal_from_mean_quantile(args.mean, args.p95, 0.95)
    kw = dict(policy=args.policy, k=args.k, t_h=args.t_h, phi=args.phi,
              speedup=args.speedup, kill=args.kill, arrival=args.arrival, seed=args.seed)
    if args.cmd == "run":
        r = simulate(args.N, args.lam, args.D, mu, s, n_jobs=args.jobs, **kw)
        print(json.dumps(r, indent=2))
    elif args.cmd == "find":
        N, r = find_min_N(args.target, args.lam, args.D, mu, s, n_jobs=args.jobs,
                          N_max=args.N_max, **kw)
        if N is None:
            print("target not reachable by adding provers; at N=%d P(success)=%.5f" % (args.N_max, r["success"]))
        else:
            print("minimal N = %d" % N)
        print(json.dumps(r, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main(sys.argv[1:])
