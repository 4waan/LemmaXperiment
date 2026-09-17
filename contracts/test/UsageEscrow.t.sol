// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {ISP1VerifierWithHash} from "../src/sp1/ISP1Verifier.sol";
import {SP1Verifier} from "../src/sp1/v6.1.0/SP1VerifierGroth16.sol";
import {ModuleRegistry} from "../src/ModuleRegistry.sol";
import {CreationBounty} from "../src/CreationBounty.sol";
import {UsageEscrow} from "../src/UsageEscrow.sol";

/// Accepts every proof while `ok` is true. Only for the state-machine tests;
/// the binding checks run before the verifier is consulted, and the real
/// verifier is exercised in SP1Verifier.t.sol and test_realVerifierRejects*.
contract MockVerifier is ISP1VerifierWithHash {
    bool public ok = true;
    uint256 public calls;

    function setOk(bool v) external {
        ok = v;
    }

    function VERIFIER_HASH() external pure returns (bytes32) {
        return keccak256("mock");
    }

    function verifyProof(bytes32, bytes calldata, bytes calldata) external view {
        require(ok, "mock: invalid proof");
    }
}

contract UsageEscrowTest is Test {
    ModuleRegistry registry;
    CreationBounty bounty;
    MockVerifier mock;
    UsageEscrow escrow;

    uint256 evaluatorPk = 0xE1;
    address sponsor = address(0x5B);
    address creator = address(0xC1);
    address buyer = address(0xB0);
    address worker = address(0x60);
    address relayer = address(0x51);
    uint256 contributorFee = 0.002 ether;
    uint256 workerFee = 0.02 ether;
    bytes32 versionId;
    UsageEscrow.Statement statement;
    uint64 proveBy;

    function setUp() public {
        vm.warp(1_790_000_000);
        address predicted = vm.computeCreateAddress(address(this), vm.getNonce(address(this)) + 1);
        registry = new ModuleRegistry(predicted);
        bounty = new CreationBounty(registry, sponsor);
        mock = new MockVerifier();
        escrow = new UsageEscrow(registry, mock, sponsor);
        vm.deal(sponsor, 1 ether);
        vm.deal(buyer, 1 ether);
        versionId = acceptVersion(keccak256("guest"));
        statement = UsageEscrow.Statement({
            blockNumber: 20600928,
            blockHash: keccak256("blockHash"),
            parentStateRoot: keccak256("parent"),
            expectedStateRoot: keccak256("post")
        });
        proveBy = uint64(block.timestamp + 1 days);
    }

    /// Runs one demand through the bounty so the registry holds a version.
    function acceptVersion(bytes32 guestKey) internal returns (bytes32) {
        uint64 submitBy = uint64(block.timestamp + 1 days);
        vm.prank(sponsor);
        bytes32 id = bounty.fundDemand{value: 0.05 ether}(
            keccak256("spec"), keccak256("policy"), keccak256("holdout"), vm.addr(evaluatorPk),
            creator, contributorFee, submitBy, submitBy + 1 days
        );
        vm.prank(creator);
        bounty.submitCandidate(id, keccak256("commit"), keccak256(abi.encode(guestKey)));
        CreationBounty.VerdictMessage memory m = CreationBounty.VerdictMessage({
            demandId: id,
            candidateDigest: keccak256(abi.encode(guestKey)),
            policyHash: keccak256("policy"),
            reportHash: keccak256("report"),
            guestKey: guestKey,
            recipient: creator,
            verdict: 1,
            validUntil: uint64(block.timestamp + 1 days),
            nonce: uint256(guestKey)
        });
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(evaluatorPk, bounty.hashVerdict(m));
        bounty.decide(id, m, abi.encodePacked(r, s, v));
        return bounty.getDemand(id).versionId;
    }

    function fund() internal returns (bytes32 jobId) {
        vm.prank(buyer);
        jobId = escrow.fundJob{value: workerFee + contributorFee}(
            versionId, worker, workerFee, statement, proveBy
        );
    }

    function goodValues(bytes32 jobId) internal view returns (bytes memory) {
        return escrow.expectedPublicValues(jobId, statement.expectedStateRoot);
    }

    function mutate(bytes memory pv, uint256 word) internal pure returns (bytes memory out) {
        out = new bytes(pv.length);
        for (uint256 i = 0; i < pv.length; i++) {
            out[i] = pv[i];
        }
        uint256 k = word * 32 + 31;
        out[k] = bytes1(uint8(out[k]) ^ 0x01);
    }

    // -------------------------------------------------------------- funding

    function test_fundSnapshotsTerms() public {
        bytes32 jobId = fund();
        UsageEscrow.Job memory j = escrow.getJob(jobId);
        assertEq(uint8(j.state), uint8(UsageEscrow.State.Funded));
        assertEq(j.buyer, buyer);
        assertEq(j.versionId, versionId);
        assertEq(j.guestKey, keccak256("guest"));
        assertEq(j.verifier, address(mock));
        assertEq(j.verifierHash, keccak256("mock"));
        assertEq(j.worker, worker);
        assertEq(j.contributor, creator);
        assertEq(j.workerFee, workerFee);
        assertEq(j.contributorFee, contributorFee);
        assertEq(j.statement.blockNumber, 20600928);
        assertEq(j.proveBy, proveBy);
        assertEq(escrow.activeEscrow(), workerFee + contributorFee);
        assertTrue(escrow.solvent());
    }

    function test_fundRequiresExactValueAndKnownVersion() public {
        vm.startPrank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(
                UsageEscrow.WrongValue.selector, workerFee + contributorFee, workerFee
            )
        );
        escrow.fundJob{value: workerFee}(versionId, worker, workerFee, statement, proveBy);
        vm.expectRevert(
            abi.encodeWithSelector(ModuleRegistry.UnknownVersion.selector, keccak256("nope"))
        );
        escrow.fundJob{value: workerFee}(keccak256("nope"), worker, workerFee, statement, proveBy);
        vm.expectRevert(abi.encodeWithSelector(UsageEscrow.BadDeadline.selector, uint64(block.timestamp)));
        escrow.fundJob{value: workerFee + contributorFee}(
            versionId, worker, workerFee, statement, uint64(block.timestamp)
        );
        vm.stopPrank();
    }

    // ----------------------------------------------------------- settlement

    function test_settleOncePaysStoredPayees() public {
        bytes32 jobId = fund();
        bytes memory pv = goodValues(jobId);
        vm.prank(relayer);
        escrow.submitProof(jobId, pv, hex"00");
        UsageEscrow.Job memory j = escrow.getJob(jobId);
        assertEq(uint8(j.state), uint8(UsageEscrow.State.Settled));
        assertEq(j.settledBy, relayer);
        assertEq(escrow.credit(worker), workerFee);
        assertEq(escrow.credit(creator), contributorFee);
        assertEq(escrow.credit(relayer), 0);
        assertEq(escrow.activeEscrow(), 0);
        assertTrue(escrow.solvent());
        vm.expectRevert(
            abi.encodeWithSelector(UsageEscrow.WrongState.selector, UsageEscrow.State.Settled)
        );
        escrow.submitProof(jobId, pv, hex"00");
        vm.prank(worker);
        escrow.withdraw();
        assertEq(worker.balance, workerFee);
    }

    function test_everyPublicValueFieldIsChecked() public {
        bytes32 jobId = fund();
        bytes memory pv = goodValues(jobId);
        string[9] memory fields = [
            "settlementChainId",
            "marketAddress",
            "jobId",
            "sourceDomain",
            "blockNumber",
            "blockHash",
            "parentStateRoot",
            "computedStateRoot",
            "success"
        ];
        for (uint256 w = 0; w < 9; w++) {
            bytes memory bad = mutate(pv, w);
            vm.expectRevert(
                abi.encodeWithSelector(UsageEscrow.PublicValueMismatch.selector, fields[w])
            );
            escrow.submitProof(jobId, bad, hex"00");
        }
    }

    function test_wrongLengthRejected() public {
        bytes32 jobId = fund();
        bytes memory pv = goodValues(jobId);
        bytes memory shorter = new bytes(287);
        for (uint256 i = 0; i < 287; i++) {
            shorter[i] = pv[i];
        }
        vm.expectRevert(abi.encodeWithSelector(UsageEscrow.BadPublicValuesLength.selector, 287));
        escrow.submitProof(jobId, shorter, hex"00");
    }

    function test_wrongChainIdRejected() public {
        bytes32 jobId = fund();
        bytes memory pv = goodValues(jobId);
        vm.chainId(421614);
        vm.expectRevert(
            abi.encodeWithSelector(UsageEscrow.PublicValueMismatch.selector, "settlementChainId")
        );
        escrow.submitProof(jobId, pv, hex"00");
    }

    function test_invalidProofRejectedAndCreditsUnchanged() public {
        bytes32 jobId = fund();
        bytes memory pv = goodValues(jobId);
        mock.setOk(false);
        vm.expectRevert("mock: invalid proof");
        escrow.submitProof(jobId, pv, hex"00");
        assertEq(escrow.credit(worker), 0);
        assertEq(uint8(escrow.getJob(jobId).state), uint8(UsageEscrow.State.Funded));
    }

    function test_boundaryAtDeadlineSettlesAfterRefunds() public {
        bytes32 jobId = fund();
        bytes32 second = fund();
        bytes memory pv = goodValues(jobId);
        vm.warp(proveBy);
        vm.expectRevert(UsageEscrow.NotYetExpired.selector);
        escrow.expireJob(jobId);
        escrow.submitProof(jobId, pv, hex"00");

        bytes memory pv2 = goodValues(second);
        vm.warp(proveBy + 1);
        vm.expectRevert(abi.encodeWithSelector(UsageEscrow.PastDeadline.selector, proveBy));
        escrow.submitProof(second, pv2, hex"00");
        escrow.expireJob(second);
        assertEq(escrow.credit(buyer), workerFee + contributorFee);
        assertTrue(escrow.solvent());
    }

    function test_pausePreservesRefundAndSettlement() public {
        bytes32 a = fund();
        bytes32 b = fund();
        vm.prank(sponsor);
        escrow.setFundingPaused(true);
        vm.prank(buyer);
        vm.expectRevert(UsageEscrow.FundingIsPaused.selector);
        escrow.fundJob{value: workerFee + contributorFee}(
            versionId, worker, workerFee, statement, proveBy
        );
        escrow.submitProof(a, goodValues(a), hex"00");
        vm.warp(proveBy + 1);
        escrow.expireJob(b);
        assertEq(escrow.credit(worker), workerFee);
        assertEq(escrow.credit(buyer), workerFee + contributorFee);
    }

    function test_realVerifierRejectsForeignProof() public {
        // A job bound to the real v6.1.0 verifier and the real baseline guest
        // key: the step 1 proof of block 20600066 committed a block header,
        // not these public values, so it cannot settle anything here.
        SP1Verifier real = new SP1Verifier();
        UsageEscrow realEscrow = new UsageEscrow(registry, real, sponsor);
        assertEq(bytes4(realEscrow.verifierHash()), bytes4(0x4388a21c));
        bytes32 vkey = vm.parseBytes32(vm.trim(vm.readFile("test/fixtures/block-20600066.vkey.txt")));
        bytes32 v2 = acceptVersion(vkey);
        vm.prank(buyer);
        bytes32 jobId = realEscrow.fundJob{value: workerFee + contributorFee}(
            v2, worker, workerFee, statement, proveBy
        );
        bytes memory proof = vm.parseBytes(
            string.concat("0x", vm.trim(vm.readFile("test/fixtures/block-20600066.proof.hex")))
        );
        bytes memory pv = realEscrow.expectedPublicValues(jobId, statement.expectedStateRoot);
        vm.expectRevert(bytes4(keccak256("ProofInvalid()")));
        realEscrow.submitProof(jobId, pv, proof);
        assertEq(uint8(realEscrow.getJob(jobId).state), uint8(UsageEscrow.State.Funded));
    }
}
