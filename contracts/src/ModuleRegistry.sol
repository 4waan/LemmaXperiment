// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ModuleRegistry
/// @notice Accepted module versions with their evidence references, guest key
/// and usage terms. An entry is created only inside the CreationBounty's
/// acceptance path (ROBINHOOD_CHAIN_PROD.md I-S8); nothing else can register,
/// and nothing can change an entry afterwards.
contract ModuleRegistry {
    struct Version {
        bytes32 demandId;
        bytes32 candidateDigest; // artifact digest of the accepted bundle
        bytes32 sourceCommit; // commit of the accepted bundle
        bytes32 guestKey; // SP1 program key the evaluator derived
        bytes32 policyHash; // evaluation policy the verdict was signed under
        bytes32 reportHash; // signed evaluation report
        address contributor; // usage-fee payee for every later job
        uint256 contributorFee; // per job, from the demand's usageFeePolicy
        uint64 registeredAt; // set by the registry
    }

    address public immutable bounty;
    bytes32[] public versionIds;
    mapping(bytes32 => Version) private _versions;

    event VersionRegistered(
        bytes32 indexed versionId,
        bytes32 indexed demandId,
        bytes32 candidateDigest,
        bytes32 guestKey,
        address contributor,
        uint256 contributorFee
    );

    error OnlyBounty();
    error AlreadyRegistered(bytes32 versionId);
    error UnknownVersion(bytes32 versionId);

    /// @param bounty_ The CreationBounty allowed to register; fixed for life.
    constructor(address bounty_) {
        bounty = bounty_;
    }

    /// @notice Registers an accepted version. Callable by the bounty only.
    function register(Version calldata v) external returns (bytes32 versionId) {
        if (msg.sender != bounty) revert OnlyBounty();
        versionId = keccak256(abi.encode("lemma.version.v1", v.demandId, v.candidateDigest));
        if (_versions[versionId].registeredAt != 0) revert AlreadyRegistered(versionId);
        Version memory stored = v;
        stored.registeredAt = uint64(block.timestamp);
        _versions[versionId] = stored;
        versionIds.push(versionId);
        emit VersionRegistered(
            versionId, v.demandId, v.candidateDigest, v.guestKey, v.contributor, v.contributorFee
        );
    }

    function getVersion(bytes32 versionId) external view returns (Version memory v) {
        v = _versions[versionId];
        if (v.registeredAt == 0) revert UnknownVersion(versionId);
    }

    function count() external view returns (uint256) {
        return versionIds.length;
    }
}
