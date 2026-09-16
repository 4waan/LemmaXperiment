#!/usr/bin/env python3
"""Scan a mainnet block range and rank blocks by gasUsed.

Used to pick small blocks for the three real CPU proofs and to sanity-check
development blocks. Holdout selection is a separate, salted rule in
evaluation; this script is only for development and proof-cost planning.

usage: select_blocks.py <start> <count> [--max-gas N]
env:   RPC_1 (archive endpoint)
"""
import json, os, sys, time, urllib.error, urllib.request

rpc = os.environ["RPC_1"]

def call(method, params):
    req = urllib.request.Request(rpc, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                 headers={"content-type":"application/json"})
    return json.load(urllib.request.urlopen(req))["result"]

def batch(start, count):
    payload = [{"jsonrpc":"2.0","id":i,"method":"eth_getBlockByNumber","params":[hex(start+i), False]} for i in range(count)]
    req = urllib.request.Request(rpc, data=json.dumps(payload).encode(), headers={"content-type":"application/json"})
    for attempt in range(6):
        try:
            res = json.load(urllib.request.urlopen(req))
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(2 * (attempt + 1))
    bad = [r for r in res if "result" not in r]
    if bad:
        raise SystemExit(f"rpc error: {bad[0].get('error')}")
    return [r["result"] for r in sorted(res, key=lambda r: r["id"])]

start, count = int(sys.argv[1]), int(sys.argv[2])
max_gas = int(sys.argv[sys.argv.index("--max-gas")+1]) if "--max-gas" in sys.argv else None
rows = []
for off in range(0, count, 20):
    time.sleep(0.5)
    for b in batch(start+off, min(20, count-off)):
        rows.append((int(b["number"],16), int(b["gasUsed"],16), len(b["transactions"]), int(b["timestamp"],16)))
rows.sort(key=lambda r: r[1])
print(f"{'block':>10} {'gasUsed':>10} {'txs':>4}")
for n, g, t, ts in rows:
    if max_gas is None or g <= max_gas:
        print(f"{n:>10} {g:>10} {t:>4}")
