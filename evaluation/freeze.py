#!/usr/bin/env python3
"""Freeze or check the evaluator hashes (evaluation/policy.json `hashing`).

  freeze.py          compute evaluatorImage.hash (tree hash of the listed
                     files), write it into policy.json, then write
                     evaluationPolicyHash, correctnessPolicyHash and
                     formalScopePolicyHash into demand/spec.json
  freeze.py --check  recompute everything and exit 1 on any difference

keccak256 comes from eth_hash (pycryptodome backend); run with the project
venv. Canonical JSON: UTF-8, sorted keys, no whitespace.
"""
import hashlib, json, os, sys

try:
    from eth_hash.auto import keccak
except ImportError:
    raise SystemExit("needs eth_hash with the pycryptodome backend (~/.venvs/lemma/bin/python)")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(ROOT, "evaluation", "policy.json")
SPEC = os.path.join(ROOT, "demand", "spec.json")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def k(obj):
    return keccak(canonical(obj)).hex()


def tree_hash(files):
    lines = []
    for rel in sorted(files):
        with open(os.path.join(ROOT, rel), "rb") as f:
            lines.append(f"{rel} {hashlib.sha256(f.read()).hexdigest()}")
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest(), lines


check = "--check" in sys.argv
policy = json.load(open(POLICY))
pins = json.load(open(os.path.join(ROOT, "apparatus", "pins.json")))
if pins["rsp"]["commit"] != policy["evaluatorImage"]["rspCommit"]:
    raise SystemExit(f"apparatus/pins.json rsp.commit {pins['rsp']['commit']} differs from evaluatorImage.rspCommit")
image_hash, lines = tree_hash(policy["evaluatorImage"]["files"])
spec_text = open(SPEC).read()
spec = json.loads(spec_text)

if check:
    ok = policy["evaluatorImage"]["hash"] == image_hash
    print(f"{'ok  ' if ok else 'FAIL'} evaluatorImage.hash {image_hash}")
    want = {"evaluationPolicyHash": k(policy), "correctnessPolicyHash": k(policy["correctness"]), "formalScopePolicyHash": k(policy["formal"])}
    for name, val in want.items():
        same = spec.get(name) == val
        ok &= same
        print(f"{'ok  ' if same else 'FAIL'} {name} {val}")
    sys.exit(0 if ok else 1)

policy["evaluatorImage"]["hash"] = image_hash
with open(POLICY, "w") as f:
    json.dump(policy, f, indent=2)
    f.write("\n")
for line in lines:
    print(line)
print(f"evaluatorImage.hash {image_hash}")
hashes = {"evaluationPolicyHash": k(policy), "correctnessPolicyHash": k(policy["correctness"]), "formalScopePolicyHash": k(policy["formal"])}
for name, val in hashes.items():
    old = f'"{name}": null'
    if old in spec_text:
        spec_text = spec_text.replace(old, f'"{name}": "{val}"')
    else:
        # replace the existing value in place, keeping the file layout
        import re
        spec_text, n = re.subn(rf'"{name}": "[0-9a-f]{{64}}"', f'"{name}": "{val}"', spec_text)
        assert n == 1, name
    print(f"{name} {val}")
json.loads(spec_text)
open(SPEC, "w").write(spec_text)
print("written: evaluation/policy.json evaluatorImage.hash and demand/spec.json hashes")
