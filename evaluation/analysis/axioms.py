#!/usr/bin/env python3
"""Frozen Lean check (evaluation/policy.json formal): toolchain pin, build,
axiom report per theorem, kernel re-check, placeholder scan.

usage: axioms.py <project dir> --policy evaluation/policy.json --out report.json

The project must contain lean-toolchain, a lakefile and theorems.json
({"modules": [...], "theorems": [fully qualified names]}). Exit 1 on any
failed check; the report says which.
"""
import argparse, json, os, re, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--policy", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "policy.json"))
ap.add_argument("--out")
a = ap.parse_args()
policy = json.load(open(a.policy))["formal"]
allowed = set(policy["allowedAxioms"])
proj = os.path.abspath(a.project)
report = {"project": proj, "checks": {}, "theorems": {}}
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    report["checks"][name] = {"pass": bool(cond), "detail": detail}
    print(f"{'ok  ' if cond else 'FAIL'} {name}{(': ' + detail) if detail else ''}")


def run(cmd):
    p = subprocess.run(cmd, cwd=proj, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


toolchain = open(os.path.join(proj, "lean-toolchain")).read().strip()
check("toolchain pinned", toolchain == policy["leanToolchain"], toolchain)
spec = json.load(open(os.path.join(proj, "theorems.json")))
check("theorems listed", bool(spec.get("theorems")) and bool(spec.get("modules")), ", ".join(spec.get("theorems", [])))

rc, out = run(["lake", "build"])
check("lake build", rc == 0, out.splitlines()[-1] if out else "")
report["build"] = out[-4000:]

# Placeholder and escape-hatch scan: informative, the axiom report is the gate.
hits = []
for root, _, files in os.walk(proj):
    if "/.lake" in root:
        continue
    for f in files:
        if f.endswith(".lean"):
            for i, line in enumerate(open(os.path.join(root, f), errors="replace"), 1):
                if re.search(r"\bsorry\b|\badmit\b|native_decide|\baxiom\b|implemented_by|\bunsafe\b|\bopaque\b", line):
                    hits.append(f"{os.path.relpath(os.path.join(root, f), proj)}:{i}: {line.strip()[:100]}")
report["scan"] = hits
check("no placeholder or escape hatch in sources", not hits, f"{len(hits)} hit(s)" if hits else "")

# Axioms per theorem through the project's own toolchain.
with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=proj, delete=False) as f:
    for m in spec["modules"]:
        f.write(f"import {m}\n")
    for t in spec["theorems"]:
        f.write(f"#print axioms {t}\n")
    check_file = f.name
try:
    rc, out = run(["lake", "env", "lean", check_file])
finally:
    os.unlink(check_file)
report["axiomOutput"] = out
check("axiom query ran", rc == 0, out.splitlines()[-1] if rc else "")
for t in spec["theorems"]:
    m = re.search(rf"'{re.escape(t)}' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])", out)
    if not m:
        report["theorems"][t] = None
        check(f"axioms of {t}", False, "not reported (theorem missing or query failed)")
        continue
    axioms = [] if m.group(2) is None else [x.strip() for x in m.group(2).split(",") if x.strip()]
    report["theorems"][t] = axioms
    extra = [x for x in axioms if x not in allowed]
    check(f"axioms of {t}", not extra, ", ".join(axioms) if axioms else "none")

# Independent kernel re-check of every listed module with the toolchain's leanchecker.
for m in spec["modules"]:
    rc, out = run(["lake", "env", "leanchecker", "--fresh", m])
    check(f"leanchecker {m}", rc == 0, out.splitlines()[-1] if out else "")

report["pass"] = ok
if a.out:
    json.dump(report, open(a.out, "w"), indent=2)
print("FORMAL CHECKS PASS" if ok else "FORMAL CHECKS FAIL")
sys.exit(0 if ok else 1)
