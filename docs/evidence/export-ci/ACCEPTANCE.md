# Bounded CI and ArtCraft testing checkpoint

2026-10-12. Base: merged PR #34, main `de4ddefab91d21dc6f6d4b81a07b0434fa619273`. Its tree equals the reviewed PR head; the prior archive verifier passed all 60 entries and 31 production inputs. These files record local collection, before the first hosted trial. A later hosted receipt must name its own run and exact head.

The [research report](../../research/artcraft-testing.md) checks pinned primary source and observed public Actions logs. It recommends realistic command/undo/export/corruption tests and independent UI references with deliberate mutation controls. It distinguishes GPU early returns, packaging, mocked desktop sessions and actual rendering. No third-party tests or applications were executed locally.

The adopted candidate adds two standard runner jobs: Ubuntu core/CLI and bounded diagnostics (15 minutes); macOS ARM64 workspace CPU tests, native check and actual Wasm-target compilation (45 minutes). It uses Rust 1.95.0 and the existing lockfile. No product code, dependencies, frozen assets, runner billing settings, cache or artifact uploads change. [Workflow and reproduction](../../../experiments/27-ci-baseline/README.md).

| Status at collection | Check | Evidence |
| --- | --- | --- |
| VERIFIED | Workspace CPU tests | [cargo-test-workspace.log](cargo-test-workspace.log), exit 0; 103 tests, zero failed or ignored |
| VERIFIED | Normal native and actual Wasm target compilation | [native](cargo-check-native.log), [Wasm](cargo-check-wasm.log), both exit 0 |
| VERIFIED | Formatting and strict core/CLI Clippy | [format](cargo-fmt.log), [Clippy](cargo-clippy-core-cli.log), exit 0 |
| VERIFIED | Candidate portable script | [portable.log](portable.log), exit 0; 27 tests are a subset of the 103 above |
| VERIFIED | Committed-fixture and synthetic diagnostic controls | [diagnostics.log](diagnostics.log), exit 0; 77 tests and two collector controls; no new browser/native evidence |
| VERIFIED | Syntax and schema | bash syntax, YAML parsing and existing actionlint 1.7.12 passed |
| VERIFIED | Independent R2 review | [REVIEW.md](REVIEW.md), including actual failure/lock-preservation probes |
| NOT-RUN | Hosted trial, clean build and reduced-debug profile | Not established by local warm-cache results; publication is the next gate |
| NOT-RUN | New native/Web startup, pixels, physical input, GPU and performance | This turn's CPU/compile checks do not renew earlier runtime evidence |

[Environment](environment.json), [action identity](action-identity.json) and [checkpoint](checkpoint.json) retain collection identity. Every command log has a corresponding `.exit` file. GitHub public standard runner minutes are free; larger/GPU runners and storage are separate. The candidate uses only standard runners and uploads no cache/artifact. [Billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

PARTIAL — Local CPU checks and independent review pass. Hosted capacity, rendering, OS input and performance remain separate gates.
