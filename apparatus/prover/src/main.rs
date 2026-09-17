//! lemma-prove: the pinned RSP host with evaluator-owned additions that do not
//! change the RSP executor crates: `--stdin-dir` (exposes the executor's
//! existing stdin dump), `--out-dir` (saves proof, vkey, timings),
//! `--proof-mode` (compressed, groth16 or plonk instead of hardcoded
//! compressed), `--stdin-file` (execute a saved stdin again, byte for byte,
//! so repeated measurements of one block share one input) and `--guest
//! settlement` (the lemma-client guest that commits the UsageEscrow public
//! values for a job instead of the block header).

use std::{path::PathBuf, sync::Arc};

use std::time::Instant;

use clap::Parser;
use either::Either;
use execute::PersistExecutionReport;
use reth_ethereum_primitives::EthPrimitives;
use rsp_client_executor::io::EthClientExecutorInput;
use rsp_host_executor::ExecutionHooks;
use rsp_host_executor::{
    build_executor, create_eth_block_execution_strategy_factory, BlockExecutor,
    EthExecutorComponents,
};
use rsp_provider::create_provider;
use save::SaveArtifacts;
use sp1_sdk::{
    env::EnvProver, include_elf, HashableKey, Prover, ProvingKey, SP1ProofMode, SP1Stdin,
};
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

    /// Guest program: `rsp` (the pinned rsp-client, commits the block header;
    /// the measured guest) or `settlement` (lemma-client, commits the nine
    /// words contracts/src/UsageEscrow.sol decodes; the reuse-job guest).
    #[clap(long, default_value = "rsp")]
    guest: String,

    /// Settlement guest only: the job context the guest binds.
    #[clap(long, default_value = "46630")]
    job_chain_id: u64,
    #[clap(long, default_value = "0x0000000000000000000000000000000000000000")]
    job_market: String,
    #[clap(
        long,
        default_value = "0x0000000000000000000000000000000000000000000000000000000000000000"
    )]
    job_id: String,
}

/// Same field order as `JobContext` in the guest; bincode is positional.
#[derive(serde::Serialize)]
struct JobContext {
    settlement_chain_id: u64,
    market: [u8; 20],
    job_id: [u8; 32],
}

/// keccak256("ethereum-mainnet-block-execution.v1"), UsageEscrow.SOURCE_DOMAIN.
const SOURCE_DOMAIN: [u8; 32] = [
    0x9b, 0x2c, 0x85, 0x38, 0x32, 0x8b, 0x41, 0xd0, 0x86, 0x28, 0x77, 0xf0, 0xc2, 0xd5, 0xbb, 0xc4,
    0x31, 0xbd, 0xb3, 0xca, 0x61, 0xb4, 0x42, 0xf6, 0x16, 0x03, 0xc4, 0x0e, 0x99, 0xaa, 0x65, 0x80,
];

