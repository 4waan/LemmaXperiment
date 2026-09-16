//! lemma-fixtures: runs the independent trie fixtures (evaluation/fixtures/trie)
//! against one `rsp_mpt::StateTries` backend of the pinned RSP, through the
//! public entry points the pipeline itself uses: `EthereumState::from_proofs`
//! (the host's witness construction from EIP-1186 proofs), the `arena`
//! re-encoding when that backend is selected, and
//! `rsp_client_executor::io::build_trie_db` (the guest's state-root and
//! storage-root checks). Expected outcomes come from the py-trie oracle
//! recorded in the fixture file, never from another backend. Panics inside the
//! backend count as rejections, which is what they are in the guest.

use std::{
    cell::RefCell,
    collections::BTreeMap,
    fs,
    panic::{catch_unwind, AssertUnwindSafe},
    path::PathBuf,
    time::Instant,
};

use alloy_primitives::{map::HashMap, Address, Bytes, B256, U256};
use clap::Parser;
use reth_primitives_traits::{Account, SealedHeader};
use reth_trie::{AccountProof, HashedPostState, HashedStorage, Nibbles, StorageProof, TrieAccount};
use revm::state::Bytecode;
use rsp_client_executor::io::build_trie_db;
use rsp_mpt::{ArenaTries, EthereumState, StateTries};
use serde::{Deserialize, Serialize};

#[derive(Debug, Parser)]
struct Args {
    /// Fixture file (evaluation/fixtures/trie/fixtures.json).
    #[clap(long)]
    fixtures: PathBuf,
    /// Backend under test: `pointer` (upstream EthereumState) or `arena`
    /// (the upstream arena feature, the seeded existing-capability control).
    #[clap(long, default_value = "pointer")]
    backend: String,
    /// Where to write the JSON results.
    #[clap(long, default_value = "fixture-results.json")]
    out: PathBuf,
}

// ------------------------------------------------------------- fixture file --

#[derive(Deserialize)]
struct Fixtures {
    schema: String,
    generator: serde_json::Value,
    cases: Vec<Case>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Case {
    id: String,
    family: String,
    #[allow(dead_code)]
    description: String,
    state_root: B256,
    expected_build: String,
    proofs: Vec<ProofEntry>,
    queries: Vec<Query>,
    updates: Option<Updates>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct ProofEntry {
    address: Address,
    nonce: u64,
    balance: U256,
    code_hash: B256,
    storage_hash: B256,
    account_proof: Vec<Bytes>,
    storage_proof: Vec<StorageEntry>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct StorageEntry {
    hashed_slot: B256,
    value: U256,
    proof: Vec<Bytes>,
}

#[derive(Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct Query {
    kind: String,
    hashed_address: B256,
    hashed_slot: Option<B256>,
    expect: String,
    account: Option<ExpectedAccount>,
    value: Option<U256>,
    note: Option<String>,
}

#[derive(Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct ExpectedAccount {
    nonce: u64,
    balance: U256,
    storage_root: B256,
    code_hash: B256,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Updates {
    accounts: BTreeMap<B256, Option<UpdAccount>>,
    storages: BTreeMap<B256, UpdStorage>,
    expected_state_root: B256,
    expected_storage_roots: BTreeMap<B256, B256>,
    expect: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct UpdAccount {
    nonce: u64,
    balance: U256,
    code_hash: Option<B256>,
}

#[derive(Deserialize)]
struct UpdStorage {
    wiped: bool,
    slots: BTreeMap<B256, U256>,
}

// ------------------------------------------------------------------ results --

#[derive(Serialize)]
struct Results {
    backend: String,
    fixtures_schema: String,
    generator: serde_json::Value,
    cases: usize,
    passed: usize,
    failed: usize,
    by_family: BTreeMap<String, FamilyCount>,
    seconds: f64,
    results: Vec<CaseResult>,
}

#[derive(Serialize, Default)]
struct FamilyCount {
    cases: usize,
    passed: usize,
    queries: usize,
    updates: usize,
}

#[derive(Serialize)]
struct CaseResult {
    id: String,
    family: String,
    expected_build: String,
    build: String,
    build_pass: bool,
    queries: Vec<QueryResult>,
    repeat_consistent: bool,
    update: Option<UpdateResult>,
    pass: bool,
}

#[derive(Serialize)]
struct QueryResult {
    kind: String,
    expect: String,
    got: String,
    pass: bool,
    note: Option<String>,
}

#[derive(Serialize)]
struct UpdateResult {
    expect: String,
    expected_state_root: B256,
    got: String,
    storage_roots: Vec<StorageRootResult>,
    pass: bool,
}

#[derive(Serialize)]
struct StorageRootResult {
    hashed_address: B256,
    expected: B256,
    account_leaf: String,
    pass: bool,
}

// --------------------------------------------------------------- panics --

thread_local! {
    static LAST_PANIC: RefCell<Option<String>> = const { RefCell::new(None) };
}

fn install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let msg = info
            .payload()
            .downcast_ref::<String>()
            .cloned()
            .or_else(|| info.payload().downcast_ref::<&str>().map(|s| s.to_string()))
            .unwrap_or_else(|| "panic".to_string());
        let loc = info.location().map(|l| format!(" at {}:{}", l.file(), l.line())).unwrap_or_default();
        LAST_PANIC.with(|p| *p.borrow_mut() = Some(format!("panic: {msg}{loc}")));
    }));
}

