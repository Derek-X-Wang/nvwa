# Production distribution notices candidate — issue #10

PARTIAL — An exact-byte, reproducible local notice candidate exists for the retained macOS and Web production artifacts. It is not a complete redistribution audit or release approval. The checker verifies integrity and refuses a complete-coverage claim. No production source, root manifest/lockfile, existing licenses, packaging script, bundle, signing setting, branch, index or ref changed.

## Frozen scope and artifact identity

Checkout: `codex/m11-export-notices`, `7851c2e74f757f93774f2d5fa05151562c393012`. This candidate uses current pinned production source and downloaded local dependencies. It excludes the diagnostic experiment 33 patched `wgpu-hal`, its helper and vendor tree. No crate/runtime download, mount, system install, heavyweight compile, browser or server was used. Ten bounded unauthenticated public requests retrieved pinned primary license/provenance data.

| Input / artifact | SHA-256 |
|---|---|
| `Cargo.lock` | `457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73` |
| `dist/Nvwa.app/Contents/MacOS/Nvwa` | `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a` |
| `dist/web/nvwa_studio_bg.wasm` | `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8` |
| Candidate `sample-production-pack/manifest.json` | `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2` |

The retained [artifact identity record](sample-production-pack/inputs/retained-build/artifact-identities.json) originated at an earlier source commit. The collector verified its native/Wasm hashes against the actual retained files and compared 32 retained build-input files byte-for-byte against the present checkout. All 32 match. The retained build source manifest is copied intact. This is source-cohort evidence, not a new build on this commit or CI evidence. No CI rerun was requested.

Retained native build command: `cargo build -p nvwa-studio -p nvwa-cli --release --locked`. The app packaging copies only Studio. The collector reproduces the two-root native resolver selection and verifies that adding CLI changes none of the selected Studio feature sets; the only extra package is `nvwa-cli@0.1.0`. CLI is absent from the app notice candidate. A separately distributed CLI binary needs its own first-party notice and artifact scope. Retained Web command: `bash scripts/build-web.sh release`, whose build is `cargo build -p nvwa-studio --lib --target wasm32-unknown-unknown --locked --release`; wasm-bindgen 0.2.129 then generates Web output. The [commands and results](sample-production-pack/inputs/retained-build/) are retained.

## Coverage boundary

| Graph | Native aarch64-apple-darwin | Web wasm32-unknown-unknown |
|---|---:|---:|
| Target-filtered workspace metadata packages | 390 | 356 |
| Selected Studio normal + build resolver inputs | 307 | 278 |
| Normal edges with procedural macros omitted | 262 | 231 |

The union contains **323 packages**, including three first-party crates. The lockfile contains **525 packages** across targets and optional possibilities. Target-filtered metadata still includes workspace/feature resolver nodes that selected `cargo tree -p nvwa-studio` does not retain. Each copied package is joined to metadata by exact name/version and stores its complete source package ID, source revision, manifest hash, authors and expression.

Normal + build includes build scripts and procedural-macro tool inputs. The normal-only count omits procedural macros, but does not prove linker-retained code. Cargo tree is a selected resolver input graph. Optimizer removal, embedded payload retention, host build units, generated code, and final symbol/link inventory were not independently reconstructed. No exact binary membership is inferred from Cargo.lock, all-features metadata, or a cache directory. `--all-features` would audit a different feature choice and is not used for the production candidate.

The pack contains **1039 indexed files**, including **323 package manifests**, **694 package notice/copyright/attribution text files**, asset/provenance texts, target tree records, and retained build evidence. Original license bytes are copied without concatenation or rewriting. [NOTICE-INDEX.md](NOTICE-INDEX.md) provides a package table. [The manifest](sample-production-pack/manifest.json) records all hashes, authors, copyright lines found in collected texts, target membership and exact features. A generic license file or populated metadata alone does not establish all applicable attributions.

## Distinct asset and code scopes

