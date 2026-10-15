# 42 — Bounded motion import and same-rig clip export

The isolated Rust importer accepts a strict portable motion document, binds it to separate raw bytes, and produces an actual new GLB animation for the exact original 18-joint Nvwa fixture. All current controls and exported artifacts are **authored_control / ai_generated=false**. No model inference ran. This does not complete M2 or close the broader issue #3/#4 gaps.

**VERIFIED —** Offline standalone Rust build; 19 tests against the actual executable boundary; independently decoded/reloaded GLB; exact sampled rotation/root components; preserved base rig/mesh/skin and original binary payload; staged profile and Work.

**NOT-RUN —** Native/Web playback, product Work validation, genuine generation, real provider raw output, actual provider coordinate compatibility, 30/77-to-18 mapping, performance and production integration.

## Reproduce

From the assigned worktree root, with a lightweight compile slot available:

```sh
python3 -B experiments/42-motion-import/run.py
```

This uses cached dependencies only, `cargo build --offline --jobs 2`, a private `.work/m2-import/target`, then Python stdlib integration tests. The experiment has its own `[workspace]` and `Cargo.lock`; no root dependency/lock/runtime change is needed. No install, model download, paid API, fetched-code execution, GUI, server, or heavy Bevy build runs.

`run.py` extracts the real authored wave, invokes the Rust boundary, reloads/compares the resulting GLB, stages a profile and Work in a fresh private run directory, and converts explicitly synthetic F32 controls. It retains immutable clip/profile/Work bytes in `artifacts/`. It refuses to replace retained artifacts with different bytes. `test-output.txt`, `build-output.txt`, `verification.json` and `.work/m2-import/latest-run.json` record the actual latest run.

Final observed build: **1.49 s**. Final tests: **19 passed, 0 failed, 2.895 s**. These are functional runs, not performance measurements. There are no Rust unit tests claimed; the tests invoke the compiled Rust executable.

## Frozen contract and supported boundaries

[CONTRACT.md](CONTRACT.md) SHA-256: `74bb268930428195242a99cffe6fd3307338be2dbd435583212607185a6bb257`.

Required motion fields include version, provenance kind, explicit skeleton identity/order/tree, rest local translation/XYZW rotation/positive scale, exact coordinate convention, strictly increasing bounded times, per-frame local rotations and absolute root translations. The source has one root; its index is discovered rather than assumed. Unknown fields, identities, layouts and coordinate conventions are rejected. Time samples must remain strictly increasing after float32 conversion.

Input limits are 4 MiB per JSON or raw F32 file, 32 MiB GLB, 77 joints, 151 frames and 5 seconds. JSON duplicate keys are rejected recursively; nonfinite numbers, invalid dimensions, nonunit quaternions, cycles/multiple roots and invalid rest transforms fail. Rest match/order checks bind playable export to the exact frozen Nvwa rig. Serialized normalized output remains compact and <=4 MiB. A serde_json float-roundtrip feature is enabled: the independent reload initially caught tiny numeric changes to untouched rig nodes with the default parser, and final output preserves their decoded numeric values exactly.

Portable raw data and normalized envelope have the same motion fields; the envelope adds provenance and the separate raw file hash. No self hash is required. Units/axes/quaternion conversion is explicitly identity-only: meters/right-handed/Y-up/local/XYZW. Unknown conversion requirements fail.

The narrow `adapt-f32` CLI accepts **two files plus a strict sidecar**, not arbitrary tensors: root positions `[F,3]` and local rotations `[F,J,4]`, row-major float32. It requires the pinned C++ revision `5679ff19ba0a522c0b0516e9a9d402fe1af2c027`, explicit little-endian declaration, counts, skeleton, exact canonical convention and sample times. Exact sizes, finiteness and normalized motion checks apply. The adapter emits portable raw/envelope plus a receipt binding both binary hashes, sidecar hash and portable output hash.

The tested F32 bytes are synthetic authored controls with synthetic joint names, not provider motion or canonical SOMA evidence. `soma30`/`soma77` identify structural count/layout only; no canonical SOMA names/rest registry is claimed. The separate mapping experiment must bind those identities before any semantic mapping claim. Real provider handedness is not explicit in current source evidence. An explicit canonical sidecar is accepted as an authored control assertion, while actual provider coordinate compatibility remains **NOT-RUN**. Rest root height `.988` and sampled absolute root trajectory `.9` remain independent in the synthetic positive test; no height offset is silently added.

NPZ, BVH, Euler, matrices, left-handed, Z-up, nonlocal transforms, arbitrary scale retargeting and general rigs are unsupported. Structural SOMA data cannot be exported onto the target: it returns `retargeting required`.

Generated metadata does not authenticate execution. The boundary requires bound run/raw provenance but currently rejects every `generated` playable import with `generated_evidence_unavailable`, even if a fabricated successful receipt has matching hashes. Parent-observed genuine execution evidence is still absent. No receipt, success boolean, renamed authored motion or synthetic control unlocks a generated artifact.

## Actual authored clip

The source remains `assets/fixtures/nvwa-humanoid.glb`, SHA-256 `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`. Its original-fixture CC0 scope remains the source license; no model/motion license is asserted.

The actual wave contains 73 samples from `0.0416666679084301` through `3.0416667461395264` seconds. Subtracting the first sample produces a `3.0000000782310963` second normalized control. The output contains one animation `imported_authored_control`, index 0, with 18 local rotation channels and one absolute root translation channel, using LINEAR interpolation.

The exporter preserves all original nodes/rest scales, meshes, skins, inverse-bind data and original binary bytes, appending actual new accessors and curve samples. An independent Python decoder reads the emitted animation accessors and compares every exported rotation/root component to the normalized input: **maximum error 0.0**. Float32 time serialization error is separately constrained below `1.2e-7` seconds. This is component/file evidence, not rendering evidence.