fn take_panic() -> String {
    LAST_PANIC.with(|p| p.borrow_mut().take()).unwrap_or_else(|| "panic".to_string())
}

/// Runs `f`, turning a panic into `Err(message)`.
fn guarded<R>(f: impl FnOnce() -> R) -> Result<R, String> {
    catch_unwind(AssertUnwindSafe(f)).map_err(|_| take_panic())
}

// ------------------------------------------------------------ build --

fn account_proofs(case: &Case) -> HashMap<Address, AccountProof> {
    let mut proofs = HashMap::default();
    for e in &case.proofs {
        let storage_proofs = e
            .storage_proof
            .iter()
            .map(|s| StorageProof {
                key: s.hashed_slot,
                nibbles: Nibbles::unpack(s.hashed_slot),
                value: s.value,
                proof: s.proof.clone(),
            })
            .collect();
        proofs.insert(
            e.address,
            AccountProof {
                address: e.address,
                info: Some(Account { nonce: e.nonce, balance: e.balance, bytecode_hash: Some(e.code_hash) }),
                proof: e.account_proof.clone(),
                storage_root: e.storage_hash,
                storage_proofs,
            },
        );
    }
    proofs
}

/// The host-side construction every backend starts from.
fn build_state(case: &Case) -> Result<EthereumState, String> {
    let proofs = account_proofs(case);
    match guarded(|| EthereumState::from_proofs(case.state_root, &proofs)) {
        Ok(Ok(state)) => Ok(state),
        Ok(Err(e)) => Err(format!("from_proofs: {e:?}")),
        Err(p) => Err(format!("from_proofs: {p}")),
    }
}

/// The guest-side checks (`initialize witness db`), unchanged upstream code.
fn guest_checks<T: StateTries>(tries: &T, anchor: B256) -> Result<(), String> {
    let headers: Vec<SealedHeader> = Vec::new();
    match guarded(|| build_trie_db(tries, anchor, std::iter::empty::<&Bytecode>(), &headers).map(|_| ())) {
        Ok(Ok(())) => Ok(()),
        Ok(Err(e)) => Err(format!("build_trie_db: {e:?}")),
        Err(p) => Err(format!("build_trie_db: {p}")),
    }
}

// ----------------------------------------------------------- queries --

fn fmt_account(a: &TrieAccount) -> String {
    format!("nonce={} balance={:#x} storageRoot={:#x} codeHash={:#x}", a.nonce, a.balance, a.storage_root, a.code_hash)
}

fn run_query<T: StateTries>(tries: &T, q: &Query) -> (String, bool, bool) {
    // returns (got, matched_expectation, rejected)
    match q.kind.as_str() {
        "account" => match guarded(|| tries.account(q.hashed_address)) {
            Err(p) => (p, q.expect == "reject", true),
            Ok(None) => ("absent".to_string(), q.expect == "absent", false),
            Ok(Some(a)) => {
                let got = fmt_account(&a);
                let pass = q.expect == "present"
                    && q.account.as_ref().is_some_and(|e| {
                        e.nonce == a.nonce && e.balance == a.balance && e.storage_root == a.storage_root && e.code_hash == a.code_hash
                    });
                (got, pass, false)
            }
        },
        "storage" => {
            let slot = q.hashed_slot.expect("storage query needs hashedSlot");
            match guarded(|| tries.storage_value(q.hashed_address, slot)) {
                Err(p) => (p, q.expect == "reject", true),
                Ok(v) => (format!("{v:#x}"), q.expect == "value" && q.value == Some(v), false),
            }
        }
        other => (format!("unknown query kind {other}"), false, false),
    }
}

