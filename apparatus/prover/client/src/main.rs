//! lemma-client: the settlement guest (EXPERIMENT.md section 9,
//! ROBINHOOD_CHAIN_PROD.md 3.2, contracts/src/UsageEscrow.sol).
//!
//! Identical to the pinned `rsp-client` up to the commit: the same client
//! input, the same `EthClientExecutor::execute` with every upstream check.
//! Instead of the block header it commits the nine 32-byte words the escrow
//! decodes, binding the execution to one settlement chain, one market
//! contract and one job. The job context arrives as one extra stdin item
//! after the client input (and, under `arena`, after the witness blob).
#![no_main]
sp1_zkvm::entrypoint!(main);

use rsp_client_executor::{
    executor::EthClientExecutor, io::EthClientExecutorInput, utils::profile_report,
};
use std::sync::Arc;

/// keccak256("ethereum-mainnet-block-execution.v1"), UsageEscrow.SOURCE_DOMAIN.
const SOURCE_DOMAIN: [u8; 32] = [
    0x9b, 0x2c, 0x85, 0x38, 0x32, 0x8b, 0x41, 0xd0, 0x86, 0x28, 0x77, 0xf0, 0xc2, 0xd5, 0xbb, 0xc4,
    0x31, 0xbd, 0xb3, 0xca, 0x61, 0xb4, 0x42, 0xf6, 0x16, 0x03, 0xc4, 0x0e, 0x99, 0xaa, 0x65, 0x80,
];

/// Written by lemma-prove (`--guest settlement`), bincode.
#[derive(serde::Deserialize)]
struct JobContext {
    settlement_chain_id: u64,
    market: [u8; 20],
    job_id: [u8; 32],
}

fn push_word_u64(out: &mut Vec<u8>, v: u64) {
    out.extend_from_slice(&[0u8; 24]);
    out.extend_from_slice(&v.to_be_bytes());
}

pub fn main() {
    let input = profile_report!(rsp_client_executor::executor::DESERIALZE_INPUTS, {
        #[cfg(not(feature = "arena"))]
        {
            let input = sp1_zkvm::io::read_vec();
            bincode::deserialize::<EthClientExecutorInput>(&input).unwrap()
        }
        #[cfg(feature = "arena")]
        {
            let header_bytes = sp1_zkvm::io::read_vec();
            let mut input: EthClientExecutorInput = bincode::deserialize(&header_bytes).unwrap();
            input.parent_state = sp1_zkvm::io::read_vec();
            input
        }
    });
    let ctx: JobContext = bincode::deserialize(&sp1_zkvm::io::read_vec()).unwrap();

    // The statement's parent anchor, taken before the input is consumed. The
    // executor verifies the witness against this root.
    let parent_state_root = input.parent_header().state_root;

    let executor = EthClientExecutor::eth(
        Arc::new((&input.genesis).try_into().unwrap()),
        input.custom_beneficiary,
    );
    let header = executor.execute(input).expect("failed to execute client");

    let mut out = Vec::with_capacity(9 * 32);
    push_word_u64(&mut out, ctx.settlement_chain_id);
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(&ctx.market);
    out.extend_from_slice(&ctx.job_id);
    out.extend_from_slice(&SOURCE_DOMAIN);
    push_word_u64(&mut out, header.number);
    out.extend_from_slice(header.hash_slow().as_slice());
    out.extend_from_slice(parent_state_root.as_slice());
    out.extend_from_slice(header.state_root.as_slice());
    out.extend_from_slice(&[0u8; 31]);
    out.push(1);
    sp1_zkvm::io::commit_slice(&out);
}
