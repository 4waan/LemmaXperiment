#!/usr/bin/env python3
"""Proof dependency graph simulator: centrality, marginal contribution, Shapley
attribution, criticality, and the attacks that break naive scores.

Pure Python 3 standard library. Companion to PROOF_GRAPH.md.

The ecosystem below is synthetic. Job costs are prover gas units (PGU) scaled
from the one recorded execute run in LemmaXperiment (block 18884864, 108.5 M
PGU). Parameters were chosen so that each phenomenon discussed in the note is
visible; they are illustrations, not estimates, and nothing here is a
measurement of any real module.

Model
  Modules form a DAG through AND dependencies (a module needs all of its deps).
  A job class lists feasible program configurations (OR choices), each a set of
  modules with a cost multiplier on the job's base PGU, plus a "none" option:
  the buyer's fallback if no configuration is feasible (direct onchain check,
  or the funded willingness to pay). A rational buyer takes the cheapest option.

  C(G)        = sum over settled jobs of the cheapest option available in G
  MC_short(j) = C(G - j - everything that transitively depends on j) - C(G)
  MC_local(j) = same, but only configurations that name j directly are removed
                (ignores the cascade; shown to demonstrate why that is wrong)
  Shapley     = per job, the saving game over market modules that are optional
                for that job class; enabling modules (present in every feasible
                configuration) are held fixed and their surplus reported apart
  PCS         = usage * marginal_speedup * success * dependency_reach, the score
                proposed in the brief, defined here in its most favorable reading

Usage
  python3 proof_graph_sim.py tables        # every table in PROOF_GRAPH.md
  python3 proof_graph_sim.py tables --seed 7
"""
import argparse
import copy
import itertools
import math
import random
import sys
from collections import defaultdict

INF = float("inf")
BLOCK_PGU = 108_529_239          # recorded execute run, block 18884864
PROVE_PER_BPGU = 2.0             # Succinct quickstart example price cap
BASE_FEE_PROVE = 0.2             # Succinct quickstart example base fee
CONTRIBUTOR_SHARE = 0.10         # r: share of a job's fee paid to module payees

# ----------------------------------------------------------------------------
# synthetic ecosystem
# ----------------------------------------------------------------------------
# recreate: declared long-run cost of doing without the module, in PGU
# equivalents: the cheaper of re-basing its dependents on an existing
# alternative or recreating it. None means "not something the market can
# recreate" (upstream infrastructure). Synthetic values.
MODULES = {
    "upstream-rsp":        dict(deps=[], market=False, creator="upstream", recreate=None),
    "upstream-codec":      dict(deps=[], market=False, creator="upstream", recreate=None),
    "membership-baseline": dict(deps=["upstream-codec"], market=False, creator="team", recreate=None),
    "bindings-wrapper":    dict(deps=[], market=False, creator="team", recreate=None),
    "codec@1":             dict(deps=[], market=True, creator="alice", recreate=60_000_000),
    "witness-cache@1":     dict(deps=["codec@1"], market=True, creator="alice", recreate=1_500_000_000),
    "arena-backend@1":     dict(deps=["codec@1"], market=True, creator="bob", recreate=1_000_000_000),
    "multiproof@1":        dict(deps=["codec@1"], market=True, creator="carol", recreate=800_000_000),
    "fork-adapter@1":      dict(deps=["codec@1"], market=True, creator="dave", recreate=600_000_000),
    "telemetry@1":         dict(deps=[], market=True, creator="erin", recreate=50_000_000),
}

THEOREMS = {
    "T-cache-refinement": "witness-cache@1",
    "T-multiproof-equiv": "multiproof@1",
    "T-codec-canonical":  "codec@1",
}

# Which payers are affiliated with which creator (disclosed relationships).
AFFILIATED = {"alice-affiliate": "alice"}


def fs(*names):
    return frozenset(names)


