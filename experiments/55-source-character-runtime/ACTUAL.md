# Path B artifact and command record

Current outcome is in [REPORT.md](REPORT.md). This record describes real execution after explicit download/local-validation approval. System Blender 5.2.2 and the MPFB reference belong to root; B did not install or change Blender.

## Identity and evidence

- Upstream commit: `286d33124648501535655a0de811cef55152b9fd`; exact 45-file inventory / 561,909 bytes. Inventory SHA-256: `3c0d8c4d2aac9c398d3b7eb75272ced08f6babafd6bd4577f895e50f10b661ab`.
- Common sample SHA-256: `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`. All 23 source/reference files are verified before derivation.
- `evidence/packaging.patch` / `packaging.json`: permitted packaging/feature changes and original/derived hashes. `actual-Cargo.lock` preserves the 342-package offline graph.
- `evidence/actual-native-check.json` / `.log`: real library check. `actual-adapter-build.json` / `.log`: current B0 CLI build; `-v1` / `-v2` files preserve earlier links.
- B0 binary `target/debug/humentity-probe`: SHA-256 `80785de84c72a542c979be5a0d24a74a3315b87ffebfe083ab019eaf41429a1b`. B0 source and outputs remain preserved during B1.
- `evidence/data-adapter.json`: each used raw hash, each derived data hash, and every unit/encoding conversion. Candidate results never use MPFB output coordinates as inputs.
- `results/run1`, `run2`: retained adapter wiring failures. `results/run3`: all eight real B0 output/log files and summary. Numeric positions, skin indices/weights, rest matrices and inverse binds stay in these ignored local artifacts.
- `evidence/B0-comparison-bound.json` / `B1-comparison-bound.json`: final same-version comparator receipts. B0 fails; B1 passes all eight numerical cases. They include exact recipe/source coverage checks, the comparator hash, variant and the B1 source patch identity. Earlier comparison receipts are retained.
- `evidence/actual-controls.json`: ten subprocess rejection/preservation controls; 69 approved file hashes preserved. `actual_controls.py` uses copied approved source bytes for mutation controls, never edits shared raw inputs, and restores its task-owned config after the rejection check.
- `evidence/threshold-prediction.json`: discarded-row classification and eight-case causal residuals.
- B1 binary `target/debug/humentity-probe-b1`: SHA-256 `d237db1ac959aeb795aceee4767aa8caab4472d2ceb73e9835e631290c57d0e2`. Source patch SHA-256: `9a7cc3f9b0ea52d2dc3dcccbe58c37228ec6a462cea2fedfd4b6381dd242756c`.
- `derived-b1`, `adapter-b1`, `evidence/B1-threshold.patch`, `B1-preparation.json`, `B1-adapter-build.json`: isolated one-line ablation, original-state preservation identities, separate lock/build and binary. B1 is not an unchanged candidate.

The headless plugin set includes Minimal, Asset, Transform, WorldSerialization, Scene, Mesh, Image, Animation and Humentity plugins. It does not initialize a renderer/window or add Humentity's GPU crowd plugin. Unconditional upstream renderer types still require compiling/linking render code. No graphics or Web result is inferred from this.

## Commands

The preparation scripts use exclusive creation and intentionally reject existing output directories/files. Preserve old runs and select a new output name; do not delete input or evidence to make a repeat green.

```sh
python3 experiments/55-source-character-runtime/prepare_build.py
python3 experiments/55-source-character-runtime/build_check.py
python3 experiments/55-source-character-runtime/build_adapter.py
python3 experiments/55-source-character-runtime/prepare_data.py --common-manifest .work/character-approved-20261016/common-sample.json --common-manifest-sha256 2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7
python3 experiments/55-source-character-runtime/run_cases.py --common-manifest .work/character-approved-20261016/common-sample.json --common-manifest-sha256 2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7 --binary-sha256 80785de84c72a542c979be5a0d24a74a3315b87ffebfe083ab019eaf41429a1b --out experiments/55-source-character-runtime/results/NEW-B0-RUN
python3 experiments/55-source-character-runtime/actual_controls.py
python3 experiments/55-source-character-runtime/predict_threshold.py
```

A future rebuild must use a new evidence path or explicitly preserve the prior build receipt first. All Cargo operations use `--offline`; builds use one job and the experiment target. The initial wefty library check succeeded. The later link capture was refused before submission because the shared checkout changed during capture; the required daily log records this and the approved direct local fallback. No extra machine or dependency download was used.

VERIFIED — B0 and B1 actual eight-case execution, final numerical comparisons, source preservation and rejection controls completed. B0 fails; B1 passes the bounded numerical gate.

NOT-RUN — graphics, poses, Web, exact rest/IBM-frame parity, tails and production adoption. No owned build/runtime process remains. Source, derived data, both binaries and caches are intentionally retained for root review.

## B1 reproduction

The one-line ablation is prepared by `prepare_b1.py`, built by `build_b1.py` and run by the same `run_cases.py --variant B1`. Use binary SHA-256 `d237db1ac959aeb795aceee4767aa8caab4472d2ceb73e9835e631290c57d0e2` and a new result directory. `compare.py --variant B0|B1` applies the same frozen numeric test and records `candidate_algorithms_changed` accurately. `B0-preservation-after-B1-build.json` proves the unchanged baseline is retained. `REVIEW-PACKET.md` and `ready-inventory-v2.json` provide the frozen handoff inventory.

## Comparator binding correction

`B0-comparison-bound.json` and `B1-comparison-bound.json` supersede earlier numerical receipts. The actual execution summary must have the correct route/class/common manifest/status, eight complete unique IDs, zero exits, true execution flags and matching per-output hashes. The comparison binds the execution-summary SHA, retained binary, adapter source, build manifest/lock and B1 patch. B0's preserved original summary predates the variant field; missing variant is accepted only for the exact B0 summary/binary identities already preserved in B1-preparation, never by default. Ten actual CLI controls on copied B1 results reject changed bytes/status/hash/missing cases, nonzero exits, false flags and identity changes without new receipts or input writes. No Rust rebuild or candidate rerun was required.

`actual-cli-identity.json` refers to a historical pre-plugin binary. Its original bytes are preserved as `actual-cli-identity-historical-v1.json`; it is not the current B0 binary identity. Current B0 is `80785de84c72a542c979be5a0d24a74a3315b87ffebfe083ab019eaf41429a1b`.
