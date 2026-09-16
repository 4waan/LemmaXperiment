#!/usr/bin/env python3
"""Independent trie fixtures for the StateTries seam of the pinned RSP.

Oracle: py-trie (pure Python Merkle Patricia trie, pinned version recorded in
the output) computes every root, every lookup and every post-update root. The
proofs are cut from the py-trie node database by a walker in this file that
follows the EIP-1186 convention (hashed nodes only, root first; nodes shorter
than 32 bytes are embedded in their parent). Nothing here imports or shells out
to the Rust implementation under test.

Output: fixtures.json next to this file. Deterministic for a given seed and
py-trie version; regenerate with `python3 gen.py` and diff.

Case families (see README.md): present and absent keys at every divergence
point, empty trie, single leaf, partial witnesses, inline and hashed child
references including the 31/32 byte boundary, inline branch and inline
extension, wrong roots, forged nodes, missing nodes, truncated and
noncanonical RLP, branch with value, storage-root consistency, trie updates
(insert, modify, delete with branch collapse, wipe, create with storage,
shared identical storage), and a consistent re-encoding after a previous
case so stale caches show.
"""
import hashlib, json, os, random, sys

import rlp
from eth_hash.auto import keccak
from trie import HexaryTrie
import importlib.metadata as md

SEED = 20260916
EMPTY_ROOT = keccak(rlp.encode(b""))
KECCAK_EMPTY = keccak(b"")

rng = random.Random(SEED)


def hx(b):
    return "0x" + bytes(b).hex()


def nibbles(b):
    out = []
    for x in b:
        out.append(x >> 4)
        out.append(x & 15)
    return out


def compact_encode(nibs, is_leaf):
    flag = 2 if is_leaf else 0
    if len(nibs) % 2:
        head = [flag + 1] + list(nibs)
    else:
        head = [flag, 0] + list(nibs)
    return bytes(head[i] << 4 | head[i + 1] for i in range(0, len(head), 2))


def compact_decode(b):
    nibs = nibbles(b)
    flag = nibs[0]
    is_leaf = flag >= 2
    if flag % 2:
        return nibs[1:], is_leaf
    return nibs[2:], is_leaf


def rand_bytes(n):
    return bytes(rng.getrandbits(8) for _ in range(n))


def rand_address():
    return rand_bytes(20)


def address_with_key_prefix(prefix_nibs, avoid=()):
    """Random address whose keccak starts with the given nibbles (brute force)."""
    while True:
        a = rand_address()
        k = keccak(a)
        if nibbles(k)[: len(prefix_nibs)] == list(prefix_nibs) and k not in avoid:
            return a


def key_from_nibbles(nibs):
    assert len(nibs) == 64
    return bytes(nibs[i] << 4 | nibs[i + 1] for i in range(0, 64, 2))


def account_rlp(nonce, balance, storage_root, code_hash):
    return rlp.encode([nonce, balance, storage_root, code_hash])


def account_fields(value):
    nonce, balance, storage_root, code_hash = rlp.decode(value)
    return {
        "nonce": int.from_bytes(nonce, "big"),
        "balance": hx(balance) if balance else "0x0",
        "storageRoot": hx(storage_root),
        "codeHash": hx(code_hash),
    }


def u256_rlp(v):
    assert v > 0
    return rlp.encode(v)


def u256_hex(v):
    return hex(v)


class Trie:
    """py-trie wrapper keeping the node database, with an EIP-1186 walker."""

    def __init__(self):
        self.t = HexaryTrie({}, prune=False)

    def copy(self):
        c = Trie()
        c.t = HexaryTrie(dict(self.t.db), self.t.root_hash, prune=False)
        return c

    def set(self, key, value):
        self.t.set(key, value)

    def delete(self, key):
        self.t.delete(key)

    def get(self, key):
        return self.t.get(key)

    @property
    def root(self):
        return self.t.root_hash

    def path_proof(self, key):
        """Encoded hashed nodes from the root along `key`, EIP-1186 style. Stops at
        the leaf, an empty branch slot or a path mismatch. Returns the proof and a
        tag naming where the walk ended."""
        if self.root == EMPTY_ROOT:
            return [], "empty-trie"
        nibs = nibbles(key)
        node_bytes = self.t.db[self.root]
        proof = [node_bytes]
        node = rlp.decode(node_bytes)
        pos = 0
        inline = False
        while True:
            if len(node) == 17:
                if pos == 64:
                    return proof, "branch-value"
                child = node[nibs[pos]]
                pos += 1
                if child == b"":
                    return proof, "branch-empty-slot" + ("-inline" if inline else "")
            else:
                path, is_leaf = compact_decode(node[0])
                if is_leaf:
                    if nibs[pos:] == path:
                        return proof, "leaf" + ("-inline" if inline else "")
                    return proof, "leaf-mismatch" + ("-inline" if inline else "")
                if nibs[pos:pos + len(path)] != path:
                    return proof, "extension-mismatch" + ("-inline" if inline else "")
                pos += len(path)
                child = node[1]
            if isinstance(child, list):
                node = child
                inline = True
            else:
                assert len(child) == 32, "child reference must be a hash or an inline node"
                node_bytes = self.t.db[child]
                proof.append(node_bytes)
                node = rlp.decode(node_bytes)
                inline = False


def walk_positions(proof, key):
    """For each hashed node of `proof`, the index of the item that leads on
    (branch slot or 1 for an extension); None for the last node."""
    nibs = nibbles(key)
    pos = 0
    out = []
    for i, node_bytes in enumerate(proof):
        node = rlp.decode(node_bytes)
        # descend through inline nodes inside this hashed node to find the item
        # that references the next hashed node
        item = None
        cur = node
        while True:
            if len(cur) == 17:
                if pos == 64:
                    break
                idx = nibs[pos]
                pos += 1
                child = cur[idx]
                if item is None:
                    item = idx
                if isinstance(child, list):
                    cur = child
                    item = None if item is None else item
                    continue
                break
            path, is_leaf = compact_decode(cur[0])
            if is_leaf:
                break
            pos += len(path)
            child = cur[1]
            if item is None:
                item = 1
            if isinstance(child, list):
                cur = child
                continue
            break
        out.append(item if i + 1 < len(proof) else None)
    return out


