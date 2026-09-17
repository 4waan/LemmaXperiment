// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {CreationBounty} from "../src/CreationBounty.sol";
import {ModuleRegistry} from "../src/ModuleRegistry.sol";

/// I-S1: balance >= activeEscrow + totalCredit after every state change, over
/// random sequences of fund, submit, decide, decline, expire and withdraw.
contract BountyHandler is Test {
    CreationBounty public bounty;
    uint256 evaluatorPk = 0xE1;
    address[] public actors;
    bytes32[] public demands;
    uint256 nonce = 1;

    constructor(CreationBounty b) {
        bounty = b;
        actors.push(address(0xA1));
        actors.push(address(0xA2));
        actors.push(address(0xA3));
        for (uint256 i = 0; i < actors.length; i++) {
            vm.deal(actors[i], 100 ether);
        }
    }

    function fund(uint256 who, uint96 amount, uint32 dt1, uint32 dt2) external {
        amount = uint96(bound(amount, 1, 1 ether));
        uint64 submitBy = uint64(block.timestamp + 1 + (dt1 % 10 days));
        uint64 evaluateBy = uint64(submitBy + 1 + (dt2 % 10 days));
        vm.prank(actors[who % actors.length]);
        demands.push(_fund(amount, actors[(who + 1) % actors.length], submitBy, evaluateBy));
        nonce++;
    }

    function _fund(uint96 amount, address payee, uint64 submitBy, uint64 evaluateBy)
        internal
        returns (bytes32)
    {
        return bounty.fundDemand{value: amount}(
            keccak256(abi.encode(nonce)),
            keccak256("policy"),
            keccak256("holdout"),
            vm.addr(evaluatorPk),
            payee,
            0.001 ether,
            submitBy,
            evaluateBy
        );
    }

    function submit(uint256 which) external {
        if (demands.length == 0) return;
        bytes32 id = demands[which % demands.length];
        CreationBounty.Demand memory d = bounty.getDemand(id);
        vm.prank(d.creatorPayee);
        try bounty.submitCandidate(id, keccak256("c"), keccak256(abi.encode(id))) {} catch {}
    }

    function decide(uint256 which, uint8 verdict) external {
        if (demands.length == 0) return;
        bytes32 id = demands[which % demands.length];
        CreationBounty.Demand memory d = bounty.getDemand(id);
        CreationBounty.VerdictMessage memory m = CreationBounty.VerdictMessage({
            demandId: id,
            candidateDigest: keccak256(abi.encode(id)),
            policyHash: keccak256("policy"),
            reportHash: keccak256("report"),
            guestKey: keccak256("guest"),
            recipient: d.creatorPayee,
            verdict: uint8(1 + (verdict % 3)),
            validUntil: uint64(block.timestamp + 1 days),
            nonce: nonce++
        });
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(evaluatorPk, bounty.hashVerdict(m));
        try bounty.decide(id, m, abi.encodePacked(r, s, v)) {} catch {}
    }

    function decline(uint256 which) external {
        if (demands.length == 0) return;
        bytes32 id = demands[which % demands.length];
        vm.prank(bounty.getDemand(id).creatorPayee);
        try bounty.decline(id) {} catch {}
    }

    function expire(uint256 which) external {
        if (demands.length == 0) return;
        try bounty.expire(demands[which % demands.length]) {} catch {}
    }

    function warp(uint32 dt) external {
        vm.warp(block.timestamp + (dt % 12 days));
    }

    function withdraw(uint256 who) external {
        vm.prank(actors[who % actors.length]);
        try bounty.withdraw() {} catch {}
    }
}

contract SolvencyInvariant is Test {
    CreationBounty bounty;
    BountyHandler handler;

    function setUp() public {
        vm.warp(1_790_000_000);
        address predicted = vm.computeCreateAddress(address(this), vm.getNonce(address(this)) + 1);
        ModuleRegistry registry = new ModuleRegistry(predicted);
        bounty = new CreationBounty(registry, address(this));
        handler = new BountyHandler(bounty);
        targetContract(address(handler));
    }

    function invariant_solvent() public view {
        assertTrue(bounty.solvent());
        assertEq(address(bounty).balance, bounty.activeEscrow() + bounty.totalCredit());
    }
}
