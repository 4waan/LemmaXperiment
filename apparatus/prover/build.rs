use sp1_build::{build_program_with_args, BuildArgs};

// Same guest build as bin/host/build.rs at the pinned commit, without the
// arena feature forwarding: the baseline is the default MPT backend.
fn main() {
    build_program_with_args("../client", BuildArgs::default());
}