def rebuild_chain(proof, key, new_last):
    """Replace the last hashed node of `proof` with `new_last` (raw bytes) and
    re-reference every ancestor. Ancestors must reference the child directly
    (no inline node in between), which holds for every case that uses this.
    Returns (new_proof, new_root)."""
    positions = walk_positions(proof, key)
    new_proof = list(proof)
    new_proof[-1] = new_last
    child_bytes = new_last
    for i in range(len(proof) - 2, -1, -1):
        node = rlp.decode(proof[i])
        idx = positions[i]
        assert idx is not None
        ref = keccak(child_bytes) if len(child_bytes) >= 32 else rlp.decode(child_bytes)
        node[idx] = ref
        child_bytes = rlp.encode(node)
        new_proof[i] = child_bytes
    return new_proof, keccak(new_proof[0])


def rlp_string_long_form(payload):
    """Noncanonical RLP: a string shorter than 56 bytes with a long-form length
    prefix (0xb8 len). Canonical RLP requires the short form 0x80+len."""
    assert len(payload) < 56
    return bytes([0xB8, len(payload)]) + payload


# ---------------------------------------------------------------- fixtures --

cases = []


def account_proof_entry(state, address, storage=None, slots=(), include_account_path=True):
    key = keccak(address)
    value = state.get(key)
    if value:
        f = account_fields(value)
        nonce, balance, storage_root, code_hash = f["nonce"], f["balance"], f["storageRoot"], f["codeHash"]
    else:
        nonce, balance, storage_root, code_hash = 0, "0x0", hx(EMPTY_ROOT), hx(KECCAK_EMPTY)
    proof, ended = state.path_proof(key) if include_account_path else ([], "omitted")
    entry = {
        "address": hx(address),
        "hashedAddress": hx(key),
        "nonce": nonce,
        "balance": balance,
        "codeHash": code_hash,
        "storageHash": storage_root,
        "accountProof": [hx(p) for p in proof],
        "accountPathEnds": ended,
        "storageProof": [],
    }
    for hashed_slot in slots:
        assert storage is not None
        sproof, sended = storage.path_proof(hashed_slot)
        v = storage.get(hashed_slot)
        entry["storageProof"].append({
            "hashedSlot": hx(hashed_slot),
            "value": u256_hex(int.from_bytes(rlp.decode(v), "big")) if v else "0x0",
            "proof": [hx(p) for p in sproof],
            "pathEnds": sended,
        })
    return entry


def q_account(hashed, expect, account=None, note=None):
    q = {"kind": "account", "hashedAddress": hx(hashed), "expect": expect}
    if account is not None:
        q["account"] = account
    if note:
        q["note"] = note
    return q


def q_storage(hashed_address, hashed_slot, expect, value=None, note=None):
    q = {"kind": "storage", "hashedAddress": hx(hashed_address), "hashedSlot": hx(hashed_slot), "expect": expect}
    if value is not None:
        q["value"] = value
    if note:
        q["note"] = note
    return q


def case(id_, family, description, state_root, proofs, queries, build="ok", updates=None, tags=(), notes=None):
    c = {
        "id": id_,
        "family": family,
        "description": description,
        "tags": list(tags),
        "stateRoot": hx(state_root),
        "expectedBuild": build,
        "proofs": proofs,
        "queries": queries,
    }
    if updates is not None:
        c["updates"] = updates
    if notes:
        c["notes"] = notes
    cases.append(c)
    return c


# ------------------------------------------------------------ base trie A --
# Twelve accounts. Two share the first two key nibbles (an extension of one
# nibble under the root branch), two share four nibbles (an extension of three
# nibbles), the rest are random. All storage roots are empty.

def build_state_a():
    st = Trie()
    accounts = {}
    a1 = address_with_key_prefix([0x3, 0x7])
    a2 = address_with_key_prefix([0x3, 0x7], avoid={keccak(a1)})
    while nibbles(keccak(a2))[2] == nibbles(keccak(a1))[2]:
        a2 = address_with_key_prefix([0x3, 0x7], avoid={keccak(a1)})
    a3 = address_with_key_prefix([0xC, 0x0, 0xD, 0xE])
    a4 = address_with_key_prefix([0xC, 0x0, 0xD, 0xE], avoid={keccak(a3)})
    while nibbles(keccak(a4))[4] == nibbles(keccak(a3))[4]:
        a4 = address_with_key_prefix([0xC, 0x0, 0xD, 0xE], avoid={keccak(a3)})
    addrs = [a1, a2, a3, a4]
    used = {nibbles(keccak(a))[0] for a in addrs}
    while len(addrs) < 12:
        a = rand_address()
        n0 = nibbles(keccak(a))[0]
        if n0 in used:
            continue
        used.add(n0)
        addrs.append(a)
    for i, a in enumerate(addrs):
        nonce = i + 1
        balance = (i + 1) * 10**18 + rng.getrandbits(40)
        code_hash = KECCAK_EMPTY if i % 3 else keccak(bytes([i]))
        v = account_rlp(nonce, balance, EMPTY_ROOT, code_hash)
        st.set(keccak(a), v)
        accounts[a] = v
    return st, addrs


state_a, addrs_a = build_state_a()

# absent addresses at controlled divergence points
k1 = nibbles(keccak(addrs_a[0]))
k3 = nibbles(keccak(addrs_a[2]))
absent_root_slot = None
used0 = {nibbles(keccak(a))[0] for a in addrs_a}
while absent_root_slot is None:
    a = rand_address()
    if nibbles(keccak(a))[0] not in used0:
        absent_root_slot = a
