# CI baseline report — 2026-10-12

Recommendation: adopt this two-job candidate as the first automatic PR/main CI,
then observe one cold standard-runner run before treating its capacity and timing
as established. Keep visual, GPU, physical input and packaging acceptance as
separate explicit gates. This is a bounded candidate for the existing code.
It changes no product source, dependencies, lockfile or contract. The parent
authorized the final candidate copy to `.github/workflows/ci.yml`.

## Current source and toolchain

Validation used checkout `de4ddefab91d21dc6f6d4b81a07b0434fa619273`,
branch `codex/export-repro-ci`, local Mac ARM64, Rust/Cargo1.95.0,
Python3.14.7 and Node25.8.2. `.work/ci-baseline/environment.json` records
full versions and lock hash. `target` and `.tools` were pre-existing symlinks
shared with the main checkout. The parent granted exclusive Cargo ownership;
all Cargo commands ran sequentially with `CARGO_BUILD_JOBS=2`.

Current manifests define core, runtime, studio and CLI crates. Core and CLI do
not depend on Bevy; runtime and studio share pinned Bevy0.19.1 window/render
features. Studio additionally uses bevy_egui0.42.0 and a revision-pinned
craft-ui Git dependency. `rust-toolchain.toml` pins1.95.0 and the Wasm target.
These facts were read from the current files rather than inferred from CI green.

`bevy_winit` is enabled while Linux X11/Wayland backend features are absent.
Full native Linux portability is therefore not assumed. The proposed Ubuntu
lane builds only core/CLI. `scripts/build-web.sh` expects the exact project-local
`wasm-bindgen-0.2.129-aarch64-apple-darwin` tool; its installer is Apple ARM only.
The existing packaging path is not a portable Linux Web build command.
The candidate deliberately performs the actual `wasm32-unknown-unknown` Rust
compile check without invoking that installer or claiming a generated Web bundle.

## Local verification

All listed runs returned exit0. Raw logs and `.exit` files are in
`.work/ci-baseline/`; they are local evidence, not hosted run records.

| Evidence ID / command | Result | Meaning |
| --- | --- | --- |
| `cargo-test-workspace` — `cargo test --workspace --locked` |103 tests | Native compilation and CPU execution of existing workspace tests |
| `cargo-check-native` — `cargo check --workspace --locked` | pass | Normal native workspace targets compile outside test configuration |
| `cargo-check-wasm` — `cargo check -p nvwa-studio --lib --target wasm32-unknown-unknown --locked` | pass | Actual current Web-target Rust compilation; no Wasm execution |
| `cargo-fmt` — `cargo fmt --all --check` | pass | Current workspace formatting |
| `cargo-clippy-core-cli` — strict selected Clippy, all targets, locked | pass | Core/CLI diagnostics; runtime/studio Clippy excluded |
| `portable` — candidate script |27 tests plus format/strict Clippy | Script exercised locally on Mac; Ubuntu execution NOT-RUN |
| `diagnostics` — candidate script |77 tests and 2 collector controls | Committed fixture/capture and helper semantics; no new browser/native evidence |
| `bash -n check.sh`; Ruby YAML parse; existing actionlint1.7.12 | pass | Shell/YAML syntax and workflow schema/action expressions; hosted execution NOT-RUN |

The 103 workspace tests comprise core21 (8 bounded history,13 transactions),
CLI6 (4 offline,2 sequence), runtime35 and studio41. The 27 portable tests are
that same core/CLI subset; they do not add 27 unique tests to the workspace count.
No tests were added that merely restate this workflow.

Meaningful real command and failure boundaries already covered include:

- `typed_ui_and_offline_cli_produce_equivalent_documents`: actual CLI subprocess
  and typed `Editor` command paths agree after undo/redo and JSON roundtrip.
- `failed_batch_does_not_overwrite_existing_output`,
  `failed_cli_batch_preserves_input_and_existing_work`, and
  `cli_rejects_duplicate_map_keys_and_preserves_unrelated_save_sibling`:
  actual CLI rejects bad command/JSON input and preserves files.
- `missing_corrupt_and_mismatched_assets_are_rejected`,
  `unknown_fields_duplicate_keys_oversized_json_and_schema_are_rejected`, and
  bounded history atomicity/eviction/retry tests: current core paths reject bad
  input and keep content/history consistent.
