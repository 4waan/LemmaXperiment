// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {SP1Verifier} from "../src/sp1/v6.1.0/SP1VerifierGroth16.sol";

/// The vendored verifier against the real Groth16 proof of mainnet block
/// 20600066 from apparatus step 1 (wrap run 35051478400): the same triple the
/// Arbitrum Sepolia gateway accepted (apparatus/runs/.../onchain-verify.md).
contract SP1VerifierTest is Test {
    SP1Verifier verifier;
    bytes32 vkey;
    bytes publicValues;
    bytes proof;

    function setUp() public {
        verifier = new SP1Verifier();
        vkey = vm.parseBytes32(vm.trim(vm.readFile("test/fixtures/block-20600066.vkey.txt")));
        publicValues = vm.parseBytes(
            string.concat("0x", vm.trim(vm.readFile("test/fixtures/block-20600066.public-values.hex")))
        );
        proof =
            vm.parseBytes(string.concat("0x", vm.trim(vm.readFile("test/fixtures/block-20600066.proof.hex"))));
    }

    function test_identity() public view {
        assertEq(verifier.VERSION(), "v6.1.0");
        assertEq(bytes4(verifier.VERIFIER_HASH()), bytes4(0x4388a21c));
        assertEq(bytes4(proof), bytes4(verifier.VERIFIER_HASH()));
        assertEq(publicValues.length, 765);
        assertEq(proof.length, 356);
    }

    function test_realProofVerifies() public view {
        verifier.verifyProof(vkey, publicValues, proof);
    }

    function test_mutatedProofReverts() public {
        bytes memory bad = proof;
        bad[bad.length - 1] = bytes1(uint8(bad[bad.length - 1]) ^ 0x01);
        vm.expectRevert();
        verifier.verifyProof(vkey, publicValues, bad);
    }

    function test_mutatedPublicValuesRevert() public {
        bytes memory bad = publicValues;
        bad[10] = bytes1(uint8(bad[10]) ^ 0x01);
        vm.expectRevert();
        verifier.verifyProof(vkey, bad, proof);
    }

    function test_wrongVkeyReverts() public {
        vm.expectRevert();
        verifier.verifyProof(bytes32(uint256(vkey) ^ 1), publicValues, proof);
    }

    function test_wrongSelectorReverts() public {
        bytes memory bad = proof;
        bad[0] = 0x00;
        vm.expectRevert(
            abi.encodeWithSelector(
                SP1Verifier.WrongVerifierSelector.selector, bytes4(bad), bytes4(0x4388a21c)
            )
        );
        verifier.verifyProof(vkey, publicValues, bad);
    }
}
