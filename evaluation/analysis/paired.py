#!/usr/bin/env python3
"""Frozen acceptance computation (evaluation/policy.json performance.acceptance).

Input: a JSON file with one record per execution:
  {"block": int, "variant": "A"|"B"|"C", "stdinSha256": hex, "pgu": int,
   "reached": bool, "publicValues": hex or null}
where A is the upstream default backend, B the candidate and C the upstream
arena backend (the registered alternative). The evaluator's collector builds
this file from run.txt, report.csv and execution.json of every run.

Output: the acceptance record: per-block medians, improvement against A and
against C, the statistic on the smaller of the two, the percentile bootstrap
interval, the regression check and the verdict for the performance gate.
Correctness and formal gates are separate inputs (--correctness-pass,
--formal-pass) so this script never invents them.

usage: paired.py <executions.json> --policy-hash <hex> [--correctness-pass]
       [--formal-pass] [--out record.json]
       paired.py --self-test
"""
import argparse, hashlib, json, random, statistics, sys

POLICY = {
    "executionsPerVariantPerBlock": 2,
    "minimumMedianPguImprovementPercent": 5.0,
    "maximumRegressionPercentPerBlock": 10.0,
    "minimumPairedBlocks": 8,
    "resamples": 10000,
    "confidence": 0.95,
}


def seed_from(policy_hash):
    return int.from_bytes(hashlib.sha256(b"lemma-eval/1" + bytes.fromhex(policy_hash)).digest()[:8], "big")


def per_block(execs, variant):
    """Median PGU per block for one variant, with the determinism check."""
    out = {}
    blocks = sorted({e["block"] for e in execs})
    for b in blocks:
        rows = [e for e in execs if e["block"] == b and e["variant"] == variant]
        if not rows or not all(r["reached"] for r in rows):
            out[b] = None
            continue
        shas = {r["stdinSha256"] for r in rows}
        pgus = {r["pgu"] for r in rows}
        out[b] = {
            "executions": len(rows),
            "pgu": int(statistics.median(r["pgu"] for r in rows)),
            "sameStdin": len(shas) == 1,
            "identicalPgu": len(pgus) == 1,
            "publicValues": sorted({r.get("publicValues") for r in rows}),
        }
    return out


def improvement(base, cand):
    return 100.0 * (base - cand) / base


def bootstrap(values, resamples, confidence, seed):
    rng = random.Random(seed)
    n = len(values)
    stats = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        stats.append(statistics.median(sample))
    stats.sort()
    lo = stats[int((1 - confidence) / 2 * resamples)]
    hi = stats[min(resamples - 1, int((1 + confidence) / 2 * resamples))]
    return lo, hi


def evaluate(execs, policy_hash, correctness_pass, formal_pass, policy=POLICY):
    a, b, c = per_block(execs, "A"), per_block(execs, "B"), per_block(execs, "C")
    blocks = sorted(a)
    rows = []
    for blk in blocks:
        row = {"block": blk, "A": a[blk], "B": b.get(blk), "C": c.get(blk)}
        row["baselineReached"] = a[blk] is not None
        row["candidateReached"] = b.get(blk) is not None
        if a[blk] and b.get(blk):
            row["improvementVsA"] = improvement(a[blk]["pgu"], b[blk]["pgu"])
            row["improvementVsC"] = improvement(c[blk]["pgu"], b[blk]["pgu"]) if c.get(blk) else None
            # the reported saving is against the better of the two alternatives
            alts = [x for x in (row["improvementVsA"], row["improvementVsC"]) if x is not None]
            row["improvement"] = min(alts)
            row["regressionVsA"] = b[blk]["pgu"] > (1 + policy["maximumRegressionPercentPerBlock"] / 100) * a[blk]["pgu"]
        rows.append(row)
    paired = [r for r in rows if r["baselineReached"] and r["candidateReached"]]
    failed_where_baseline_passed = [r["block"] for r in rows if r["baselineReached"] and not r["candidateReached"]]
    record = {
        "policyHash": policy_hash,
        "policy": policy,
        "blocks": rows,
        "pairedBlocks": [r["block"] for r in paired],
        "candidateFailedWhereBaselineReached": failed_where_baseline_passed,
        "determinism": {
            "everyPairSameStdin": all(v["sameStdin"] for m in (a, b, c) for v in m.values() if v),
            "everyPairIdenticalPgu": all(v["identicalPgu"] for m in (a, b, c) for v in m.values() if v),
        },
    }
    if len(paired) < policy["minimumPairedBlocks"]:
        record["performance"] = "Inconclusive" if not failed_where_baseline_passed else "Fail"
        record["reason"] = f"{len(paired)} paired blocks, minimum {policy['minimumPairedBlocks']}"
    else:
        values = [r["improvement"] for r in paired]
        stat = statistics.median(values)
        seed = seed_from(policy_hash)
        lo, hi = bootstrap(values, policy["resamples"], policy["confidence"], seed)
        regressions = [r["block"] for r in paired if r["regressionVsA"]]
        conditions = {
            "noCandidateFailureWhereBaselineReached": not failed_where_baseline_passed,
            "statisticAtLeastMinimum": stat >= policy["minimumMedianPguImprovementPercent"],
            "intervalLowerBoundAboveZero": lo > 0,
            "noBlockRegressesBeyondCap": not regressions,
        }
        record.update({
            "statistic": stat,
            "interval": {"low": lo, "high": hi, "seed": seed, "resamples": policy["resamples"]},
            "regressions": regressions,
            "conditions": conditions,
            "performance": "Pass" if all(conditions.values()) else "Fail",
        })
    gates = {"correctness": correctness_pass, "formal": formal_pass, "performance": record["performance"] == "Pass"}
    record["gates"] = gates
    if record["performance"] == "Inconclusive":
        record["verdict"] = "Inconclusive" if (correctness_pass and formal_pass) else "Fail"
    else:
        record["verdict"] = "Pass" if all(gates.values()) else "Fail"
    return record