CLASSES = {
    "block-cancun": dict(
        base=(95_000_000, 125_000_000),
        configs={
            fs("upstream-rsp", "bindings-wrapper", "upstream-codec"): 1.000,
            fs("upstream-rsp", "bindings-wrapper", "codec@1"): 0.990,
            fs("upstream-rsp", "bindings-wrapper", "arena-backend@1"): 0.970,
            fs("upstream-rsp", "bindings-wrapper", "witness-cache@1"): 0.950,
            fs("upstream-rsp", "bindings-wrapper", "witness-cache@1", "arena-backend@1"): 0.935,
        },
        none=1.5,                      # funded willingness to pay, x base
        bundle="telemetry@1",          # optional add-on, no cost effect
        payers=["P1", "P2", "P3", "P4", "P5", "alice-affiliate"],
        n=30, failed=2,
    ),
    "block-prague": dict(
        base=(95_000_000, 125_000_000),
        configs={
            fs("upstream-rsp", "bindings-wrapper", "fork-adapter@1"): 1.000,
            fs("upstream-rsp", "bindings-wrapper", "fork-adapter@1", "witness-cache@1"): 0.950,
        },
        none=1.5,
        bundle=None,
        payers=["P6", "P7"],
        n=8, failed=0,
    ),
    "membership-small": dict(
        base=(1_600_000, 2_400_000),
        configs={
            fs("bindings-wrapper", "membership-baseline"): 1.00,
            fs("bindings-wrapper", "multiproof@1"): 0.80,
        },
        none=0.90,                     # direct onchain check is cheaper than the baseline proof
        bundle=None,
        payers=["P8", "P9"],
        n=10, failed=0,
    ),
    "membership-large": dict(
        base=(4_800_000, 7_200_000),
        configs={
            fs("bindings-wrapper", "membership-baseline"): 1.00,
            fs("bindings-wrapper", "multiproof@1"): 0.75,
        },
        none=2.00,
        bundle=None,
        payers=["P8", "P9"],
        n=10, failed=0,
    ),
}


