# Experiment 26: bounded Blender export byte drift

2026-10-12. Resolves the investigation alternative in [issue 7](https://github.com/Derek-X-Wang/nvwa/issues/7): document which fields vary without changing the frozen published fixture.

Two independent Blender exports remain **not byte-identical**. This pair isolates actual GLB variation to eye triangle sequence order, associated accessor sharing/storage layout, and small float32 base/morph normal changes. Exact normal values differ. This is a measured bound for this pair, not a guarantee for future exports or complete semantic equivalence.

No generator, validator, source asset, profile, provenance, dependency, or lockfile change was made. All work belongs to this experiment and its private `.work/export-drift/` outputs. No publication, rendering, GPU work, installation, machine settings, or extra Blender process was used.

## Control and actual processes

Installed Blender 3.3.1 arm64, build `b292cfe5a936`, bundled Khronos exporter 3.3.32. The installed exporter's version and relevant source hashes are recorded in `installed-exporter-sources.json`. Original generator and export options were used. Previews were disabled and CPU threads were set to two. The two processes ran serially, PIDs **96234** and **96308**, with exit codes **0 / 0** and elapsed times **3.000 / 1.830 seconds**. `processes.json` records exact argv and timing.

```sh
NVWA_FIXTURE_OUTPUT="$PWD/.work/export-drift/control/run-1" \
NVWA_RENDER_PREVIEWS=0 \
/opt/homebrew/bin/blender -b -t 2 --python-exit-code 1 \
  --python tools/blender/generate_fixture.py
# Repeat serially with NVWA_FIXTURE_OUTPUT ending in run-2.
```

`--python-exit-code 1` changes error reporting only. `--factory-startup` was **not** used; user startup state was the same control as experiment 01. A startup-state or single-thread comparison was NOT-RUN. Total actual generation/export processes: **two**.

| Artifact | Run 1 SHA-256 | Run 2 SHA-256 | Bytes each |
| --- | --- | --- | --- |
| GLB | `2be228b1967a97219982be0d5344d7b242f5df3c46d0fb8cb5bc183fd8161d49` | `781f8d579ee86a5452241d4eb43a92590c81742da6d1e65539bfe2c38b6e8882` | 3,827,840 |
| `.blend` | `c750514f5b5758df94c3cb190541e998dee6223efa8b90edbbfe314f5340f628` | `d61345b77b3fd934040c089cf53a6dbee6d0ceeac79c1178d60ac882c0683a59` | 6,436,028 |
| Source structure | `acd23cb37f1d315dd0b371014365b0a8c254532b4971390fcf7a3be89f1e1b1d` | Same | 732 |

## Exact GLB delta map

`measurements.json` retains **all 33 raw JSON field changes**, every raw accessor comparison, and all **414 resolved accessor usage comparisons**. Raw array order, reference changes, descriptors, numeric differences, signed zero, decoded hashes, and counts are preserved. No epsilon threshold makes a comparison pass.

All raw JSON changes occur in accessor descriptors 17–22, buffer-view layout 17–22, and eye mesh 2/3 accessor references. For example, mesh 2's indices reference changes `5 → 17`; mesh 3's indices changes `22 → 5`, its POSITION changes `17 → 18`, and its NORMAL changes `18 → 19`. These are storage/reference changes, rather than position or weight changes: the comparator resolves each reference before comparing its actual values and descriptor.

The four eye index sequences differ in 2,156 / 2,156 / 2,160 / 2,160 scalar entries, respectively. Each still has 720 triangles. A separate, secondary comparison proves that the oriented triangle multiset is exact for each eye, including multiplicity and winding. It permits cyclic rotation within a triangle and triangle sequence changes only. It does not erase raw index differences or declare an exact export. Body primitive indices are exact.

Ten referenced normal accessors differ in **485 scalar components**. No signed-zero-only difference occurred in this pair. Here `M/P` identifies mesh/primitive; morph index follows the published profile.

| Semantic field | Left/right accessor | Changed components | Maximum absolute delta |
| --- | --- | --- | --- |
| Eye M0/P0 base NORMAL | 1/1 | 81 | 1.1920928955078125e-7 |
| Eye M1/P0 base NORMAL | 8/8 | 98 | 1.1920928955078125e-7 |
| Eye M2/P0 base NORMAL | 13/13 | 88 | 1.1920928955078125e-7 |
| Eye M3/P0 base NORMAL | 18/19 | 85 | 1.1920928955078125e-7 |
| Body M4/P0 base NORMAL | 24/24 | 8 | 5.960464477539063e-8 |
| Body M4/P0 jaw_width NORMAL | 29/29 | 8 | 5.960464477539063e-8 |
| Body M4/P0 nose_width NORMAL | 31/31 | 18 | 1.1920928955078125e-7 |
| Body M4/P0 smile NORMAL | 33/33 | 77 | 1.1920928955078125e-7 |
| Body M4/P0 shoulder_width NORMAL | 35/35 | 5 | 5.960464477539063e-8 |
| Body M4/P1 smile NORMAL | 46/46 | 17 | 1.1920928955078125e-7 |

An actual base-normal change is `-0.7188056111335754 → -0.7188056707382202` at M0/P0 row 16, component 1. Actual morph normals include `-0.0 → -3.725290298461914e-9` at M4/P0 jaw_width row 1500, component 2. These are real numeric shading-data changes. Their visual effect was NOT-RUN.

Exactly equal after reference resolution:

- Every mesh POSITION, TEXCOORD_0, JOINTS_0 and WEIGHTS_0 value and accessor descriptor.
- Every morph POSITION delta, all four morph ordering/names/default weights, and the unchanged NORMAL accessors outside the table.
- All 18 inverse bind matrices, skin joint order, node hierarchy, transforms, mesh/skin assignments and root scene definitions.
- Every idle/turn/wave input time and output sample; all channel targets, sampler references, interpolation, action names, durations and animation order.
- Every material field, including colors, roughness, metallic factors, opacity, sidedness and primitive material assignment. All remaining nonstorage GLB JSON fields are exact. No accessor is unreferenced in either export.

Both exports passed the unchanged `validate_fixture.validate()` against their actual GLB: 18 joints, 23,044 weighted material-split body vertices, one 22,572-vertex welded surface, four distinct morph POSITION hashes, and all three actions. Both exports also match the frozen profile's morph indices and actual clip indices/durations. Their new byte hashes are deliberately **not** published into that profile.

## Explanation and causal limit

SOURCE-VERIFIED in installed exporter 3.3.32: extraction calls Blender `calc_loop_triangles()` and reads its loop sequence; it obtains split base/shape normals from Blender and computes normalized float32 morph normal deltas. Indices are serialized from their resulting array bytes. `gather_accessor()` is cached, and `BinaryData` equality/hash use those bytes. In the measured pair, identical eye index sequences are shared by meshes 0/1/2 in run 1 and meshes 0/1/3 in run 2. Changed sequence sharing therefore changes where the later eye accessors and binary blocks are allocated. This explains the measured JSON reference/layout cascade.

The exact internal origin of the changing eye triangle order and tiny calculated normal differences remains **UNKNOWN**. Memory ordering and floating-point execution order are hypotheses, not proved causes. No change to normal export options, precision, sorting, source geometry, animation or threading was used to claim determinism. Such a fix would require a deliberately scoped asset/export revision and its own verification.

## Bounded `.blend` evidence

The parser reads uncompressed native file headers and each BHead's code, payload length, old address, DNA index and count. The `old` field is a stored pointer/address field in the version-matched [Blender 3.3.1 BHead definitions](https://raw.githubusercontent.com/blender/blender/v3.3.1/source/blender/makesdna/DNA_sdna_types.h). Both files have the same header and 27,624 blocks, with identical code/length/DNA/count at every corresponding block. **27,623 old-address headers differ**. **156,683 payload bytes also differ**, including 11 GLOB bytes, so ignoring only BHead addresses would not establish byte equality. The per-code counts remain in the measurement file.

This is block-layout and exact byte evidence. Internal payload pointers, save paths, padding and complete native scene semantics were **not decoded**. Save metadata is a possible contributor, not a proved explanation for all payload differences. The unchanged JSON source proof and GLB semantic checks do not establish complete `.blend` scene equivalence.

## Reproduction and negative evidence

From the repo root, use `control` on the first run in a fresh checkout; the harness refuses an existing directory, runs serially, captures process errors, compares protected hashes before/after, validates both actual GLBs, and records differences:

```sh
python3 experiments/26-export-drift/run_pair.py --label control
python3 experiments/26-export-drift/compare.py \
  .work/export-drift/control/run-1 .work/export-drift/control/run-2 \
  --require-exact
# Actual pair: exit 1. Drift remains visible.
python3 experiments/26-export-drift/compare.py \
  .work/export-drift/control/run-1 .work/export-drift/control/run-1 \
  --require-exact
# Self control: exit 0.
python3 -m unittest discover -s experiments/26-export-drift -p test_compare.py -v
```

Fourteen tests pass. They cover the actual pair, self control, real-fixture mutations to a skin joint order, animation interpolation, material roughness and one binary normal value, actual-validator rejection of nonfinite animation data, signed zero, shape/tail reporting, triangle winding/multiplicity, the production-called harness comparison seam, and actual CLI byte-only mutations to GLB JSON formatting, one `.blend` payload byte, and source-proof whitespace. Mutating `check=True` to `check=False` made the harness failure test fail (exit 1); restoring it made the complete suite pass (exit 0). `test-evidence.txt` retains both results. No Blender job is launched by these tests.

`--require-exact` requires byte equality of **all three compared artifacts**: GLB, `.blend`, and source proof. The decoded GLB comparison remains a separate informational field. The three byte-only CLI regression tests first failed against the former semantic-only exit gate (exit 0 despite unequal artifact bytes); after correction, the full fourteen-test suite passes. An explicit mutation that restores the former semantic-only gate also makes all three CLI tests fail; restoring the byte gate makes them pass. `byte-gate-test-evidence.txt` retains both red/green sequences.

For later repetitions, use a fresh label and apply the same label to both comparison paths and the test environment:

```sh
python3 experiments/26-export-drift/run_pair.py --label control-2
python3 experiments/26-export-drift/compare.py \
  .work/export-drift/control-2/run-1 .work/export-drift/control-2/run-2 \
  --require-exact
NVWA_EXPORT_TEST_PAIR=control-2 python3 -m unittest discover \
  -s experiments/26-export-drift -p test_compare.py -v
```

The recorded original pair remains `control`. Future runs can produce different delta counts; the tests do not require the original pair's ten-normal-accessor count.

## Frozen inputs and cleanup

`protected-hashes.json` records identical before/after hashes for all **28** protected files: every asset, all three authoring/validation/reproducibility Python sources, and the existing experiment 01 files. This includes the published GLB, `.blend`, profile, provenance manifest, source proof, previews and original reports. The frozen GLB remains `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`; the frozen `.blend` remains `ab76175ba9c3fe64823cb3e3872a495ddd0b3abf82ccfeb31f2051a00a231b66`.

Generated binaries and raw logs remain private under `.work/export-drift/` for inspection. No process remains running; test temporary directories were removed. The previously generated validator bytecode cache is also absent at the final check; the comparator disables future bytecode writes beside the frozen validator. No backup deletion or cleanup outside the owned directories was performed.

VERIFIED — Two independent CPU exports, exact field/accessor delta map, both actual validators, profile metadata, 28 unchanged protected hashes, 14 tests, byte-only CLI regression red/green, real exact-mode red/self-control green, and harness mutation-red/restored-green.

NOT-RUN — Export determinism fix, full `.blend` semantics, native/Web rendering, visual shading impact, arbitrary rigs, cross-host/version/platform repeatability, and a future-run nondeterminism bound.
