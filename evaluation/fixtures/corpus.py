#!/usr/bin/env python3
"""Write development-corpus.json: the manifest of the public development
blocks (EXPERIMENT.md section 4 step 3, TRIE_MODULE_PROTOCOL.md section 8).

For every block it records the header fields two providers agree on (the
pinned archive provider and an unrelated public endpoint), the fork era by
timestamp, the sha256 and size of the committed client input, the run that
produced it and the cycle and prover-gas totals that run measured. The sha256
of the written file is `publicDevelopmentCorpusHash` in demand/spec.json.

usage: corpus.py <block>=<apparatus/runs dir> ...
env:   RPC_1 (archive endpoint); PUBLIC_RPC optional second endpoint
"""
import hashlib, json, os, sys, urllib.request

RPC = os.environ["RPC_1"]
PUBLIC = os.environ.get("PUBLIC_RPC", "https://ethereum-rpc.publicnode.com")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# alloy-hardforks 0.4.7 src/ethereum/mainnet.rs, the version the pinned RSP locks
FORKS = [("shanghai", 1_681_338_455), ("cancun", 1_710_338_135), ("prague", 1_746_612_311),
         ("osaka", 1_764_798_551), ("bpo1", 1_765_290_071), ("bpo2", 1_767_747_671)]


def call(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"content-type": "application/json", "user-agent": "lemma-corpus/1"})
    return json.load(urllib.request.urlopen(req, timeout=60))["result"]


def header(url, number):
    b = call(url, "eth_getBlockByNumber", [hex(number), False])
    return {"number": int(b["number"], 16), "hash": b["hash"], "parentHash": b["parentHash"], "stateRoot": b["stateRoot"],
            "timestamp": int(b["timestamp"], 16), "gasUsed": int(b["gasUsed"], 16), "txCount": len(b["transactions"]),
            "requestsHash": b.get("requestsHash"), "excessBlobGas": b.get("excessBlobGas")}


def fork_of(ts):
    name = "pre-shanghai"
    for n, t in FORKS:
        if ts >= t:
            name = n
    return name


def kv(path):
    out = {}
    for line in open(path):
        if ":" in line:
            k, v = line.split(":", 1)
            out.setdefault(k.strip(), v.strip())
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


blocks = []
for arg in sys.argv[1:]:
    number, run_dir = arg.split("=")
    number = int(number)
    run_path = os.path.join(ROOT, "apparatus", "runs", run_dir)
    rec = kv(os.path.join(run_path, "run.txt"))
    report = open(os.path.join(run_path, "report.csv")).read().splitlines()
    cols = dict(zip(report[0].split(","), report[1].split(",")))
    ex = json.load(open(os.path.join(run_path, "out", f"{number}.execution.json")))
    h1 = header(RPC, number)
    h2 = header(PUBLIC, number)
    p1 = header(RPC, number - 1)
    agree = all(h1[k] == h2[k] for k in ("hash", "parentHash", "stateRoot", "timestamp", "gasUsed", "txCount"))
    if not agree:
        raise SystemExit(f"providers disagree on block {number}: {h1} vs {h2}")
    rel = f"blocks/1/{number}.bin"
    path = os.path.join(HERE, rel)
    digest = sha256(path)
    if digest != rec["client_input_sha256"]:
        raise SystemExit(f"{rel} sha256 {digest} differs from the run record {rec['client_input_sha256']}")
    blocks.append({
        "number": number,
        "hash": h1["hash"],
        "parentHash": h1["parentHash"],
        "parentStateRoot": p1["stateRoot"],
        "stateRoot": h1["stateRoot"],
        "timestamp": h1["timestamp"],
        "fork": fork_of(h1["timestamp"]),
        "gasUsed": h1["gasUsed"],
        "txCount": h1["txCount"],
        "requestsHash": h1["requestsHash"],
        "clientInput": rel,
        "clientInputSha256": digest,
        "clientInputBytes": os.path.getsize(path),
        "producedBy": {"run": run_dir, "variant": rec["variant"], "stateBackend": rec["state_backend"],
                       "lemmaProveSha256": rec["lemma_prove_sha256"], "vkey": rec["vkey"]},
        "expected": {
            "blockHash": h1["hash"],
            "stateRoot": h1["stateRoot"],
            "totalCycles": int(cols["total_cycles_count"]),
            "proverGas": ex["prover_gas"],
            "note": "cycles and prover gas from that run's standard build; repeat executions move by about 0.01% (stdin map order), see apparatus/INTERFACES.md section 7",
        },
        "headerCheckedAgainst": PUBLIC.split("//")[1].split("/")[0],
    })

out = {
    "schema": "lemma-development-corpus/1",
    "chainId": 1,
    "pipeline": json.load(open(os.path.join(ROOT, "apparatus", "pins.json")))["rsp"]["commit"],
    "inputProvenance": "client inputs written by the pinned host (lemma-prove, standard build) from eth_getProof state on the pinned archive provider in the apparatus-execute runs named per block; headers cross-checked against an unrelated public endpoint; no light client proves canonicality (TRIE_MODULE_PROTOCOL.md section 8)",
    "howToUse": "apparatus-execute with input_source=fixture executes a block offline from blocks/1/<number>.bin after checking its sha256 against this file; the guest recomputes the post-state root and must reach stateRoot",
    "selection": {
        "20600066": "step 1 baseline: a small Cancun-era block chosen so a compressed proof fits one GitHub runner job",
        "18884864": "rsp-tests cached block (Shanghai era), used for the first offline execution in step 1",
        "23945771": "Osaka-era fork-support check block chosen by apparatus/fork_windows.py (lower median gasUsed of the 120 blocks starting 10,000 blocks after Osaka activation). The current-era (BPO2) median block 25988980 chosen by the same rule is not reproducible by the pinned host (apparatus/FAILURES.md #10), so the latest era check that executed is the third development block",
    },
    "blocks": blocks,
}
text = json.dumps(out, indent=1) + "\n"
path = os.path.join(HERE, "development-corpus.json")
open(path, "w").write(text)
print(f"{len(blocks)} blocks -> {path} sha256={hashlib.sha256(text.encode()).hexdigest()}")
for b in blocks:
    print(f"  {b['number']} {b['fork']:8} gas={b['gasUsed']:>9} txs={b['txCount']:>3} cycles={b['expected']['totalCycles']:>10} input={b['clientInputBytes']:>8} B sha256={b['clientInputSha256'][:16]}")
