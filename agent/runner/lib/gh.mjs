// GitHub Actions access for the runner process only (the model never holds
// the token). Dispatches are validated by the tools before they reach here.
import {execFile} from "node:child_process";
import {promisify} from "node:util";

const run = promisify(execFile);
export const REPO = "4waan/LemmaXperiment";

async function gh(args, opts = {}) {
    const {stdout} = await run("gh", args, {maxBuffer: 64 * 1024 * 1024, ...opts});
    return stdout;
}

export async function latestRunId(workflow) {
    const out = await gh(["run", "list", "-R", REPO, "-w", workflow, "-L", "1", "--json", "databaseId", "-q", ".[0].databaseId"]);
    return out.trim() ? Number(out.trim()) : null;
}

/** Dispatches a workflow and returns the id of the run it created. */
export async function dispatch(workflow, inputs, {ref = "main", sleepMs = 8000} = {}) {
    const before = await latestRunId(workflow);
    const args = ["workflow", "run", workflow, "-R", REPO, "--ref", ref];
    for (const [k, v] of Object.entries(inputs)) args.push("-f", `${k}=${v}`);
    await gh(args);
    for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, sleepMs));
        const id = await latestRunId(workflow);
        if (id && id !== before) return id;
    }
    throw new Error(`dispatch of ${workflow} was accepted but no new run appeared`);
}

export async function runStatus(runId) {
    const out = await gh(["run", "view", String(runId), "-R", REPO, "--json", "status,conclusion,workflowName,createdAt,updatedAt,jobs,url"]);
    const r = JSON.parse(out);
    return {
        runId,
        workflow: r.workflowName,
        status: r.status,
        conclusion: r.conclusion,
        createdAt: r.createdAt,
        updatedAt: r.updatedAt,
        url: r.url,
        jobs: (r.jobs ?? []).map((j) => ({name: j.name, status: j.status, conclusion: j.conclusion})),
    };
}

export async function downloadArtifacts(runId, dir) {
    await gh(["run", "download", String(runId), "-R", REPO, "-D", dir]);
}

export async function pushBranch(repoDir, branch) {
    // The runner's own credentials (gh auth) through the http remote; the
    // workspace remote the model sees has no push URL.
    const token = (await gh(["auth", "token"])).trim();
    const url = `https://x-access-token:${token}@github.com/${REPO}.git`;
    await run("git", ["-C", repoDir, "push", "--quiet", url, `HEAD:refs/heads/${branch}`]);
}
