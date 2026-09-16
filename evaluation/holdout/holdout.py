#!/usr/bin/env python3
"""Holdout selection for LemmaXperiment (EXPERIMENT.md section 4 step 4).

Implements evaluation/holdout/RULE.md. Four commands:

  precommit  draw preSalt on this machine, pick the beacon block, write the
             public commitment.json (phase precommit); push that before the
             beacon block exists
  seal       after the beacon block is finalized: derive the salt and the
             window, fetch the ten headers from two providers, write the
             sealed manifest into the evaluator directory, record its sha256
             (the commitment) and the evaluator signature in commitment.json
  derive     print the window for a given salt (offline)
  verify     after the reveal: recompute everything from a published manifest
             and preSalt and compare with commitment.json and the chain

env: RPC_1 (archive endpoint, seal and verify), PUBLIC_RPC (second endpoint,
default https://ethereum-rpc.publicnode.com), EVALUATOR_PRIVATE_KEY (seal
--sign only). Nothing secret is ever printed.
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RULE = os.path.join(HERE, "RULE.md")
COMMITMENT = os.path.join(HERE, "commitment.json")
PUBLIC = os.environ.get("PUBLIC_RPC", "https://ethereum-rpc.publicnode.com")
SEALED_DEFAULT = os.path.expanduser("~/.lemma-evaluator/holdout/set-1")

# RULE.md section 1
RANGE = (19426587, 22431083)
WINDOW = 10
STARTS = RANGE[1] - RANGE[0] + 1 - (WINDOW - 1)
EXCLUDED = [18884864, 20600000, 20600066, 22441128, 23945771, 23985839, 25988970, 25988980]
MARGIN = 1000
DOMAIN = b"lemma-holdout/1"
FIELDS = ("number", "hash", "parentHash", "stateRoot", "transactionsRoot", "receiptsRoot", "withdrawalsRoot",
          "timestamp", "gasUsed", "gasLimit", "baseFeePerGas", "blobGasUsed", "excessBlobGas", "transactionCount")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def rpc(url, label, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=body, headers={"content-type": "application/json", "user-agent": "lemma-holdout/1"})
            res = json.load(urllib.request.urlopen(req, timeout=60))
            if "error" in res:
                raise SystemExit(f"{label}: {method} returned an error: {res['error'].get('message')}")
            return res["result"]
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # the endpoint may carry a credential: report the label, not the URL
            reason = getattr(e, "code", None) or getattr(e, "reason", "network error")
            if attempt == 3:
                raise SystemExit(f"{label}: {method} failed after 4 attempts ({reason})")
            time.sleep(2 * (attempt + 1))


def header(url, label, which):
    tag = which if isinstance(which, str) else hex(which)
    b = rpc(url, label, "eth_getBlockByNumber", [tag, False])
    if b is None:
        raise SystemExit(f"{label}: block {tag} not available")
    out = {}
    for f in FIELDS:
        if f == "transactionCount":
            out[f] = len(b["transactions"])
        elif f in ("number", "timestamp", "gasUsed", "gasLimit", "baseFeePerGas", "blobGasUsed", "excessBlobGas"):
            out[f] = int(b[f], 16) if b.get(f) is not None else None
        else:
            out[f] = b.get(f)
    return out


def sources():
    if "RPC_1" not in os.environ:
        raise SystemExit("RPC_1 is not set (archive endpoint)")
    return [(os.environ["RPC_1"], "archive"), (PUBLIC, "public")]


def agreed_header(which):
    hs = [header(u, l, which) for u, l in sources()]
    if hs[0] != hs[1]:
        diff = [f for f in FIELDS if hs[0][f] != hs[1][f]]
        raise SystemExit(f"providers disagree on block {which} in {diff}")
    return hs[0]


def derive(salt):
    """RULE.md section 3: attempts and the accepted start."""
    attempts = []
    k = 0
    while True:
        r = hashlib.sha256(DOMAIN + salt + k.to_bytes(4, "big")).digest()
        start = RANGE[0] + int.from_bytes(r, "big") % STARTS
        window = range(start, start + WINDOW)
        hit = [x for x in EXCLUDED if any(abs(b - x) <= MARGIN for b in window)]
        attempts.append({"k": k, "start": start, "rejected": f"within {MARGIN} of {hit[0]}" if hit else None})
        if not hit:
            return attempts, start
        k += 1


def eip191_hash(message):
    from eth_hash.auto import keccak
    m = message.encode()
    return keccak(b"\x19Ethereum Signed Message:\n" + str(len(m)).encode() + m)


def sign(message):
    from eth_keys import keys
    key = os.environ.get("EVALUATOR_PRIVATE_KEY")
    if not key:
        raise SystemExit("EVALUATOR_PRIVATE_KEY is not set")
    pk = keys.PrivateKey(bytes.fromhex(key[2:] if key.startswith("0x") else key))
    sig = pk.sign_msg_hash(eip191_hash(message))
    raw = sig.r.to_bytes(32, "big") + sig.s.to_bytes(32, "big") + bytes([sig.v + 27])
    return pk.public_key.to_checksum_address(), "0x" + raw.hex()


def recover(message, signature):
    from eth_keys import keys
    raw = bytes.fromhex(signature[2:])
    sig = keys.Signature(vrs=(raw[64] - 27, int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:64], "big")))
    return sig.recover_public_key_from_msg_hash(eip191_hash(message)).to_checksum_address()


def load_commitment():
    return json.load(open(COMMITMENT))


def save_commitment(c):
    with open(COMMITMENT, "w") as f:
        json.dump(c, f, indent=2)
        f.write("\n")


def cmd_precommit(a):
    os.makedirs(a.sealed_dir, mode=0o700, exist_ok=True)
    os.chmod(a.sealed_dir, 0o700)
    path = os.path.join(a.sealed_dir, "presalt.hex")
    if os.path.exists(path):
        raise SystemExit(f"{path} exists; a set is committed once. Start a new set id for another draw")
    if os.path.exists(COMMITMENT):
        raise SystemExit(f"{COMMITMENT} exists; a set is committed once")
    presalt = os.urandom(32)
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        f.write(presalt.hex() + "\n")
    head = header(PUBLIC, "public", "latest")
    c = {
        "schema": "lemma-holdout-commitment/1",
        "setId": a.set_id,
        "phase": "precommit",
        "rule": {"file": "evaluation/holdout/RULE.md", "sha256": sha256_file(RULE)},
        "selector": {"file": "evaluation/holdout/holdout.py", "sha256": sha256_file(os.path.abspath(__file__))},
        "precommit": {
            "at": now(),
            "preSaltSha256": hashlib.sha256(presalt).hexdigest(),
            "beaconBlock": head["number"] + a.ahead,
            "headAtPrecommit": {"number": head["number"], "hash": head["hash"], "timestamp": head["timestamp"], "source": PUBLIC},
            "evidence": "the push of this file triggers .github/workflows/holdout-commitment.yml, whose log records the chain head at that time",
        },
        "sealed": None,
        "storage": "preSalt and the sealed manifest stay in the evaluator environment (outside the repository and the creator workspace); not in any GitHub secret",
        "reveal": "after the final evaluation is signed: publish the manifest and preSalt under evaluation/holdout/revealed/ and run holdout.py verify",
    }
    save_commitment(c)
    print(f"preSalt drawn into {path} (never commit it)")
    print(f"preSaltSha256 {c['precommit']['preSaltSha256']}")
    print(f"head {head['number']} at {head['timestamp']}; beaconBlock {c['precommit']['beaconBlock']}")
    print(f"wrote {COMMITMENT}; commit and push it before block {c['precommit']['beaconBlock']} exists")


def cmd_seal(a):
    c = load_commitment()
    if c["phase"] != "precommit":
        raise SystemExit("commitment.json is not in the precommit phase")
    for part, path in (("rule", RULE), ("selector", os.path.abspath(__file__))):
        if sha256_file(path) != c[part]["sha256"]:
            raise SystemExit(f"{part} changed since the precommit; the rule is frozen at precommit time")
    presalt = bytes.fromhex(open(os.path.join(a.sealed_dir, "presalt.hex")).read().strip())
    if hashlib.sha256(presalt).hexdigest() != c["precommit"]["preSaltSha256"]:
        raise SystemExit("presalt.hex does not match the precommit")
    beacon_number = c["precommit"]["beaconBlock"]
    fin = agreed_header("finalized")
    if fin["number"] < beacon_number:
        raise SystemExit(f"beacon block {beacon_number} is not finalized yet (finalized {fin['number']})")
    beacon = agreed_header(beacon_number)
    salt = hashlib.sha256(presalt + bytes.fromhex(beacon["hash"][2:])).digest()
    attempts, start = derive(salt)
    blocks = [agreed_header(n) for n in range(start, start + WINDOW)]
    manifest = {
        "schema": "lemma-holdout-manifest/1",
        "setId": c["setId"],
        "chainId": 1,
        "rule": c["rule"],
        "selector": c["selector"],
        "preSalt": presalt.hex(),
        "beacon": {"block": beacon_number, "hash": beacon["hash"], "timestamp": beacon["timestamp"], "finalizedAtRead": fin["number"]},
        "salt": salt.hex(),
        "derivation": {"attempts": attempts, "acceptedK": attempts[-1]["k"], "start": start},
        "blocks": blocks,
        "headerSources": ["archive provider (RPC_1)", PUBLIC],
        "sealedAt": now(),
    }
    data = canonical(manifest)
    out = os.path.join(a.sealed_dir, "holdout-manifest.json")
    if os.path.exists(out):
        raise SystemExit(f"{out} exists; a set is sealed once")
    with open(os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        f.write(data)
    commitment = hashlib.sha256(data).hexdigest()
    sealed = {
        "at": manifest["sealedAt"],
        "commitment": commitment,
        "manifestSchema": manifest["schema"],
        "manifestBytes": len(data),
        "beacon": {"block": beacon_number, "hash": beacon["hash"], "timestamp": beacon["timestamp"], "finalizedAtRead": fin["number"], "sources": manifest["headerSources"]},
        "precommitGitCommit": a.precommit_commit,
        "precommitRun": a.precommit_run,
        "signedMessage": None,
        "evaluatorSigner": None,
        "evaluatorSignature": None,
    }
    if a.sign:
        msg = f"lemma-holdout/1 commitment {commitment}"
        signer, signature = sign(msg)
        sealed.update({"signedMessage": msg, "evaluatorSigner": signer, "evaluatorSignature": signature})
    c["phase"] = "sealed"
    c["sealed"] = sealed
    save_commitment(c)
    print(f"sealed manifest written to {out} ({len(data)} bytes)")
    print(f"commitment {commitment}")
    if a.sign:
        print(f"signed by {sealed['evaluatorSigner']}")
    print("block numbers stay in the sealed manifest; commitment.json updated")


def cmd_derive(a):
    attempts, start = derive(bytes.fromhex(a.salt))
    for t in attempts:
        print(f"k={t['k']} start={t['start']} {'rejected: ' + t['rejected'] if t['rejected'] else 'accepted'}")
    print(f"window {start} to {start + WINDOW - 1}")


def cmd_verify(a):
    c = load_commitment()
    if c["phase"] != "sealed":
        raise SystemExit("commitment.json is not sealed")
    data = open(a.manifest, "rb").read()
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"{'ok  ' if cond else 'FAIL'} {name}{(': ' + detail) if detail else ''}")

    got = hashlib.sha256(data).hexdigest()
    if got != c["sealed"]["commitment"] and data.endswith(b"\n"):
        got = hashlib.sha256(data.rstrip(b"\n")).hexdigest()
        print("note: trailing newline stripped before hashing")
    check("commitment", got == c["sealed"]["commitment"], got)
    m = json.loads(data)
    presalt = a.presalt
    if os.path.exists(presalt):
        presalt = open(presalt).read().strip()
    check("preSalt in manifest", m["preSalt"] == presalt)
    check("preSalt matches precommit", hashlib.sha256(bytes.fromhex(presalt)).hexdigest() == c["precommit"]["preSaltSha256"])
    check("beacon block number", m["beacon"]["block"] == c["precommit"]["beaconBlock"])
    check("beacon above head at precommit", m["beacon"]["block"] > c["precommit"]["headAtPrecommit"]["number"])
    beacon = agreed_header(m["beacon"]["block"])
    check("beacon hash on chain", beacon["hash"] == m["beacon"]["hash"], beacon["hash"])
    salt = hashlib.sha256(bytes.fromhex(presalt) + bytes.fromhex(beacon["hash"][2:])).digest()
    check("salt", salt.hex() == m["salt"])
    attempts, start = derive(salt)
    check("derivation", start == m["derivation"]["start"] and attempts == m["derivation"]["attempts"], f"start {start}")
    check("ten consecutive blocks", [b["number"] for b in m["blocks"]] == list(range(start, start + WINDOW)))
    for b in m["blocks"]:
        h = agreed_header(b["number"])
        check(f"header {b['number']}", h == b, b["hash"])
    check("rule hash", m["rule"]["sha256"] == c["rule"]["sha256"] == sha256_file(RULE))
    check("selector hash", m["selector"]["sha256"] == c["selector"]["sha256"] == sha256_file(os.path.abspath(__file__)))
    s = c["sealed"]
    if s.get("evaluatorSignature"):
        try:
            check("evaluator signature", recover(s["signedMessage"], s["evaluatorSignature"]) == s["evaluatorSigner"], s["evaluatorSigner"])
            check("signed message names the commitment", s["signedMessage"].endswith(s["commitment"]))
        except ImportError:
            print("skip evaluator signature (eth_keys not installed)")
    print("VERIFIED" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("precommit"); s.add_argument("--sealed-dir", default=SEALED_DEFAULT); s.add_argument("--set-id", type=int, default=1); s.add_argument("--ahead", type=int, default=30); s.set_defaults(fn=cmd_precommit)
s = sub.add_parser("seal"); s.add_argument("--sealed-dir", default=SEALED_DEFAULT); s.add_argument("--sign", action="store_true"); s.add_argument("--precommit-commit"); s.add_argument("--precommit-run"); s.set_defaults(fn=cmd_seal)
s = sub.add_parser("derive"); s.add_argument("--salt", required=True); s.set_defaults(fn=cmd_derive)
s = sub.add_parser("verify"); s.add_argument("--manifest", required=True); s.add_argument("--presalt", required=True, help="hex or a file holding it"); s.set_defaults(fn=cmd_verify)
args = p.parse_args()
args.fn(args)