absent_ext1_mismatch = address_with_key_prefix([k1[0]], avoid={keccak(a) for a in addrs_a})
while nibbles(keccak(absent_ext1_mismatch))[1] == k1[1]:
    absent_ext1_mismatch = address_with_key_prefix([k1[0]], avoid={keccak(a) for a in addrs_a})
absent_branch_under_ext = address_with_key_prefix(k1[:2], avoid={keccak(a) for a in addrs_a})
while nibbles(keccak(absent_branch_under_ext))[2] in {nibbles(keccak(addrs_a[0]))[2], nibbles(keccak(addrs_a[1]))[2]}:
    absent_branch_under_ext = address_with_key_prefix(k1[:2], avoid={keccak(a) for a in addrs_a})
absent_ext3_mismatch = address_with_key_prefix(k3[:2], avoid={keccak(a) for a in addrs_a})
while nibbles(keccak(absent_ext3_mismatch))[2:4] == k3[2:4]:
    absent_ext3_mismatch = address_with_key_prefix(k3[:2], avoid={keccak(a) for a in addrs_a})
# diverges inside a depth-1 leaf: shares the first three nibbles with a lone leaf
lone = addrs_a[5]
kl = nibbles(keccak(lone))
absent_leaf_mismatch = address_with_key_prefix(kl[:3], avoid={keccak(a) for a in addrs_a})


def full_proofs_a(state=None):
    state = state or state_a
    return [account_proof_entry(state, a) for a in addrs_a]


def present_queries_a(state=None):
    state = state or state_a
    return [q_account(keccak(a), "present", account_fields(state.get(keccak(a)))) for a in addrs_a]


absent_queries_a = [
    q_account(keccak(absent_root_slot), "absent", note="empty slot in the root branch"),
    q_account(keccak(absent_ext1_mismatch), "absent", note="path mismatch inside the one-nibble extension"),
    q_account(keccak(absent_branch_under_ext), "absent", note="empty slot in the branch under the extension"),
    q_account(keccak(absent_ext3_mismatch), "absent", note="path mismatch inside the three-nibble extension"),
    q_account(keccak(absent_leaf_mismatch), "absent", note="reaches a leaf whose path differs"),
]
absent_addrs_a = [absent_root_slot, absent_ext1_mismatch, absent_branch_under_ext, absent_ext3_mismatch, absent_leaf_mismatch]

# A-1 full witness, every present account, five absent keys with exclusion paths
case("a01-full-present-absent", "lookups",
     "twelve accounts, full witness; present lookups and absent keys at every divergence point "
     "(root branch slot, extension mismatch at two depths, branch under extension, leaf mismatch)",
     state_a.root, full_proofs_a() + [account_proof_entry(state_a, a) for a in absent_addrs_a],
     present_queries_a() + absent_queries_a, tags=["present", "absent", "extension", "branch", "leaf"])

# A-2 partial witness: four accounts and one exclusion path; the rest unresolved
partial = addrs_a[:4]
case("a02-partial-witness", "missing-witness",
     "paths for four accounts and one absent key only; every other account's path ends in an "
     "unresolved digest and must be rejected, never reported absent",
     state_a.root, [account_proof_entry(state_a, a) for a in partial] + [account_proof_entry(state_a, absent_root_slot)],
     [q_account(keccak(a), "present", account_fields(state_a.get(keccak(a)))) for a in partial]
     + [q_account(keccak(absent_root_slot), "absent", note="exclusion path present")]
     + [q_account(keccak(a), "reject", note="path not in witness") for a in addrs_a[4:]]
     + [q_account(keccak(absent_branch_under_ext), "absent", note="absent key under the resolved extension: its branch is in the witness"),
        q_account(keccak(absent_leaf_mismatch), "reject", note="absent key whose root slot is an unresolved digest")],
     tags=["missing-witness", "absent"])

# A-3 wrong declared root
wrong_root = bytearray(state_a.root)
wrong_root[5] ^= 0x01
case("a03-wrong-root", "incorrect-root", "full witness, declared state root differs in one bit",
     bytes(wrong_root), full_proofs_a(), [], build="reject", tags=["incorrect-root"])

# A-4 dropped inner node in one path (chain of references broken)
victim = addrs_a[0]
p = state_a.path_proof(keccak(victim))[0]
assert len(p) >= 3, "victim path must have an inner node"
dropped = [hx(x) for x in p[:1] + p[2:]]
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(victim):
        e["accountProof"] = dropped
        e["accountPathEnds"] = "dropped-inner-node"
case("a04-dropped-inner-node", "missing-witness", "one account path lacks its second node; the parent references a hash no listed node has",
     state_a.root, proofs, [], build="reject", tags=["missing-witness", "forged"])

# A-5 truncated path: the leaf of one account is left out; build passes, the lookup must reject
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(victim):
        e["accountProof"] = e["accountProof"][:-1]
        e["accountPathEnds"] = "truncated-before-leaf"
case("a05-truncated-path", "missing-witness",
     "one account path stops before its leaf; the leaf digest stays unresolved. The guest's storage-root check reads every revealed account, "
     "so a builder may reject the witness outright; if it builds, the truncated account must reject and the others must read",
     state_a.root, proofs,
     [q_account(keccak(victim), "reject", note="leaf not in witness")]
     + [q_account(keccak(a), "present", account_fields(state_a.get(keccak(a)))) for a in addrs_a[1:4]],
     build="ok-or-reject", tags=["missing-witness"])

# A-6 forged leaf, parent unchanged (hash chain broken)
leaf = rlp.decode(p[-1])
forged_leaf = rlp.encode([leaf[0], account_rlp(99, 5, EMPTY_ROOT, KECCAK_EMPTY)])
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(victim):
        e["accountProof"] = [hx(x) for x in p[:-1]] + [hx(forged_leaf)]
        e["accountPathEnds"] = "forged-leaf"
case("a06-forged-leaf-broken-chain", "forged", "one leaf replaced by a leaf with another balance; its parent still references the original hash",
     state_a.root, proofs, [], build="reject", tags=["forged"])

