// Read side of the settlement venue: the funded demand, the posting clock
// (ROBINHOOD_CHAIN_PROD.md 3.3, I-V2) and the CreationBounty ABI the
// controller projects against. No key lives here.
import {createPublicClient, defineChain, http, parseAbi} from "viem";

export const robinhoodTestnet = defineChain({
    id: 46630,
    name: "Robinhood Chain Testnet",
    nativeCurrency: {name: "Ether", symbol: "ETH", decimals: 18},
    rpcUrls: {default: {http: ["https://rpc.testnet.chain.robinhood.com"]}},
    blockExplorers: {default: {name: "Blockscout", url: "https://explorer.testnet.chain.robinhood.com"}},
    testnet: true,
});

export const NODE_INTERFACE = "0x00000000000000000000000000000000000000C8";

export const bountyAbi = parseAbi([
    "function getDemand(bytes32 demandId) view returns ((address sponsor,address creatorPayee,address evaluatorSigner,bytes32 specHash,bytes32 policyHash,bytes32 holdoutCommitment,uint256 bounty,uint256 contributorFee,uint64 submitBy,uint64 evaluateBy,uint8 state,bytes32 sourceCommit,bytes32 candidateDigest,uint64 submittedAt,uint8 verdict,bytes32 reportHash,bytes32 guestKey,bytes32 versionId,uint64 decidedAt))",
    "function submitCandidate(bytes32 demandId, bytes32 sourceCommit, bytes32 candidateDigest)",
    "function decline(bytes32 demandId)",
    "event DemandFunded(bytes32 indexed demandId, address indexed sponsor, address indexed creatorPayee, address evaluatorSigner, bytes32 specHash, bytes32 policyHash, bytes32 holdoutCommitment, uint256 bounty, uint256 contributorFee, uint64 submitBy, uint64 evaluateBy)",
    "event CandidateSubmitted(bytes32 indexed demandId, bytes32 sourceCommit, bytes32 candidateDigest)",
    "event DemandDeclined(bytes32 indexed demandId)",
]);

export const nodeInterfaceAbi = parseAbi([
    "function findBatchContainingBlock(uint64 blockNum) view returns (uint64 batch)",
    "function getL1Confirmations(bytes32 blockHash) view returns (uint64 confirmations)",
]);

export const DEMAND_STATES = ["None", "Funded", "Submitted", "Accepted", "Rejected", "Expired", "Declined"];

export function publicClient(rpcUrl) {
    return createPublicClient({chain: robinhoodTestnet, transport: http(rpcUrl ?? robinhoodTestnet.rpcUrls.default.http[0])});
}

export async function readDemand(client, bounty, demandId) {
    const d = await client.readContract({address: bounty, abi: bountyAbi, functionName: "getDemand", args: [demandId]});
    return {...d, stateName: DEMAND_STATES[d.state]};
}

/** The posting clock: the batch that contains the block, or null while the
 * sequencer has not posted it to the parent chain yet. NodeInterface reverts
 * for an unposted block, which is the signal. */
export async function batchContaining(client, blockNumber) {
    try {
        const batch = await client.readContract({address: NODE_INTERFACE, abi: nodeInterfaceAbi, functionName: "findBatchContainingBlock", args: [BigInt(blockNumber)]});
        return Number(batch);
    } catch (err) {
        if (/revert|execution reverted|not yet|unknown/i.test(String(err))) return null;
        throw err;
    }
}

export async function l1Confirmations(client, blockHash) {
    return Number(await client.readContract({address: NODE_INTERFACE, abi: nodeInterfaceAbi, functionName: "getL1Confirmations", args: [blockHash]}));
}

export async function waitForPosting(client, blockNumber, {pollMs = 60_000, log = () => {}} = {}) {
    for (;;) {
        const batch = await batchContaining(client, blockNumber);
        if (batch !== null) return batch;
        log(`block ${blockNumber} not posted to the parent chain yet; polling again in ${pollMs / 1000} s`);
        await new Promise((r) => setTimeout(r, pollMs));
    }
}
