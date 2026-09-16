//! lemma-prove: the pinned RSP host with four additions, none of which touch
//! the guest or the executor crates: `--stdin-dir` (exposes the executor's
//! existing stdin dump), `--out-dir` (saves proof, vkey, timings),
//! `--proof-mode` (compressed, groth16 or plonk instead of hardcoded
//! compressed) and `--stdin-file` (execute a saved stdin again, byte for byte,
//! so repeated measurements of one block share one input).

use std::{path::PathBuf, sync::Arc};

use clap::Parser;
use execute::PersistExecutionReport;
use rsp_client_executor::io::EthClientExecutorInput;
use rsp_host_executor::{
    build_executor, create_eth_block_execution_strategy_factory, BlockExecutor,
    EthExecutorComponents,
};
use rsp_provider::create_provider;
use save::SaveArtifacts;
use sp1_sdk::{env::EnvProver, include_elf, HashableKey, SP1ProofMode, SP1Stdin};
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

    /// Execute this saved stdin (`{block}.bin` from --stdin-dir) instead of
    /// building one from the RPC provider or the input cache. Execute only.
    #[clap(long)]
    stdin_file: Option<PathBuf>,
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
    let chain_id = config.chain.id();
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

    // The program key is derived from the embedded guest ELF, so recording it
    // in every mode (not only with --prove) lets two host builds show they
    // carry the same guest.
    let vkey = executor.vk().bytes32();
    std::fs::write(args.out_dir.join("vkey.txt"), &vkey)?;
    tracing::info!(variant = save::VARIANT, executor = save::EXECUTOR, %vkey, "lemma-prove");

    if let Some(path) = args.stdin_file.as_ref() {
        // Replay: the executor's own validation path (guest execution, header
        // check, hooks) on the exact bytes a previous run produced. The block
        // metadata the hooks need is the first stdin item, the bincode client
        // input; under `arena` its witness field is skipped there and travels
        // as the second item, which the guest reads on its own.
        eyre::ensure!(!args.host.prove, "--stdin-file is execute only");
        let stdin: SP1Stdin = bincode::deserialize(&std::fs::read(path)?)?;
        let first = stdin.buffer.first().ok_or_else(|| eyre::eyre!("empty stdin"))?;
        let client_input: EthClientExecutorInput = bincode::deserialize(first)?;
        eyre::ensure!(
            client_input.current_block.header.number == block_number,
            "stdin holds block {}, not {block_number}",
            client_input.current_block.header.number
        );
        let hooks = (
            PersistExecutionReport::new(
                chain_id,
                args.host.report_path.clone(),
                args.host.precompile_tracking,
                args.host.opcode_tracking,
            ),
            SaveArtifacts::new(args.out_dir.clone())?,
        );
        tracing::info!(path = %path.display(), "replaying saved stdin");
        executor.execute_input(&client_input, stdin, &hooks).await?;
        return Ok(());
    }

    executor.execute(block_number).await?;
    Ok(())
}
