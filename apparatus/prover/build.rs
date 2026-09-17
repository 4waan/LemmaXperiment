use sp1_build::{build_program_with_args, BuildArgs};

// Same guest build as bin/host/build.rs at the pinned commit: the `arena`
// feature of this crate is forwarded to the guests so their MPT backend and
// witness codec match the host's. Two programs: the pinned rsp-client (the
// measured guest, commits the header) and lemma-client (the settlement guest,
// commits the nine UsageEscrow words).
fn main() {
    let features: Vec<String> = if std::env::var_os("CARGO_FEATURE_ARENA").is_some() {
        vec!["arena".to_string()]
    } else {
        Vec::new()
    };
    build_program_with_args("../client", BuildArgs { features: features.clone(), ..Default::default() });
    build_program_with_args("../lemma-client", BuildArgs { features, ..Default::default() });
}
