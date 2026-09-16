#!/usr/bin/env python3
"""Apply a candidate overlay onto the pinned RSP checkout, enforcing the
demand's allowedSourcePaths (evaluation/policy.json reproduction).

The candidate ships its RSP changes as files under candidate/rsp/ mirroring
the RSP tree. Every overlay file must match an allowed path: a glob from
demand/spec.json allowedSourcePaths (text after " (" is a review note, not
part of the pattern), or a new crate directory under crates/ that does not
exist at the pin (the `crates/<new-module-crate>/**` entry). The workspace
Cargo.toml and Cargo.lock are accepted and their diffs printed for review.

usage: overlay.py --spec demand/spec.json --overlay candidate/rsp --rsp rsp [--record overlay.txt]
Exit 1 if any file is outside the allowed paths; nothing is copied then.
"""
import argparse, fnmatch, hashlib, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--spec", required=True)
ap.add_argument("--overlay", required=True)
ap.add_argument("--rsp", required=True)
ap.add_argument("--record")
a = ap.parse_args()

spec = json.load(open(a.spec))
patterns = []
for entry in spec["allowedSourcePaths"]:
    pat = entry.split(" (")[0].strip()
    patterns.append(pat)
REVIEWED = {"Cargo.toml", "Cargo.lock"}


def matches(path):
    for pat in patterns:
        if "<new-module-crate>" in pat:
            parts = path.split("/")
            if len(parts) >= 3 and parts[0] == "crates" and not os.path.exists(os.path.join(a.rsp, "crates", parts[1])):
                return f"new crate crates/{parts[1]}"
            continue
        if pat.endswith("/**"):
            if path.startswith(pat[:-3] + "/"):
                return pat
        elif fnmatch.fnmatchcase(path, pat) or path == pat:
            return pat
    return None


files = []
for root, _, names in os.walk(a.overlay):
    for n in names:
        full = os.path.join(root, n)
        files.append(os.path.relpath(full, a.overlay))
files.sort()
if not files:
    print("empty overlay")
    sys.exit(0)

lines = []
bad = []
for rel in files:
    why = "reviewed workspace file" if rel in REVIEWED else matches(rel)
    digest = hashlib.sha256(open(os.path.join(a.overlay, rel), "rb").read()).hexdigest()
    existed = os.path.exists(os.path.join(a.rsp, rel))
    lines.append(f"{'ok  ' if why else 'DENY'} {rel} sha256={digest} {'modified' if existed else 'new'} ({why or 'outside allowedSourcePaths'})")
    if not why:
        bad.append(rel)
print("\n".join(lines))
if bad:
    print(f"{len(bad)} file(s) outside allowedSourcePaths; nothing applied")
    sys.exit(1)

for rel in files:
    dst = os.path.join(a.rsp, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(a.overlay, rel), dst)
diff = subprocess.run(["git", "-C", a.rsp, "diff", "--", "Cargo.toml", "Cargo.lock"], capture_output=True, text=True).stdout
print(f"applied {len(files)} file(s)")
if diff:
    print("== workspace manifest and lock diff (review)")
    print(diff)
if a.record:
    with open(a.record, "w") as f:
        f.write("\n".join(lines) + "\n")
        if diff:
            f.write("== workspace manifest and lock diff\n" + diff)
