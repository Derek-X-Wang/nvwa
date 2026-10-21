# Current-source 18-slot baseline replay

This producer captures exactly 18 current production-plugin CPU snapshots. Together with the separately authenticated original fresh-default anchor, these form a **hybrid comparison cohort**. They do not recover historical gzip bytes. Historical replay remains `NOT-RUN_MISSING18`.

The driver copies the headless host, manual clock, wait and public `b1_frame_snapshot` pattern from experiment60. It opens `CharacterProfile::b1_motion()` with its canonical legacy two-parameter profile and backend version2. Every sample uses `probe-entry`, start0, duration4, speed1, loopingfalse and paused playback. For torso -1/0/+1 and jaw0, it captures arm k0/8/16/24/32 (seconds0/1/2/3/4) and knee k16 (seconds2). It performs no594-frame sweep, rendering, model work or candidate installation.

Root owns Cargo manifest/lock integration and build scheduling. `Cargo.toml.proposed` is a review aid only. The actual nested manifest uses existing dependencies and the original Bevy0.19.1 feature union. Do not regenerate a lock or fetch dependencies to run the collector.

After the root-scheduled build, from the source checkout:

```sh
python3 -B experiments/84-shoulder-rest-refit/replay/collect.py \
  --binary <frozen-built-replay-binary> \
  --build-receipt <actual-completed-build-receipt.json> \
  --asset-root <current-source-checkout>/assets \
  --fresh <original-retained-source-proof>/h80proof-v1/combined/capture.json \
  --out <new-private-output-directory>
```

The collector freezes complete assets, production source, relevant independent validators, manifest/locks and binary hashes before/run/after. It records source HEAD, dirty paths, toolchain, architecture, original garment identity and a fresh run UUID. Outputs use relative paths. Original input/source bytes remain unchanged.

The required completed build receipt is copied byte-for-byte to `build-receipt.json`. Its schema is:

```json
{
  "schema_version": 1,
  "kind": "nvwa84-completed-native-build-v1",
  "status": "PASS_COMPLETED_BUILD",
  "build_run_id": "<actual-completed-build-run>",
  "exit_code": 0,
  "source_head": "<40-character-source-HEAD>",
  "source_files": [{"path":"<repo-relative>","bytes":0,"sha256":"<SHA256>"}],
  "source_files_sha256": "<inventory_digest(source_files)>",
  "toolchain": {"rustc":"<actual-rustc-version>","cargo":"<actual-cargo-version>"},
  "host": {"system":"<actual-system>","machine":"<actual-architecture>"},
  "command": ["<actual-build-argv>"],
  "binary": {"name":"nvwa-shoulder-rest-replay","bytes":0,"sha256":"<actual-binary-SHA256>"}
}
```

The parent must create this receipt from a successful completed build. `build_source_files(root)` is a read-only helper returning the exact sorted source rows; `inventory_digest(rows)` calculates their canonical digest. This conservative compiled-input subset includes root Cargo/toolchain files, complete `crates/`, the three local vendored crates, `.cargo/`, complete `assets/` (some are compiled through include macros), and replay main/Cargo/lock. It excludes Python collectors/tests, README, authoring and evaluation work. Receipt rows must equal the same subset of the capture source receipt. Capture UUID and completed build run ID must differ.

The frozen corpus manifest binds exact byte counts/SHA256 for identity, build and all three source receipts. Authentication verifies these bindings before reading their claims, then checks source HEAD/closure, build status/exit, source inventory, command, binary, toolchain and host crosslinks. A changed identity or build receipt cannot retain acceptance through the old frozen manifest.

Every `B1_84_REPLAY` record must bind the expected run, exact legacy backend/profile, requested recipe, returned pose/time and timeline. Missing, duplicate, extra, malformed and mixed records reject the corpus. The gzip stores the exact producer JSON substring, including LF; geometry/bone numbers are never reserialized. Gzip uses mtime0. Both compressed and raw byte counts/SHA256 are recorded.

Source guards use unchanged experiment70 `Source`/`analyze`, all53 source bone hierarchy and anchor bone ordering, unchanged experiment60 `check_bones`, source-derived full positive influence support, and independent skinning on every body and garment render row. The new source/rest reconstruction ceiling is1e-7; original independent positive skinning bound remains1e-5. These numerical reconstruction bounds are distinct from exact identity comparisons. Per-shape rest, inverse binds, influence rows, duplicate source mapping and display placement must remain exact across poses. Exact selected historical fixture bone fields must match every slot. A mismatch rejects; no fallback or new tolerance is chosen.

The current torso0 arm2 slot additionally requires exact original-anchor bones, source IDs, indices, rest arrays, normals, tangents, influence rows and transform conventions. Only posed positions use the historical1e-5 overlap bound. The original anchor remains at its original hash. Its profile/entry identity differs explicitly from the legacy replay and does not become a fresh capture.

`manifest.json` uses `schema_version:1`, `cohort_type:hybrid-current18-original-anchor`, a separate run/source identity,18 new gzip rows and one original anchor row. Freeze its SHA256 and source inventory SHA256 before candidate scoring. The scoring-input seam is:

```python
records = collect.authenticate_corpus(
    new_output_directory,
    frozen_new_manifest_sha256,
    frozen_source_inventory_sha256,
    original_anchor_path,
)
```

This rejects missing/tampered/mixed/duplicate/wrong-recipe/wrong-source inputs. It does not replace experiment81's immutable historical authenticator or input list. The evaluator owns separate candidate/source-fit and quality gates. Source reconstruction, corpus acceptance, full19 scoring, actual Web/CLI behavior and visual quality remain distinct evidence.

Targeted structural/scoring-seam controls:

```sh
python3 -B -m unittest discover -s experiments/84-shoulder-rest-refit/replay -p test_collect.py
python3 -B -O -m unittest discover -s experiments/84-shoulder-rest-refit/replay -p test_collect.py
```

These controls use synthetic snapshots only for structural failures. Their geometry validation is explicitly `NOT-RUN`; they do not claim an actual production capture. An actual collector run is required for source/bone/geometry admissibility.