# A-7 forged leaf with the chain rebuilt, but the declared root is the original
new_proof, new_root = rebuild_chain(p, keccak(victim), forged_leaf)
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(victim):
        e["accountProof"] = [hx(x) for x in new_proof]
        e["accountPathEnds"] = "forged-leaf-rebuilt"
case("a07-forged-leaf-rebuilt-chain", "forged",
     "one leaf replaced and every ancestor on its path re-referenced, declared root unchanged. The other paths still carry the original ancestors, "
     "so a builder may end up with either root node: with the rebuilt one the root check fails, with the original one the forged leaf is unreachable. "
     "Either the build rejects or the lookup shows the original account; the forged balance must never appear",
     state_a.root, proofs,
     [q_account(keccak(victim), "present", account_fields(state_a.get(keccak(victim))), note="original value or reject; never the forged one")],
     build="ok-or-reject", tags=["forged", "incorrect-root"])

# A-8 consistent re-encoding: same witness with one balance changed, root declared accordingly.
# Run after a01: a stale cross-job cache would still serve the old leaf.
alt = state_a.copy()
alt_value = account_rlp(7, 12345, EMPTY_ROOT, KECCAK_EMPTY)
alt.set(keccak(victim), alt_value)
case("a08-modified-leaf-new-root", "lookups", "same accounts as a01 with one balance changed and the root declared for the new trie; lookups must show the new value",
     alt.root, full_proofs_a(alt), present_queries_a(alt), tags=["present", "stale-cache"])

# A-9 truncated RLP in one node
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(victim):
        e["accountProof"] = [hx(x) for x in p[:-1]] + [hx(p[-1][:-1])]
        e["accountPathEnds"] = "truncated-rlp"
case("a09-truncated-rlp", "malformed-rlp", "the last byte of one leaf's RLP is missing", state_a.root, proofs, [], build="reject", tags=["malformed-rlp"])

# A-10 noncanonical RLP: leaf value string with a long-form length prefix, chain and root rebuilt consistently
leaf_path, leaf_value = rlp.decode(p[-1])
# the account value is 56 bytes or longer (long form is canonical there), so the
# noncanonical prefix goes on the 32-byte compact path item
payload = rlp_string_long_form(leaf_path) + rlp.encode(leaf_value)
assert 56 <= len(payload) < 256
nc_leaf = bytes([0xF8, len(payload)]) + payload
nc_proof, nc_root = rebuild_chain(p, keccak(victim), nc_leaf)
proofs = full_proofs_a()
for e in proofs:
    e["accountProof"] = [hx(x) for x in state_a.path_proof(bytes.fromhex(e["hashedAddress"][2:]))[0]]
# every path shares the root; rebuild all shared ancestors from the victim's rebuilt chain
victim_nodes = {keccak(x): x for x in p}
replacement = dict(zip([keccak(x) for x in p], nc_proof))
for e in proofs:
    e["accountProof"] = [hx(replacement.get(keccak(x), x)) for x in (bytes.fromhex(h[2:]) for h in e["accountProof"])]
    if e["address"] == hx(victim):
        e["accountPathEnds"] = "noncanonical-leaf-path"
case("a10-noncanonical-rlp", "malformed-rlp",
     "one leaf's path item uses a long-form RLP length prefix for a 32-byte string; every ancestor and the declared root are consistent with those bytes. "
     "Canonical Ethereum decoders reject the node, so the witness must be rejected",
     nc_root, proofs, [], build="reject", tags=["malformed-rlp", "noncanonical"],
     notes="the declared root is the keccak chain over the noncanonical bytes, so a decoder that accepts long-form lengths would accept this witness")

# A-11 branch with a value, chain rebuilt consistently
root_node = rlp.decode(p[0])
assert len(root_node) == 17
victim_positions = walk_positions(p, keccak(victim))
bad_root = list(root_node)
bad_root[16] = b"\x01"
bad_root_bytes = rlp.encode(bad_root)
proofs = full_proofs_a()
for e in proofs:
    e["accountProof"] = [hx(bad_root_bytes)] + e["accountProof"][1:]
case("a11-branch-with-value", "malformed-rlp", "the root branch carries a value; keys are fixed length so no Ethereum state trie branch has one",
     keccak(bad_root_bytes), proofs, [], build="reject", tags=["malformed-rlp"])

# A-12 two-item node with an empty path item
empty_path_leaf = rlp.encode([b"", leaf_value])
ep_proof, ep_root = rebuild_chain(p, keccak(victim), empty_path_leaf)
replacement = dict(zip([keccak(x) for x in p], ep_proof))
proofs = full_proofs_a()
for e in proofs:
    e["accountProof"] = [hx(replacement.get(keccak(x), x)) for x in (bytes.fromhex(h[2:]) for h in e["accountProof"])]
case("a12-empty-path-item", "malformed-rlp", "a two-item node whose path item is empty, chain and root consistent",
     ep_root, proofs, [], build="reject", tags=["malformed-rlp"])

# ------------------------------------------------------------- empty trie --
case("e01-empty-trie", "lookups", "empty state trie: any account is absent; an insert yields a single-leaf root",
     EMPTY_ROOT, [], [q_account(keccak(addrs_a[0]), "absent"), q_account(keccak(absent_root_slot), "absent")],
     updates={
         "accounts": {hx(keccak(addrs_a[0])): {"nonce": 1, "balance": "0x1", "codeHash": None}},
         "storages": {},
         "expectedStateRoot": hx((lambda t: (t.set(keccak(addrs_a[0]), account_rlp(1, 1, EMPTY_ROOT, KECCAK_EMPTY)), t.root)[1])(Trie())),
         "expectedStorageRoots": {},
     }, tags=["empty", "absent", "update"])

