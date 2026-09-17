// The tools the creator gets beyond file access and Bash: everything that
// touches GitHub Actions, the repository branch or the chain goes through
// here, is validated against the demand and the budget, and is logged. The
// model passes structured arguments; credentials stay in the runner.
import {mkdirSync, readdirSync, readFileSync, statSync, writeFileSync} from "node:fs";
import path from "node:path";
import {z} from "zod";
import {createSdkMcpServer, tool} from "@anthropic-ai/claude-agent-sdk";
import {sha256Hex, treeHash} from "./canonical.mjs";
import {scrubString} from "./scrub.mjs";
import * as ghClient from "./gh.mjs";
import * as ws from "./workspace.mjs";

const VARIANTS = /^[a-z][a-z0-9-]{1,40}$/;
const WORKFLOWS = {
    build: "apparatus-build.yml",
    execute: "apparatus-execute.yml",
    fixtures: "apparatus-fixtures.yml",
    formal: "evaluation-formal.yml",
};

function text(value) {
    return {content: [{type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2)}]};
}

function fail(message) {
    return {content: [{type: "text", text: `error: ${message}`}], isError: true};
}

export function createTools(ctx) {
    // ctx: {log, repo, baseCommit, runId, demand, budget, corpusBlocks, controller, dispatchEnabled, gh?}
    const gh = ctx.gh ?? ghClient;
    const state = {
        disposition: null,
        hypothesisHash: null,
        published: [],
        dispatches: {build: 0, execute: 0, fixtures: 0, formal: 0},
        revisions: new Set(),
        runs: [],
        submission: null,
        declined: null,
    };
    const counts = ctx.budget.dispatches;

    function checkDispatch(kind) {
        if (!ctx.dispatchEnabled) throw new Error("workflow dispatch is disabled in this run (control or smoke run)");
        if (state.dispatches[kind] >= counts[WORKFLOWS[kind].replace(".yml", "")]) {
            throw new Error(`budget: ${kind} dispatches exhausted (${counts[WORKFLOWS[kind].replace(".yml", "")]})`);
        }
    }

    function requirePublished(commit) {
        if (!state.published.some((p) => p.commit === commit)) throw new Error(`commit ${commit} was not published by publish_revision`);
    }

    async function doDispatch(kind, inputs, extra = {}) {
        checkDispatch(kind);
        const runId = await gh.dispatch(WORKFLOWS[kind], inputs);
        state.dispatches[kind] += 1;
        state.runs.push({kind, runId, inputs, ...extra, at: new Date().toISOString()});
        ctx.log.append("dispatch", {kind, runId, inputs, remaining: counts[WORKFLOWS[kind].replace(".yml", "")] - state.dispatches[kind]});
        return {runId, url: `https://github.com/${ghClient.REPO}/actions/runs/${runId}`, remaining: counts[WORKFLOWS[kind].replace(".yml", "")] - state.dispatches[kind]};
    }

    const tools = [
        tool(
            "record_disposition",
            "Record the Search step's outcome before any build: reuse, compose, create or decline, with the evidence that supports it (alternatives considered, eligibility, estimates). Required once; a later call replaces it and is logged.",
            {
                disposition: z.enum(["reuse", "compose", "create", "decline"]),
                evidence: z.string().min(40).max(8000),
                alternativesConsidered: z.array(z.string()).min(1),
            },
            async (args) => {
                state.disposition = args.disposition;
                ctx.log.append("disposition", args);
                return text({recorded: args.disposition, at: new Date().toISOString()});
            },
        ),
        tool(
            "record_hypothesis",
            "Hash the hypothesis into the run log before implementation: insertion point, affected operation, baseline share, mechanism, failure risks. Builds of a candidate are refused until this exists.",
            {hypothesis: z.string().min(80).max(12000)},
            async (args) => {
                state.hypothesisHash = sha256Hex(args.hypothesis);
                ctx.log.append("hypothesis", {sha256: state.hypothesisHash, text: args.hypothesis});
                return text({hypothesisHash: state.hypothesisHash, committedAt: new Date().toISOString()});
            },
        ),
        tool(
            "publish_revision",
            "Commit the current candidate/ and formal/ trees on this run's branch and push them so workflows can build them. Refuses changes outside those two trees. Returns the commit and the bundle digest (tree hash of candidate/ and formal/).",
            {message: z.string().min(3).max(200)},
            async (args) => {
                try {
                    const {commit, files} = ws.commitWritable(ctx.repo, args.message);
                    await gh.pushBranch(ctx.repo, ws.CREATOR_BRANCH(ctx.runId));
                    const digest = treeHash(ctx.repo, ws.WRITABLE);
                    const rec = {commit, digest: "0x" + digest.hash, files, at: new Date().toISOString()};
                    state.published.push(rec);
                    ctx.log.append("publish", rec);
                    return text(rec);
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "dispatch_build",
            "Build the pinned RSP plus lemma-prove with the candidate overlay from a published commit (apparatus-build.yml). variant is the candidate's cargo feature name, or standard/arena for references. Counts against the build budget; distinct candidate commits count as revisions (limit localAttemptLimit).",
            {commit: z.string().regex(/^[0-9a-f]{40}$/), variant: z.string().regex(VARIANTS)},
            async (args) => {
                try {
                    requirePublished(args.commit);
                    if (!["standard", "arena", "cycle-tracking"].includes(args.variant)) {
                        if (!state.hypothesisHash) throw new Error("record_hypothesis first");
                        if (!state.revisions.has(args.commit) && state.revisions.size >= ctx.budget.localAttemptLimit) {
                            throw new Error(`budget: ${ctx.budget.localAttemptLimit} candidate revisions already built`);
                        }
                        state.revisions.add(args.commit);
                    }
                    return text(await doDispatch("build", {overlay_ref: args.commit, variant: args.variant}, {revision: state.revisions.size}));
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "dispatch_execute",
            "Execute one public development block in the SP1 executor (apparatus-execute.yml): PGU, cycles, report.csv. block must be a corpus block. input_source fixture (offline, standard-format inputs) or replay (a saved stdin from replay_run) or rpc (corpus blocks only). build_run selects which apparatus-build artifact to run (required for candidate variants).",
            {
                block: z.number().int(),
                variant: z.string().regex(VARIANTS),
                input_source: z.enum(["fixture", "replay", "rpc"]),
                build_run: z.number().int().optional(),
                replay_run: z.number().int().optional(),
                replay_sha256: z.string().regex(/^[0-9a-f]{64}$/).optional(),
            },
            async (args) => {
                try {
                    if (!ctx.corpusBlocks.includes(args.block)) throw new Error(`block ${args.block} is not in the public development corpus ${ctx.corpusBlocks.join(", ")}`);
                    if (args.input_source === "replay" && !(args.replay_run && args.replay_sha256)) throw new Error("replay needs replay_run and replay_sha256");
                    const inputs = {
                        block: String(args.block),
                        state_backend: "proofs",
                        variant: args.variant,
                        input_source: args.input_source,
                        replay_run: args.replay_run ? String(args.replay_run) : "",
                        replay_sha256: args.replay_sha256 ?? "",
                        build_run: args.build_run ? String(args.build_run) : "",
                    };
                    return text(await doDispatch("execute", inputs));
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "dispatch_fixtures",
            "Run the independent trie fixtures through the harness on the given backends inside a published commit's overlay (apparatus-fixtures.yml). The evaluator's harness has arms for pointer and arena; a candidate backend needs the adapter you document in candidate/manifest.json (the evaluator writes the evaluator-side arm).",
            {commit: z.string().regex(/^[0-9a-f]{40}$/), backends: z.array(z.string().regex(VARIANTS)).min(1).max(4)},
            async (args) => {
                try {
                    requirePublished(args.commit);
                    return text(await doDispatch("fixtures", {overlay_ref: args.commit, backends: JSON.stringify(args.backends)}));
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "dispatch_formal",
            "Run the frozen Lean check (evaluation-formal.yml) on formal/ at a published commit: toolchain pin, lake build, #print axioms against the allowed set, leanchecker.",
            {commit: z.string().regex(/^[0-9a-f]{40}$/)},
            async (args) => {
                try {
                    requirePublished(args.commit);
                    return text(await doDispatch("formal", {ref: args.commit, project: "formal"}));
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "workflow_status",
            "Status and conclusion of a workflow run dispatched in this session.",
            {run_id: z.number().int()},
            async (args) => {
                try {
                    return text(await gh.runStatus(args.run_id));
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "fetch_run",
            "Download a completed run's artifact into runs/<run_id>/ in your workspace (scrubbed of credentials) and return the file list with the key record lines (run.txt, report.csv, execution.json, build-record.txt, results, formal report).",
            {run_id: z.number().int()},
            async (args) => {
                try {
                    const dir = path.join(ctx.repo, "runs", String(args.run_id));
                    mkdirSync(dir, {recursive: true});
                    await gh.downloadArtifacts(args.run_id, dir);
                    const files = [];
                    const summary = {};
                    walk(dir, (f) => {
                        const rel = path.relative(dir, f);
                        files.push(rel);
                        if (/\.(txt|csv|json|log)$/.test(rel) && statSync(f).size < 200_000) {
                            const raw = readFileSync(f, "utf8");
                            const clean = scrubString(raw);
                            if (clean !== raw) writeFileSync(f, clean);
                            if (/run\.txt$|build-record\.txt$|report\.csv$|execution\.json$|formal-report\.json$|results-.*\.json$|overlay\.txt$/.test(rel)) {
                                summary[rel] = clean.length > 6000 ? clean.slice(0, 6000) + "\n...<truncated>" : clean;
                            }
                        }
                    });
                    ctx.log.append("fetch_run", {runId: args.run_id, files: files.length});
                    return text({dir: path.relative(ctx.repo, dir), files, summary});
                } catch (e) {
                    return fail(e.message);
                }
            },
        ),
        tool(
            "submit_candidate",
            "Final submission (one per run, irreversible): the published commit's candidate/ and formal/ bundle is hashed by the runner, candidate/manifest.json is checked for the required fields, and the restricted controller sends submitCandidate to CreationBounty. Requires a recorded disposition of create or compose and a recorded hypothesis.",
            {commit: z.string().regex(/^[0-9a-f]{40}$/), note: z.string().max(2000).optional()},
            async (args) => {
                try {
                    if (state.submission) throw new Error("already submitted");
                    if (!["create", "compose"].includes(state.disposition)) throw new Error("submission needs a recorded disposition of create or compose");
                    if (!state.hypothesisHash) throw new Error("record_hypothesis first");
                    const pub = state.published.find((p) => p.commit === args.commit);
                    if (!pub) throw new Error("commit was not published by publish_revision");
                    const manifestText = ws.fileAtCommit(ctx.repo, args.commit, "candidate/manifest.json");
                    if (!manifestText) throw new Error("candidate/manifest.json is missing at that commit");
                    const manifest = JSON.parse(manifestText);
                    const required = ["candidateId", "moduleInterface", "compatibilityManifest", "reproducibleBuildRecipe", "guestProgramKey", "featureName", "dependencyVersions", "dependencyLicenses", "originalContributions", "compositionManifest", "theoremStatements", "leanToolchain", "axiomReport", "modelToImplementationMap", "knownFormalGaps", "publicCheckResults", "developmentBenchmarkReport", "integrationInstructions", "licenseReference"];
                    const missing = required.filter((k) => manifest[k] === undefined || manifest[k] === null || manifest[k] === "");
                    if (missing.length) throw new Error(`manifest is missing: ${missing.join(", ")}`);
                    if (ws.headCommit(ctx.repo) !== args.commit) throw new Error("check out the published commit as HEAD before submitting (it must be the latest publish)");
                    const digest = "0x" + treeHash(ctx.repo, ws.WRITABLE).hash;
                    if (digest !== pub.digest) throw new Error("bundle digest changed since publish; publish again");
                    const sourceCommit = "0x" + args.commit.padEnd(64, "0");
                    const receipt = await ctx.controller.submitCandidate({demandId: ctx.demand.demandId, sourceCommit, candidateDigest: digest});
                    state.submission = {commit: args.commit, sourceCommit, candidateDigest: digest, txHash: receipt.hash, at: new Date().toISOString(), note: args.note ?? null};
                    ctx.log.append("submission", state.submission);
                    return text(state.submission);
                } catch (e) {
                    ctx.log.append("submission_refused", {reason: e.message, commit: args.commit});
                    return fail(e.message);
                }
            },
        ),
        tool(
            "decline_demand",
            "Decline the demand (one per run, irreversible): requires a recorded disposition of decline and a published investigation report at candidate/investigation.md. The restricted controller sends decline to CreationBounty, which refunds the sponsor.",
            {commit: z.string().regex(/^[0-9a-f]{40}$/)},
            async (args) => {
                try {
                    if (state.submission || state.declined) throw new Error("a terminal action was already taken");
                    if (state.disposition !== "decline") throw new Error("decline needs a recorded disposition of decline");
                    requirePublished(args.commit);
                    if (!ws.fileAtCommit(ctx.repo, args.commit, "candidate/investigation.md")) throw new Error("candidate/investigation.md is missing at that commit");
                    const receipt = await ctx.controller.decline({demandId: ctx.demand.demandId});
                    state.declined = {commit: args.commit, txHash: receipt.hash, at: new Date().toISOString()};
                    ctx.log.append("decline", state.declined);
                    return text(state.declined);
                } catch (e) {
                    ctx.log.append("decline_refused", {reason: e.message});
                    return fail(e.message);
                }
            },
        ),
    ];
    const server = createSdkMcpServer({name: "lemma", version: "0.1.0", tools});
    return {server, state, toolNames: tools.map((t) => `mcp__lemma__${t.name}`), handlers: Object.fromEntries(tools.map((t) => [t.name, t.handler]))};
}

function walk(dir, visit) {
    for (const e of readdirSync(dir, {withFileTypes: true})) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) walk(full, visit);
        else if (e.isFile()) visit(full);
    }
}
