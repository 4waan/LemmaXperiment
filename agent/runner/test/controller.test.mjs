import test from "node:test";
import assert from "node:assert/strict";
import {Controller, MandateError, projectSubmit} from "../lib/controller.mjs";

const key = "0x" + "11".repeat(32);
const mandate = {demandId: "0x" + "aa".repeat(32), bounty: "0x2C920C76751fCBf080f0443e6A85813A5B3f798E", chainId: 46630, submitBy: 2_000_000_000};
const req = {demandId: mandate.demandId, sourceCommit: "0x" + "bb".repeat(32), candidateDigest: "0x" + "cc".repeat(32)};

test("projection encodes submitCandidate against the mandated contract", () => {
    const p = projectSubmit(mandate, req);
    assert.equal(p.to, mandate.bounty);
    assert.ok(p.data.startsWith("0x"));
    assert.equal(p.data.length, 2 + 8 + 64 * 3);
    assert.throws(() => projectSubmit(mandate, {...req, demandId: "0x" + "dd".repeat(32)}), (e) => e instanceof MandateError && e.code === "WRONG_DEMAND");
    assert.throws(() => projectSubmit(mandate, {...req, sourceCommit: "abc"}), (e) => e.code === "BAD_COMMIT");
});

test("controller sends once, refuses a second terminal action and the deadline", async () => {
    const sent = [];
    const c = new Controller(mandate, key, {sender: async (tx) => (sent.push(tx), "0xhash1")});
    const r = await c.submitCandidate(req);
    assert.equal(r.hash, "0xhash1");
    assert.equal(sent.length, 1);
    await assert.rejects(() => c.submitCandidate(req), (e) => e.code === "SPENT");
    await assert.rejects(() => c.decline({demandId: mandate.demandId}), (e) => e.code === "SPENT");
    const late = new Controller(mandate, key, {sender: async () => "0x", now: () => mandate.submitBy + 1});
    await assert.rejects(() => late.submitCandidate(req), (e) => e.code === "DEADLINE");
    const noDecline = new Controller({...mandate, allowedMethods: ["submitCandidate"]}, key, {sender: async () => "0x"});
    await assert.rejects(() => noDecline.decline({demandId: mandate.demandId}), (e) => e.code === "METHOD");
});

test("controller never exposes the key on its public surface", () => {
    const c = new Controller(mandate, key, {sender: async () => "0x"});
    const json = JSON.stringify(Object.assign({}, c, {wallet: undefined}));
    assert.ok(!json.includes("1111111111"), "key leaked through enumerable state");
    assert.equal(c.address, "0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A");
});