# ----------------------------------------------------------- single leaf --
single = Trie()
single.set(keccak(addrs_a[3]), state_a.get(keccak(addrs_a[3])))
case("e02-single-leaf", "lookups", "one account: the root is a leaf; absent keys mismatch at nibble 0; deleting it gives the empty root",
     single.root, [account_proof_entry(single, addrs_a[3]), account_proof_entry(single, addrs_a[0])],
     [q_account(keccak(addrs_a[3]), "present", account_fields(single.get(keccak(addrs_a[3])))),
      q_account(keccak(addrs_a[0]), "absent", note="root leaf path differs")],
     updates={"accounts": {hx(keccak(addrs_a[3])): None}, "storages": {}, "expectedStateRoot": hx(EMPTY_ROOT), "expectedStorageRoots": {}},
     tags=["leaf", "absent", "update", "delete"])

# ------------------------------------------------------------ base trie B --
# Six accounts; three carry storage: S1 random slots with values of several
# sizes, S2 the synthetic deep inline family (inline extension, inline branch,
# inline leaves), S3 the 31/32 byte leaf boundary under a nine-nibble
# extension, S4 and S5 identical storage contents, S6 storage not in witness.

def build_storage_s1():
    s = Trie()
    slots = {}
    for i in range(8):
        hs = rand_bytes(32)
        if i < 3:
            v = i + 1                      # one byte, below 0x80
        elif i < 5:
            v = 0x80 + i                   # one byte, RLP takes two
        else:
            v = int.from_bytes(rand_bytes(32), "big") | (1 << 255)  # full width
        s.set(hs, u256_rlp(v))
        slots[hs] = v
    return s, slots


def build_storage_s2():
    # keys A and B share nibbles 0..62 and differ at 63; C shares 0..48 and differs at 49
    base = nibbles(rand_bytes(32))
    a = list(base); a[63] = 0x1
    b = list(base); b[63] = 0x2
    c = list(base); c[49] = (base[49] + 1) % 16
    ka, kb, kc = key_from_nibbles(a), key_from_nibbles(b), key_from_nibbles(c)
    s = Trie()
    s.set(ka, u256_rlp(1)); s.set(kb, u256_rlp(2)); s.set(kc, u256_rlp(3))
    return s, {ka: 1, kb: 2, kc: 3}, (ka, kb, kc)


def build_storage_s3():
    base = nibbles(rand_bytes(32))
    a = list(base); a[9] = 0x4
    b = list(base); b[9] = 0xA
    c = list(base); c[0] = (base[0] + 1) % 16
    ka, kb, kc = key_from_nibbles(a), key_from_nibbles(b), key_from_nibbles(c)
    s = Trie()
    s.set(ka, u256_rlp(0x7F)); s.set(kb, u256_rlp(0x80)); s.set(kc, u256_rlp(0x1234))
    return s, {ka: 0x7F, kb: 0x80, kc: 0x1234}, (ka, kb, kc)


def build_storage_shared():
    s = Trie()
    slots = {}
    for i in range(4):
        hs = rand_bytes(32)
        v = 1000 + i
        s.set(hs, u256_rlp(v))
        slots[hs] = v
    return s, slots


s1, s1_slots = build_storage_s1()
s2, s2_slots, (s2a, s2b, s2c) = build_storage_s2()
s3, s3_slots, (s3a, s3b, s3c) = build_storage_s3()
s4, s4_slots = build_storage_shared()
s5 = s4.copy()
s6, s6_slots = build_storage_shared()

# sanity on the synthetic shapes
_, tag = s2.path_proof(s2a); assert tag == "leaf-inline", tag
_, tag = s3.path_proof(s3a); assert tag == "leaf-inline", tag
_, tag = s3.path_proof(s3b); assert tag == "leaf", tag
s2_branch49 = rlp.decode(s2.path_proof(s2a)[0][-1])
assert len(s2_branch49) == 17 and isinstance(s2_branch49[nibbles(s2a)[49]], list) and len(s2_branch49[nibbles(s2a)[49]]) == 2, "inline extension expected"
assert isinstance(s2_branch49[nibbles(s2a)[49]][1], list) and len(s2_branch49[nibbles(s2a)[49]][1]) == 17, "inline branch expected"

addrs_b = [rand_address() for _ in range(6)]
used0 = set()
addrs_b = []
while len(addrs_b) < 6:
    a = rand_address()
    n0 = nibbles(keccak(a))[0]
    if n0 in used0:
        continue
    used0.add(n0)
    addrs_b.append(a)
b_storage = {addrs_b[0]: s1, addrs_b[1]: s2, addrs_b[2]: s3, addrs_b[3]: s4, addrs_b[4]: s5, addrs_b[5]: s6}
state_b = Trie()
for i, a in enumerate(addrs_b):
    state_b.set(keccak(a), account_rlp(10 + i, (i + 1) * 10**17, b_storage[a].root, keccak(bytes([0x60, i]))))


def storage_queries(addr, storage, slots, absent_hashed=()):
    ha = keccak(addr)
    qs = [q_storage(ha, hs, "value", u256_hex(v)) for hs, v in slots.items()]
    for hs, note in absent_hashed:
        qs.append(q_storage(ha, hs, "value", "0x0", note=note))
    return qs


# absent storage keys at chosen divergence points
s1_absent = [(rand_bytes(32), "random slot; diverges near the root")]
n = nibbles(s2a)
s2_absent = [
    (key_from_nibbles(n[:63] + [0x9]), "empty slot of the inline branch at depth 63"),
    (key_from_nibbles(n[:55] + [(n[55] + 1) % 16] + n[56:]), "mismatch inside the inline extension"),
    (key_from_nibbles(n[:49] + [(n[49] + 2) % 16] + n[50:]), "empty slot of the branch at depth 49"),
    (key_from_nibbles([(n[0] + 1) % 16] + n[1:]), "mismatch inside the root extension"),
]
m = nibbles(s3a)
s3_absent = [
    (key_from_nibbles(m[:9] + [0x5] + m[10:]), "empty slot of the branch under the nine-nibble extension"),
    (key_from_nibbles(m[:9] + [0x4] + m[10:20] + [(m[20] + 1) % 16] + m[21:]), "mismatch inside the inline leaf"),
    (key_from_nibbles(m[:9] + [0xA] + m[10:20] + [(m[20] + 1) % 16] + m[21:]), "mismatch inside the 32-byte hashed leaf"),
]


