//! lemma-prove: the pinned RSP host with three additions, none of which touch
//! the guest or the executor crates: `--stdin-dir` (exposes the executor's
//! existing stdin dump), `--out-dir` (saves proof, vkey, timings), and
//! `--proof-mode` (compressed, groth16 or plonk instead of hardcoded compressed).
#![cfg_attr(not(test), warn(unused_crate_dependencies))]

use std::{path::PathBuf, sync::Arc};

use clap::Parser;
use execute::PersistExecutionReport;
use rsp_host_executor::{
    build_executor, create_eth_block_execution_strategy_factory, BlockExecutor,
    EthExecutorComponents,
};
use rsp_provider::create_provider;
use save::SaveArtifacts;
use sp1_sdk::{env::EnvProver, include_elf, SP1ProofMode};
use tracing_subscriber::{
    filter::EnvFilter, fmt, prelude::__tracing_subscriber_SubscriberExt, util::SubscriberInitExt,
};

// Copied verbatim from bin/host/src/execute.rs at build time so the CSV
// report format is byte-identical to the pinned CLI.
mod execute;

mod cli;
mod save;
use cli::HostArgs;

#[derive(Debug, Clone, Parser)]
struct Args {
    #[clap(flatten)]
    host: HostArgs,

    /// Directory to write `{block}.bin` prover-ready stdin into.
    #[clap(long)]
    stdin_dir: Option<PathBuf>,

    /// Directory to write execution/proving JSON, proof bytes and vkey into.
    #[clap(long, default_value = "out")]
    out_dir: PathBuf,

    /// Proof mode used with --prove: compressed, groth16 or plonk.
    #[clap(long, default_value = "compressed")]
    proof_mode: String,
}

#[tokio::main]
async fn main() -> eyre::Result<()> {
    dotenv::dotenv().ok();
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }
    // Upstream pins sp1_prover to warn, which hides shard progress. SP1_LOG
    // (e.g. "debug") overrides that one directive so long CPU proofs can be
    // followed from the job log.
    let sp1_level = std::env::var("SP1_LOG").unwrap_or_else(|_| "warn".to_string());
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(
            EnvFilter::from_default_env()
                .add_directive("sp1_core_machine=warn".parse().unwrap())
                .add_directive("sp1_core_executor::executor=warn".parse().unwrap())
                .add_directive(format!("sp1_prover={sp1_level}").parse().unwrap()),
        )
        .init();

    let args = Args::parse();
    let block_number = args.host.block_number;
    let report_path = args.host.report_path.clone();
    let mut config = args.host.as_config().await?;
    config.stdin_dir = args.stdin_dir.clone();
    if args.host.prove {
        config.prove_mode = Some(match args.proof_mode.as_str() {
            "compressed" => SP1ProofMode::Compressed,
            "groth16" => SP1ProofMode::Groth16,
            "plonk" => SP1ProofMode::Plonk,
            other => eyre::bail!("unknown proof mode {other}"),
        });
    }

    let hooks = (
        PersistExecutionReport::new(
            config.chain.id(),
            report_path,
            args.host.precompile_tracking,
            args.host.opcode_tracking,
        ),
        SaveArtifacts::new(args.out_dir.clone())?,
    );

    let prover_client = Arc::new(EnvProver::new().await);
    let elf = include_elf!("rsp-client").to_vec();
    let block_execution_strategy_factory =
        create_eth_block_execution_strategy_factory(&config.genesis, config.custom_beneficiary);
    let provider = config.rpc_url.as_ref().map(|url| create_provider(url.clone()));

    let executor = build_executor::<EthExecutorComponents<_>, _>(
        elf,
        provider,
        block_execution_strategy_factory,
        prover_client,
        hooks,
        config,
    )
    .await?;

    executor.execute(block_number).await?;
    Ok(())
}