- Original humanoid fixture: `CC0-1.0`; original scoped statement and provenance remain distinct from repository code. The statement links to the legal instrument but does not contain its full text. No repository-wide license is inferred.
- Nvwa Sans SC derivative: `OFL-1.1`; existing OFL, copyright/NOTICE and derivation provenance copied intact. The source commit, source font hash, derivative hash, renamed family and original copyright remain recorded. The font bytes match the current retained source cohort.
- epaint default fonts: four pinned `.ttf` payload candidates receive separate notices and payload hashes. `Hack-Regular.txt` contains Source Foundry MIT, DejaVu public-domain and Bitstream Vera text. Noto Emoji uses its `OFL.txt`; Ubuntu Light uses `UFL.txt`; emoji-icon-font uses its MIT notice. The embedding declarations from pinned `src/lib.rs` are retained. This does not establish each font's final linker retention.
- epaint library expression stays `(MIT OR Apache-2.0) AND OFL-1.1 AND Ubuntu-font-1.0`. Font notices alone do not supply shared egui MIT/Apache Rust-code texts. Both shared code license files are now separately recovered from the exact egui source commit. Hack's additional embedded notice is retained even though it is not separately expressed in the crate's metadata.
- craft-ui source at `5c874d51eeb3de70e735c8ce87a59a7dedd47675` declares `MIT OR Apache-2.0`, while the selected existing repository table says MIT. Both pinned root license files, NOTICE and ATTRIBUTION.md are copied. The existing packaged MIT file remains separately recorded; no licensing branch is newly selected. The pinned NOTICE identifies adapted code from other Storytold projects and associated revisions/copyright.
- Optional model code, checkpoint and encoder research remain separately scoped in `experiments/05-ai-motion`. No model runtime/weights are bundled by the current packaging scripts. No VaM character or asset was imported. Model-service behavior is unchanged.

## Explicit gaps and decisions

**Completeness is BLOCKED by 45 gap records.** These records are findings, not a count of legal obligations.

The initial local-only pass found 32 packages with no notice text. Pinned primary recovery and matching local repository-root recovery reduced the final missing-license-text count to **21**, including first-party `nvwa-core`, `nvwa-runtime`, and `nvwa-studio`. The remaining 18 third-party entries are: block2 0.5.1 and 0.6.2; constgebra 0.1.4; dispatch2 0.3.1; dispatch 0.2.0; hexf-parse 0.2.1; objc-sys 0.3.5; objc2-app-kit 0.2.2 and 0.3.2; objc2-core-foundation, objc2-core-graphics, objc2-metal and objc2-quartz-core 0.3.2; objc2-encode 4.1.0; objc2 0.5.3 and 0.6.5; profiling 1.0.18; svg_fmt 0.4.5. The original local-only checks and raw controls remain under `evidence-local-only/`; local-only full pack remains `.work/issue10-notices/pack-final-fixed/`.

Ten requests (10-second timeout, 256 KiB per-response bound, no authentication) yielded eight full license-text candidates, one root provenance/licensing explanation and one root tree listing. All ten returned HTTP 200; no failure, 404 or fallback occurred. Exact request URLs, response hashes and bytes remain in [primary/requests.json](primary/requests.json). [The receipts](primary/supplements.json) bind every reused source to its exact repository and commit. The collector verifies these against each package's `.cargo_vcs_info.json`, copies original bytes and rejects a receipt hash mismatch or an unpinned URL.