# ----------------------------------------------------------------------------
# graph helpers
# ----------------------------------------------------------------------------
class Ecosystem:
    def __init__(self, modules, classes, seed=1):
        self.modules = copy.deepcopy(modules)
        self.classes = copy.deepcopy(classes)
        self.rng = random.Random(seed)
        self.jobs = []
        self._closure_cache = {}
        self._make_jobs()

    # -- structure -----------------------------------------------------------
    def closure(self, m):
        """m plus all transitive dependencies."""
        if m in self._closure_cache:
            return self._closure_cache[m]
        out = {m}
        stack = list(self.modules[m]["deps"])
        while stack:
            d = stack.pop()
            if d not in out:
                out.add(d)
                stack.extend(self.modules[d]["deps"])
        self._closure_cache[m] = frozenset(out)
        return self._closure_cache[m]

    def config_closure(self, cfg):
        out = set()
        for m in cfg:
            out |= self.closure(m)
        return frozenset(out)

    def dependents(self, j):
        """modules (other than j) whose closure contains j"""
        return {m for m in self.modules if m != j and j in self.closure(m)}

    def in_degree(self, j):
        return sum(1 for m in self.modules if j in self.modules[m]["deps"])

    # -- jobs ----------------------------------------------------------------
    def _make_jobs(self):
        jid = 0
        for cname, c in self.classes.items():
            for i in range(c["n"] + c["failed"]):
                base = self.rng.uniform(*c["base"])
                payer = self.rng.choice(c["payers"])
                bundled = c["bundle"] is not None and self.rng.random() < 0.5
                self.jobs.append(dict(
                    id=f"{cname}-{jid}", cls=cname, base=base, payer=payer,
                    bundled=bundled, status="settled" if i < c["n"] else "failed",
                ))
                jid += 1

    def add_job(self, cname, payer, base=None, status="settled"):
        c = self.classes[cname]
        base = base if base is not None else self.rng.uniform(*c["base"])
        self.jobs.append(dict(id=f"{cname}-x{len(self.jobs)}", cls=cname, base=base,
                              payer=payer, bundled=False, status=status))

    def all_modules(self):
        return frozenset(self.modules)

    def feasible(self, cfg, available):
        return self.config_closure(cfg) <= available

    def cost(self, job, available):
        """cheapest option for the job given the available module set"""
        c = self.classes[job["cls"]]
        best = c["none"] * job["base"]
        for cfg, mult in c["configs"].items():
            if self.feasible(cfg, available):
                best = min(best, mult * job["base"])
        return best

    def used(self, job, available=None):
        """configuration actually used (argmin), or None if the buyer fell back"""
        available = available if available is not None else self.all_modules()
        c = self.classes[job["cls"]]
        best, bestcfg = c["none"] * job["base"], None
        for cfg, mult in sorted(c["configs"].items(), key=lambda kv: (kv[1], sorted(kv[0]))):
            if self.feasible(cfg, available) and mult * job["base"] < best:
                best, bestcfg = mult * job["base"], cfg
        if bestcfg is None:
            return None
        if job["bundled"] and c["bundle"]:
            bestcfg = bestcfg | {c["bundle"]}
        return bestcfg

    def used_closure(self, job):
        u = self.used(job)
        return self.config_closure(u) if u else frozenset()

    def fee(self, job):
        pgu = self.cost(job, self.all_modules())
        return BASE_FEE_PROVE + PROVE_PER_BPGU * pgu / 1e9

    def settled(self):
        return [j for j in self.jobs if j["status"] == "settled"]

    # -- metrics -------------------------------------------------------------
    def uses(self, j, job):
        return j in self.used_closure(job)

    def usage(self, j):
        return [job for job in self.settled() if self.uses(j, job)]

    def money_reach(self, j):
        return sum(self.fee(job) for job in self.usage(j))

    def reach(self, j):
        return len(self.dependents(j)) + len(self.usage(j))

    def success(self, j):
        used = [job for job in self.jobs if self.uses(j, job)]
        if not used:
            return 0.0
        return sum(1 for job in used if job["status"] == "settled") / len(used)

    def speedup(self, j):
        """brief's 'marginal_speedup', most favorable reading: the whole job-level
        saving versus the upstream-only pipeline, credited to every module used"""
        vals = []
        nonmarket = frozenset(m for m in self.modules if not self.modules[m]["market"])
        for job in self.usage(j):
            base = self.cost(job, nonmarket)
            vals.append((base - self.cost(job, self.all_modules())) / base)
        return sum(vals) / len(vals) if vals else 0.0

    def pcs(self, j):
        return len(self.usage(j)) * self.speedup(j) * self.success(j) * self.reach(j)

    def pcs_mc(self, j):
        """PCS with marginal_speedup read as the module's own marginal saving fraction
        (MC_short over the base PGU of the jobs that used it)"""
        jobs = self.usage(j)
        if not jobs:
            return 0.0
        frac = self.mc_short(j) / sum(job["base"] for job in jobs)
        return len(jobs) * frac * self.success(j) * self.reach(j)

    def mc_short(self, j, jobs=None):
        """cascade removal: j and everything depending on it disappear"""
        jobs = jobs if jobs is not None else self.settled()
        removed = self.dependents(j) | {j}
        avail = self.all_modules() - removed
        return sum(self.cost(job, avail) - self.cost(job, self.all_modules()) for job in jobs)

    def mc_split(self, j):
        """MC_short split into the part where an alternative exists and the part
        where the job falls back to 'none' (enabling surplus)"""
        removed = self.dependents(j) | {j}
        avail = self.all_modules() - removed
        subst, enable = 0.0, 0.0
        for job in self.settled():
            with_ = self.cost(job, self.all_modules())
            without = self.cost(job, avail)
            if without == with_:
                continue
            c = self.classes[job["cls"]]
            has_alt = any(self.feasible(cfg, avail) for cfg in c["configs"])
            if has_alt:
                subst += without - with_
            else:
                enable += without - with_
        return subst, enable

    def mc_local(self, j):
        """no cascade: only configurations naming j directly are unavailable"""
        total = 0.0
        for job in self.settled():
            c = self.classes[job["cls"]]
            best = c["none"] * job["base"]
            for cfg, mult in c["configs"].items():
                if j in cfg:
                    continue
                if self.feasible(cfg, self.all_modules()):
                    best = min(best, mult * job["base"])
            total += best - self.cost(job, self.all_modules())
        return total

    def or_alternatives(self, j):
        """minimum over jobs using j of the number of feasible configurations
        whose closure excludes j (0 means j is enabling for some job)"""
        counts = []
        for job in self.usage(j):
            c = self.classes[job["cls"]]
            n = sum(1 for cfg in c["configs"]
                    if j not in self.config_closure(cfg) and self.feasible(cfg, self.all_modules()))
            counts.append(n)
        return min(counts) if counts else None

    def mc_independent(self, j):
        creator = self.modules[j]["creator"]
        jobs = [job for job in self.settled() if AFFILIATED.get(job["payer"]) != creator]
        return self.mc_short(j, jobs)

    def effective_payers(self, j):
        money = defaultdict(float)
        for job in self.usage(j):
            money[job["payer"]] += self.fee(job)
        tot = sum(money.values())
        if tot == 0:
            return 0.0
        return 1.0 / sum((v / tot) ** 2 for v in money.values())

    # -- Shapley saving game ---------------------------------------------------
    def saving_game(self, job):
        """players: market modules in the class's configurations, minus the enabling
        set E (market modules in every feasible configuration's closure). v(T) is
        the saving relative to the pipeline with only non-market modules plus E."""
        c = self.classes[job["cls"]]
        nonmarket = frozenset(m for m in self.modules if not self.modules[m]["market"])
        market_in_class = set()
        closures = []
        for cfg in c["configs"]:
            cl = self.config_closure(cfg)
            closures.append(cl)
            market_in_class |= {m for m in cl if self.modules[m]["market"]}
        if c["bundle"]:
            market_in_class.add(c["bundle"])
        enabling = frozenset(set.intersection(*[set(cl) for cl in closures]) & market_in_class)
        players = sorted(market_in_class - enabling)
        fixed = nonmarket | enabling
        ref = self.cost(job, fixed)

        def v(T):
            return ref - self.cost(job, fixed | frozenset(T))

        return players, v, enabling, ref

    def shapley(self, job):
        players, v, enabling, ref = self.saving_game(job)
        m = len(players)
        phi = {p: 0.0 for p in players}
        for p in players:
            others = [q for q in players if q != p]
            for r in range(len(others) + 1):
                for T in itertools.combinations(others, r):
                    w = math.factorial(r) * math.factorial(m - r - 1) / math.factorial(m)
                    phi[p] += w * (v(set(T) | {p}) - v(set(T)))
        c = self.classes[job["cls"]]
        surplus = (c["none"] * job["base"] - ref) if enabling else 0.0
        return phi, enabling, surplus

    def shapley_by_creator(self, job):
        """same game, but players are creators: a creator's modules enter together"""
        players, v, enabling, ref = self.saving_game(job)
        creators = sorted({self.modules[p]["creator"] for p in players})
        mods_of = {c: [p for p in players if self.modules[p]["creator"] == c] for c in creators}

        def vc(C):
            return v({p for c in C for p in mods_of[c]})

        m = len(creators)
        phi = {c: 0.0 for c in creators}
        for c in creators:
            others = [d for d in creators if d != c]
            for r in range(len(others) + 1):
                for T in itertools.combinations(others, r):
                    w = math.factorial(r) * math.factorial(m - r - 1) / math.factorial(m)
                    phi[c] += w * (vc(set(T) | {c}) - vc(set(T)))
        return phi

    def shapley_creator_totals(self):
        tot = defaultdict(float)
        for job in self.settled():
            for c, val in self.shapley_by_creator(job).items():
                tot[c] += val
        return tot

    def shapley_totals(self):
        tot = defaultdict(float)
        surplus_at_risk = defaultdict(float)
        for job in self.settled():
            phi, enabling, surplus = self.shapley(job)
            for p, val in phi.items():
                tot[p] += val
            for e in enabling:
                surplus_at_risk[e] += surplus
        return tot, surplus_at_risk


