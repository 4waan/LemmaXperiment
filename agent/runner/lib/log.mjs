// Hash-chained, append-only run log: one JSON line per event, each carrying
// the sha256 of the previous line, so a record cannot be edited or dropped
// unnoticed (ROBINHOOD_CHAIN_PROD.md I-A4, I-A8). Every payload is scrubbed
// before it is written.
import {appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync} from "node:fs";
import path from "node:path";
import {canonicalJson, sha256Hex} from "./canonical.mjs";
import {scrub} from "./scrub.mjs";

const EMPTY_HEAD = "0".repeat(64);

export class RunLog {
    constructor(dir) {
        this.dir = dir;
        mkdirSync(dir, {recursive: true});
        this.file = path.join(dir, "actions.jsonl");
        this.seq = 0;
        this.head = EMPTY_HEAD;
        if (existsSync(this.file)) {
            for (const line of readFileSync(this.file, "utf8").split("\n").filter(Boolean)) {
                const entry = JSON.parse(line);
                this.seq = entry.seq + 1;
                this.head = entry.hash;
            }
        }
    }

    append(kind, data) {
        const body = {seq: this.seq, at: new Date().toISOString(), kind, data: scrub(data), prev: this.head};
        const hash = sha256Hex(canonicalJson(body));
        appendFileSync(this.file, JSON.stringify({...body, hash}) + "\n");
        this.seq += 1;
        this.head = hash;
        return hash;
    }

    /** Re-reads the file and checks every link; returns the entry count. */
    static verify(file) {
        let prev = EMPTY_HEAD;
        let n = 0;
        for (const line of readFileSync(file, "utf8").split("\n").filter(Boolean)) {
            const {hash, ...body} = JSON.parse(line);
            if (body.prev !== prev) throw new Error(`broken chain at seq ${body.seq}`);
            if (sha256Hex(canonicalJson(body)) !== hash) throw new Error(`bad hash at seq ${body.seq}`);
            if (body.seq !== n) throw new Error(`bad seq at ${n}`);
            prev = hash;
            n += 1;
        }
        return {entries: n, head: prev};
    }

    writeJson(name, value) {
        writeFileSync(path.join(this.dir, name), JSON.stringify(scrub(value), null, 2) + "\n");
    }
}
