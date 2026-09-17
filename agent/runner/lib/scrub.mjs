// Nothing a run log, a receipt or a tool result carries may hold a credential
// (ROBINHOOD_CHAIN_PROD.md I-A8; apparatus/FAILURES.md #11). Keys are dropped
// by name, and strings are cleaned by the same patterns .gitleaks.toml uses.
const FORBIDDEN_KEYS = new Set([
    "privatekey", "private_key", "signingkey", "secretkey", "secret_key", "mnemonic",
    "seed", "passphrase", "password", "token", "apikey", "api_key", "authorization",
    "cookie", "presalt", "salt", "witness", "signedtransaction", "rawtransaction",
]);

const PATTERNS = [
    /(alchemy\.com\/v2\/|\balch_)[A-Za-z0-9_-]{16,}/g,
    /https?:\/\/[a-z0-9.-]+\.(?:g\.alchemy\.com|infura\.io|quiknode\.pro|chainstack\.com|blastapi\.io|ankr\.com|getblock\.io)\/(?:v[0-9]\/)?[A-Za-z0-9_-]{16,}/g,
    /((?:private[_-]?key|privkey|secret[_-]?key|mnemonic)[A-Za-z0-9_]*\s*[=:]\s*["']?)(?:0x)?[0-9a-fA-F]{64}\b/gi,
    /\b(sk-ant-[A-Za-z0-9_-]{8})[A-Za-z0-9_-]+/g,
    /(ghp_|github_pat_)[A-Za-z0-9_]{8,}/g,
];

export function scrubString(s) {
    let out = s;
    for (const p of PATTERNS) out = out.replace(p, (m, g1) => `${g1 && !m.startsWith(g1) ? "" : g1 || ""}<redacted>`);
    return out;
}

export function scrub(value, depth = 0) {
    if (depth > 24) return "<too deep>";
    if (typeof value === "string") return scrubString(value);
    if (Array.isArray(value)) return value.map((v) => scrub(v, depth + 1));
    if (value !== null && typeof value === "object") {
        const out = {};
        for (const [k, v] of Object.entries(value)) {
            if (FORBIDDEN_KEYS.has(k.toLowerCase().replace(/[^a-z_]/g, ""))) out[k] = "<dropped>";
            else out[k] = scrub(v, depth + 1);
        }
        return out;
    }
    return value;
}