# ----------------------------------------------------------------------------
# formatting
# ----------------------------------------------------------------------------
def M(x):
    if x is None or x == INF:
        return "n/a"
    return f"{x / 1e6:,.1f}"


def table(headers, rows, aligns=None):
    widths = [len(h) for h in headers]
    srows = [[str(c) for c in r] for r in rows]
    for r in srows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))
    aligns = aligns or ["<"] + [">"] * (len(headers) - 1)
    line = "  ".join(f"{h:{a}{w}}" for h, a, w in zip(headers, aligns, widths))
    out = [line, "  ".join("-" * w for w in widths)]
    for r in srows:
        out.append("  ".join(f"{c:{a}{w}}" for c, a, w in zip(r, aligns, widths)))
    return "\n".join(out)


def node_table(eco, nodes=None, title=None):
    nodes = nodes or list(eco.modules)
    sh, risk = eco.shapley_totals()
    rows = []
    for j in nodes:
        subst, enable = eco.mc_split(j)
        rec = eco.modules[j]["recreate"]
        capped = min(sh.get(j, 0.0), rec) if rec is not None else sh.get(j, 0.0)
        alt = eco.or_alternatives(j)
        rows.append([
            j,
            eco.in_degree(j),
            eco.reach(j),
            len(eco.usage(j)),
            f"{eco.money_reach(j):.2f}",
            "n/a" if alt is None else alt,
            M(subst),
            M(enable),
            M(sh.get(j, 0.0)),
            M(rec) if rec is not None else "inf",
            M(capped),
            f"{eco.pcs(j):.1f}",
            f"{eco.pcs_mc(j):.1f}",
        ])
    rows.sort(key=lambda r: -float(r[2]))
    hdr = ["node", "in", "reach", "usage", "money PROVE", "alt", "MC subst M", "MC enable M",
           "Shapley M", "recreate M", "capped M", "PCS(job)", "PCS(MC)"]
    s = table(hdr, rows)
    if title:
        s = title + "\n" + s
    return s


