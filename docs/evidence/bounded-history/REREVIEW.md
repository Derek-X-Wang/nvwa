# Targeted R2 rereview — Nvwa #8 additive CLI fix

Outcome: accepted within the reviewed scope. The prior P2 f32-widening finding is resolved for the reported reproduction. No open finding or related regression was identified.

## Fix inspection

At `crates/nvwa-cli/src/main.rs:93–99`, the final implementation first serializes the typed character profile directly with `serde_json::to_string`, then parses that JSON to add `editor_retention`. This preserves the original f32 decimal serialization before composing the final JSON object. The rejected implementation serialized the Rust f32 directly into `Value`, which widened it to f64 before choosing its JSON decimal representation.

The difference from the frozen rejected source is limited to this conversion and explanatory comment. Existing top-level profile keys remain alongside the additive metadata. The `inspect` branch, command parsing, file read/save behavior, and retention policy metadata are unchanged by the correction. The extra temporary string and parse are confined to capability discovery; no session retention accounting changed.

## Execution evidence

- Inspected `additive-checks/evidence.json`: rejected CLI hash `be678f9530e053b20dbe7194109e469843ab839a94b5da8ff2bbb0e8ba7ca7d7`; real capability probe exit 1. Its raw log reports `Existing profile capability changed: clips`, matching the initial finding.
- Inspected `additive-final-checks/evidence.json` and raw logs: final CLI hash matches below; 27 core/CLI tests pass, real capability probe passes, strict core/CLI clippy passes, and formatting exits 0. These build/test/lint records were produced by integration, not rerun by this reviewer.
- Independently reran the read-only real capability probe against the existing `/tmp/nvwa-bounded-history-target/debug/nvwa-cli`: exit 0. No build was run. The probe asserts exact existing fixture profile values, the sole additive top-level key, all policy metadata, document-only inspect output, help commands, and an unchanged input file.
- Independently hashed the executed CLI binary: `cd8d87b35aa0607da45b92ff3c1297c44bdf05dfef78b865944a82a763efdb12`, matching the preserved green probe log. Fixture hash: `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`.
- Inspected saved `capability-output.json`: idle/wave duration is again `3.0416667`; turn is `4.0416665`.

## Exact inspected source hashes (SHA-256)

| Source | SHA-256 |
| --- | --- |
| `crates/nvwa-cli/src/main.rs` | `8ddf575e24de088b319aed601214055ce2fa3abba916e3effb04e612d9b0700b` |
| `crates/nvwa-core/src/lib.rs` | `4c2f06d56b43e3849ee9040c8c5c5f999401816f8b64431d0dbfa240d952b797` |
| `crates/nvwa-core/src/bounded_history_tests.rs` | `4d20f38f8ee7f270a469af64ab0de0c357d8b5e0e6d73a8abd856c3840762e3b` |
| `docs/adr/0005-portable-document-and-commands.md` | `35bb5cd4669adc4d95f406cec446b664adbb229d05c4368c541ef511c7538f4c` |

All four dispatch hashes were checked. Core/test/ADR content is unchanged from the first R2 review, so the earlier bounded acceptance of the retention state machine continues to apply.

## Limits and disposition

The independent executable replay covers the supplied default profile, not an exhaustive sweep of every valid float/profile. Core tests and lint results were inspected as preserved execution evidence. No fresh builds, GUI/GPU/Wasm checks, release checks, or exact heap/RSS measurements were performed. No implementation, fixture, Git, or external writes were made; the only write is this rereview report.

VERIFIED — reported f32 regression closed by final-source inspection, matching red/green evidence, and independent real-CLI capability probe (exit 0). No open R2 finding remains within this scope.
