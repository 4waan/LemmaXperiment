#!/usr/bin/env python3
"""Pick one fork-support check block per mainnet fork era, by a fixed rule.

For each era the rule is: take the 120-block window that starts 10,000 blocks
after the era's activation block (well inside the era, past the transition
block), rank the window by gasUsed, and take the lower median. For the current
era (no next fork scheduled) the window is the 120 blocks ending at the block
that was `finalized` when this script ran; that block number is printed so the
choice can be re-derived. The result is a fork-support check, not a benchmark.

usage: fork_windows.py [--window 120] [--offset 10000]
env:   RPC_1 (archive endpoint)
"""
import json, os, sys, time, urllib.error, urllib.request

rpc = os.environ["RPC_1"]

# alloy-hardforks 0.4.7 (the version locked by the pinned RSP), src/ethereum/mainnet.rs
FORKS = [
    ("prague", 1_746_612_311),
    ("osaka", 1_764_798_551),
    ("bpo1", 1_765_290_071),
    ("bpo2", 1_767_747_671),
]


def post(payload):
    req = urllib.request.Request(rpc, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json"})
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(2 * (attempt + 1))


def header(tag):
    r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [tag, False]})
    b = r["result"]
    return int(b["number"], 16), int(b["timestamp"], 16), int(b["gasUsed"], 16), len(b["transactions"])


def first_block_at_or_after(ts, lo, hi):
    """Smallest block number in [lo, hi] whose timestamp is >= ts."""
    while lo < hi:
        mid = (lo + hi) // 2
        if header(hex(mid))[1] >= ts:
            hi = mid
        else:
            lo = mid + 1
    return lo


def window(start, count):
    rows = []
    for off in range(0, count, 20):
        payload = [{"jsonrpc": "2.0", "id": i, "method": "eth_getBlockByNumber",
                    "params": [hex(start + off + i), False]} for i in range(min(20, count - off))]
        res = post(payload)
        bad = [r for r in res if "result" not in r]
        if bad:
            raise SystemExit(f"rpc error: {bad[0].get('error')}")
        for r in sorted(res, key=lambda r: r["id"]):
            b = r["result"]
            rows.append((int(b["number"], 16), int(b["gasUsed"], 16), len(b["transactions"]), int(b["timestamp"], 16)))
        time.sleep(0.3)
    return rows


def lower_median(rows):
    by_gas = sorted(rows, key=lambda r: (r[1], r[0]))
    return by_gas[(len(by_gas) - 1) // 2]


args = sys.argv[1:]
win = int(args[args.index("--window") + 1]) if "--window" in args else 120
offset = int(args[args.index("--offset") + 1]) if "--offset" in args else 10_000

fin_number, fin_ts, _, _ = header("finalized")
out = {"rule": f"lower median gasUsed of a {win}-block window; past eras: window starts activation+{offset}; "
               f"current era: window ends at the finalized block at selection time",
       "finalizedAtSelection": {"number": fin_number, "timestamp": fin_ts}, "eras": {}}
lo = 22_000_000
for i, (name, ts) in enumerate(FORKS):
    activation = first_block_at_or_after(ts, lo, fin_number)
    lo = activation
    current = i == len(FORKS) - 1
    start = fin_number - win + 1 if current else activation + offset
    rows = window(start, win)
    n, g, t, bts = lower_median(rows)
    gas = sorted(r[1] for r in rows)
    out["eras"][name] = {
        "activationBlock": activation, "activationTimestamp": ts,
        "window": [start, start + win - 1],
        "windowGasUsed": {"min": gas[0], "median": gas[(len(gas) - 1) // 2], "max": gas[-1]},
        "check": {"block": n, "gasUsed": g, "txCount": t, "timestamp": bts},
    }
    print(f"{name:7} activation {activation} window {start}-{start + win - 1} -> block {n} gasUsed {g} txs {t}", file=sys.stderr)
json.dump(out, sys.stdout, indent=2)
print()
