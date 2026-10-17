# B1 production Work integration (#74)

Status: implementation and bounded validation in progress. Actual native/Web launch, exchange, final-head CI and merged-main CI are separate pending gates. No B1 appearance, continuous-motion or performance acceptance is claimed.

## Reproduce

```sh
cargo build -p nvwa-cli --locked
mkdir -p .work/b1-example
target/debug/nvwa-cli new-b1 assets .work/b1-example/character.nvwa.json
target/debug/nvwa-cli describe-capabilities .work/b1-example/character.nvwa.json
target/debug/nvwa-cli validate .work/b1-example/character.nvwa.json assets
cargo run -p nvwa-studio --locked -- --work "$PWD/.work/b1-example/character.nvwa.json"
```

For the Web build, copy that Work to `dist/web/works/character.nvwa.json`, serve the existing static bundle, then open `/?work=works/character.nvwa.json`. Studio's New B1 button constructs the same canonical profile. Open/new candidates authenticate assets and build the real CPU display before replacing the current Work. Save during a pending candidate saves the committed Work. Editing cancels a pending candidate. The original GLB is the default entry and retains authored animation.

```sh
python3 -B scripts/verify-b1-inputs.py
python3 -B scripts/test-b1-inputs.py
python3 -B -O scripts/test-b1-inputs.py
bash scripts/check-b1-work.sh
```

The last script is the full offline CPU/native/Web package gate and requires an existing wasm-bindgen0.2.129 tool. `NVWA_WASM_BINDGEN` can point to an existing tool; the script does not install it. Native/Web graphical launch remains separate. [Source admission](SOURCE-ADMISSION.md) preserves provenance, licenses, the frozen baseline and the narrow production lazy-resource scheduling adaptation.

## Evidence recorded so far

- Actual no-window CLI independently created a schema3 B1 Work, validated the descriptor and all thirteen raw files, and read back the expected two zero-default parameters, neutral pose and empty continuous timeline.
- Core/CLI: 47 passing tests (30 core, 17 CLI), strict Clippy and formatting. Binary tests cover advertised command execution and asset rejection/output preservation. They are separate from renderer evidence.
- Source input controls: 17 test methods, including28 real mutation cases, pass in normal and optimized Python. These reject an always-neutral pose lookup, changed adapter/dependency code, source inventory and provenance mutation, missing/extra files, asset corruption and symlinks using isolated copies. Every negative first verifies a valid complete copy.
- Admitted source adapter compiled in a local immutable wefty snapshot (run `run_a5ba3a5ee7d9bc622fc33575470329a7`, 2m14s). This predates the scheduling-only production guard adaptation and is not current full product build proof.
- Native runtime/Studio including test targets passed compile-only checks. The latest vertex-assertion strengthening and actual test execution remain separate pending gates.
- Independent cross-model reviews found and statically re-reviewed legacy startup decoding, Web entropy feature, canceled-edit readiness, CLI asset-root requirement and source-integrity controls. Test execution and graphical acceptance remain integration-owner gates.

## Retained limits

Only the approved MakeHuman/MPFB body and sportsuit, two signed shape parameters and five authored static diagnostic poses are admitted. B1 GPU4 remains HOLD; A remains a numeric control. Original numeric8x5 and prototype native/Web results remain historical experiments53–59, not production Work evidence. Cloth folds/poke-through, appearance, normals at extreme folds, continuous B1 animation and performance are unaccepted. #3 remains blocked; #4 retains its measurement gaps; the older M2 action-quality HOLD is unchanged. Public binary release notice closure, signing/notarization and clean-machine launch remain unverified.
