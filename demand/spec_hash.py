#!/usr/bin/env python3
"""specificationHash for demand/spec.json: keccak256 of the canonical JSON
(UTF-8, sorted keys, no whitespace) of the file with `demandId` and
`specificationHash` set to null, since both are known only after funding.

  spec_hash.py          print the hash
  spec_hash.py --check  exit 1 unless spec.json carries this hash
"""
import json, os, sys

try:
    from eth_hash.auto import keccak
except ImportError:
    raise SystemExit("needs eth_hash with the pycryptodome backend (~/.venvs/lemma/bin/python)")

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec.json")
spec = json.load(open(SPEC))
preimage = dict(spec)
preimage["demandId"] = None
preimage["specificationHash"] = None
digest = "0x" + keccak(json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hex()
if "--check" in sys.argv:
    ok = spec.get("specificationHash") == digest
    print(f"{'ok  ' if ok else 'FAIL'} specificationHash {digest}")
    sys.exit(0 if ok else 1)
print(digest)
