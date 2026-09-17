import test from "node:test";
import assert from "node:assert/strict";
import {mkdirSync, mkdtempSync, readFileSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {RunLog} from "../lib/log.mjs";
import {scrub, scrubString} from "../lib/scrub.mjs";
import {canonicalJson, sha256Json, treeHash} from "../lib/canonical.mjs";

test("canonical json sorts keys and drops whitespace", () => {
    assert.equal(canonicalJson({b: 1, a: [1, {d: null, c: "x"}]}), '{"a":[1,{"c":"x","d":null}],"b":1}');
    assert.equal(sha256Json({a: 1}), sha256Json({a: 1}));
});

test("scrub removes provider keys, private keys and forbidden fields", () => {
    const s = scrubString("url https://eth-mainnet.g.alchemy.com/v2/alch_ABCDEFGHIJKLMNOPQRSTUVWXYZ123 done");
    assert.ok(!s.includes("ABCDEFGHIJKLMNOP"), s);
    const k = scrubString("SPONSOR_PRIVATE_KEY=0x" + "ab".repeat(32));
    assert.ok(!k.includes("abab"), k);
    const o = scrub({privateKey: "x", nested: {token: "y", ok: "sha256=" + "cd".repeat(32)}});
    assert.equal(o.privateKey, "<dropped>");
    assert.equal(o.nested.token, "<dropped>");
    assert.ok(o.nested.ok.includes("cd".repeat(32)), "plain digests are kept");
});

test("run log chains and verifies, and detects tampering", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "runlog-"));
    const log = new RunLog(dir);
    log.append("start", {runId: "r1"});
    log.append("tool", {name: "Read", input: {file: "x", privateKey: "nope"}});
    const {entries, head} = RunLog.verify(log.file);
    assert.equal(entries, 2);
    assert.equal(head, log.head);
    const reopened = new RunLog(dir);
    reopened.append("end", {});
    assert.equal(RunLog.verify(log.file).entries, 3);
    const lines = readFileSync(log.file, "utf8").split("\n").filter(Boolean);
    lines[1] = lines[1].replace('"Read"', '"Write"');
    writeFileSync(log.file, lines.join("\n") + "\n");
    assert.throws(() => RunLog.verify(log.file), /bad hash at seq 1/);
    assert.ok(!readFileSync(log.file, "utf8").includes("nope"));
});

test("tree hash is stable and covers only the named prefixes", () => {
    const dir = mkdtempSync(path.join(tmpdir(), "tree-"));
    mkdirSync(path.join(dir, "candidate", "module"), {recursive: true});
    mkdirSync(path.join(dir, "formal"), {recursive: true});
    mkdirSync(path.join(dir, "demand"), {recursive: true});
    writeFileSync(path.join(dir, "candidate", "module", "lib.rs"), "fn main(){}");
    writeFileSync(path.join(dir, "formal", "A.lean"), "theorem t : True := trivial");
    writeFileSync(path.join(dir, "demand", "spec.json"), "{}");
    const a = treeHash(dir, ["candidate", "formal"]);
    const b = treeHash(dir, ["formal", "candidate"]);
    assert.equal(a.hash, b.hash);
    assert.equal(a.files, 2);
    writeFileSync(path.join(dir, "demand", "spec.json"), "{\"x\":1}");
    assert.equal(treeHash(dir, ["candidate", "formal"]).hash, a.hash);
    writeFileSync(path.join(dir, "formal", "A.lean"), "theorem t : True := by trivial");
    assert.notEqual(treeHash(dir, ["candidate", "formal"]).hash, a.hash);
});