def full_proofs_b(state=None, storage=None, slots_for=None, omit_storage=()):
    state = state or state_b
    storage = storage or b_storage
    out = []
    for a in addrs_b:
        st = storage[a]
        if a in omit_storage:
            out.append(account_proof_entry(state, a))
            continue
        keys = slots_for[a] if slots_for and a in slots_for else list(all_slots(a))
        out.append(account_proof_entry(state, a, st, keys))
    return out


def all_slots(a):
    return {addrs_b[0]: list(s1_slots) + [k for k, _ in s1_absent],
            addrs_b[1]: list(s2_slots) + [k for k, _ in s2_absent],
            addrs_b[2]: list(s3_slots) + [k for k, _ in s3_absent],
            addrs_b[3]: list(s4_slots), addrs_b[4]: list(s4_slots), addrs_b[5]: list(s6_slots)}[a]


present_b = [q_account(keccak(a), "present", account_fields(state_b.get(keccak(a)))) for a in addrs_b]

case("b01-storage-full", "lookups",
     "six accounts with storage; S1 random slots (1-byte, 2-byte and 32-byte values), S2 inline extension over an inline branch "
     "over inline leaves at depth 63, S3 a 31-byte inline leaf and a 32-byte hashed leaf under one branch (the encoding boundary), "
     "S4 and S5 identical storage tries, S6 random; present values and absent slots at every divergence point",
     state_b.root, full_proofs_b(),
     present_b + storage_queries(addrs_b[0], s1, s1_slots, s1_absent) + storage_queries(addrs_b[1], s2, s2_slots, s2_absent)
     + storage_queries(addrs_b[2], s3, s3_slots, s3_absent) + storage_queries(addrs_b[3], s4, s4_slots)
     + storage_queries(addrs_b[4], s5, s4_slots) + storage_queries(addrs_b[5], s6, s6_slots),
     tags=["storage", "inline", "hashed", "boundary", "absent", "shared-bytes"])

# B-2 storage trie of S6 not in the witness: its lookups must reject; an account with empty storage reads zero
empty_storage_addr = addrs_a[0]
state_b2 = state_b.copy()
state_b2.set(keccak(empty_storage_addr), account_rlp(1, 1, EMPTY_ROOT, KECCAK_EMPTY))
proofs = full_proofs_b(state_b2, omit_storage=(addrs_b[5],)) + [account_proof_entry(state_b2, empty_storage_addr)]
case("b02-storage-not-in-witness", "missing-witness",
     "S6's storage trie is only its root digest; reading any of its slots must reject. An account whose storage root is the empty root reads zero without a trie",
     state_b2.root, proofs,
     [q_storage(keccak(addrs_b[5]), hs, "reject", note="storage trie not in witness") for hs in list(s6_slots)[:2]]
     + [q_storage(keccak(empty_storage_addr), rand_bytes(32), "value", "0x0", note="empty storage root")]
     + storage_queries(addrs_b[0], s1, s1_slots),
     tags=["missing-witness", "storage"])

# B-3 declared storage hash wrong
proofs = full_proofs_b()
sh = bytearray(bytes.fromhex(proofs[0]["storageHash"][2:])); sh[0] ^= 0x80
proofs[0]["storageHash"] = hx(bytes(sh))
case("b03-wrong-storage-hash", "incorrect-root", "S1's declared storage hash differs from the trie its proofs build", state_b.root, proofs, [], build="reject",
     tags=["incorrect-root", "storage"])

# B-4 account leaf claims another storage root than the (valid) storage trie supplied
state_b4 = state_b.copy()
other_root = s6.root
state_b4.set(keccak(addrs_b[0]), account_rlp(10, 10**17, other_root, keccak(bytes([0x60, 0]))))
proofs = full_proofs_b(state_b4)
proofs[0]["storageHash"] = hx(s1.root)          # the storage proofs are S1's, consistent with themselves
case("b04-account-storage-root-mismatch", "incorrect-root",
     "S1's account leaf carries S6's storage root while the witness supplies S1's storage trie; the storage root check against the account leaf must reject",
     state_b4.root, proofs, [], build="reject", tags=["incorrect-root", "storage"])

# B-5 missing storage node: S2's branch at depth 49 left out
proofs = full_proofs_b()
for sp in proofs[1]["storageProof"]:
    sp["proof"] = sp["proof"][:1]
    sp["pathEnds"] = "truncated-before-branch49"
case("b05-storage-missing-node", "missing-witness", "S2's storage paths stop at the root extension; slot lookups must reject",
     state_b.root, proofs,
     [q_storage(keccak(addrs_b[1]), hs, "reject", note="branch not in witness") for hs in s2_slots] + present_b,
     tags=["missing-witness", "storage", "inline"])

# B-6 forged inline leaf: the inline leaf value inside S3's branch changed, parent hash chain broken
proofs = full_proofs_b()
sp = proofs[2]["storageProof"][0]
assert sp["hashedSlot"] == hx(s3a)
bytes_list = [bytes.fromhex(h[2:]) for h in sp["proof"]]
branch = rlp.decode(bytes_list[-1])
idx = nibbles(s3a)[9]
assert isinstance(branch[idx], list)
branch[idx] = [branch[idx][0], rlp.encode(0x11)]
sp["proof"] = [hx(x) for x in bytes_list[:-1]] + [hx(rlp.encode(branch))]
sp["pathEnds"] = "forged-inline-leaf"
case("b06-forged-inline-leaf", "forged", "the inline leaf of S3's boundary slot carries another value; the branch no longer hashes to its parent's reference",
     state_b.root, proofs, [], build="reject", tags=["forged", "inline", "storage"])

# ------------------------------------------------------------------ updates --

