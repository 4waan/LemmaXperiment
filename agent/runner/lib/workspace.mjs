// The creator's restricted workspace (EXPERIMENT.md section 5, ROBINHOOD C3,
// I-A3): a clone of this repository at the funded commit with candidate/ and
// formal/ as the only writable trees, the pinned RSP source as read-only
// reference, and a remote that cannot be pushed to from inside.
import {execFileSync} from "node:child_process";
import {existsSync, mkdirSync, readFileSync, writeFileSync} from "node:fs";
import path from "node:path";

export const WRITABLE = ["candidate", "formal"];
export const CREATOR_BRANCH = (runId) => `creator/${runId}`;

function git(dir, args, opts = {}) {
    return execFileSync("git", ["-C", dir, ...args], {encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...opts}).trim();
}

export function materialize({root, sourceRepo, sourceCommit, rspCommit, runId}) {
    const repo = path.join(root, "repo");
    if (!existsSync(repo)) {
        mkdirSync(root, {recursive: true});
        execFileSync("git", ["clone", "--quiet", "--no-hardlinks", sourceRepo, repo], {stdio: "inherit"});
    }
    git(repo, ["checkout", "--quiet", "--detach", sourceCommit]);
    git(repo, ["checkout", "--quiet", "-B", CREATOR_BRANCH(runId)]);
    // No credentials inside: the model can fetch nothing and push nowhere.
    git(repo, ["remote", "set-url", "origin", "https://github.com/4waan/LemmaXperiment"]);
    git(repo, ["remote", "set-url", "--push", "origin", "no_push"]);
    git(repo, ["config", "user.name", "creator-agent"]);
    git(repo, ["config", "user.email", "creator-agent@lemma.invalid"]);
    git(repo, ["submodule", "update", "--init", "--quiet"]);
    const upstream = path.join(repo, "upstream", "rsp");
    if (!existsSync(upstream)) {
        mkdirSync(path.dirname(upstream), {recursive: true});
        execFileSync("git", ["clone", "--quiet", "https://github.com/succinctlabs/rsp", upstream], {stdio: "inherit"});
        git(upstream, ["checkout", "--quiet", rspCommit]);
    }
    // Reference and download trees stay out of the creator's commits.
    const exclude = path.join(repo, ".git", "info", "exclude");
    const lines = existsSync(exclude) ? readFileSync(exclude, "utf8") : "";
    if (!lines.includes("/upstream/")) writeFileSync(exclude, lines + "/upstream/\n/runs/\n");
    mkdirSync(path.join(repo, "runs"), {recursive: true});
    mkdirSync(path.join(repo, "candidate"), {recursive: true});
    mkdirSync(path.join(repo, "formal"), {recursive: true});
    return {repo, upstream, branch: CREATOR_BRANCH(runId), head: git(repo, ["rev-parse", "HEAD"])};
}

/** Paths changed in the working tree that fall outside the writable trees. */
export function forbiddenChanges(repo) {
    // Not through git(): trim would eat the status column's leading space.
    const status = execFileSync("git", ["-C", repo, "status", "--porcelain", "--untracked-files=all"], {encoding: "utf8"});
    return status
        .split("\n")
        .filter(Boolean)
        .map((l) => l.slice(3).replace(/^"|"$/g, ""))
        .filter((p) => !WRITABLE.some((w) => p === w || p.startsWith(`${w}/`)));
}

export function commitWritable(repo, message) {
    const forbidden = forbiddenChanges(repo);
    if (forbidden.length) throw new Error(`changes outside ${WRITABLE.join("/")}: ${forbidden.slice(0, 10).join(", ")}`);
    git(repo, ["add", "--", ...WRITABLE]);
    const staged = git(repo, ["diff", "--cached", "--name-only"]);
    if (!staged) throw new Error("nothing to commit in candidate/ or formal/");
    git(repo, ["commit", "--quiet", "-m", message]);
    return {commit: git(repo, ["rev-parse", "HEAD"]), files: staged.split("\n")};
}

export function headCommit(repo) {
    return git(repo, ["rev-parse", "HEAD"]);
}

export function commitExists(repo, commit) {
    try {
        return git(repo, ["cat-file", "-t", commit]) === "commit";
    } catch {
        return false;
    }
}

export function fileAtCommit(repo, commit, file) {
    try {
        return git(repo, ["show", `${commit}:${file}`]);
    } catch {
        return null;
    }
}

export function changedPathsSince(repo, base, commit) {
    return git(repo, ["diff", "--name-only", base, commit]).split("\n").filter(Boolean);
}
