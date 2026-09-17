// B7, the restricted transaction controller (ROBINHOOD_CHAIN_PROD.md I-A1,
// I-A2, I-A5, I-A7). Holds the creator payee key for one demand and can do
// exactly two things with it, each once: submit a candidate and decline.
// Every call is projected to calldata from a typed request, checked against
// the mandate, compared byte for byte with what is about to be signed, then
// sent. The model never sees this module; it reaches it through a tool that
// passes structured arguments only.
import {createWalletClient, encodeFunctionData, http} from "viem";
import {privateKeyToAccount} from "viem/accounts";
import {bountyAbi, robinhoodTestnet} from "./chain.mjs";

export class MandateError extends Error {
    constructor(code, message) {
        super(message);
        this.code = code;
        this.name = "MandateError";
    }
}

const HEX32 = /^0x[0-9a-f]{64}$/;

export function projectSubmit(mandate, request) {
    if (request.demandId !== mandate.demandId) throw new MandateError("WRONG_DEMAND", "demandId is not the mandated demand");
    if (!HEX32.test(request.sourceCommit)) throw new MandateError("BAD_COMMIT", "sourceCommit must be a 32-byte hex value");
    if (!HEX32.test(request.candidateDigest)) throw new MandateError("BAD_DIGEST", "candidateDigest must be a 32-byte hex value");
    return {
        to: mandate.bounty,
        value: 0n,
        data: encodeFunctionData({abi: bountyAbi, functionName: "submitCandidate", args: [request.demandId, request.sourceCommit, request.candidateDigest]}),
        method: "submitCandidate",
    };
}

export function projectDecline(mandate, request) {
    if (request.demandId !== mandate.demandId) throw new MandateError("WRONG_DEMAND", "demandId is not the mandated demand");
    return {to: mandate.bounty, value: 0n, data: encodeFunctionData({abi: bountyAbi, functionName: "decline", args: [request.demandId]}), method: "decline"};
}

export function assertMatchesProjection(tx, projection) {
    if (tx.to.toLowerCase() !== projection.to.toLowerCase()) throw new MandateError("PROJECTION", "recipient differs from the projection");
    if ((tx.value ?? 0n) !== projection.value) throw new MandateError("PROJECTION", "value differs from the projection");
    if (tx.data !== projection.data) throw new MandateError("PROJECTION", "calldata differs from the projection");
}

export class Controller {
    /**
     * @param mandate {demandId, bounty, chainId, submitBy (unix), allowedMethods}
     * @param privateKey the creator payee key; read from the environment by the runner, never logged
     * @param sender optional async (tx) => hash, for tests
     */
    constructor(mandate, privateKey, {rpcUrl, sender, now = () => Math.floor(Date.now() / 1000)} = {}) {
        this.mandate = {allowedMethods: ["submitCandidate", "decline"], ...mandate};
        this.account = privateKeyToAccount(privateKey);
        this.now = now;
        this.spent = new Map();
        this.wallet = sender
            ? null
            : createWalletClient({account: this.account, chain: robinhoodTestnet, transport: http(rpcUrl ?? robinhoodTestnet.rpcUrls.default.http[0])});
        this.sender = sender ?? ((tx) => this.wallet.sendTransaction({to: tx.to, value: tx.value, data: tx.data}));
    }

    get address() {
        return this.account.address;
    }

    async #send(projection) {
        if (!this.mandate.allowedMethods.includes(projection.method)) throw new MandateError("METHOD", `${projection.method} is not mandated`);
        if (this.spent.has(projection.method)) throw new MandateError("SPENT", `${projection.method} was already used by this run`);
        if (this.spent.size > 0) throw new MandateError("SPENT", "the mandate allows one terminal action per run");
        if (this.now() > this.mandate.submitBy) throw new MandateError("DEADLINE", "submitBy has passed");
        const tx = {to: projection.to, value: projection.value, data: projection.data};
        assertMatchesProjection(tx, projection);
        this.spent.set(projection.method, {at: this.now()});
        const hash = await this.sender(tx);
        this.spent.get(projection.method).hash = hash;
        return {hash, method: projection.method, to: tx.to, data: tx.data};
    }

    submitCandidate(request) {
        return this.#send(projectSubmit(this.mandate, request));
    }

    decline(request) {
        return this.#send(projectDecline(this.mandate, request));
    }
}