The egui root MIT/Apache texts come from [49682f8baa058bf49e011035cfbd6e825f88a5ef](https://github.com/emilk/egui/tree/49682f8baa058bf49e011035cfbd6e825f88a5ef). The AccessKit root files were retrieved separately for three exact commits; they are not reused across different revisions. The locally downloaded Bevy and encase repository-root packages match the missing subcrates' exact VCS commits and supply their root MIT/Apache and MIT-0 files without a network request.

The [objc2 pinned root explanation](https://github.com/madsmtm/objc2/blob/7b1abfd750a2cacaea71d6a56ecfb83cb7de560b/LICENSE.md) names declared license choices and discusses Apple SDK-derived source implications, but contains no full license text. It is retained as **notice-only** for the five matching framework crates. Their missing full-text findings remain open, and SDK provenance/applicability remains unresolved. No legal conclusion is drawn from that explanation. Metadata-only/notice-only coverage never becomes complete-text coverage.

Thirteen historical slash expressions such as `MIT/Apache-2.0` remain unchanged and are marked for review. `AND`, `OR` and `WITH` expressions are preserved; neither slash syntax nor an OR expression is silently flattened to a selected license.

Root first-party `LICENSE` is absent, and first-party Cargo license metadata is absent. **UNKNOWN / owner decision required before public release.** The concrete candidate is reviewable; this experiment does not choose MIT or another license for the owner.

Remaining boundaries: source copyright-header/applicability review; Rust standard library/compiler-builtins notices outside Cargo metadata; native system frameworks and dynamic libraries; generated wasm-bindgen JavaScript runtime license scope; full CC0 legal-instrument text; and signing/notarization/clean-machine/public distribution. Generic license texts can contain placeholders; retaining them does not invent a package copyright. No complete attribution or redistribution-compliance claim follows from green integrity checks.

Signing, notarization, clean-machine launch and public binary distribution are **NOT-RUN**. No paid account, Apple Developer Account, machine-wide trust/permission or signing settings changed.

## Reproduce and reject regressions

From the assigned repository root, using the installed Rust 1.95.0 and Python 3.11+ (verified here: 3.14.7; v2 uses the standard-library TOML parser):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/collect.py --output .work/issue10-notices/new-review-pack --scratch .work/issue10-notices/new-review-inputs --supplements experiments/36-distribution-notices/primary/supplements.json
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/check.py .work/issue10-notices/new-review-pack --source-root .
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/check.py .work/issue10-notices/new-review-pack --require-complete
PYTHONDONTWRITEBYTECODE=1 python3 experiments/36-distribution-notices/controls.py .work/issue10-notices/new-review-pack --scratch .work/issue10-notices/new-controls --evidence .work/issue10-notices/new-controls-evidence
```

Use new output/scratch directory names; the collector refuses to overwrite a pack. Cargo runs locked/offline and does not download dependencies. The collector refuses a mismatch in native/Wasm/lock cohort identity or retained production source inputs. The checker supports only the two explicit targets and this exact independently reviewed production cohort. It verifies file hashes, metadata/expression anchors, required package references, target closure/features and retained gaps. The version-2 checker also binds the complete captured schema to a separately preserved, SHA-pinned cohort record. It is an integrity checker, not a signature/authenticity or legal-policy evaluator.

VERIFIED — Two independent collections yielded the same manifest bytes and SHA-256. Eighteen real checker runs passed their expected outcome: baseline green, eight mutations rejected, eight restored greens, and completeness rejected. Mutations removed font OFL, altered craft-ui NOTICE, inserted unknown and malformed expressions, omitted a required Ubuntu-font file reference, substituted an unsupported Windows target, changed selected Bevy features and altered frozen identity. Raw red stdout/stderr, restoration outputs and reproduction identity are retained under [evidence](evidence/). The initial multi-root tree parser rejected Cargo's blank separator; raw failed checker evidence remains in `.work/issue10-notices/check-final.json`, and the captured parser error is retained under evidence. The repaired parser and actual native two-root comparison passed.

The existing native/Web packages also contain fourteen inspected asset/notice files with bytes equal to their repository source; hashes and paths are in `evidence/current-packaged-assets.json`. The new comprehensive candidate was not installed into either package.

Only finite subprocesses were created and synchronously reaped. Control mutation copies were removed after retaining outputs. The sample pack, script sources and scratch collections remain for root review. Preexisting `.tools`, `target` symlinks and shared Cargo caches remain unchanged. No persistent processes or cleanup claims about unrelated tasks.

Potential integration: copy the reviewed complete notice pack through existing native/Web packaging, update the selected license table from the reviewed graph, and choose the first-party license. Those are root/owner decisions; this experiment performs none of them. Issue #10 remains open at its acceptance boundary.