# ----------------------------------------------------------------------------
# experiments
# ----------------------------------------------------------------------------
def exp_baseline(seed):
    eco = Ecosystem(MODULES, CLASSES, seed)
    print("T1. Synthetic ecosystem: every metric per node (M = million PGU-equivalents)")
    print(f"    settled jobs: {len(eco.settled())}, failed: {len(eco.jobs) - len(eco.settled())}, "
          f"C(G) = {M(sum(eco.cost(j, eco.all_modules()) for j in eco.settled()))} M PGU")
    print(node_table(eco))
    print()
    tot, _ = eco.shapley_totals()
    surplus = sum(eco.shapley(j)[2] for j in eco.settled())
    saving = sum(eco.cost(j, frozenset(m for m in eco.modules if not eco.modules[m]['market']))
                 - eco.cost(j, eco.all_modules()) for j in eco.settled())
    print(f"    efficiency check: sum of Shapley {M(sum(tot.values()))} M + enabling surplus "
          f"{M(surplus)} M = {M(sum(tot.values()) + surplus)} M; total saving vs upstream-only = {M(saving)} M")
    ctot = eco.shapley_creator_totals()
    print("    Shapley by creator (payee-level): " + ", ".join(f"{c} {M(v)} M" for c, v in sorted(ctot.items())))
    print()
    return eco


def exp_cascade(eco):
    print("T2. Cascade: removing a node removes everything that depends on it")
    rows = []
    for j in ["codec@1", "witness-cache@1", "arena-backend@1", "fork-adapter@1", "telemetry@1"]:
        rows.append([j, sorted(eco.dependents(j)) or "-", M(eco.mc_local(j)), M(eco.mc_short(j))])
    print(table(["node", "dependents", "MC local M", "MC short M"], rows, ["<", "<", ">", ">"]))
    print()


def exp_best_alternative(eco):
    print("T3. The counterfactual is the best alternative, not the naive baseline (membership jobs)")
    rows = []
    for cname in ["membership-small", "membership-large"]:
        jobs = [j for j in eco.settled() if j["cls"] == cname]
        naive = sum(j["base"] * 1.00 - eco.cost(j, eco.all_modules()) for j in jobs)
        avail = eco.all_modules() - {"multiproof@1"}
        best_alt = sum(eco.cost(j, avail) - eco.cost(j, eco.all_modules()) for j in jobs)
        c = eco.classes[cname]
        rows.append([cname, len(jobs), f"{c['none']:.2f} x base", M(naive), M(best_alt)])
    print(table(["class", "jobs", "direct check", "dC vs naive M", "dC vs best alt M"],
                rows, ["<", ">", ">", ">", ">"]))
    print()