V1 keeps nonroot translations/scales at the actual base rest values. The source wave's omitted animated export noise is bounded by **2.5908671830165986e-7 m** for nonroot translation and **2.980232238769531e-7** for scale components. This is deliberately a same-rig control, not lossless arbitrary TRS animation interchange. `fixtures/extraction-receipt.json` retains the measurements.

| Artifact | SHA-256 |
|---|---|
| Portable authored raw | `b79022cb56a6a8f9e6b5003c70ae3f8c5a41b460b9e6ef494e86e198ebe2df3b` |
| Actual exported GLB | `06ded48fbf464e5014f4f529c38a43e4958ef30f3304a9e25a08842a61544a35` |
| Staged/retained Work | `99e67ba6dbc532609e761d35d069937e33c46fb9d0493881f3b1d687306735f0` |
| Staged/retained profile | `6628f07be69e4cace4467bafc0c5344bb30944ae66d81ff2509afeed89d87e79` |

## Rejection and state-preservation controls

The 19 executable integration tests cover valid real authored input; wrong joint/frame dimensions/order; axes/units/order/space/root mode; top-level and nested duplicate keys; truncated raw/GLB bytes; NaN/infinity/invalid quaternions; malformed trees and duplicate names; invalid scales/rest mismatch; nonmonotonic/oversized/f32-collapsed times; unknown schemas/fields; false generated claims and forged successful receipts; raw hash/payload mismatch; existing destinations/unrelated files; oversized JSON and leaf symlink input; valid synthetic F32 conversion; truncated/extra/nonfinite F32 and unsupported metadata; and rejection of unretargeted SOMA export.

Every negative control calls the real Rust executable. Rejection leaves the requested output absent. An existing output directory and its unrelated sentinel remain unchanged. A saved-Work sentinel is byte-identical after every test. The importer accepts no current-Work attachment command and never mutates product state. All input validation/GLB construction precedes exclusive new-output-directory creation. On a later write failure it removes its known output files and then its created directory; it does not recursively remove unrelated contents. Concurrent hostile filesystem mutation is not a tested security boundary.

## Parent runtime handoff and retained resources

Latest private stage at report time:

- Asset root: `.work/m2-import/runs/authored-3fg10qft/assets`
- Work: `.work/m2-import/runs/authored-3fg10qft/authored-control.nvwa.json`

Read `.work/m2-import/latest-run.json` after reproduction for current absolute paths. The Work references `fixtures/clip.glb` with the actual emitted asset hash and clip index 0. With the parent's separate GPU/UI token, launch the chosen renderer using `NVWA_ASSET_ROOT=<absolute staged asset root>` and `--player --benchmark --work <absolute staged Work>`. Choose and record the renderer cohort separately. No renderer was launched here and no product document validator was run.

Changed scope is only `experiments/42-motion-import/**` plus private `.work/m2-import/**`. No Git/GitHub write occurred. Both lightweight compile tokens are released; no owned process/server/GPU workload remains. The private 136 MiB build cache and authored run directories remain for parent review/playback, owned by the parent after handoff. Earlier partial/repeated stages are retained privately; none is production state. Root fixtures, Work, Cargo.toml/Cargo.lock and product Rust code are unchanged.

## R2 provenance hash clarification

The independent R2 review found no P0–P2 blocker and one P3 manifest naming issue. The original `normalized_sha256` identified supplied input bytes, while published `normalized.json` is reserialized. New imports now record **`input_normalized_sha256`** and **`output_normalized_sha256`** explicitly. The positive executable test supplies deliberately reformatted JSON and checks both exact file hashes, requires them to differ, and checks that the ambiguous legacy field is absent.

One targeted offline two-job build passed in **3.58 s**; the existing **19 executable integration tests passed in 4.599 s**. A fresh authored import produced the unchanged clip SHA `06ded48fbf464e5014f4f529c38a43e4958ef30f3304a9e25a08842a61544a35`. New manifest SHA is `5d5478f63382456bff63f77471b59664f619b49272842a3462d989dccf24d0e6`; its input normalized hash is `d10bbeb529556cda3bc12b9fe13fc14882ff2e5a7212e0f47684f094b504678d` and published normalized hash is `337c7745d7482f069a9419080984eba6be9bd6c9d8b429d83a0b53f1834b7f5b`.

Historical `artifacts/manifest.json`, original `SHA256SUMS.json`, prior logs and staged Works/GLBs remain byte-identical. New output metadata is retained separately in `artifacts/manifest-current.json`. `run.py` now retains that filename so a reproduction does not replace the historical manifest. The full reproduction driver was not rerun after this filename-only change; its importer path was rebuilt and exercised by all 19 boundary tests and the fresh import. `SHA256SUMS-current.json` inventories the current source cohort; the original index remains historical review evidence.

Exact before/after hashes, source diff, build/test logs and fresh published artifact are under `.work/m2-import/provenance-hash-fix/`. Both input/output hashes are assertions about actual bytes, not generation authentication. Contract hash remains unchanged.

Parent evidence subsequently validates the original authored, naive and calibrated staged Works with the unchanged product `nvwa-cli`: all three returned `valid:true`, `asset_checked:true`, exit 0. See `.work/m2-import/parent-runtime/cli-validation.json`, CLI binary SHA `c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e`. This was parent-run validation, not a new worker execution. The earlier product-validation NOT-RUN entries describe the initial handoff. Native/Web GUI evidence remains parent-owned and is not claimed here.

VERIFIED — Explicit input/output manifest hashes, 19 boundary tests, unchanged clip bytes and 13 historical files; parent-recorded product validation of all three staged Works. Compile gate released. No worker UI/GPU/model/Git/GitHub action or persistent process.