fn run_queries<T: StateTries>(tries: &T, case: &Case, build_may_reject: bool) -> (Vec<QueryResult>, bool) {
    let forward: Vec<_> = case.queries.iter().map(|q| run_query(tries, q)).collect();
    // reordered and repeated lookups must not change any answer
    let backward: Vec<_> = case.queries.iter().rev().map(|q| run_query(tries, q)).collect();
    let repeat: Vec<_> = case.queries.iter().map(|q| run_query(tries, q)).collect();
    let consistent = forward.iter().zip(backward.iter().rev()).all(|(a, b)| a.0 == b.0)
        && forward.iter().zip(repeat.iter()).all(|(a, b)| a.0 == b.0);
    let results = case
        .queries
        .iter()
        .zip(forward)
        .map(|(q, (got, matched, rejected))| QueryResult {
            kind: q.kind.clone(),
            expect: q.expect.clone(),
            pass: matched || (build_may_reject && rejected),
            got,
            note: q.note.clone(),
        })
        .collect();
    (results, consistent)
}

// ------------------------------------------------------------ updates --

fn hashed_post_state(u: &Updates) -> HashedPostState {
    let mut post = HashedPostState::default();
    for (hashed, acct) in &u.accounts {
        post.accounts.insert(
            *hashed,
            acct.as_ref().map(|a| Account { nonce: a.nonce, balance: a.balance, bytecode_hash: a.code_hash }),
        );
    }
    for (hashed, s) in &u.storages {
        let mut hs = HashedStorage::new(s.wiped);
        for (slot, value) in &s.slots {
            hs.storage.insert(*slot, *value);
        }
        post.storages.insert(*hashed, hs);
    }
    post
}

fn run_update<T: StateTries>(tries: &mut T, u: &Updates) -> UpdateResult {
    let expect = u.expect.clone().unwrap_or_else(|| "ok".to_string());
    let post = hashed_post_state(u);
    let applied = guarded(|| tries.update(&post));
    let root = match applied {
        Err(p) => Err(p),
        Ok(()) => guarded(|| tries.state_root()),
    };
    let mut storage_roots = Vec::new();
    let mut roots_pass = true;
    if root.is_ok() {
        for (hashed, expected) in &u.expected_storage_roots {
            let leaf = guarded(|| tries.account(*hashed));
            let (text, pass) = match &leaf {
                Ok(Some(a)) => (format!("{:#x}", a.storage_root), a.storage_root == *expected),
                Ok(None) => ("account absent".to_string(), false),
                Err(p) => (p.clone(), false),
            };
            roots_pass &= pass;
            storage_roots.push(StorageRootResult { hashed_address: *hashed, expected: *expected, account_leaf: text, pass });
        }
    }
    let (got, pass) = match (&root, expect.as_str()) {
        (Err(p), "reject") => (p.clone(), true),
        (Err(p), _) => (p.clone(), false),
        (Ok(r), "reject") => (format!("{r:#x}"), *r != u.expected_state_root),
        (Ok(r), _) => (format!("{r:#x}"), *r == u.expected_state_root && roots_pass),
    };
    UpdateResult { expect, expected_state_root: u.expected_state_root, got, storage_roots, pass }
}

// --------------------------------------------------------------- cases --

fn run_on<T: StateTries>(tries: &mut T, case: &Case, build_text: String) -> CaseResult {
    let build_may_reject = case.expected_build == "ok-or-reject";
    let (queries, repeat_consistent) = run_queries(tries, case, build_may_reject);
    let update = case.updates.as_ref().map(|u| run_update(tries, u));
    let build_pass = case.expected_build == "ok" || build_may_reject;
    let pass = build_pass && repeat_consistent && queries.iter().all(|q| q.pass) && update.as_ref().is_none_or(|u| u.pass);
    CaseResult {
        id: case.id.clone(),
        family: case.family.clone(),
        expected_build: case.expected_build.clone(),
        build: build_text,
        build_pass,
        queries,
        repeat_consistent,
        update,
        pass,
    }
}

