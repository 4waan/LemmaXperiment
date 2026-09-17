import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {mkdtempSync, mkdirSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {RunLog} from "../lib/log.mjs";
import {createTools} from "../lib/tools.mjs";
import * as ws from "../lib/workspace.mjs";

function git(dir, args) {
    return execFileSync("git", ["-C", dir, ...args], {encoding: "utf8"}).trim();
}

function repoWithCommit() {
    const dir = mkdtempSync(path.join(tmpdir(), "wsrepo-"));
    execFileSync("git", ["init", "-q", dir]);
    git(dir, ["config", "user.email", "t@t"]);
    git(dir, ["config", "user.name", "t"]);
    for (const d of ["candidate", "formal", "demand"]) mkdirSync(path.join(dir, d));
    writeFileSync(path.join(dir, "demand", "spec.json"), "{}");
    writeFileSync(path.join(dir, "README.md"), "x");
    git(dir, ["add", "."]);
    git(dir, ["commit", "-q", "-m", "base"]);
    return dir;
}

function fakeGh() {
    const calls = [];
    let next = 100;
    return {
        calls,
        dispatch: async (workflow, inputs) => (calls.push({workflow, inputs}), next++),
        runStatus: async (id) => ({runId: id, status: "completed", conclusion: "success"}),
        downloadArtifacts: async () => {},
        pushBranch: async (repo, branch) => calls.push({push: branch}),
    };
}

function ctxFor(repo, {dispatch = false, controller = null, gh = fakeGh()} = {}) {
    const log = new RunLog(mkdtempSync(path.join(tmpdir(), "log-")));
    return {log, repo, baseCommit: git(repo, ["rev-parse", "HEAD"]), runId: "test", demand: {demandId: "0x" + "aa".repeat(32)}, budget: {dispatches: {"apparatus-build": 2, "apparatus-execute": 2, "apparatus-fixtures": 1, "evaluation-formal": 1}, localAttemptLimit: 1}, corpusBlocks: [20600066, 18884864, 23945771], controller, dispatchEnabled: dispatch, gh};
}

const textOf = (r) => r.content[0].text;

test("workspace: forbidden changes are refused, writable trees commit", () => {
    const repo = repoWithCommit();
    writeFileSync(path.join(repo, "demand", "spec.json"), "{\"changed\":1}");
    assert.deepEqual(ws.forbiddenChanges(repo), ["demand/spec.json"]);
    assert.throws(() => ws.commitWritable(repo, "x"), /changes outside/);
    git(repo, ["checkout", "--", "demand/spec.json"]);
    writeFileSync(path.join(repo, "candidate", "a.txt"), "hello");
    const {commit, files} = ws.commitWritable(repo, "add a");
    assert.deepEqual(files, ["candidate/a.txt"]);
    assert.equal(ws.headCommit(repo), commit);
    assert.equal(ws.fileAtCommit(repo, commit, "candidate/a.txt"), "hello");
    assert.equal(ws.fileAtCommit(repo, commit, "candidate/missing"), null);
});

test("tools: order, corpus, publication and budget checks", async () => {
    const repo = repoWithCommit();
    const gh = fakeGh();
    const ctx = ctxFor(repo, {dispatch: true, gh});
    const t = createTools(ctx).handlers;
    const commit = git(repo, ["rev-parse", "HEAD"]);
    let r = await t.dispatch_build({commit, variant: "lemma-cache"});
    assert.match(textOf(r), /not published/);
    writeFileSync(path.join(repo, "candidate", "lib.rs"), "fn f(){}");
    r = await t.publish_revision({message: "first"});
    const pub = JSON.parse(textOf(r));
    assert.match(pub.digest, /^0x[0-9a-f]{64}$/);
    assert.deepEqual(gh.calls.at(-1), {push: "creator/test"});
    r = await t.dispatch_build({commit: pub.commit, variant: "lemma-cache"});
    assert.match(textOf(r), /record_hypothesis first/);
    await t.record_hypothesis({hypothesis: "x".repeat(100)});
    r = await t.dispatch_build({commit: pub.commit, variant: "lemma-cache"});
    assert.equal(JSON.parse(textOf(r)).runId, 100);
    r = await t.dispatch_execute({block: 1, variant: "lemma-cache", input_source: "fixture"});
    assert.match(textOf(r), /not in the public development corpus/);
    r = await t.dispatch_execute({block: 20600066, variant: "lemma-cache", input_source: "replay"});
    assert.match(textOf(r), /replay needs/);
    r = await t.dispatch_execute({block: 20600066, variant: "lemma-cache", input_source: "fixture", build_run: 100});
    assert.equal(JSON.parse(textOf(r)).remaining, 1);
    await t.dispatch_execute({block: 18884864, variant: "standard", input_source: "fixture"});
    r = await t.dispatch_execute({block: 18884864, variant: "standard", input_source: "fixture"});
    assert.match(textOf(r), /budget: execute dispatches exhausted/);
    // a second candidate commit exceeds localAttemptLimit 1
    writeFileSync(path.join(repo, "candidate", "lib.rs"), "fn g(){}");
    const pub2 = JSON.parse(textOf(await t.publish_revision({message: "second"})));
    r = await t.dispatch_build({commit: pub2.commit, variant: "lemma-cache"});
    assert.match(textOf(r), /candidate revisions already built/);
    r = await t.dispatch_build({commit: pub2.commit, variant: "standard"});
    assert.equal(JSON.parse(textOf(r)).runId, 103, "reference builds do not count as revisions");
});

test("tools: submit needs disposition, hypothesis, manifest and the controller; decline needs the report", async () => {
    const repo = repoWithCommit();
    const sent = [];
    const controller = {submitCandidate: async (req) => (sent.push(req), {hash: "0xsub"}), decline: async (req) => (sent.push(req), {hash: "0xdec"})};
    const t = createTools(ctxFor(repo, {dispatch: true, controller})).handlers;
    writeFileSync(path.join(repo, "candidate", "lib.rs"), "fn f(){}");
    const pub = JSON.parse(textOf(await t.publish_revision({message: "first"})));
    let r = await t.submit_candidate({commit: pub.commit});
    assert.match(textOf(r), /disposition of create or compose/);
    await t.record_disposition({disposition: "create", evidence: "e".repeat(50), alternativesConsidered: ["arena"]});
    r = await t.submit_candidate({commit: pub.commit});
    assert.match(textOf(r), /record_hypothesis first/);
    await t.record_hypothesis({hypothesis: "h".repeat(100)});
    r = await t.submit_candidate({commit: pub.commit});
    assert.match(textOf(r), /manifest.json is missing/);
    const manifest = Object.fromEntries(["candidateId", "moduleInterface", "compatibilityManifest", "reproducibleBuildRecipe", "guestProgramKey", "featureName", "dependencyVersions", "dependencyLicenses", "originalContributions", "compositionManifest", "theoremStatements", "leanToolchain", "axiomReport", "modelToImplementationMap", "knownFormalGaps", "publicCheckResults", "developmentBenchmarkReport", "integrationInstructions", "licenseReference"].map((k) => [k, "x"]));
    writeFileSync(path.join(repo, "candidate", "manifest.json"), JSON.stringify(manifest));
    const pub2 = JSON.parse(textOf(await t.publish_revision({message: "manifest"})));
    r = await t.submit_candidate({commit: pub2.commit});
    const sub = JSON.parse(textOf(r));
    assert.equal(sub.txHash, "0xsub");
    assert.equal(sub.candidateDigest, pub2.digest);
    assert.equal(sent[0].sourceCommit, "0x" + pub2.commit.padEnd(64, "0"));
    r = await t.submit_candidate({commit: pub2.commit});
    assert.match(textOf(r), /already submitted/);
    r = await t.decline_demand({commit: pub2.commit});
    assert.match(textOf(r), /terminal action was already taken/);
});
