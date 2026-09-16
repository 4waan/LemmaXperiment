use sp1_build::{build_program_with_args, BuildArgs};

// Same guest build as bin/host/build.rs at the pinned commit: the `arena`
// feature of this crate is forwarded to the guest so the ELF's MPT backend and
// witness codec match the host's. Without it the baseline default MPT is built.
fn main() {
    let features = if std::env::var_os("CARGO_FEATURE_ARENA").is_some() {
        vec!["arena".to_string()]
    } else {
        Vec::new()
    };
    build_program_with_args("../client", BuildArgs { features, ..Default::default() });
}