def self_test():
    """Shape of the rule on synthetic ten-block sets; prints what passes."""
    h = "00" * 32
    def synth(impr):
        ex = []
        for i, p in enumerate(impr):
            base = 100_000_000 + i
            cand = int(base * (1 - p / 100))
            for k in range(2):
                ex.append({"block": i, "variant": "A", "stdinSha256": f"a{i}", "pgu": base, "reached": True})
                ex.append({"block": i, "variant": "B", "stdinSha256": f"b{i}", "pgu": cand, "reached": True})
                ex.append({"block": i, "variant": "C", "stdinSha256": f"c{i}", "pgu": base, "reached": True})
        return ex
    cases = {
        "uniform 6%": [6.0] * 10,
        "uniform 5%": [5.0] * 10,
        "uniform 4.9%": [4.9] * 10,
        "8% on nine, -1% on one": [8.0] * 9 + [-1.0],
        "8% on eight, -1% on two": [8.0] * 8 + [-1.0] * 2,
        "8% on seven, -1% on three": [8.0] * 7 + [-1.0] * 3,
        "8% on six, -1% on four": [8.0] * 6 + [-1.0] * 4,
        "20% on five, 0% on five": [20.0] * 5 + [0.0] * 5,
        "6% on nine, -11% on one (cap)": [6.0] * 9 + [-11.0],
        "spread 2..12": [2, 3, 4, 5, 6, 7, 8, 9, 10, 12],
    }
    for name, impr in cases.items():
        r = evaluate(synth(impr), h, True, True)
        iv = r.get("interval")
        interval = "" if not iv else "[%.2f, %.2f]" % (iv["low"], iv["high"])
        print("%-32s statistic=%6.2f interval=%-18s performance=%s" % (name, r.get("statistic", float("nan")), interval, r["performance"]))
    # inconclusive: baseline fails three blocks
    ex = synth([6.0] * 10)
    ex = [e for e in ex if not (e["variant"] == "A" and e["block"] < 3)] + [
        {"block": i, "variant": "A", "stdinSha256": f"a{i}", "pgu": 0, "reached": False} for i in range(3)]
    r = evaluate(ex, h, True, True)
    print(f"{'baseline fails three blocks':32s} performance={r['performance']} verdict={r['verdict']} ({r['reason']})")
    ex = synth([6.0] * 10)
    ex = [e for e in ex if not (e["variant"] == "B" and e["block"] == 0)] + [
        {"block": 0, "variant": "B", "stdinSha256": "b0", "pgu": 0, "reached": False}]
    r = evaluate(ex, h, True, True)
    print(f"{'candidate fails one block':32s} performance={r['performance']} verdict={r['verdict']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("executions", nargs="?")
    ap.add_argument("--policy-hash")
    ap.add_argument("--correctness-pass", action="store_true")
    ap.add_argument("--formal-pass", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        sys.exit(0)
    if not a.executions or not a.policy_hash:
        ap.error("executions file and --policy-hash are required")
    record = evaluate(json.load(open(a.executions)), a.policy_hash, a.correctness_pass, a.formal_pass)
    text = json.dumps(record, indent=2)
    if a.out:
        open(a.out, "w").write(text + "\n")
    print(text if not a.out else f"verdict {record['verdict']} (performance {record['performance']}) written to {a.out}")
