// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {CreationBounty} from "../src/CreationBounty.sol";
import {ModuleRegistry} from "../src/ModuleRegistry.sol";

contract Reenterer {
    CreationBounty bounty;
    uint256 public calls;

    constructor(CreationBounty b) {
        bounty = b;
    }

    receive() external payable {
        calls++;
        if (calls < 3) bounty.withdraw();
    }
}

contract CreationBountyTest is Test {
    ModuleRegistry registry;
    CreationBounty bounty;

    uint256 evaluatorPk = 0xE1;
    address evaluator;
    address sponsor = address(0x5B);
    address creator = address(0xC1);
    address stranger = address(0x51);

    bytes32 specHash = keccak256("spec");
    bytes32 policyHash = keccak256("policy");
    bytes32 holdout = keccak256("holdout");
    uint256 bountyAmount = 0.05 ether;
    uint256 contributorFee = 0.002 ether;
    uint64 submitBy;
    uint64 evaluateBy;

    function setUp() public {
        evaluator = vm.addr(evaluatorPk);
        address deployer = address(this);
        address predicted = vm.computeCreateAddress(deployer, vm.getNonce(deployer) + 1);
        registry = new ModuleRegistry(predicted);
        bounty = new CreationBounty(registry, sponsor);
        assertEq(address(bounty), predicted);
        vm.deal(sponsor, 1 ether);
        vm.warp(1_790_000_000);
        submitBy = uint64(block.timestamp + 4 days);
        evaluateBy = uint64(submitBy + 5 days);
    }

    function fund() internal returns (bytes32 id) {
        vm.prank(sponsor);
        id = bounty.fundDemand{value: bountyAmount}(
            specHash, policyHash, holdout, evaluator, creator, contributorFee, submitBy, evaluateBy
        );
    }

    function submit(bytes32 id) internal {
        vm.prank(creator);
        bounty.submitCandidate(id, keccak256("commit"), keccak256("digest"));
    }

    function message(bytes32 id, uint8 verdict, uint256 nonce)
        internal
        view
        returns (CreationBounty.VerdictMessage memory m)
    {
        m = CreationBounty.VerdictMessage({
            demandId: id,
            candidateDigest: keccak256("digest"),
            policyHash: policyHash,
            reportHash: keccak256("report"),
            guestKey: keccak256("guest"),
            recipient: creator,
            verdict: verdict,
            validUntil: uint64(block.timestamp + 7 days),
            nonce: nonce
        });
    }

    function sign(uint256 pk, CreationBounty.VerdictMessage memory m)
        internal
        view
        returns (bytes memory)
    {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, bounty.hashVerdict(m));
        return abi.encodePacked(r, s, v);
    }

    // ------------------------------------------------------------- funding

    function test_fundFreezesTerms() public {
        bytes32 id = fund();
        CreationBounty.Demand memory d = bounty.getDemand(id);
        assertEq(uint8(d.state), uint8(CreationBounty.State.Funded));
        assertEq(d.sponsor, sponsor);
        assertEq(d.creatorPayee, creator);
        assertEq(d.evaluatorSigner, evaluator);
        assertEq(d.specHash, specHash);
        assertEq(d.policyHash, policyHash);
        assertEq(d.holdoutCommitment, holdout);
        assertEq(d.bounty, bountyAmount);
        assertEq(d.contributorFee, contributorFee);
        assertEq(d.submitBy, submitBy);
        assertEq(d.evaluateBy, evaluateBy);
        assertEq(bounty.activeEscrow(), bountyAmount);
        assertTrue(bounty.solvent());
    }

    function test_fundRejectsBadDeadlines() public {
        vm.startPrank(sponsor);
        vm.expectRevert(
            abi.encodeWithSelector(CreationBounty.BadDeadlines.selector, submitBy, submitBy)
        );
        bounty.fundDemand{value: 1}(
            specHash, policyHash, holdout, evaluator, creator, contributorFee, submitBy, submitBy
        );
        uint64 past = uint64(block.timestamp);
        vm.expectRevert(
            abi.encodeWithSelector(CreationBounty.BadDeadlines.selector, past, evaluateBy)
        );
        bounty.fundDemand{value: 1}(
            specHash, policyHash, holdout, evaluator, creator, contributorFee, past, evaluateBy
        );
        vm.expectRevert(CreationBounty.ZeroBounty.selector);
        bounty.fundDemand(
            specHash, policyHash, holdout, evaluator, creator, contributorFee, submitBy, evaluateBy
        );
        vm.stopPrank();
    }

    function test_pauseBlocksOnlyFunding() public {
        bytes32 id = fund();
        vm.prank(sponsor);
        bounty.setFundingPaused(true);
        vm.prank(sponsor);
        vm.expectRevert(CreationBounty.FundingIsPaused.selector);
        bounty.fundDemand{value: 1}(
            specHash, policyHash, holdout, evaluator, creator, contributorFee, submitBy, evaluateBy
        );
        // existing demand still moves and refunds
        submit(id);
        vm.warp(evaluateBy + 1);
        bounty.expire(id);
        assertEq(bounty.credit(sponsor), bountyAmount);
        vm.prank(stranger);
        vm.expectRevert(CreationBounty.NotPauser.selector);
        bounty.setFundingPaused(false);
    }

    // ------------------------------------------------------------ submission

    function test_submitAtDeadlineOnlyByCreator() public {
        bytes32 id = fund();
        vm.prank(stranger);
        vm.expectRevert(CreationBounty.NotCreator.selector);
        bounty.submitCandidate(id, keccak256("c"), keccak256("d"));
        vm.warp(submitBy);
        submit(id);
        CreationBounty.Demand memory d = bounty.getDemand(id);
        assertEq(uint8(d.state), uint8(CreationBounty.State.Submitted));
        assertEq(d.candidateDigest, keccak256("digest"));
        vm.prank(creator);
        vm.expectRevert(
            abi.encodeWithSelector(
                CreationBounty.WrongState.selector, CreationBounty.State.Submitted
            )
        );
        bounty.submitCandidate(id, keccak256("c2"), keccak256("d2"));
    }

    function test_submitAfterDeadlineReverts() public {
        bytes32 id = fund();
        vm.warp(submitBy + 1);
        vm.prank(creator);
        vm.expectRevert(abi.encodeWithSelector(CreationBounty.PastDeadline.selector, submitBy));
        bounty.submitCandidate(id, keccak256("c"), keccak256("d"));
        bounty.expire(id);
        assertEq(bounty.credit(sponsor), bountyAmount);
    }

    function test_declineRefundsSponsor() public {
        bytes32 id = fund();
        vm.prank(creator);
        bounty.decline(id);
        assertEq(uint8(bounty.getDemand(id).state), uint8(CreationBounty.State.Declined));
        assertEq(bounty.credit(sponsor), bountyAmount);
        assertEq(bounty.activeEscrow(), 0);
    }

    // -------------------------------------------------------------- verdicts

    function test_passRegistersAndCreditsAtomically() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        bytes memory sig = sign(evaluatorPk, m);
        assertEq(registry.count(), 0);
        vm.prank(stranger); // any relayer
        bounty.decide(id, m, sig);
        CreationBounty.Demand memory d = bounty.getDemand(id);
        assertEq(uint8(d.state), uint8(CreationBounty.State.Accepted));
        assertEq(registry.count(), 1);
        ModuleRegistry.Version memory v = registry.getVersion(d.versionId);
        assertEq(v.guestKey, keccak256("guest"));
        assertEq(v.contributor, creator);
        assertEq(v.contributorFee, contributorFee);
        assertEq(v.reportHash, keccak256("report"));
        assertEq(bounty.credit(creator), bountyAmount);
        assertEq(bounty.credit(sponsor), 0);
        assertEq(bounty.activeEscrow(), 0);
        assertTrue(bounty.solvent());
        // the creator withdraws
        vm.prank(creator);
        bounty.withdraw();
        assertEq(creator.balance, bountyAmount);
        assertEq(bounty.totalCredit(), 0);
    }

    function test_failAndInconclusiveCreditSponsor() public {
        for (uint8 verdict = 2; verdict <= 3; verdict++) {
            bytes32 id = fund();
            submit(id);
            CreationBounty.VerdictMessage memory m = message(id, verdict, verdict);
            bounty.decide(id, m, sign(evaluatorPk, m));
            CreationBounty.Demand memory d = bounty.getDemand(id);
            assertEq(uint8(d.state), uint8(CreationBounty.State.Rejected));
            assertEq(uint8(d.verdict), verdict);
        }
        assertEq(registry.count(), 0);
        assertEq(bounty.credit(sponsor), 2 * bountyAmount);
    }

    function test_badVerdictValues() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 0, 1);
        bytes memory sig = sign(evaluatorPk, m);
        vm.expectRevert(abi.encodeWithSelector(CreationBounty.BadVerdict.selector, 0));
        bounty.decide(id, m, sig);
        m = message(id, 4, 1);
        sig = sign(evaluatorPk, m);
        vm.expectRevert(abi.encodeWithSelector(CreationBounty.BadVerdict.selector, 4));
        bounty.decide(id, m, sig);
    }

    function test_wrongSignerRejected() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        bytes memory sig = sign(0xBAD, m);
        vm.expectRevert(
            abi.encodeWithSelector(CreationBounty.NotEvaluator.selector, vm.addr(0xBAD))
        );
        bounty.decide(id, m, sig);
    }

    function test_replayAcrossDemandsRejected() public {
        bytes32 a = fund();
        bytes32 b = fund();
        submit(a);
        submit(b);
        CreationBounty.VerdictMessage memory m = message(a, 1, 1);
        bytes memory sig = sign(evaluatorPk, m);
        vm.expectRevert(CreationBounty.VerdictMismatch.selector);
        bounty.decide(b, m, sig);
        bounty.decide(a, m, sig);
        // the same nonce cannot serve a second demand even with matching fields
        CreationBounty.VerdictMessage memory m2 = message(b, 1, 1);
        bytes memory sig2 = sign(evaluatorPk, m2);
        vm.expectRevert(abi.encodeWithSelector(CreationBounty.NonceUsed.selector, 1));
        bounty.decide(b, m2, sig2);
    }

    function test_replayAcrossContractsRejected() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        // signature made for another deployment's domain
        address predicted = vm.computeCreateAddress(address(this), vm.getNonce(address(this)) + 1);
        ModuleRegistry r2 = new ModuleRegistry(predicted);
        CreationBounty other = new CreationBounty(r2, sponsor);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(evaluatorPk, other.hashVerdict(m));
        bytes memory sig = abi.encodePacked(r, s, v);
        vm.expectRevert(); // NotEvaluator(some other address)
        bounty.decide(id, m, sig);
    }

    function test_replayAcrossChainsRejected() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        bytes memory sig = sign(evaluatorPk, m);
        vm.chainId(421614);
        vm.expectRevert();
        bounty.decide(id, m, sig);
        vm.chainId(31337);
        bounty.decide(id, m, sig);
    }

    function test_expiredVerdictRejected() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        m.validUntil = uint64(block.timestamp + 1);
        bytes memory sig = sign(evaluatorPk, m);
        vm.warp(block.timestamp + 2);
        vm.expectRevert(
            abi.encodeWithSelector(CreationBounty.VerdictExpired.selector, m.validUntil)
        );
        bounty.decide(id, m, sig);
    }

    function test_decideAfterEvaluateByRejectedThenExpires() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        m.validUntil = uint64(evaluateBy + 30 days);
        bytes memory sig = sign(evaluatorPk, m);
        vm.warp(evaluateBy + 1);
        vm.expectRevert(abi.encodeWithSelector(CreationBounty.PastDeadline.selector, evaluateBy));
        bounty.decide(id, m, sig);
        bounty.expire(id);
        assertEq(bounty.credit(sponsor), bountyAmount);
        assertEq(registry.count(), 0);
    }

    function test_decideAtEvaluateByWorks() public {
        bytes32 id = fund();
        submit(id);
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        m.validUntil = uint64(evaluateBy + 1 days);
        bytes memory sig = sign(evaluatorPk, m);
        vm.warp(evaluateBy);
        bounty.decide(id, m, sig);
        assertEq(registry.count(), 1);
    }

    function test_expireBeforeDeadlinesReverts() public {
        bytes32 id = fund();
        vm.expectRevert(CreationBounty.NotYetExpired.selector);
        bounty.expire(id);
        vm.warp(submitBy);
        submit(id);
        vm.warp(evaluateBy);
        vm.expectRevert(CreationBounty.NotYetExpired.selector);
        bounty.expire(id);
    }

    function test_registryRejectsDirectRegistration() public {
        ModuleRegistry.Version memory v;
        v.demandId = keccak256("x");
        vm.expectRevert(ModuleRegistry.OnlyBounty.selector);
        registry.register(v);
    }

    function test_withdrawIsReentrancySafe() public {
        Reenterer payee = new Reenterer(bounty);
        vm.prank(sponsor);
        bytes32 id = bounty.fundDemand{value: bountyAmount}(
            specHash, policyHash, holdout, evaluator, address(payee), contributorFee, submitBy,
            evaluateBy
        );
        vm.prank(address(payee));
        bounty.submitCandidate(id, keccak256("c"), keccak256("digest"));
        CreationBounty.VerdictMessage memory m = message(id, 1, 1);
        m.recipient = address(payee);
        bounty.decide(id, m, sign(evaluatorPk, m));
        vm.prank(address(payee));
        vm.expectRevert(CreationBounty.WithdrawFailed.selector);
        bounty.withdraw();
        // credit intact after the failed reentrant attempt
        assertEq(bounty.credit(address(payee)), bountyAmount);
        assertTrue(bounty.solvent());
    }

    function test_withdrawNothingReverts() public {
        vm.expectRevert(CreationBounty.NothingToWithdraw.selector);
        bounty.withdraw();
    }
}
