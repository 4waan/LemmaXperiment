#!/usr/bin/env node
// Demand-to-agent runner (EXPERIMENT.md sections 5 and 13; agent/runner/README.md).
//
//   node run.mjs status                 funded demand, posting clock, budgets
//   node run.mjs dry-run                materialize the workspace, print the tool policy, no model
//   node run.mjs smoke                  a few Haiku turns with the real tools, dispatch disabled
//   node run.mjs start [--model M]      the creation run under demand/budget.json limits
//   node run.mjs control A1|A3          disposition-only control runs (registry controls)
//
// Keys and tokens live in this process only (.env, gh auth); the model gets
// tools. The run log under agent/runner/runs/<runId>/ is hash-chained.
import {existsSync, mkdirSync, readFileSync, writeFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {query} from "@anthropic-ai/claude-agent-sdk";
import {sha256Hex, sha256Json} from "./lib/canonical.mjs";
import {batchContaining, publicClient, readDemand} from "./lib/chain.mjs";
import {Controller} from "./lib/controller.mjs";
import {RunLog} from "./lib/log.mjs";
import {scrub} from "./lib/scrub.mjs";
import {createTools} from "./lib/tools.mjs";
import * as ws from "./lib/workspace.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const RUNS = path.join(HERE, "runs");
const WORKSPACES = path.join(HERE, "workspaces");

function loadEnv() {
    const file = path.join(ROOT, ".env");
    if (!existsSync(file)) return {};
    const out = {};
    for (const line of readFileSync(file, "utf8").split("\n")) {
        const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
        if (m && !line.trim().startsWith("#")) out[m[1]] = m[2].replace(/^"|"$/g, "");
    }
    return out;
}

function json(rel) {
    return JSON.parse(readFileSync(path.join(ROOT, rel), "utf8"));
}

function git(args) {
    return process.getBuiltinModule("node:child_process").execFileSync("git", ["-C", ROOT, ...args], {encoding: "utf8"}).trim();
}

function arg(name, fallback) {
    const i = process.argv.indexOf(name);
    return i > 0 ? process.argv[i + 1] : fallback;
}

const spec = json("demand/spec.json");
const budget = json("demand/budget.json");
const funding = json("demand/funding.json");
const corpus = json("evaluation/fixtures/development-corpus.json");
const pins = json("apparatus/pins.json");
const registry = json("demand/registry-snapshot.json");
const corpusBlocks = corpus.blocks.map((b) => b.number);

function fill(template, values) {
    return template.replace(/\{\{(\w+)\}\}/g, (_, k) => (values[k] === undefined ? `<${k}>` : String(values[k])));
}

function buildPrompt() {
    const template = readFileSync(path.join(HERE, "prompts", "creator.md"), "utf8");
    const limits = budget.creatorBudget.limits;
    return fill(template, {
        demandId: spec.demandId,
        specificationHash: spec.specificationHash,
        objective: spec.objective,
        evaluationPolicyHash: spec.evaluationPolicyHash,
        leanToolchain: json("evaluation/policy.json").formal.leanToolchain,
        integrationInterface: spec.integrationInterface,
        allowedSourcePaths: spec.allowedSourcePaths.map((p) => `\n  - ${p}`).join(""),
        corpusBlocks: corpusBlocks.join(", "),
        rspCommit: pins.rsp.commit,
        localAttemptLimit: limits.localAttemptLimit,
        budgetSummary: `USD ${limits.usdLimit}, ${limits.tokenLimit.toLocaleString()} tokens, ${limits.outputTokenLimit.toLocaleString()} output tokens, ${limits.maxTurns} turns, ${limits.wallTimeSeconds / 3600} h wall time, ${limits.localAttemptLimit} candidate revisions.`,
        dispatchCounts: Object.entries(budget.creatorComputeBudget.dispatches).map(([k, v]) => `${k} ${v}`).join(", "),
    });
}

async function status() {
    const client = publicClient();
    const d = await readDemand(client, funding.creationBounty, funding.demandId);
    const batch = await batchContaining(client, funding.block);
    const now = Math.floor(Date.now() / 1000);
    console.log(JSON.stringify({
        demandId: funding.demandId,
        state: d.stateName,
        bounty: d.bounty.toString(),
        creatorPayee: d.creatorPayee,
        submitBy: {unix: Number(d.submitBy), hoursLeft: ((Number(d.submitBy) - now) / 3600).toFixed(1)},
        evaluateBy: {unix: Number(d.evaluateBy), hoursLeft: ((Number(d.evaluateBy) - now) / 3600).toFixed(1)},
        fundingBlock: funding.block,
        postedToParentChain: batch !== null ? {batch} : false,
        triggerSatisfied: d.stateName === "Funded" && batch !== null && now < Number(d.submitBy),
        creatorBudget: budget.creatorBudget.limits,
        dispatches: budget.creatorComputeBudget.dispatches,
        sourceCommit: git(["rev-parse", "HEAD"]),
    }, null, 2));
}

function readActions(runDir) {
    const file = path.join(runDir, "actions.jsonl");
    if (!existsSync(file)) return [];
    return readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

function sessionIdOf(runDir) {
    const file = path.join(runDir, "messages.jsonl");
    if (!existsSync(file)) return null;
    for (const line of readFileSync(file, "utf8").split("\n").filter(Boolean)) {
        const m = JSON.parse(line);
        if (m.type === "system" && m.subtype === "init") return m.session_id;
    }
    return null;
}

/** Picks up an interrupted run: same workspace, same run directory, the
 * enforcement state rebuilt from the log, the model session resumed. */
async function resumePrepare(runId) {
    const runDir = path.join(RUNS, runId);
    if (!existsSync(path.join(runDir, "run.json"))) throw new Error(`no run ${runId}`);
    const manifest = JSON.parse(readFileSync(path.join(runDir, "run.json"), "utf8"));
    if (manifest.submission || manifest.declined) throw new Error("that run already took its terminal action");
    const client = publicClient();
    const demand = await readDemand(client, funding.creationBounty, funding.demandId);
    const log = new RunLog(runDir);
    const actions = readActions(runDir);
    const sessionId = sessionIdOf(runDir);
    const repo = manifest.workspace;
    if (!existsSync(repo)) throw new Error(`workspace ${repo} is gone`);
    const workspace = {repo, branch: manifest.branch, head: manifest.sourceSnapshotHash};
    const prompt = readFileSync(path.join(runDir, "prompt.md"), "utf8");
    const spentUsd = actions.filter((e) => e.kind === "result").reduce((a, e) => a + (e.data.costUsd ?? 0), 0);
    log.append("resume", {sessionId, entriesBefore: actions.length, spentUsd});
    return {runId, runDir, log, workspace, prompt, manifest, demand, limits: manifest.budget, restore: actions, sessionId, spentUsd};
}

async function prepare(mode) {
    const client = publicClient();
    const demand = await readDemand(client, funding.creationBounty, funding.demandId);
    const batch = await batchContaining(client, funding.block);
    const now = Math.floor(Date.now() / 1000);
    if (mode === "start") {
        if (demand.stateName !== "Funded") throw new Error(`demand is ${demand.stateName}, not Funded`);
        if (batch === null) throw new Error("funding block is not posted to the parent chain yet (I-V2); try later");
        if (now >= Number(demand.submitBy)) throw new Error("submitBy has passed");
    }
    const sourceCommit = git(["rev-parse", "HEAD"]);
    if (git(["status", "--porcelain"])) console.warn("warning: the source repository has uncommitted changes; the workspace uses HEAD");
    const runId = `${mode}-${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}`;
    const runDir = path.join(RUNS, runId);
    const log = new RunLog(runDir);
    const workspace = ws.materialize({root: path.join(WORKSPACES, runId), sourceRepo: ROOT, sourceCommit, rspCommit: pins.rsp.commit, runId});
    const prompt = buildPrompt();
    const limits = budget.creatorBudget.limits;
    const manifest = {
        runId,
        mode,
        demandId: funding.demandId,
        specificationHash: spec.specificationHash,
        evaluationPolicyHash: spec.evaluationPolicyHash,
        sourceSnapshotHash: sourceCommit,
        registrySnapshotHash: sha256Hex(readFileSync(path.join(ROOT, "demand/registry-snapshot.json"))),
        initialPromptHash: sha256Hex(prompt),
        toolPolicyHash: null,
        budget: limits,
        dispatches: budget.creatorComputeBudget.dispatches,
        fundingBlock: funding.block,
        postedInBatch: batch,
        workspace: workspace.repo,
        branch: workspace.branch,
        startedAt: new Date().toISOString(),
    };
    return {runId, runDir, log, workspace, prompt, manifest, demand, limits};
}

function toolPolicy(workspaceRepo, toolNames, {dispatch}) {
    const home = process.env.HOME;
    // Rule syntax: a `//` prefix is an absolute filesystem path, `~/` the home
    // directory; deny rules win over allow rules. Edit, Write and Bash are not
    // in allowedTools on purpose: they are reachable only through the allow
    // rules below, so any other path or command falls to "ask", which
    // permissionMode dontAsk turns into a denial.
    const allowed = ["Read", "Glob", "Grep", "TodoWrite", ...(dispatch ? toolNames : toolNames.filter((n) => /record_|publish_revision/.test(n)))];
    const permissions = {
        allow: [
            `Edit(/${workspaceRepo}/candidate/**)`,
            `Edit(/${workspaceRepo}/formal/**)`,
            `Write(/${workspaceRepo}/candidate/**)`,
            `Write(/${workspaceRepo}/formal/**)`,
            "Bash(cargo check:*)",
            "Bash(cargo build:*)",
            "Bash(cargo test:*)",
            "Bash(cargo tree:*)",
            "Bash(cargo metadata:*)",
            "Bash(lake:*)",
            "Bash(lean:*)",
            "Bash(git status:*)",
            "Bash(git diff:*)",
            "Bash(git log:*)",
            "Bash(git show:*)",
            "Bash(git ls-files:*)",
            "Bash(ls:*)",
            "Bash(cat:*)",
            "Bash(head:*)",
            "Bash(tail:*)",
            "Bash(wc:*)",
            "Bash(grep:*)",
            "Bash(rg:*)",
            "Bash(find:*)",
            "Bash(python3:*)",
            "Bash(sha256sum:*)",
            "Bash(shasum:*)",
            "Bash(cp:*)",
            "Bash(mkdir:*)",
            "Bash(diff:*)",
            "Bash(jq:*)",
            "Bash(sed:*)",
            "Bash(awk:*)",
            "Bash(sort:*)",
            "Bash(uniq:*)",
            "Bash(tr:*)",
            "Bash(xargs:*)",
            "Bash(echo:*)",
            "Bash(printf:*)",
            "Bash(rustc --version)",
            "Bash(cargo --version)",
        ],
        deny: [
            `Read(/${home}/.lemma-evaluator/**)`,
            `Read(/${ROOT}/.env)`,
            "Read(**/.env)",
            "Read(**/.env.*)",
            "Read(~/.claude/**)",
            "Read(~/.config/gh/**)",
            "Read(~/.ssh/**)",
            "Read(~/.lemma-evaluator/**)",
            `Read(/${ROOT}/agent/runner/runs/**)`,
            "Edit(**/demand/**)",
            "Edit(**/evaluation/**)",
            "Edit(**/apparatus/**)",
            "Edit(**/.github/**)",
            "Write(**/demand/**)",
            "Write(**/evaluation/**)",
            "Write(**/apparatus/**)",
            "Write(**/.github/**)",
            "Bash(git push:*)",
            "Bash(git remote:*)",
            "Bash(gh:*)",
            "Bash(curl:*)",
            "Bash(wget:*)",
            "Bash(cast:*)",
            "Bash(forge:*)",
            "Bash(ssh:*)",
            "Bash(sudo:*)",
            "Bash(env:*)",
            "Bash(printenv:*)",
            "WebFetch",
            "WebSearch",
        ],
    };
    const sandbox = {
        enabled: true,
        failIfUnavailable: false,
        autoAllowBashIfSandboxed: false,
        network: {allowedDomains: ["crates.io", "static.crates.io", "index.crates.io", "github.com", "codeload.github.com", "objects.githubusercontent.com", "releases.lean-lang.org", "elan.lean-lang.org"]},
        filesystem: {
            allowWrite: [`${workspaceRepo}/candidate`, `${workspaceRepo}/formal`, `${workspaceRepo}/runs`, `${workspaceRepo}/upstream`, "/tmp", `${home}/.cargo`, `${home}/.elan`],
            denyRead: [`${home}/.lemma-evaluator`, `${ROOT}/.env`, `${home}/.config/gh`, `${home}/.ssh`, `${ROOT}/agent/runner/runs`],
        },
    };
    return {allowed, permissions, sandbox};
}

async function runSession({runId, runDir, log, workspace, prompt, manifest, demand, limits, restore, sessionId, spentUsd = 0}, {model, maxTurns, maxBudgetUsd, wallSeconds, dispatch, controller, promptOverride}) {
    const tools = createTools({log, repo: workspace.repo, baseCommit: workspace.head, runId, demand: {demandId: funding.demandId}, budget: {dispatches: budget.creatorComputeBudget.dispatches, localAttemptLimit: limits.localAttemptLimit}, corpusBlocks, controller, dispatchEnabled: dispatch, restore});
    maxBudgetUsd = Math.max(0, maxBudgetUsd - spentUsd);
    const policy = toolPolicy(workspace.repo, tools.toolNames, {dispatch});
    manifest.toolPolicyHash = sha256Json(policy);
    manifest.model = model;
    manifest.maxTurns = maxTurns;
    manifest.maxBudgetUsd = maxBudgetUsd;
    log.writeJson("run.json", manifest);
    writeFileSync(path.join(runDir, "prompt.md"), promptOverride ?? prompt);
    log.writeJson("tool-policy.json", policy);
    log.append("start", {runId, model, maxTurns, maxBudgetUsd, wallSeconds, dispatch, sourceCommit: manifest.sourceSnapshotHash, promptHash: manifest.initialPromptHash, toolPolicyHash: manifest.toolPolicyHash});

    const abort = new AbortController();
    const timer = setTimeout(() => {
        log.append("stop", {reason: "wall time limit", wallSeconds});
        abort.abort();
    }, wallSeconds * 1000);
    const usage = {turns: 0, inputTokens: 0, outputTokens: 0, cacheRead: 0, cacheWrite: 0, costUsd: 0};
    const transcript = path.join(runDir, "messages.jsonl");
    let result = null;
    try {
        const q = query({
            prompt: sessionId ? "Continue from where the previous session stopped; the run log and your workspace are unchanged. State what you were doing and proceed." : (promptOverride ?? prompt),
            options: {
                model,
                resume: sessionId ?? undefined,
                cwd: workspace.repo,
                maxTurns,
                maxBudgetUsd,
                permissionMode: "dontAsk",
                allowedTools: policy.allowed,
                disallowedTools: ["WebFetch", "WebSearch", "Task", "Agent"],
                settings: {permissions: policy.permissions},
                settingSources: [],
                sandbox: policy.sandbox,
                mcpServers: {lemma: tools.server},
                abortController: abort,
                persistSession: true,
                hooks: {
                    PreToolUse: [{hooks: [async (input) => {
                        log.append("tool_call", {tool: input.tool_name, input: input.tool_input});
                        return {continue: true};
                    }]}],
                    PermissionDenied: [{hooks: [async (input) => {
                        log.append("denied", {tool: input.tool_name, input: input.tool_input, reason: input.reason ?? null});
                        return {continue: true};
                    }]}],
                    PostToolUse: [{hooks: [async (input) => {
                        const out = typeof input.tool_response === "string" ? input.tool_response : JSON.stringify(input.tool_response ?? "");
                        log.append("tool_result", {tool: input.tool_name, bytes: out.length, head: out.slice(0, 400)});
                        return {continue: true};
                    }]}],
                },
            },
        });
        for await (const message of q) {
            const line = JSON.stringify(scrub(message));
            process.getBuiltinModule("node:fs").appendFileSync(transcript, line + "\n");
            if (message.type === "assistant" && message.message?.usage) {
                const u = message.message.usage;
                usage.turns += 1;
                usage.inputTokens += u.input_tokens ?? 0;
                usage.outputTokens += u.output_tokens ?? 0;
                usage.cacheRead += u.cache_read_input_tokens ?? 0;
                usage.cacheWrite += u.cache_creation_input_tokens ?? 0;
                const total = usage.inputTokens + usage.outputTokens + usage.cacheRead + usage.cacheWrite;
                if (total > limits.tokenLimit || usage.outputTokens > limits.outputTokenLimit) {
                    log.append("stop", {reason: "token limit", usage});
                    abort.abort();
                }
                if (usage.turns % 25 === 0) log.append("usage", usage);
            }
            if (message.type === "result") {
                result = {subtype: message.subtype, numTurns: message.num_turns, costUsd: message.total_cost_usd, durationMs: message.duration_ms, isError: message.is_error};
                usage.costUsd = message.total_cost_usd ?? usage.costUsd;
                log.append("result", result);
            }
        }
    } catch (err) {
        log.append("error", {message: String(err?.message ?? err)});
    } finally {
        clearTimeout(timer);
    }
    const end = {
        endedAt: new Date().toISOString(),
        usage,
        result,
        disposition: tools.state.disposition,
        hypothesisHash: tools.state.hypothesisHash,
        revisions: [...tools.state.revisions],
        published: tools.state.published,
        dispatches: tools.state.dispatches,
        runs: tools.state.runs,
        submission: tools.state.submission,
        declined: tools.state.declined,
        humanInterventions: [],
        assistanceLevel: "unassisted within the supplied environment (edit this file if that changed)",
    };
    log.writeJson("run.json", {...manifest, ...end});
    log.append("end", end);
    const chain = RunLog.verify(log.file);
    console.log(JSON.stringify({runId, runDir, ...end, logEntries: chain.entries, logHead: chain.head}, null, 2));
}

const cmd = process.argv[2];
if (cmd === "status") {
    await status();
} else if (cmd === "dry-run") {
    const p = await prepare("dry-run");
    const tools = createTools({log: p.log, repo: p.workspace.repo, baseCommit: p.workspace.head, runId: p.runId, demand: {demandId: funding.demandId}, budget: {dispatches: budget.creatorComputeBudget.dispatches, localAttemptLimit: p.limits.localAttemptLimit}, corpusBlocks, controller: null, dispatchEnabled: false});
    const policy = toolPolicy(p.workspace.repo, tools.toolNames, {dispatch: true});
    p.manifest.toolPolicyHash = sha256Json(policy);
    p.log.writeJson("run.json", p.manifest);
    p.log.writeJson("tool-policy.json", policy);
    writeFileSync(path.join(p.runDir, "prompt.md"), p.prompt);
    console.log(JSON.stringify({...p.manifest, tools: tools.toolNames, promptBytes: p.prompt.length, demandState: p.demand.stateName}, null, 2));
} else if (cmd === "smoke" || cmd === "start") {
    const env = loadEnv();
    const p = await prepare(cmd === "start" ? "start" : "smoke");
    const controller = cmd === "start"
        ? new Controller({demandId: funding.demandId, bounty: funding.creationBounty, chainId: 46630, submitBy: Number(p.demand.submitBy)}, env.CREATOR_PAYEE_PRIVATE_KEY)
        : null;
    if (cmd === "start" && controller.address.toLowerCase() !== p.demand.creatorPayee.toLowerCase()) throw new Error("CREATOR_PAYEE_PRIVATE_KEY does not match the funded creatorPayee");
    const limits = p.limits;
    await runSession(p, cmd === "start"
        ? {model: arg("--model", spec.agentBudget.model), maxTurns: Number(arg("--max-turns", limits.maxTurns)), maxBudgetUsd: Number(arg("--budget-usd", limits.usdLimit)), wallSeconds: limits.wallTimeSeconds, dispatch: true, controller}
        : {model: arg("--model", "claude-haiku-4-5-20251001"), maxTurns: Number(arg("--max-turns", 6)), maxBudgetUsd: Number(arg("--budget-usd", 2)), wallSeconds: 900, dispatch: false, controller: null, promptOverride: `${p.prompt}\n\n## Smoke test\n\nThis is a smoke test of the runner, not the creation run. Do exactly this and stop: 1) list the tools you have; 2) read demand/spec.json and state the demandId; 3) call record_disposition with disposition "decline" and evidence "smoke test only"; 4) try to read ${ROOT}/.env and report whether it was denied; 5) try to write the file demand/smoke-should-fail.txt in your workspace and report whether it was denied; 6) try the Bash command "git push origin HEAD" and report whether it was denied; 7) try the Bash command "curl -s https://example.com" and report whether it was denied; 8) run the Bash command "cargo --version" and report the output; 9) create candidate/smoke.txt with one line and call publish_revision; 10) stop.`});
} else if (cmd === "resume") {
    const env = loadEnv();
    const p = await resumePrepare(process.argv[3]);
    if (!p.runId.startsWith("start-")) throw new Error("resume is for creation runs");
    if (p.demand.stateName !== "Funded") throw new Error(`demand is ${p.demand.stateName}`);
    const controller = new Controller({demandId: funding.demandId, bounty: funding.creationBounty, chainId: 46630, submitBy: Number(p.demand.submitBy)}, env.CREATOR_PAYEE_PRIVATE_KEY);
    const elapsed = (Date.now() - Date.parse(p.manifest.startedAt)) / 1000;
    await runSession(p, {model: p.manifest.model, maxTurns: p.manifest.maxTurns, maxBudgetUsd: p.manifest.maxBudgetUsd, wallSeconds: Math.max(600, p.limits.wallTimeSeconds - elapsed), dispatch: true, controller});
} else if (cmd === "control") {
    const which = process.argv[3];
    const control = which === "A1" ? registry.controls.existingCapabilityControl : which === "A3" ? registry.controls.noViableOpportunityControl : null;
    if (!control) throw new Error("control A1 or A3");
    const p = await prepare(`control-${which}`);
    const limits = {...p.limits, ...budget.creatorBudget.controls.perRun};
    const promptOverride = `${p.prompt}\n\n## Control request ${control.requestId} (this replaces the demand objective above for this run; it is a disposition-only run, no builds, no submission)\n\nRequest: ${control.request}\n\nDo the Interpret and Search steps against demand/registry-snapshot.json and the measured records, then call record_disposition once with your disposition and evidence (alternatives, eligibility, estimates, what you would do next), write candidate/decision.md with the same content, call publish_revision, and stop. Do not call any dispatch or submit tool.`;
    await runSession({...p, limits}, {model: arg("--model", spec.agentBudget.model), maxTurns: limits.maxTurns, maxBudgetUsd: limits.usdLimit, wallSeconds: limits.wallTimeSeconds, dispatch: false, controller: null, promptOverride});
} else {
    console.log("usage: node run.mjs status | dry-run | smoke | start [--model M] [--max-turns N] [--budget-usd X] | resume <runId> | control A1|A3");
    process.exit(1);
}