def apply_updates(state, storage_by_hashed, updates):
    """Oracle: apply an update batch to copies of the tries, return new roots."""
    st = state.copy()
    tries = {k: v.copy() for k, v in storage_by_hashed.items()}
    for ha_hex, acct in updates["accounts"].items():
        ha = bytes.fromhex(ha_hex[2:])
        if acct is None:
            st.delete(ha)
            continue
        stor = updates["storages"].get(ha_hex, {"wiped": False, "slots": {}})
        t = tries.get(ha)
        if t is None:
            # storage root from the account leaf, or empty
            existing = st.get(ha)
            if existing and account_fields(existing)["storageRoot"] != hx(EMPTY_ROOT):
                raise AssertionError("oracle needs the storage trie for " + ha_hex)
            t = Trie()
        if stor["wiped"]:
            t = Trie()
        for hs_hex, v_hex in stor["slots"].items():
            hs = bytes.fromhex(hs_hex[2:])
            v = int(v_hex, 16)
            if v == 0:
                t.delete(hs)
            else:
                t.set(hs, u256_rlp(v))
        tries[ha] = t
        code_hash = bytes.fromhex(acct["codeHash"][2:]) if acct["codeHash"] else KECCAK_EMPTY
        st.set(ha, account_rlp(acct["nonce"], int(acct["balance"], 16), t.root, code_hash))
    roots = {hx(ha): hx(tries[ha].root) for ha_hex in updates["accounts"] if updates["accounts"][ha_hex] is not None for ha in [bytes.fromhex(ha_hex[2:])]}
    return hx(st.root), roots


storage_by_hashed_b = {keccak(a): t for a, t in b_storage.items()}


def upd(accounts, storages=None):
    return {"accounts": accounts, "storages": storages or {}}


def finish(u, state=state_b, storage=storage_by_hashed_b):
    root, roots = apply_updates(state, storage, u)
    u["expectedStateRoot"] = root
    u["expectedStorageRoots"] = roots
    return u


hb = [keccak(a) for a in addrs_b]

# U-1 balances and nonces of two accounts
u = finish(upd({hx(hb[0]): {"nonce": 11, "balance": hex(3 * 10**17), "codeHash": hx(keccak(bytes([0x60, 0])))},
                hx(hb[3]): {"nonce": 14, "balance": "0x0", "codeHash": hx(keccak(bytes([0x60, 3])))}}))
case("u01-modify-accounts", "update", "two account leaves rewritten (nonce, balance); storage untouched", state_b.root, full_proofs_b(), present_b, updates=u, tags=["update"])

# U-2 create accounts: one splits a leaf into a branch, one lands in an empty root slot
new_split = address_with_key_prefix(nibbles(hb[2])[:3], avoid=set(hb))
new_free = None
while new_free is None:
    a = rand_address()
    if nibbles(keccak(a))[0] not in used0:
        new_free = a
u = finish(upd({hx(keccak(new_split)): {"nonce": 1, "balance": "0x64", "codeHash": None},
                hx(keccak(new_free)): {"nonce": 0, "balance": "0x1", "codeHash": None}}))
case("u02-create-accounts", "update", "two new accounts: one shares three key nibbles with an existing leaf (leaf splits into a branch), one takes an empty root slot",
     state_b.root, full_proofs_b() + [account_proof_entry(state_b, new_split), account_proof_entry(state_b, new_free)], present_b, updates=u,
     tags=["update", "insert", "leaf-split"])

# U-3 delete an account whose removal collapses a branch (base A: the two accounts under the one-nibble extension)
u = finish(upd({hx(keccak(addrs_a[1])): None}), state=state_a, storage={})
case("u03-delete-collapse-branch", "update", "delete one of the two leaves under the one-nibble extension; the branch collapses and the sibling leaf's path grows",
     state_a.root, full_proofs_a(), [], updates=u, tags=["update", "delete", "branch-collapse"])

# U-3b same deletion with the sibling leaf unresolved
proofs = full_proofs_a()
for e in proofs:
    if e["address"] == hx(addrs_a[0]):
        e["accountProof"] = e["accountProof"][:-1]
        e["accountPathEnds"] = "truncated-before-leaf"
case("u03b-delete-collapse-unresolved-sibling", "update",
     "same deletion, but the sibling leaf is only a digest; the witness may be rejected at build (the guest reads every revealed account), "
     "and if it builds the update must reject or yield a root that fails the check",
     state_a.root, proofs, [], build="ok-or-reject",
     updates={"accounts": {hx(keccak(addrs_a[1])): None}, "storages": {}, "expectedStateRoot": u["expectedStateRoot"], "expectedStorageRoots": {}, "expect": "reject"},
     tags=["update", "delete", "missing-witness"])

# U-4 storage writes across the three shaped tries
s2_absent_key = key_from_nibbles(nibbles(s2a)[:63] + [0x9])
u = finish(upd(
    {hx(hb[0]): {"nonce": 10, "balance": hex(10**17), "codeHash": hx(keccak(bytes([0x60, 0])))},
     hx(hb[1]): {"nonce": 11, "balance": hex(2 * 10**17), "codeHash": hx(keccak(bytes([0x60, 1])))},
     hx(hb[2]): {"nonce": 12, "balance": hex(3 * 10**17), "codeHash": hx(keccak(bytes([0x60, 2])))}},
    {hx(hb[0]): {"wiped": False, "slots": {hx(list(s1_slots)[0]): "0x2a", hx(list(s1_slots)[1]): "0x0", hx(s1_absent[0][0]): hex(1 << 200), hx(list(s1_slots)[5]): "0x7"}},
     hx(hb[1]): {"wiped": False, "slots": {hx(s2a): "0x5", hx(s2b): "0x0", hx(s2_absent_key): "0x9"}},
     hx(hb[2]): {"wiped": False, "slots": {hx(s3a): "0x80", hx(s3b): "0x7f"}}}))
