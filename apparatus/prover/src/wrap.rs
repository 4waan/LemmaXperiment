//! lemma-wrap: turn a saved compressed SP1 proof into a Groth16 proof plus
//! the on-chain material (proof bytes, public values, vkey).
//!
//! Mirrors the Groth16Wrap task in sp1-prover 6.8.0 step for step so the
//! pinned prover crates stay untouched; only the orchestration lives here.
//! Splitting compress and wrap into separate jobs keeps each under the
//! 6 hour GitHub job cap.

use std::{borrow::Borrow, fs, path::PathBuf, time::Instant};

use clap::Parser;
use slop_algebra::{AbstractField, PrimeField, PrimeField32};
use slop_bn254::Bn254Fr;
use sp1_hypercube::{koalabears_to_bn254, SP1WrapProof};
use sp1_primitives::SP1Field;
use sp1_prover::{
    build::try_build_groth16_artifacts_dir,
    worker::{cpu_worker_builder, SP1LocalNodeBuilder},
};
use sp1_recursion_circuit::{
    machine::SP1ShapedWitnessValues,
    utils::{koalabear_bytes_to_bn254, koalabears_proof_nonce_to_bn254, words_to_bytes},
    witness::{OuterWitness, Witnessable},
};
use sp1_recursion_compiler::config::OuterConfig;
use sp1_recursion_executor::RecursionPublicValues;
use sp1_recursion_gnark_ffi::Groth16Bn254Prover;
use sp1_sdk::{
    env::EnvProver, include_elf, Elf, HashableKey, Prover, ProvingKey, SP1Proof,
    SP1ProofWithPublicValues, SP1Stdin, SP1_CIRCUIT_VERSION,
};
use tracing_subscriber::{
    filter::EnvFilter, fmt, prelude::__tracing_subscriber_SubscriberExt, util::SubscriberInitExt,
};

#[derive(Debug, Clone, Parser)]
struct Args {
    /// bincode `SP1Proof::Compressed`, as written by lemma-prove ({block}.proof.bin).
    #[clap(long)]
    compressed_proof: PathBuf,

    /// bincode `SP1Stdin`, as written by lemma-prove --stdin-dir ({block}.bin).
    #[clap(long)]
    stdin: PathBuf,

    #[clap(long, default_value = "wrap-out")]
    out_dir: PathBuf,
}