- `corrupt_and_missing_sources_recover_on_same_path_work_open`,
  `ready_character_replaced_by_corrupt_bytes_is_not_exposed`,
  `matching_hash_glb_with_gltf_parse_error_surfaces_and_recovers`, and
  overlapping-open tests: current runtime uses its reader/loader harness and
  real GLB data to check loading, errors and stale result fencing. Reader gates
  are test harnesses; these tests do not exercise browser network or GPU pixels.
- Studio tests exercise production editor/input/platform helper paths, including
  discarded UI passes, keyboard ownership and import limits. CPU tests do not
  prove the physical window, OS candidate UI or rendered placement.

Experiment20 reads the committed capture
`docs/evidence/input-scale/observed/chrome-tab-return-scale.json` and checks it
alongside in-memory mutants. This validates checker sensitivity against that
historical packet; it collects no new browser or native evidence.

Diagnostic coverage is experiments20 geometry15,22 fixed CSS controls26,
23 provenance checker20,24 HTTP boundary11,25 export adapter5. Two Node collector
controls additionally run actual collector source against DOM-shaped/Node
harnesses. Export controls are explicitly SYNTHETIC and establish neither PNG
pixels nor durable browser downloads. The experiment23 package preparation tests
are excluded because they require historical frozen build bytes and a private
parent directory; a fresh hosted checkout does not contain that cohort.

## Hosted runner and security basis

GitHub currently lists public standard `ubuntu-24.04` as x64,4CPU,16GB RAM and
14GB SSD; `macos-14` as ARM64 M1,3CPU,7GB RAM and14GB SSD. Standard hosted use is
free and unlimited for public repositories. These are runner-minute facts;
storage and paid larger/GPU runners are separate. Nvwa visibility was verified
by the parent. [GitHub runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
[GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

The complete pre-existing local target cache is26GB across prior native/Web
builds. That is not a measured size for a clean candidate build. It is enough to
reject uploading/caching the whole target as the baseline. CI disables debug
info/incremental output to reduce disk and runs one Mac compiler process; the
14GB cold-build capacity and45-minute bound remain NOT-RUN. No hosted run,
benchmark, runner upgrade or billing change was made.

The sole action is `actions/checkout` v7.0.1 pinned to
`3d3c42e5aac5ba805825da76410c181273ba90b1`. The official tag API resolved to that
exact commit, and its official commit verification was true. Downloaded
`action.yml` was inspected as text only and saved under `.work/ci-baseline/`;
`action-identity.json` records its SHA256. No downloaded action/source scripts
were executed locally. [Official release](https://github.com/actions/checkout/releases/tag/v7.0.1)
[Official tag API](https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1)
[Official commit](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1)

Full SHA pinning and verification against the action owner follow GitHub's
security guidance. [Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
`contents: read` leaves unspecified scopes disabled, and checkout uses
`persist-credentials: false`. No PR-controlled string is interpolated into shell
commands. [Workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)
[Checkout source](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1)

The candidate uses no cache steps or cache action. Fork PRs may read base caches;
cache contents are neither signed nor trusted and must not contain credentials.
Any later cache proposal must be scoped and reviewed separately.
[Cache permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)

## Adoption boundary and limits

The parent authorized adoption after the bounded source review. The final
candidate was copied to `.github/workflows/ci.yml`, with the candidate-only
header removed. Existing actionlint1.7.12 passed on both files; it validates
workflow schema/action expressions beyond plain YAML. No remote write or hosted
execution was made by this worker. The parent retains R2 review and publication
ownership. No owned background process remains; compile token released.

NOT-RUN: hosted Actions, fresh/cold build, CI reduced-debug profile, actual Linux
execution, Linux renderer, Windows, runtime/studio strict Clippy, release/native
packaging, wasm-bindgen JS/asset packaging, browser Wasm execution, screenshot
pixels, original DPR, GPU/adapter availability, visual reference comparison,
physical keyboard/clipboard/IME, provider attribution, production networking,
performance acceptance, fuzzing, and mutation-red validation of this baseline.
Existing negative-input tests did run; no claim is made that these results prove
all historical mutations fail. A checked Wasm target cannot establish a physical
IME input source or native/Web rendering acceptance.

PARTIAL — current local CPU tests and bounded diagnostics pass; candidate is
reviewable and runnable locally, while hosted capacity and runtime acceptance
remain unverified.