fn rejected(case: &Case, why: String) -> CaseResult {
    let build_pass = case.expected_build == "reject" || case.expected_build == "ok-or-reject";
    CaseResult {
        id: case.id.clone(),
        family: case.family.clone(),
        expected_build: case.expected_build.clone(),
        build: format!("reject: {why}"),
        build_pass,
        queries: Vec::new(),
        repeat_consistent: true,
        update: None,
        pass: build_pass,
    }
}

fn run_case(case: &Case, backend: &str) -> CaseResult {
    let state = match build_state(case) {
        Ok(s) => s,
        Err(why) => return rejected(case, why),
    };
    match backend {
        "pointer" => {
            let mut tries = state;
            if let Err(why) = guest_checks(&tries, case.state_root) {
                return rejected(case, why);
            }
            run_on(&mut tries, case, "ok".to_string())
        }
        "arena" => {
            // The host re-encodes the pointer state into the arena witness and the guest
            // decodes it zero-copy, exactly as the `arena` feature wires it.
            let blob = match guarded(|| state.to_arena_witness()) {
                Ok(b) => b,
                Err(p) => return rejected(case, format!("to_arena_witness: {p}")),
            };
            let bump = bumpalo::Bump::new();
            let mut tries = match guarded(|| ArenaTries::decode(&bump, &blob)) {
                Ok(Ok(t)) => t,
                Ok(Err(e)) => return rejected(case, format!("ArenaTries::decode: {e:?}")),
                Err(p) => return rejected(case, format!("ArenaTries::decode: {p}")),
            };
            if let Err(why) = guest_checks(&tries, case.state_root) {
                return rejected(case, why);
            }
            run_on(&mut tries, case, format!("ok (arena witness {} bytes)", blob.len()))
        }
        other => panic!("unknown backend {other}"),
    }
}

fn main() -> eyre::Result<()> {
    let args = Args::parse();
    let text = fs::read_to_string(&args.fixtures)?;
    let fixtures: Fixtures = serde_json::from_str(&text)?;
    install_panic_hook();

    let start = Instant::now();
    let mut results = Vec::new();
    let mut by_family: BTreeMap<String, FamilyCount> = BTreeMap::new();
    for case in &fixtures.cases {
        let r = run_case(case, &args.backend);
        let f = by_family.entry(case.family.clone()).or_default();
        f.cases += 1;
        f.passed += r.pass as usize;
        f.queries += r.queries.len();
        f.updates += r.update.is_some() as usize;
        let status = if r.pass { "pass" } else { "FAIL" };
        println!("{status} {:44} build={} queries={} update={}", r.id, r.build, r.queries.len(), r.update.as_ref().map_or("-".to_string(), |u| u.got.clone()));
        for q in r.queries.iter().filter(|q| !q.pass) {
            println!("       query {} expect={} got={} {}", q.kind, q.expect, q.got, q.note.clone().unwrap_or_default());
        }
        if let Some(u) = r.update.as_ref().filter(|u| !u.pass) {
            println!("       update expect={} expectedRoot={:#x} got={}", u.expect, u.expected_state_root, u.got);
            for s in u.storage_roots.iter().filter(|s| !s.pass) {
                println!("       storage root {:#x} expected={:#x} leaf={}", s.hashed_address, s.expected, s.account_leaf);
            }
        }
        if !r.repeat_consistent {
            println!("       reordered or repeated lookups gave different answers");
        }
        results.push(r);
    }
    let passed = results.iter().filter(|r| r.pass).count();
    let failed = results.len() - passed;
    let out = Results {
        backend: args.backend.clone(),
        fixtures_schema: fixtures.schema,
        generator: fixtures.generator,
        cases: results.len(),
        passed,
        failed,
        by_family,
        seconds: start.elapsed().as_secs_f64(),
        results,
    };
    fs::write(&args.out, serde_json::to_string_pretty(&out)?)?;
    println!("{} cases, {} passed, {} failed, backend {} -> {}", out.cases, passed, failed, args.backend, args.out.display());
    if failed > 0 {
        std::process::exit(1);
    }
    Ok(())
}
