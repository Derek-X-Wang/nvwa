# One separate CPU-only Wasm admission attempt

This receiver implements the bounded R2-approved current-source Wasm capture. It does not change `collect.py`, the rejected native corpus, historical hashes, numerical gates, original fixtures or candidate assets. Admission still requires exactly18 current legacy-profile snapshots plus the unchanged authenticated original anchor. Failure stops the receiver/client attempt; it does not trigger another platform or tolerance.

Parent owns actual build, browser/client execution, one capture authorization, ports and cleanup. This module has no side effects on import. The worker's tests launch no browser or corpus server. One bounded control uses an ephemeral loopback HTTP socket to verify stalled request lines/headers time out; it posts no capture and closes its owned socket/thread.

## Actual completed build receipt

```json
{
  "schema_version": 1,
  "kind": "nvwa84-completed-cpu-wasm-build-v1",
  "target": "wasm32-unknown-unknown",
  "status": "PASS_COMPLETED_BUILD",
  "exit_code": 0,
  "build_run_id": "<actual-successful-build-run>",
  "source_head": "<40-character-HEAD>",
  "source_files": [{"path":"<repo-relative>","bytes":0,"sha256":"<SHA256>"}],
  "source_files_sha256": "<canonical-source-rows-SHA256>",
  "command": ["<actual-cargo-and-bindgen-command-argv>"],
  "toolchain": {"rustc":"<actual-version>","cargo":"<actual-version>","wasm_bindgen":"<actual-version>"},
  "host": {"system":"<actual-system>","machine":"<actual-architecture>"},
  "artifacts": [{"path":"pkg/<bindgen-file>","bytes":0,"sha256":"<actual-SHA256>"}]
}
```

No native `binary` field is accepted. `artifacts` must contain the complete dedicated bindgen package, including `pkg/nvwa_shoulder_wasm_replay.js` and a `.wasm`. The parent creates this receipt only after actual completed Cargo and wasm-bindgen success. Exact receipt bytes are copied into capture output.

Read-only build helpers:

```python
import collect_wasm
source_rows = collect_wasm.wasm_build_source_files(source_root)
source_sha = collect_wasm.inventory_digest(source_rows)
artifact_rows = collect_wasm.artifact_files(bindgen_pkg_directory)
```

The compiled/transport closure includes current production crates, three vendored crates, `.cargo`, root Cargo/toolchain files, complete assets and all owned wasm-replay source/client/Cargo files. It excludes native replay source and generated `pkg`/`target`. The capture source inventory also includes the frozen original validators/fixtures and receiver/test source. Artifact hashes are separate, with no external absolute paths in `source-before.json.files`.

## Root-authorized receiver invocation

After actual build success, frozen receiver review and root's capture GO:

```sh
python3 -B experiments/84-shoulder-rest-refit/replay/collect_wasm.py \
  --pkg <actual-completed-bindgen-pkg-directory> \
  --build-receipt <actual-completed-Wasm-build-receipt.json> \
  --wasm-bindgen <installed-version-pinned-wasm-bindgen> \
  --asset-root <current-source-checkout>/assets \
  --fresh <original-retained-proof>/h80proof-v1/combined/capture.json \
  --out <new-private-output> \
  --port 9218 --timeout-seconds 300
```

Bind failure does not steal another service's port. The only listener is `127.0.0.1:9218`. Its exact origin is `http://127.0.0.1:9218`; `localhost` and other ports are not aliases. Root must verify the port is free and keep all current sources/artifacts frozen during capture. Source/bindgen snapshots before/run/after must remain exact.

## Transport

- `GET /config`: `{run_id,recipes,asset_root:"assets",pkg_module:"/pkg/nvwa_shoulder_wasm_replay.js",capture_path:"/capture",complete_path:"/complete"}`. Recipes use the unchanged native collector's exact18 order and semantics.
- `POST /capture`: exact UTF8 Rust `kind:matrix` JSON string plus one LF, with the new run ID and original request/snapshot schema. Send the string directly; do not parse and reserialize geometry or bones. Receiver writes deterministic gzip before deeper validation.
- `POST /complete`: exact Rust JSON plus LF, with `kind:complete`, matching run ID and integer `matrix_samples:18`.
- POST requires exact Host, Origin, `Content-Type: application/json` and exact positive Content-Length no larger than64MiB. Each accepted socket gets a10-second timeout before request-line/header parsing, also bounding stalled static-response writes. Chunked bodies, other paths, mismatches and duplicate/missing/malformed cases reject and close the run.
- Static GET serves only owned index/client, receipt-bound bindgen package files and source-inventory-bound existing assets. Traversal, encoded traversal, query strings, escaped symlinks and other paths reject. No external service is contacted by this Python server.

The receiver calls unchanged `collect.validate_record` and `collect.geometry_validator`; selected fixture exactness, all53 ordering/skin conventions, source fitting, full positive skinning, full-anchor exact fields and original position bounds remain unchanged. It neither requests a GPU nor launches a browser.

## New manifest and scoring seam

The manifest uses `cohort_type: hybrid-current18-wasm-original-anchor`, success `PASS_NEW_CURRENT18_WASM_CORPUS` and `historical_replay: NOT-RUN_MISSING18`. Identity explicitly states CPU-only Wasm production execution and a distinct new capture UUID. Failure uses `REJECT_WASM_CORPUS` and preserves available raw files. Accepted entries are retained individually; they do not grant full-corpus credit after failure.

Frozen manifest receipt hashes bind identity, completed build, source-before/at-run/after and raw completion. Artifact/build/source/toolchain/run/host/origin crosslinks must all agree. The evaluator imports only this new seam for this new kind:

```python
records = collect_wasm.authenticate_corpus(
    output_directory,
    frozen_manifest_sha256,
    frozen_source_inventory_sha256,
    original_anchor_path,
)
```

The same four-argument API returns only18 parsed records from the new Wasm corpus. It rejects a native cohort and has no fallback. The original fresh anchor is validated separately by the evaluator as the nineteenth slot.

Controls exercise the actual receiver and authenticator with synthetic geometry explicitly marked `NOT-RUN`:

```sh
python3 -B -m unittest discover -s experiments/84-shoulder-rest-refit/replay -p 'test_collect*.py'
python3 -B -O -m unittest discover -s experiments/84-shoulder-rest-refit/replay -p 'test_collect*.py'
```
