// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ModuleRegistry} from "./ModuleRegistry.sol";

/// @title CreationBounty
/// @notice Escrows a creation bounty for one frozen demand and releases it on
/// the evaluator's signed verdict (EXPERIMENT.md section 9).
///
///   FUNDED -> SUBMITTED -> ACCEPTED (Pass: registers the version and credits the creator)
///      |          |
///      |          +-> REJECTED (Fail or Inconclusive: credits the sponsor)
///      +----------+-> EXPIRED  (no submission by submitBy, or no decision by evaluateBy)
///      +-> DECLINED (the creator declines; credits the sponsor)
///
/// Funding fixes the spec hash, policy hash, holdout commitment, evaluator,
/// creator payee, amount and both deadlines (I-S6, I-S10). The verdict is an
/// EIP-712 message bound to this chain and contract with a nonce and validUntil
/// (I-S9). Every payout is a pull withdrawal (I-S12). The contract stays
/// solvent by construction (I-S1): balance >= activeEscrow + totalCredit.
contract CreationBounty {
    enum State {
        None,
        Funded,
        Submitted,
        Accepted,
        Rejected,
        Expired,
        Declined
    }

    enum Verdict {
        None,
        Pass,
        Fail,
        Inconclusive
    }

    struct Demand {
        address sponsor;
        address creatorPayee;
        address evaluatorSigner;
        bytes32 specHash;
        bytes32 policyHash;
        bytes32 holdoutCommitment;
        uint256 bounty;
        uint256 contributorFee;
        uint64 submitBy;
        uint64 evaluateBy;
        State state;
        bytes32 sourceCommit;
        bytes32 candidateDigest;
        uint64 submittedAt;
        Verdict verdict;
        bytes32 reportHash;
        bytes32 guestKey;
        bytes32 versionId;
        uint64 decidedAt;
    }

    /// @notice The evaluator's signed message. chainId and the contract address
    /// live in the EIP-712 domain separator, so the same signature cannot be
    /// replayed on another chain or contract.
    struct VerdictMessage {
        bytes32 demandId;
        bytes32 candidateDigest;
        bytes32 policyHash;
        bytes32 reportHash;
        bytes32 guestKey;
        address recipient;
        uint8 verdict;
        uint64 validUntil;
        uint256 nonce;
    }

    bytes32 public constant VERDICT_TYPEHASH = keccak256(
        "Verdict(bytes32 demandId,bytes32 candidateDigest,bytes32 policyHash,bytes32 reportHash,bytes32 guestKey,address recipient,uint8 verdict,uint64 validUntil,uint256 nonce)"
    );
    bytes32 private constant _DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    uint256 private constant _SECP256K1N_HALF =
        0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    ModuleRegistry public immutable registry;
    address public immutable pauser;
    bool public fundingPaused;

    uint256 public activeEscrow;
    uint256 public totalCredit;
    mapping(address => uint256) public credit;
    mapping(bytes32 => Demand) private _demands;
    mapping(address => mapping(uint256 => bool)) public nonceUsed;
    uint256 private _demandCount;
    uint256 private _entered;

    event DemandFunded(
        bytes32 indexed demandId,
        address indexed sponsor,
        address indexed creatorPayee,
        address evaluatorSigner,
        bytes32 specHash,
        bytes32 policyHash,
        bytes32 holdoutCommitment,
        uint256 bounty,
        uint256 contributorFee,
        uint64 submitBy,
        uint64 evaluateBy
    );
    event CandidateSubmitted(bytes32 indexed demandId, bytes32 sourceCommit, bytes32 candidateDigest);
    event DemandDecided(
        bytes32 indexed demandId, Verdict verdict, bytes32 reportHash, bytes32 guestKey, bytes32 versionId
    );
    event DemandDeclined(bytes32 indexed demandId);
    event DemandExpired(bytes32 indexed demandId, State from);
    event Withdrawn(address indexed payee, uint256 amount);
    event FundingPaused(bool paused);

    error FundingIsPaused();
    error ZeroBounty();
    error ZeroAddress();
    error BadDeadlines(uint64 submitBy, uint64 evaluateBy);
    error WrongState(State state);
    error NotCreator();
    error NotPauser();
    error PastDeadline(uint64 deadline);
    error NotYetExpired();
    error VerdictMismatch();
    error VerdictExpired(uint64 validUntil);
    error NonceUsed(uint256 nonce);
    error BadSignature();
    error NotEvaluator(address recovered);
    error BadVerdict(uint8 verdict);
    error Reentrancy();
    error NothingToWithdraw();
    error WithdrawFailed();

    modifier nonReentrant() {
        if (_entered == 1) revert Reentrancy();
        _entered = 1;
        _;
        _entered = 0;
    }

    constructor(ModuleRegistry registry_, address pauser_) {
        if (address(registry_) == address(0) || pauser_ == address(0)) revert ZeroAddress();
        registry = registry_;
        pauser = pauser_;
    }

    // ---------------------------------------------------------------- funding

    /// @notice Escrows the bounty and freezes the demand's terms.
    function fundDemand(
        bytes32 specHash,
        bytes32 policyHash,
        bytes32 holdoutCommitment,
        address evaluatorSigner,
        address creatorPayee,
        uint256 contributorFee,
        uint64 submitBy,
        uint64 evaluateBy
    ) external payable returns (bytes32 demandId) {
        if (fundingPaused) revert FundingIsPaused();
        if (msg.value == 0) revert ZeroBounty();
        if (evaluatorSigner == address(0) || creatorPayee == address(0)) revert ZeroAddress();
        if (submitBy <= block.timestamp || evaluateBy <= submitBy) {
            revert BadDeadlines(submitBy, evaluateBy);
        }
        demandId = keccak256(
            abi.encode(
                "lemma.demand.v1", block.chainid, address(this), msg.sender, specHash, _demandCount++
            )
        );
        Demand storage d = _demands[demandId];
        d.sponsor = msg.sender;
        d.creatorPayee = creatorPayee;
        d.evaluatorSigner = evaluatorSigner;
        d.specHash = specHash;
        d.policyHash = policyHash;
        d.holdoutCommitment = holdoutCommitment;
        d.bounty = msg.value;
        d.contributorFee = contributorFee;
        d.submitBy = submitBy;
        d.evaluateBy = evaluateBy;
        d.state = State.Funded;
        activeEscrow += msg.value;
        emit DemandFunded(
            demandId,
            msg.sender,
            creatorPayee,
            evaluatorSigner,
            specHash,
            policyHash,
            holdoutCommitment,
            msg.value,
            contributorFee,
            submitBy,
            evaluateBy
        );
    }

    // -------------------------------------------------------------- creator

    /// @notice One submission, by the assigned creator payee, at or before submitBy.
    function submitCandidate(bytes32 demandId, bytes32 sourceCommit, bytes32 candidateDigest)
        external
    {
        Demand storage d = _demands[demandId];
        if (d.state != State.Funded) revert WrongState(d.state);
        if (msg.sender != d.creatorPayee) revert NotCreator();
        if (block.timestamp > d.submitBy) revert PastDeadline(d.submitBy);
        d.state = State.Submitted;
        d.sourceCommit = sourceCommit;
        d.candidateDigest = candidateDigest;
        d.submittedAt = uint64(block.timestamp);
        emit CandidateSubmitted(demandId, sourceCommit, candidateDigest);
    }

    /// @notice The creator declines the demand; the sponsor is credited.
    function decline(bytes32 demandId) external {
        Demand storage d = _demands[demandId];
        if (d.state != State.Funded) revert WrongState(d.state);
        if (msg.sender != d.creatorPayee) revert NotCreator();
        d.state = State.Declined;
        _release(d.sponsor, d.bounty);
        emit DemandDeclined(demandId);
    }

    // ------------------------------------------------------------ evaluator

    /// @notice Applies the evaluator's signed verdict. Anyone may relay it; the
    /// signature carries the authority. Pass registers the version and credits
    /// the creator in this transaction (I-S11). Fail and Inconclusive credit
    /// the sponsor.
    function decide(bytes32 demandId, VerdictMessage calldata m, bytes calldata signature)
        external
    {
        Demand storage d = _demands[demandId];
        if (d.state != State.Submitted) revert WrongState(d.state);
        if (block.timestamp > d.evaluateBy) revert PastDeadline(d.evaluateBy);
        if (
            m.demandId != demandId || m.candidateDigest != d.candidateDigest
                || m.policyHash != d.policyHash || m.recipient != d.creatorPayee
        ) revert VerdictMismatch();
        if (block.timestamp > m.validUntil) revert VerdictExpired(m.validUntil);
        if (m.verdict == 0 || m.verdict > uint8(Verdict.Inconclusive)) revert BadVerdict(m.verdict);
        if (nonceUsed[d.evaluatorSigner][m.nonce]) revert NonceUsed(m.nonce);
        address recovered = _recover(hashVerdict(m), signature);
        if (recovered != d.evaluatorSigner) revert NotEvaluator(recovered);
        nonceUsed[d.evaluatorSigner][m.nonce] = true;

        d.verdict = Verdict(m.verdict);
        d.reportHash = m.reportHash;
        d.guestKey = m.guestKey;
        d.decidedAt = uint64(block.timestamp);
        if (m.verdict == uint8(Verdict.Pass)) {
            d.state = State.Accepted;
            d.versionId = registry.register(
                ModuleRegistry.Version({
                    demandId: demandId,
                    candidateDigest: d.candidateDigest,
                    sourceCommit: d.sourceCommit,
                    guestKey: m.guestKey,
                    policyHash: d.policyHash,
                    reportHash: m.reportHash,
                    contributor: d.creatorPayee,
                    contributorFee: d.contributorFee,
                    registeredAt: 0
                })
            );
            _release(d.creatorPayee, d.bounty);
        } else {
            d.state = State.Rejected;
            _release(d.sponsor, d.bounty);
        }
        emit DemandDecided(demandId, d.verdict, m.reportHash, m.guestKey, d.versionId);
    }

    // --------------------------------------------------------------- expiry

    /// @notice After submitBy without a submission, or after evaluateBy
    /// without a decision, the sponsor is credited. Anyone may call.
    function expire(bytes32 demandId) external {
        Demand storage d = _demands[demandId];
        State from = d.state;
        if (from == State.Funded) {
            if (block.timestamp <= d.submitBy) revert NotYetExpired();
        } else if (from == State.Submitted) {
            if (block.timestamp <= d.evaluateBy) revert NotYetExpired();
        } else {
            revert WrongState(from);
        }
        d.state = State.Expired;
        _release(d.sponsor, d.bounty);
        emit DemandExpired(demandId, from);
    }

    // ------------------------------------------------------------- payouts

    function withdraw() external nonReentrant {
        uint256 amount = credit[msg.sender];
        if (amount == 0) revert NothingToWithdraw();
        credit[msg.sender] = 0;
        totalCredit -= amount;
        (bool ok,) = msg.sender.call{value: amount}("");
        if (!ok) revert WithdrawFailed();
        emit Withdrawn(msg.sender, amount);
    }

    function setFundingPaused(bool paused) external {
        if (msg.sender != pauser) revert NotPauser();
        fundingPaused = paused;
        emit FundingPaused(paused);
    }

    // --------------------------------------------------------------- views

    function getDemand(bytes32 demandId) external view returns (Demand memory) {
        return _demands[demandId];
    }

    function solvent() external view returns (bool) {
        return address(this).balance >= activeEscrow + totalCredit;
    }

    function domainSeparator() public view returns (bytes32) {
        return keccak256(
            abi.encode(
                _DOMAIN_TYPEHASH,
                keccak256("LemmaCreationBounty"),
                keccak256("1"),
                block.chainid,
                address(this)
            )
        );
    }

    function hashVerdict(VerdictMessage calldata m) public view returns (bytes32) {
        bytes32 structHash = keccak256(
            abi.encode(
                VERDICT_TYPEHASH,
                m.demandId,
                m.candidateDigest,
                m.policyHash,
                m.reportHash,
                m.guestKey,
                m.recipient,
                m.verdict,
                m.validUntil,
                m.nonce
            )
        );
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    // ------------------------------------------------------------ internal

    function _release(address payee, uint256 amount) internal {
        activeEscrow -= amount;
        credit[payee] += amount;
        totalCredit += amount;
    }

    function _recover(bytes32 digest, bytes calldata signature) internal pure returns (address) {
        if (signature.length != 65) revert BadSignature();
        bytes32 r = bytes32(signature[0:32]);
        bytes32 s = bytes32(signature[32:64]);
        uint8 v = uint8(signature[64]);
        if (uint256(s) > _SECP256K1N_HALF || (v != 27 && v != 28)) revert BadSignature();
        address recovered = ecrecover(digest, v, r, s);
        if (recovered == address(0)) revert BadSignature();
        return recovered;
    }
}
