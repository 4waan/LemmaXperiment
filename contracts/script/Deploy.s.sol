// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {SP1Verifier} from "../src/sp1/v6.1.0/SP1VerifierGroth16.sol";
import {ModuleRegistry} from "../src/ModuleRegistry.sol";
import {CreationBounty} from "../src/CreationBounty.sol";
import {UsageEscrow} from "../src/UsageEscrow.sol";

/// Deploys the four contracts in one nonce sequence and writes the evidence
/// file deployments/<chainId>-lemma.json (ROBINHOOD_CHAIN_PROD.md I-V5). The
/// registry is constructed with the bounty's predicted address so neither
/// contract needs an admin setter.
///
///   DEPLOYER_PRIVATE_KEY=... forge script script/Deploy.s.sol --rpc-url robinhood_testnet --broadcast
contract Deploy is Script {
    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(pk);
        uint64 n = vm.getNonce(deployer);
        address predictedBounty = vm.computeCreateAddress(deployer, n + 2);

        vm.startBroadcast(pk);
        SP1Verifier verifier = new SP1Verifier();
        ModuleRegistry registry = new ModuleRegistry(predictedBounty);
        CreationBounty bounty = new CreationBounty(registry, deployer);
        UsageEscrow escrow = new UsageEscrow(registry, verifier, deployer);
        vm.stopBroadcast();

        require(address(bounty) == predictedBounty, "bounty address prediction failed");
        require(registry.bounty() == address(bounty), "registry not bound to bounty");
        require(escrow.verifierHash() == verifier.VERIFIER_HASH(), "verifier hash mismatch");

        string memory j = "deployment";
        vm.serializeString(j, "network", "robinhood-chain-testnet");
        vm.serializeUint(j, "chainId", block.chainid);
        vm.serializeUint(j, "deployedAtTimestamp", block.timestamp);
        vm.serializeUint(j, "deployedAtBlock", block.number);
        vm.serializeAddress(j, "deployer", deployer);
        vm.serializeUint(j, "firstNonce", n);
        vm.serializeAddress(j, "sp1VerifierGroth16", address(verifier));
        vm.serializeBytes32(j, "sp1VerifierCodeHash", address(verifier).codehash);
        vm.serializeBytes32(j, "sp1VerifierHash", verifier.VERIFIER_HASH());
        vm.serializeString(j, "sp1VerifierVersion", verifier.VERSION());
        vm.serializeAddress(j, "moduleRegistry", address(registry));
        vm.serializeBytes32(j, "moduleRegistryCodeHash", address(registry).codehash);
        vm.serializeAddress(j, "creationBounty", address(bounty));
        vm.serializeBytes32(j, "creationBountyCodeHash", address(bounty).codehash);
        vm.serializeBytes32(j, "creationBountyDomainSeparator", bounty.domainSeparator());
        vm.serializeAddress(j, "usageEscrow", address(escrow));
        vm.serializeBytes32(j, "usageEscrowCodeHash", address(escrow).codehash);
        vm.serializeAddress(j, "pauser", deployer);
        string memory out = vm.serializeString(
            j,
            "note",
            "testnet deployment; verifier is the unmodified sp1-contracts v6.1.0 SP1VerifierGroth16; source verification ids added after forge verify-contract"
        );
        string memory path = string.concat("deployments/", vm.toString(block.chainid), "-lemma.json");
        vm.writeJson(out, path);
        console.log("verifier", address(verifier));
        console.log("registry", address(registry));
        console.log("bounty", address(bounty));
        console.log("escrow", address(escrow));
        console.log("evidence", path);
    }
}