#[tokio::main]
async fn main() -> eyre::Result<()> {
    dotenv::dotenv().ok();
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }
    let sp1_level = std::env::var("SP1_LOG").unwrap_or_else(|_| "info".to_string());
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(
            EnvFilter::from_default_env()
                .add_directive(format!("sp1_prover={sp1_level}").parse().unwrap()),
        )
        .init();

    let args = Args::parse();
    fs::create_dir_all(&args.out_dir)?;

    let elf = include_elf!("rsp-client").to_vec();
    let compressed: SP1Proof = bincode::deserialize(&fs::read(&args.compressed_proof)?)?;
    let stdin: SP1Stdin = bincode::deserialize(&fs::read(&args.stdin)?)?;

    // 1. Public values: re-execute the guest on the same stdin (deterministic, seconds).
    let client = EnvProver::new().await;
    let pk = client.setup(Elf::from(elf.as_slice())).await.map_err(|e| eyre::eyre!("{e}"))?;
    let vk = pk.verifying_key().clone();
    let t = Instant::now();
    let (public_values, report) =
        client.execute(Elf::from(elf.as_slice()), stdin).await.map_err(|e| eyre::eyre!("{e}"))?;
    tracing::info!(
        cycles = report.total_instruction_count(),
        secs = t.elapsed().as_secs_f64(),
        "executed guest for public values"
    );

    // 2. The compressed proof must verify against the pinned vkey before wrapping.
    let compressed_bundle = SP1ProofWithPublicValues::new(
        compressed.clone(),
        public_values.clone(),
        SP1_CIRCUIT_VERSION.to_string(),
    );
    client
        .verify(&compressed_bundle, &vk, None)
        .map_err(|e| eyre::eyre!("compressed proof failed verification: {e}"))?;
    tracing::info!(vkey = vk.bytes32(), "compressed proof verified");

    // 3. Shrink and wrap: two recursion proofs, the second over the outer field.
    let node = SP1LocalNodeBuilder::from_worker_client_builder(cpu_worker_builder())
        .build()
        .await
        .map_err(|e| eyre::eyre!("{e}"))?;
    let t = Instant::now();
    let wrap_proof = node.shrink_wrap(&compressed).await.map_err(|e| eyre::eyre!("{e}"))?;
    let shrink_wrap_seconds = t.elapsed().as_secs_f64();
    tracing::info!(secs = shrink_wrap_seconds, "shrink-wrap done");

    // 4. Groth16 via gnark (docker image ghcr.io/succinctlabs/sp1-gnark:<circuit version>).
    let build_dir = try_build_groth16_artifacts_dir(&wrap_proof.vk, &wrap_proof.proof)
        .await
        .map_err(|e| eyre::eyre!("{e}"))?;
    let t = Instant::now();
    let groth16 = tokio::task::spawn_blocking(move || -> eyre::Result<_> {
        let SP1WrapProof { vk, proof } = wrap_proof;
        let input =
            SP1ShapedWitnessValues { vks_and_proofs: vec![(vk, proof.clone())], is_complete: true };
        let pv: &RecursionPublicValues<SP1Field> = proof.public_values.as_slice().borrow();
        let vkey_hash = koalabears_to_bn254(&pv.sp1_vk_digest);
        let digest_bytes: [SP1Field; 32] = words_to_bytes(&pv.committed_value_digest)
            .try_into()
            .map_err(|_| eyre::eyre!("committed_value_digest has invalid length"))?;
        let committed_values_digest = koalabear_bytes_to_bn254(&digest_bytes);
        let exit_code = Bn254Fr::from_canonical_u32(pv.exit_code.as_canonical_u32());
        let proof_nonce = koalabears_proof_nonce_to_bn254(&pv.proof_nonce);
        let vk_root = koalabears_to_bn254(&pv.vk_root);

        let mut witness: OuterWitness<OuterConfig> = OuterWitness::default();
        input.write(&mut witness);
        witness.write_committed_values_digest(committed_values_digest);
        witness.write_vkey_hash(vkey_hash);
        witness.write_exit_code(exit_code);
        witness.write_vk_root(vk_root);
        witness.write_proof_nonce(proof_nonce);

        let prover = Groth16Bn254Prover::new();
        let proof = prover.prove(witness, &build_dir);
        prover
            .verify(
                &proof,
                &vkey_hash.as_canonical_biguint(),
                &committed_values_digest.as_canonical_biguint(),
                &exit_code.as_canonical_biguint(),
                &vk_root.as_canonical_biguint(),
                &proof_nonce.as_canonical_biguint(),
                &build_dir,
            )
            .map_err(|e| eyre::eyre!("groth16 verify failed: {e}"))?;
        Ok(proof)
    })
    .await??;
    let groth16_seconds = t.elapsed().as_secs_f64();
    tracing::info!(secs = groth16_seconds, "groth16 done");

    // 5. Bundle, verify with the SDK, write on-chain material.
    let bundle = SP1ProofWithPublicValues::new(
        SP1Proof::Groth16(groth16),
        public_values,
        SP1_CIRCUIT_VERSION.to_string(),
    );
    client
        .verify(&bundle, &vk, None)
        .map_err(|e| eyre::eyre!("groth16 bundle failed SDK verification: {e}"))?;

    bundle.save(args.out_dir.join("groth16.bin")).map_err(|e| eyre::eyre!("{e}"))?;
    fs::write(args.out_dir.join("proof.hex"), hex::encode(bundle.bytes()))?;
    fs::write(
        args.out_dir.join("public-values.hex"),
        hex::encode(bundle.public_values.as_slice()),
    )?;
    fs::write(args.out_dir.join("vkey.txt"), vk.bytes32())?;
    let summary = serde_json::json!({
        "vkey": vk.bytes32(),
        "circuit_version": SP1_CIRCUIT_VERSION,
        "proof_bytes_len": bundle.bytes().len(),
        "public_values_len": bundle.public_values.as_slice().len(),
        "shrink_wrap_seconds": shrink_wrap_seconds,
        "groth16_seconds": groth16_seconds,
    });
    fs::write(args.out_dir.join("wrap.json"), serde_json::to_string_pretty(&summary)?)?;
    tracing::info!("wrote {}", args.out_dir.display());
    Ok(())
}
