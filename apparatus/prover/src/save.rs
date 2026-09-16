//! Hook that persists everything the RSP CLI computes but throws away:
//! proof bytes, verifying key, and phase durations.

use std::{collections::BTreeMap, fs, path::PathBuf, time::Duration};

use alloy_consensus::Block;
use reth_primitives_traits::NodePrimitives;
use rsp_host_executor::ExecutionHooks;
use sp1_sdk::{ExecutionReport, HashableKey, SP1VerifyingKey};

/// Which build produced the record. The guest ELF is the same in both; only
/// the host-side SP1 executor differs (see Cargo.toml `cycle-tracking`).
pub const VARIANT: &str =
    if cfg!(feature = "cycle-tracking") { "cycle-tracking" } else { "standard" };
pub const EXECUTOR: &str = if cfg!(feature = "cycle-tracking") {
    "sp1 portable interpreter (profiling feature)"
} else {
    "sp1 default (native on x86_64 linux)"
};

pub struct SaveArtifacts {
    out_dir: PathBuf,
}

impl SaveArtifacts {
    pub fn new(out_dir: PathBuf) -> eyre::Result<Self> {
        fs::create_dir_all(&out_dir)?;
        Ok(Self { out_dir })
    }

    fn path(&self, block: u64, suffix: &str) -> PathBuf {
        self.out_dir.join(format!("{block}.{suffix}"))
    }
}

impl ExecutionHooks for SaveArtifacts {
    async fn on_execution_end<P: NodePrimitives>(
        &self,
        executed_block: &Block<P::SignedTx>,
        report: &ExecutionReport,
        execution_duration: Duration,
    ) -> eyre::Result<()> {
        let block = executed_block.header.number;
        // Per-phase cycles keyed by the guest's cycle-tracker labels. Only the
        // cycle-tracking build fills these (the SP1 executor drops the labels
        // otherwise), so sorted maps make the two variants diff cleanly.
        let cycle_tracker: BTreeMap<_, _> =
            report.cycle_tracker.iter().map(|(k, v)| (k.clone(), *v)).collect();
        let invocation_tracker: BTreeMap<_, _> =
            report.invocation_tracker.iter().map(|(k, v)| (k.clone(), *v)).collect();
        let json = serde_json::json!({
            "block": block,
            "variant": VARIANT,
            "executor": EXECUTOR,
            "total_instruction_count": report.total_instruction_count(),
            "total_syscall_count": report.total_syscall_count(),
            "prover_gas": report.gas(),
            "execution_seconds": execution_duration.as_secs_f64(),
            "cycle_tracker": cycle_tracker,
            "invocation_tracker": invocation_tracker,
        });
        fs::write(self.path(block, "execution.json"), serde_json::to_string_pretty(&json)?)?;
        Ok(())
    }

    async fn on_proving_end(
        &self,
        block: u64,
        proof_bytes: &[u8],
        vk: &SP1VerifyingKey,
        cycle_count: Option<u64>,
        proving_duration: Duration,
    ) -> eyre::Result<()> {
        fs::write(self.path(block, "proof.bin"), proof_bytes)?;
        fs::write(self.path(block, "vk.bin"), bincode::serialize(vk)?)?;
        fs::write(self.path(block, "vk.txt"), vk.bytes32())?;
        let json = serde_json::json!({
            "block": block,
            "vkey": vk.bytes32(),
            "proof_bytes_len": proof_bytes.len(),
            "cycle_count": cycle_count,
            "proving_seconds": proving_duration.as_secs_f64(),
        });
        fs::write(self.path(block, "proving.json"), serde_json::to_string_pretty(&json)?)?;
        Ok(())
    }
}
