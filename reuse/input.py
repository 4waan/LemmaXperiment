#!/usr/bin/env python3
"""Write reuse/input.json: the identity of the fresh reuse input
(BUILD_CASE_MAP.md F0 item 3, reuse/README.md step 1), recorded before any
measured use.

Selection rule (no randomness, no sealed material read):
- The block must lie inside the supported range S = [19426587, 22431083]
  (evaluation/holdout/RULE.md section 1) so the pinned host reproduces it.
- It must not be a public development block (demand/spec.json
  publicDevelopmentBlocks) or an apparatus-executed block.
- It must be disjoint from holdout set 1 by construction. RULE.md rejects
  any window that contains a block within 1000 of an executed block, so
  every block in [20599066, 20601066] is excluded from every possible
  holdout window. Choosing inside that margin proves disjointness from the
  frozen rule alone; nothing sealed is opened.
- Among [20600067, 20601066] (the 1000 blocks after the baseline block),
  take the block with the lowest gasUsed, lowest number on ties, so that a
  real proof of it fits one GitHub runner job (apparatus/pins.json
  hardware.runnerThroughput).

The header is taken from two unrelated public endpoints that must agree.
The sha256 of the written file is `freshReuseInputHash` in demand/spec.json.

usage: input.py            (scan, select, write)
env:   RPC_A, RPC_B optional endpoint overrides
"""
import hashlib, json, os, urllib.request

A = os.environ.get("RPC_A", "https://ethereum-rpc.publicnode.com")
B = os.environ.get("RPC_B", "https://eth.drpc.org")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUPPORTED = (19426587, 22431083)
BASELINE = 20600066
MARGIN = 1000
DEVELOPMENT = json.load(open(os.path.join(ROOT, "demand", "spec.json")))["publicDevelopmentBlocks"]
EXECUTED = [18884864, 20600000, 20600066, 22441128, 23945771, 23985839, 25988970, 25988980]  # RULE.md X


def rpc(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "user-agent": "lemma-reuse-input/1"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def fields(b):
    return {"number": int(b["number"], 16), "hash": b["hash"], "parentHash": b["parentHash"], "stateRoot": b["stateRoot"],
            "transactionsRoot": b["transactionsRoot"], "receiptsRoot": b["receiptsRoot"], "withdrawalsRoot": b.get("withdrawalsRoot"),
            "timestamp": int(b["timestamp"], 16), "gasUsed": int(b["gasUsed"], 16), "gasLimit": int(b["gasLimit"], 16),
            "baseFeePerGas": int(b["baseFeePerGas"], 16), "blobGasUsed": int(b.get("blobGasUsed", "0x0"), 16),
            "excessBlobGas": int(b.get("excessBlobGas", "0x0"), 16), "txCount": len(b["transactions"])}


def header(url, n):
    return fields(rpc(url, {"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [hex(n), False]})["result"])


lo, hi = BASELINE + 1, BASELINE + MARGIN
assert SUPPORTED[0] + MARGIN <= lo and hi <= SUPPORTED[1]
scan = []
for s in range(lo, hi + 1, 50):
    nums = range(s, min(s + 50, hi + 1))
    body = [{"jsonrpc": "2.0", "id": n, "method": "eth_getBlockByNumber", "params": [hex(n), False]} for n in nums]
    for r in rpc(A, body):
        b = r["result"]
        scan.append((int(b["gasUsed"], 16), int(b["number"], 16)))
scan.sort()
gas, chosen = scan[0]
assert chosen not in DEVELOPMENT and chosen not in EXECUTED
assert any(abs(chosen - x) <= MARGIN for x in EXECUTED), "not inside an exclusion margin"

ha, hb = header(A, chosen), header(B, chosen)
if ha != hb:
    raise SystemExit(f"providers disagree on block {chosen}:\n{ha}\n{hb}")
parent = header(A, chosen - 1)

out = {
    "schema": "lemma-reuse-input/1",
    "chainId": 1,
    "purpose": "fresh input for the paid reuse job (reuse/README.md); recorded before any execution or proof of it",
    "recordedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "selection": {
        "rule": "lowest gasUsed in [20600067, 20601066], lowest number on ties",
        "scanned": len(scan),
        "candidatesByGasUsed": [{"number": n, "gasUsed": g} for g, n in scan[:5]],
        "disjointFromDevelopment": {"blocks": DEVELOPMENT, "reason": "not a member"},
        "disjointFromHoldoutSet1": {
            "rule": "evaluation/holdout/RULE.md section 1",
            "reason": f"RULE.md rejects any holdout window containing a block within {MARGIN} of an executed block; "
                      f"{chosen} is {chosen - BASELINE} blocks above executed block {BASELINE}, so no accepted window can contain it",
            "sealedMaterialRead": False,
        },
        "supportedRange": {"from": SUPPORTED[0], "to": SUPPORTED[1], "fork": "cancun"},
        "caveat": "state is about three hours after the baseline block; a PGU comparison on this block is a continued-savings check on the same era, not a generalization result. The holdout set carries the performance claim",
    },
    "block": dict(ha, parentStateRoot=parent["stateRoot"], fork="cancun"),
    "headerCheckedAgainst": [A.split("//")[1].split("/")[0], B.split("//")[1].split("/")[0]],
    "expected": {"blockHash": ha["hash"], "stateRoot": ha["stateRoot"], "totalCycles": None, "proverGas": None,
                 "note": "cycles and prover gas are filled by the clean worker's run record, never before it"},
}
text = json.dumps(out, indent=1) + "\n"
path = os.path.join(HERE, "input.json")
open(path, "w").write(text)
print(f"block {chosen} gasUsed={gas} txs={ha['txCount']} -> {path} sha256={hashlib.sha256(text.encode()).hexdigest()}")