def exp_sybil(seed, n=20):
    eco = Ecosystem(MODULES, CLASSES, seed)
    target = "witness-cache@1"
    before = dict(in_=eco.in_degree(target), reach=eco.reach(target), usage=len(eco.usage(target)),
                  pcs=eco.pcs(target), mc=eco.mc_short(target))
    for i in range(n):
        eco.modules[f"sybil-{i}"] = dict(deps=[target], market=True, creator="mallory", recreate=0)
    eco._closure_cache.clear()
    after = dict(in_=eco.in_degree(target), reach=eco.reach(target), usage=len(eco.usage(target)),
                 pcs=eco.pcs(target), mc=eco.mc_short(target))
    print(f"T4. Sybil packages: {n} empty packages declare a dependency on {target} (cost to attacker: registry curation only)")
    rows = [[k, f"{before[k]:.2f}" if isinstance(before[k], float) else before[k],
             f"{after[k]:.2f}" if isinstance(after[k], float) else after[k],
             f"x{after[k] / before[k]:.2f}" if before[k] else "-"]
            for k in ["in_", "reach", "usage", "pcs", "mc"]]
    rows = [[{"in_": "in-degree", "reach": "reach", "usage": "usage", "pcs": "PCS", "mc": "MC short (PGU)"}[r[0]]] + r[1:] for r in rows]
    print(table(["metric", "before", "after", "ratio"], rows))
    print()


def exp_wash(seed, n=20):
    eco = Ecosystem(MODULES, CLASSES, seed)
    target = "witness-cache@1"
    before = dict(usage=len(eco.usage(target)), pcs=eco.pcs(target), mc=eco.mc_short(target),
                  mc_ind=eco.mc_independent(target), payers=eco.effective_payers(target))
    cost = 0.0
    for i in range(n):
        eco.add_job("block-cancun", "alice-affiliate")
        cost += eco.fee(eco.jobs[-1]) * (1 - CONTRIBUTOR_SHARE)
    after = dict(usage=len(eco.usage(target)), pcs=eco.pcs(target), mc=eco.mc_short(target),
                 mc_ind=eco.mc_independent(target), payers=eco.effective_payers(target))
    print(f"T5. Wash jobs: {n} self-funded settled jobs on {target} by an affiliated payer")
    rows = []
    for k, label in [("usage", "usage"), ("pcs", "PCS"), ("mc", "MC short (M PGU)"),
                     ("mc_ind", "MC independent payers (M PGU)"), ("payers", "effective payers (1/HHI)")]:
        b, a = before[k], after[k]
        if k in ("mc", "mc_ind"):
            b, a = b / 1e6, a / 1e6
        rows.append([label, f"{b:.2f}", f"{a:.2f}", f"x{a / b:.2f}" if b else "-"])
    print(table(["metric", "before", "after", "ratio"], rows))
    fabricated = (after["mc"] - before["mc"]) / 1e9 * PROVE_PER_BPGU
    print(f"    attacker outlay: {cost:.2f} PROVE net of the {CONTRIBUTOR_SHARE:.0%} contributor share "
          f"({n} jobs) to add {fabricated:.3f} PROVE of measured saving to the ledger: "
          f"{cost / fabricated:.0f} PROVE spent per PROVE of ledger value. The ledger pays nothing on its "
          f"total, so the outlay is recovered only if something external pays on MC at more than that rate.")
    print()