fn parse_hex<const N: usize>(s: &str, what: &str) -> eyre::Result<[u8; N]> {
    let raw = hex::decode(s.trim_start_matches("0x"))?;
    let arr: [u8; N] = raw
        .try_into()
        .map_err(|_| eyre::eyre!("{what} must be {N} bytes of hex"))?;
    Ok(arr)
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
        config.prove_mode = Some(config_prove_mode(&args.proof_mode)?);
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
    let settlement = match args.guest.as_str() {
        "rsp" => false,
        "settlement" => true,
        other => eyre::bail!("unknown guest {other}; use rsp or settlement"),
    };
    let elf = if settlement {
        include_elf!("lemma-client").to_vec()
    } else {
        include_elf!("rsp-client").to_vec()
    };
    let block_execution_strategy_factory =
        create_eth_block_execution_strategy_factory(&config.genesis, config.custom_beneficiary);
    let provider = config
        .rpc_url
        .as_ref()
        .map(|url| create_provider(url.clone()));

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
    tracing::info!(variant = save::VARIANT, executor = save::EXECUTOR, guest = %args.guest, %vkey, "lemma-prove");

    if settlement {
        // The settlement guest commits a different layout, so the executor's
        // own validation path (which reads a CommittedHeader) does not apply.
        // Same client input, same stdin plus the job context, executed and
        // proved through the executor's client and keys.
        let hooks = (
            PersistExecutionReport::new(
                chain_id,
                args.host.report_path.clone(),
                args.host.precompile_tracking,
                args.host.opcode_tracking,
            ),
            SaveArtifacts::new(args.out_dir.clone())?,
        );
        let ctx = JobContext {
            settlement_chain_id: args.job_chain_id,
            market: parse_hex::<20>(&args.job_market, "--job-market")?,
            job_id: parse_hex::<32>(&args.job_id, "--job-id")?,
        };
        let (client_input, stdin) = if let Some(path) = args.stdin_file.as_ref() {
            eyre::ensure!(!args.host.prove, "--stdin-file is execute only");
            let stdin: SP1Stdin = bincode::deserialize(&std::fs::read(path)?)?;
            let first = stdin
                .buffer
                .first()
                .ok_or_else(|| eyre::eyre!("empty stdin"))?;
            let client_input: EthClientExecutorInput = bincode::deserialize(first)?;
            (client_input, stdin)
        } else {
            let full = match &executor {
                Either::Left(full) => full,
                Either::Right(_) => {
                    eyre::bail!("the settlement guest needs the RPC provider or --stdin-file")
                }
            };
            let client_input = full.fetch_client_input(block_number).await?;
            let mut stdin = executor.build_stdin(&client_input)?;
            stdin.write_vec(bincode::serialize(&ctx)?);
            executor.save_stdin(block_number, &stdin)?;
            (client_input, stdin)
        };
        eyre::ensure!(
            client_input.current_block.header.number == block_number,
            "input holds block {}, not {block_number}",
            client_input.current_block.header.number
        );
        let client = executor.client();
        let guest_elf = executor.pk().elf().clone();
        let start = Instant::now();
        let (public_values, report) = client
            .execute(guest_elf, stdin.clone())
            .await
            .map_err(|err| eyre::eyre!("{err}"))?;
        let duration = start.elapsed();
        let pv = public_values.as_slice();
        eyre::ensure!(
            pv.len() == 9 * 32,
            "settlement guest committed {} bytes, expected 288",
            pv.len()
        );
        let word = |i: usize| &pv[i * 32..(i + 1) * 32];
        let expect_block_hash = client_input.current_block.header.hash_slow();
        let parent_root = client_input.parent_header().state_root;
        let expected_state_root = client_input.current_block.header.state_root;
        let mut chain_word = [0u8; 32];
        chain_word[24..].copy_from_slice(&ctx.settlement_chain_id.to_be_bytes());
        let mut market_word = [0u8; 32];
        market_word[12..].copy_from_slice(&ctx.market);
        let mut block_word = [0u8; 32];
        block_word[24..].copy_from_slice(&block_number.to_be_bytes());
        let mut success_word = [0u8; 32];
        success_word[31] = 1;
        eyre::ensure!(word(0) == chain_word, "chain id mismatch in public values");
        eyre::ensure!(word(1) == market_word, "market mismatch in public values");
        eyre::ensure!(
            word(2) == &ctx.job_id[..],
            "job id mismatch in public values"
        );
        eyre::ensure!(
            word(3) == SOURCE_DOMAIN,
            "source domain mismatch in public values"
        );
        eyre::ensure!(
            word(4) == block_word,
            "block number mismatch in public values"
        );
        eyre::ensure!(
            word(5) == expect_block_hash.as_slice(),
            "block hash mismatch in public values"
        );
        eyre::ensure!(
            word(6) == parent_root.as_slice(),
            "parent state root mismatch in public values"
        );
        eyre::ensure!(
            word(7) == expected_state_root.as_slice(),
            "computed state root mismatch in public values"
        );
        eyre::ensure!(word(8) == success_word, "success flag not set");
        let computed_state_root = format!("0x{}", hex::encode(word(7)));
        std::fs::write(
            args.out_dir
                .join(format!("{block_number}.public-values.hex")),
            hex::encode(pv),
        )?;
        tracing::info!(%computed_state_root, cycles = report.total_instruction_count(), "settlement guest executed");
        hooks
            .on_execution_end::<EthPrimitives>(&client_input.current_block, &report, duration)
            .await?;
        if args.host.prove {
            let mode = config_prove_mode(&args.proof_mode)?;
            let (proof_bytes, proving_duration) = executor
                .prove_only(block_number, stdin, mode, &hooks)
                .await?;
            hooks
                .on_proving_end(
                    block_number,
                    &proof_bytes,
                    executor.vk().as_ref(),
                    Some(report.total_instruction_count()),
                    proving_duration,
                )
                .await?;
        }
        return Ok(());
    }

    if let Some(path) = args.stdin_file.as_ref() {
        // Replay: the executor's own validation path (guest execution, header
        // check, hooks) on the exact bytes a previous run produced. The block
        // metadata the hooks need is the first stdin item, the bincode client
        // input; under `arena` its witness field is skipped there and travels
        // as the second item, which the guest reads on its own.
        eyre::ensure!(!args.host.prove, "--stdin-file is execute only");
        let stdin: SP1Stdin = bincode::deserialize(&std::fs::read(path)?)?;
        let first = stdin
            .buffer
            .first()
            .ok_or_else(|| eyre::eyre!("empty stdin"))?;
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

fn config_prove_mode(mode: &str) -> eyre::Result<SP1ProofMode> {
    Ok(match mode {
        "compressed" => SP1ProofMode::Compressed,
        "groth16" => SP1ProofMode::Groth16,
        "plonk" => SP1ProofMode::Plonk,
        other => eyre::bail!("unknown proof mode {other}"),
    })
}
