// Canonical JSON and digests shared by the run log, the controller and the
// artifact identity (ROBINHOOD_CHAIN_PROD.md 3.2: sorted keys, no whitespace;
// sha256 for offchain records, keccak256 for values that go onchain).
import {createHash} from "node:crypto";
import {readdirSync, readFileSync, statSync} from "node:fs";
import path from "node:path";
import {keccak256, toHex} from "viem";

export function canonicalJson(value) {
    if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
    if (value !== null && typeof value === "object") {
        return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
    }
    if (value === undefined) return "null";
    return JSON.stringify(value);
}

export function sha256Hex(data) {
    return createHash("sha256").update(data).digest("hex");
}

export function sha256Json(value) {
    return sha256Hex(canonicalJson(value));
}

export function keccakJson(value) {
    return keccak256(toHex(new TextEncoder().encode(canonicalJson(value))));
}

/** Sorted `<relative path> <sha256>` lines over every file under the given
 * directories (relative to root), hashed once more: the same tree hash
 * evaluation/freeze.py computes for the evaluator image, here for the
 * candidate bundle (candidate/ and formal/). */
export function treeHash(root, prefixes) {
    const lines = [];
    for (const prefix of prefixes) {
        const base = path.join(root, prefix);
        let st;
        try {
            st = statSync(base);
        } catch {
            continue;
        }
        if (!st.isDirectory()) continue;
        walk(base, (file) => {
            const rel = path.relative(root, file).split(path.sep).join("/");
            lines.push(`${rel} ${sha256Hex(readFileSync(file))}`);
        });
    }
    lines.sort();
    return {hash: sha256Hex(lines.join("\n") + "\n"), files: lines.length, lines};
}

function walk(dir, visit) {
    for (const entry of readdirSync(dir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
        if (entry.name === ".git" || entry.name === ".lake" || entry.name === "target" || entry.name === "node_modules") continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full, visit);
        else if (entry.isFile()) visit(full);
    }
}
