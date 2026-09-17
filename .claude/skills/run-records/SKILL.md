---
name: run-records
description: "Before any file produced by a job, tool or workflow is copied into the repository (run records, artifacts, logs, timing files, deployment output), scan it for credentials and check that no command line ever carried one. Written after apparatus/FAILURES.md #11."
tags: [security, secrets, artifacts, workflows, credentials]
---

# Run records and artifacts

GitHub masks secrets in job logs and nowhere else. A file written by a tool
inside a job (`/usr/bin/time -v` output, a crash dump, a config echo, a
deployment manifest, a debug log) carries whatever was on the command line
or in the environment, and an uploaded artifact or a committed run record
publishes it. That is how an archive-provider key reached this repository:
`time.txt` recorded `Command being timed: ... --rpc-url https://...v2/<key>`.

## Rules

1. Credentials never go on a command line. Pass them through environment
   variables the program reads itself (`RPC_1`, `RPC_{chain_id}`, env-backed
   clap args), so no argv listing, `ps`, shell trace or timing tool can
   record them. `cast send --private-key "$VAR"` inside a subshell that
   sources `.env` is acceptable on the laptop; never in a workflow.
2. Every workflow step that writes a file destined for an artifact scrubs it
   before upload (`sed` the provider-key patterns of `.gitleaks.toml` to
   `<redacted>`), and the job never `cat`s a credential-bearing file.
3. Before `cp`-ing a downloaded artifact into `apparatus/runs/` or anywhere
   tracked, run `gitleaks detect --no-git --source <dir> --redact`; a finding
   means the artifact is deleted from GitHub, the key is rotated, and only
   then is a scrubbed copy committed.
4. `git add -A` is not allowed for artifact directories; add the run
   directory explicitly after the scan.
5. The pre-commit hook (`.githooks/pre-commit`) is the last net, not the
   first. If it fires, treat the finding as a live leak until proven a
   fixture.
6. When a leak has reached a public remote: rotate at the provider first,
   delete artifacts and scrub files second, then record it in
   `apparatus/FAILURES.md` with the commit range, and re-freeze any policy
   hash that covers the changed workflow.

## Checklist for a new workflow step

- Does any command receive a secret as an argument? Move it to `env:`.
- Does any file the step writes contain argv, env, or a URL? Scrub it.
- Is the artifact readable by everyone (public repo)? Assume yes.
- Does the job print a file? Only files that cannot hold a secret.