def exp_split(seed):
    eco = Ecosystem(MODULES, CLASSES, seed)
    orig = "witness-cache@1"
    sh, _ = eco.shapley_totals()
    before = dict(reach=eco.reach(orig), pcs=eco.pcs(orig), mc=eco.mc_short(orig), sh=sh[orig],
                  shc=eco.shapley_creator_totals()["alice"])

    mods = copy.deepcopy(MODULES)
    del mods[orig]
    mods["witness-cache-a@1"] = dict(deps=["codec@1"], market=True, creator="alice", recreate=750_000_000)
    mods["witness-cache-b@1"] = dict(deps=["codec@1"], market=True, creator="alice", recreate=750_000_000)
    classes = copy.deepcopy(CLASSES)
    for c in classes.values():
        new = {}
        for cfg, mult in c["configs"].items():
            if orig in cfg:
                cfg = (cfg - {orig}) | {"witness-cache-a@1", "witness-cache-b@1"}
            new[cfg] = mult
        c["configs"] = new
    eco2 = Ecosystem(mods, classes, seed)
    sh2, _ = eco2.shapley_totals()
    parts = ["witness-cache-a@1", "witness-cache-b@1"]
    after = dict(reach=sum(eco2.reach(p) for p in parts), pcs=sum(eco2.pcs(p) for p in parts),
                 mc=sum(eco2.mc_short(p) for p in parts), sh=sum(sh2[p] for p in parts),
                 shc=eco2.shapley_creator_totals()["alice"])
    print("T6. Split: one module republished as two complementary halves (both required)")
    rows = []
    for k, label in [("reach", "reach (sum)"), ("pcs", "PCS (sum)"), ("mc", "MC short (sum, M PGU)"),
                     ("sh", "Shapley over nodes (sum, M PGU)"), ("shc", "Shapley over creators: alice (M PGU)")]:
        b, a = before[k], after[k]
        if k in ("mc", "sh", "shc"):
            b, a = b / 1e6, a / 1e6
        rows.append([label, f"{b:.2f}", f"{a:.2f}", f"x{a / b:.2f}" if b else "-"])
    print(table(["metric", "one module", "two halves", "ratio"], rows))
    print()


def exp_criticality(eco):
    print("T7. Criticality: nodes with no alternative, ranked by exposure (redundancy bounty candidates)")
    print("    exposure = what settled buyers would have lost had the node not existed (cascade included)")
    _, risk = eco.shapley_totals()
    rows = []
    for j in eco.modules:
        alt = eco.or_alternatives(j)
        subst, enable = eco.mc_split(j)
        if enable > 0 or (alt == 0):
            crit_jobs = [job for job in eco.usage(j)
                         if not any(eco.feasible(cfg, eco.all_modules() - eco.dependents(j) - {j})
                                    for cfg in eco.classes[job["cls"]]["configs"])]
            money = sum(eco.fee(job) for job in crit_jobs)
            rec = eco.modules[j]["recreate"]
            rows.append([j, len(crit_jobs), f"{money:.2f}", M(enable), M(rec) if rec is not None else "inf",
                         "outside market" if not eco.modules[j]["market"] else
                         ("redundancy bounty <= min(exposure, recreate)")])
    rows.sort(key=lambda r: -float(r[3].replace(",", "")))
    print(table(["node", "jobs w/o alt", "fees PROVE", "exposure M", "recreate M", "action"],
                rows, ["<", ">", ">", ">", ">", "<"]))
    print()


def exp_aggregation():
    print("T8. Recursive aggregation: when does a reused child proof have positive marginal value?")
    print("    MC(n) = n*i - (c + n*v): i = inline cost of the subcomputation, c = i + o cost of proving it")
    print("    separately (o = per-proof overhead), v = cost of verifying the child inside each parent.")
    print("    Break-even parents n* = (i + o) / (i - v). All quantities as fractions of i.")
    rows = []
    for o in [0.0, 0.1, 0.3]:
        for v in [0.05, 0.2, 0.5]:
            nstar = (1 + o) / (1 - v)
            mcs = [f"{(n - (1 + o) - n * v):+.2f}" for n in [1, 2, 3, 5]]
            rows.append([f"{o:.1f}", f"{v:.2f}", f"{nstar:.2f}", math.ceil(nstar - 1e-9)] + mcs)
    print(table(["o/i", "v/i", "n*", "min n", "MC n=1", "MC n=2", "MC n=3", "MC n=5"], rows))
    print("    A child proof consumed by exactly one parent never has positive marginal value.")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tables"])
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    eco = exp_baseline(args.seed)
    exp_cascade(eco)
    exp_best_alternative(eco)
    exp_sybil(args.seed)
    exp_wash(args.seed)
    exp_split(args.seed)
    exp_criticality(eco)
    exp_aggregation()


if __name__ == "__main__":
    main()