case("u04-storage-writes", "update",
     "S1: rewrite, zero (delete), insert, shrink a 32-byte value; S2: rewrite an inline leaf, delete one (the inline branch collapses into the inline extension), "
     "insert into the inline branch; S3: swap the values so each leaf crosses the 31/32-byte boundary the other way",
     state_b.root, full_proofs_b(), [], updates=u, tags=["update", "storage", "inline", "boundary", "delete"])

# U-5 wipe S1 then write one slot
u = finish(upd({hx(hb[0]): {"nonce": 10, "balance": hex(10**17), "codeHash": hx(keccak(bytes([0x60, 0])))}},
               {hx(hb[0]): {"wiped": True, "slots": {hx(rand_bytes(32)): "0x1"}}}))
case("u05-wipe-storage", "update", "S1's storage wiped, then one slot written: the storage root is a single-leaf trie", state_b.root, full_proofs_b(), [], updates=u,
     tags=["update", "storage", "wipe"])

# U-6 delete an account that has storage
u = finish(upd({hx(hb[0]): None}))
case("u06-delete-account-with-storage", "update", "S1 deleted from the state trie", state_b.root, full_proofs_b(), [], updates=u, tags=["update", "delete", "storage"])

# U-7 create an account with storage
u = finish(upd({hx(keccak(new_free)): {"nonce": 1, "balance": "0x0", "codeHash": hx(keccak(b"code"))}},
               {hx(keccak(new_free)): {"wiped": False, "slots": {hx(rand_bytes(32)): "0x1", hx(rand_bytes(32)): hex(1 << 255)}}}))
case("u07-create-account-with-storage", "update", "a new account with two slots: a fresh storage trie and a new state leaf",
     state_b.root, full_proofs_b() + [account_proof_entry(state_b, new_free)], [], updates=u, tags=["update", "insert", "storage"])

# U-8 update through an unresolved path
proofs = full_proofs_b()
proofs[3]["accountProof"] = proofs[3]["accountProof"][:1]
proofs[3]["accountPathEnds"] = "truncated-after-root"
u = finish(upd({hx(hb[3]): {"nonce": 99, "balance": "0x1", "codeHash": None}}))
u["expect"] = "reject"
case("u08-update-unresolved-path", "update",
     "S4's account path is only the root; the witness may be rejected at build, and if it builds rewriting S4 must reject (or miss the expected root)",
     state_b.root, proofs, [], build="ok-or-reject", updates=u, tags=["update", "missing-witness"])

# U-9 shared identical storage: S4 changes, S5 must not
u = finish(upd({hx(hb[3]): {"nonce": 13, "balance": hex(4 * 10**17), "codeHash": hx(keccak(bytes([0x60, 3])))}},
               {hx(hb[3]): {"wiped": False, "slots": {hx(list(s4_slots)[0]): "0xbeef"}}}))
u["expectedStorageRoots"][hx(hb[4])] = hx(s5.root)
case("u09-shared-storage-immutability", "update",
     "S4 and S5 hold byte-identical storage tries; a write to S4 must leave S5's root unchanged (node identity is per trie, not per byte content)",
     state_b.root, full_proofs_b(), [], updates=u, tags=["update", "storage", "shared-bytes"])

# U-10 code hash None means the empty code hash
u = finish(upd({hx(hb[5]): {"nonce": 15, "balance": hex(6 * 10**17), "codeHash": None}}))
case("u10-codehash-none", "update", "an account rewritten with no bytecode hash stores the empty code hash", state_b.root, full_proofs_b(), [], updates=u, tags=["update"])

# ------------------------------------------------------------------ output --

def canonical(o):
    return json.dumps(o, indent=1, sort_keys=False)


out = {
    "schema": "lemma-trie-fixtures/1",
    "generator": {
        "script": "evaluation/fixtures/trie/gen.py",
        "seed": SEED,
        "oracle": f"py-trie {md.version('trie')} (HexaryTrie), rlp {md.version('rlp')}, eth-hash {md.version('eth-hash')} with pycryptodome {md.version('pycryptodome')}",
        "python": sys.version.split()[0],
        "independence": "pure-Python trie; no Rust code from the pipeline under test is imported or executed",
    },
    "conventions": {
        "proofs": "EIP-1186 layout per address: accountProof lists the RLP of every hashed node from the state root along keccak(address), root first; nodes shorter than 32 bytes are embedded in their parent and never listed. storageProof entries do the same inside the account's storage trie along the hashed slot. A hashed node that is not listed is unresolved.",
        "keys": "queries and updates use hashed keys (keccak of the address or slot), the keys the StateTries trait takes; addresses are given because the upstream builder hashes them",
        "expectedBuild": "ok: the witness builds and passes the state-root and storage-root checks of the guest; reject: any error or panic while building or checking; ok-or-reject: either, and the queries then apply only if it built",
        "query expect": "present (account with the given fields), absent (no account), value (storage value, 0x0 when unset), reject (error or panic; an absent or zero answer is a failure). In an ok-or-reject case a query may also reject",
        "updates": "accounts: hashedAddress to account or null (delete); storages: hashedAddress to {wiped, slots: hashedSlot to value, 0x0 deletes}; expectedStateRoot and expectedStorageRoots after applying the batch; expect=reject means the update must error, panic, or produce a state root different from expectedStateRoot",
        "order": "cases are run in file order in one process; a08 follows a01 on purpose",
        "witnessDomain": "the pipeline's witnesses carry the complete path of every revealed account; the guest's storage-root check reads every revealed account, so cases with an incomplete account path (a05, u03b, u08) are ok-or-reject",
    },
    "caseCount": len(cases),
    "cases": cases,
}
text = canonical(out)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures.json")
with open(path, "w") as f:
    f.write(text + "\n")
print(f"{len(cases)} cases -> {path} sha256={hashlib.sha256((text + chr(10)).encode()).hexdigest()}")
for c in cases:
    print(f"  {c['id']:44} {c['family']:16} build={c['expectedBuild']:6} queries={len(c['queries']):3} updates={'yes' if 'updates' in c else 'no'}")
