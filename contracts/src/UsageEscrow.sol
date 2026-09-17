// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ISP1VerifierWithHash} from "./sp1/ISP1Verifier.sol";
import {ModuleRegistry} from "./ModuleRegistry.sol";

/// @title UsageEscrow
/// @notice A funded proof job settles once on a verified SP1 proof whose
/// public values bind this chain, this contract, the job and the statement,
/// or expires with a refund after its deadline (EXPERIMENT.md section 9,
/// ROBINHOOD_CHAIN_PROD.md 3.2 and I-S2 to I-S7, I-S14, I-V1).
///
/// Public values the guest wrapper commits, as abi.encode of nine words:
///   uint64  settlementChainId   must equal block.chainid
///   address marketAddress       must equal this contract
///   bytes32 jobId
///   bytes32 sourceDomain        keccak256("ethereum-mainnet-block-execution.v1")
///   uint64  blockNumber
///   bytes32 blockHash
///   bytes32 parentStateRoot
///   bytes32 computedStateRoot   must equal the statement's expectedStateRoot
///   bool    success             must be true
/// The witness is bound by the guest's own checks against parentStateRoot;
/// its sha256 is a ledger field (run.txt), not a public value.
contract UsageEscrow {
    enum State {
        None,
        Funded,
        Settled,
        Expired
    }

    struct Statement {
        uint64 blockNumber;
        bytes32 blockHash;
        bytes32 parentStateRoot;
        bytes32 expectedStateRoot;
    }

    /// @dev The nine committed words in order; abi.decode of the static
    /// struct reads exactly the layout the guest writes.
    struct PublicValues {
        uint256 settlementChainId;
        address marketAddress;
        bytes32 jobId;
        bytes32 sourceDomain;
        uint256 blockNumber;
        bytes32 blockHash;
        bytes32 parentStateRoot;
        bytes32 computedStateRoot;
        uint256 success;
    }

    struct Job {
        address buyer;
        bytes32 versionId;
        bytes32 guestKey;
        address verifier;
        bytes32 verifierHash;
        address worker;
        address contributor;
        uint256 workerFee;
        uint256 contributorFee;
        Statement statement;
        bytes32 statementHash;
        uint64 proveBy;
        State state;
        uint64 settledAt;
        address settledBy;
    }

    bytes32 public constant SOURCE_DOMAIN = keccak256("ethereum-mainnet-block-execution.v1");
    uint256 public constant PUBLIC_VALUES_LENGTH = 9 * 32;

    ModuleRegistry public immutable registry;
    ISP1VerifierWithHash public immutable verifier;
    bytes32 public immutable verifierHash;
    address public immutable pauser;
    bool public fundingPaused;

    uint256 public activeEscrow;
    uint256 public totalCredit;
    mapping(address => uint256) public credit;
    mapping(bytes32 => Job) private _jobs;
    uint256 private _jobCount;
    uint256 private _entered;

    event JobFunded(
        bytes32 indexed jobId,
        address indexed buyer,
        bytes32 indexed versionId,
        bytes32 guestKey,
        address worker,
        address contributor,
        uint256 workerFee,
        uint256 contributorFee,
        bytes32 statementHash,
        uint64 proveBy
    );
    event JobSettled(bytes32 indexed jobId, address indexed submitter, bytes32 computedStateRoot);
    event JobExpired(bytes32 indexed jobId);
    event Withdrawn(address indexed payee, uint256 amount);
    event FundingPaused(bool paused);

    error FundingIsPaused();
    error ZeroAddress();
    error WrongValue(uint256 expected, uint256 got);
    error BadDeadline(uint64 proveBy);
    error WrongState(State state);
    error PastDeadline(uint64 proveBy);
    error NotYetExpired();
    error BadPublicValuesLength(uint256 length);
    error PublicValueMismatch(string field);
    error NotPauser();
    error Reentrancy();
    error NothingToWithdraw();
    error WithdrawFailed();

    modifier nonReentrant() {
        if (_entered == 1) revert Reentrancy();
        _entered = 1;
        _;
        _entered = 0;
    }

    constructor(ModuleRegistry registry_, ISP1VerifierWithHash verifier_, address pauser_) {
        if (
            address(registry_) == address(0) || address(verifier_) == address(0)
                || pauser_ == address(0)
        ) revert ZeroAddress();
        registry = registry_;
        verifier = verifier_;
        verifierHash = verifier_.VERIFIER_HASH();
        pauser = pauser_;
    }

    // ---------------------------------------------------------------- funding

    /// @notice Funds one job for an accepted version. msg.value is the worker
    /// fee plus the version's contributor fee. Every term is snapshotted here
    /// and never changes (I-S6, I-S14).
    function fundJob(
        bytes32 versionId,
        address worker,
        uint256 workerFee,
        Statement calldata statement,
        uint64 proveBy
    ) external payable returns (bytes32 jobId) {
        if (fundingPaused) revert FundingIsPaused();
        if (worker == address(0)) revert ZeroAddress();
        if (proveBy <= block.timestamp) revert BadDeadline(proveBy);
        ModuleRegistry.Version memory v = registry.getVersion(versionId);
        uint256 expected = workerFee + v.contributorFee;
        if (msg.value != expected) revert WrongValue(expected, msg.value);
        bytes32 statementHash = keccak256(
            abi.encode(
                "lemma.statement.v1",
                SOURCE_DOMAIN,
                statement.blockNumber,
                statement.blockHash,
                statement.parentStateRoot,
                statement.expectedStateRoot
            )
        );
        jobId = keccak256(
            abi.encode(
                "lemma.job.v1", block.chainid, address(this), msg.sender, _jobCount++, statementHash
            )
        );
        Job storage j = _jobs[jobId];
        j.buyer = msg.sender;
        j.versionId = versionId;
        j.guestKey = v.guestKey;
        j.verifier = address(verifier);
        j.verifierHash = verifierHash;
        j.worker = worker;
        j.contributor = v.contributor;
        j.workerFee = workerFee;
        j.contributorFee = v.contributorFee;
        j.statement = statement;
        j.statementHash = statementHash;
        j.proveBy = proveBy;
        j.state = State.Funded;
        activeEscrow += msg.value;
        emit JobFunded(
            jobId,
            msg.sender,
            versionId,
            v.guestKey,
            worker,
            v.contributor,
            workerFee,
            v.contributorFee,
            statementHash,
            proveBy
        );
    }

    // ------------------------------------------------------------ settlement

    /// @notice Settles the job on a verified proof. Any relayer may call;
    /// payees come from storage (I-S4). Allowed at the deadline, not after (I-S5).
    function submitProof(bytes32 jobId, bytes calldata publicValues, bytes calldata proofBytes)
        external
    {
        Job storage j = _jobs[jobId];
        if (j.state != State.Funded) revert WrongState(j.state);
        if (block.timestamp > j.proveBy) revert PastDeadline(j.proveBy);
        if (publicValues.length != PUBLIC_VALUES_LENGTH) {
            revert BadPublicValuesLength(publicValues.length);
        }
        PublicValues memory pv = abi.decode(publicValues, (PublicValues));
        _checkBindings(jobId, j, pv);

        // Reverts on an invalid proof, wrong selector or wrong vk root.
        ISP1VerifierWithHash(j.verifier).verifyProof(j.guestKey, publicValues, proofBytes);

        j.state = State.Settled;
        j.settledAt = uint64(block.timestamp);
        j.settledBy = msg.sender;
        uint256 total = j.workerFee + j.contributorFee;
        activeEscrow -= total;
        credit[j.worker] += j.workerFee;
        credit[j.contributor] += j.contributorFee;
        totalCredit += total;
        emit JobSettled(jobId, msg.sender, pv.computedStateRoot);
    }

    function _checkBindings(bytes32 jobId, Job storage j, PublicValues memory pv) internal view {
        if (pv.settlementChainId != block.chainid) revert PublicValueMismatch("settlementChainId");
        if (pv.marketAddress != address(this)) revert PublicValueMismatch("marketAddress");
        if (pv.jobId != jobId) revert PublicValueMismatch("jobId");
        if (pv.sourceDomain != SOURCE_DOMAIN) revert PublicValueMismatch("sourceDomain");
        if (pv.blockNumber != j.statement.blockNumber) revert PublicValueMismatch("blockNumber");
        if (pv.blockHash != j.statement.blockHash) revert PublicValueMismatch("blockHash");
        if (pv.parentStateRoot != j.statement.parentStateRoot) {
            revert PublicValueMismatch("parentStateRoot");
        }
        if (pv.computedStateRoot != j.statement.expectedStateRoot) {
            revert PublicValueMismatch("computedStateRoot");
        }
        if (pv.success != 1) revert PublicValueMismatch("success");
    }

    /// @notice Refunds the buyer after proveBy without settlement. Anyone may call.
    function expireJob(bytes32 jobId) external {
        Job storage j = _jobs[jobId];
        if (j.state != State.Funded) revert WrongState(j.state);
        if (block.timestamp <= j.proveBy) revert NotYetExpired();
        j.state = State.Expired;
        uint256 total = j.workerFee + j.contributorFee;
        activeEscrow -= total;
        credit[j.buyer] += total;
        totalCredit += total;
        emit JobExpired(jobId);
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

    function getJob(bytes32 jobId) external view returns (Job memory) {
        return _jobs[jobId];
    }

    function solvent() external view returns (bool) {
        return address(this).balance >= activeEscrow + totalCredit;
    }

    /// @notice The exact bytes a guest must commit for a job to settle.
    function expectedPublicValues(bytes32 jobId, bytes32 computedStateRoot)
        external
        view
        returns (bytes memory)
    {
        Job storage j = _jobs[jobId];
        return abi.encode(
            uint256(block.chainid),
            address(this),
            jobId,
            SOURCE_DOMAIN,
            uint256(j.statement.blockNumber),
            j.statement.blockHash,
            j.statement.parentStateRoot,
            computedStateRoot,
            uint256(1)
        );
    }
}
