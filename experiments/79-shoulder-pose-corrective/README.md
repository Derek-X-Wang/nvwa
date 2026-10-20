# Shoulder source correspondence and one rejected pose target

PARTIAL — fresh Web source correspondence and one actual corrective preview passed provenance checks. The single-point corrective is **REJECTED** by its frozen no-new-crossing-pair gate. Product source, assets, root dependencies and Work capabilities are unchanged. See [results](RESULTS.md) and [record identities](evidence/observations.json).

The visible rear-shoulder notch is body source quad7941 ahead of garment quad131. This differs from the older quad200/201 stretch investigation. Actual source colors, full source topology, camera and same-update render-mesh association confirm this target. This is CPU binding plus observed source-color correspondence, not GPU object-ID readback or collision depth.

The app starts without a corrective. It uses shared production Studio/runtime and existing approved character inputs. `source_body` colors only body7941 green; `source_garment` colors only garment131 magenta. Ordered displayed triangles, materials, depth, visibility and body mask remain unchanged. Deindexing discards unreferenced vertices, so its exact whole-buffer bounds can differ from the indexed baseline. Every changed mesh must have its own exact bounds. Production `NoFrustumCulling` is preserved.

Publication is measured after production appearance and before bounds/visibility. Last independently checks actual handles, every rendered attribute, bounds and the same update. Readiness requires two distinct stable updates. [The browser helper](browser/README.md) preserves original report/frame strings and currentness fences. [The authoring contract](AUTHORING-CONTRACT.md) permits one hash-bound source847 target after three actual source proofs. The frozen target moves that point about1.31mm at full activation, driven by actual upper-arm angle and posed clavicle rotation. It remains an isolated preview, not a saved Work feature.

## Portable controls

From the repository root; Python and Node must be available. These synthetic controls are separate from the recorded actual source and Web evidence.

```sh
python3 -B -m unittest discover -s experiments/79-shoulder-pose-corrective -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/79-shoulder-pose-corrective -p 'test_*.py'
python3 -B -m unittest discover -s experiments/79-shoulder-pose-corrective/browser -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/79-shoulder-pose-corrective/browser -p 'test_*.py'
cargo test --manifest-path experiments/79-shoulder-pose-corrective/Cargo.toml --lib --locked --offline
```

The Python groups currently contain13 mapping/authoring tests and12 browser/transfer/source tests. The Rust suite has12 CPU/ECS tests. Rust compilation and ordinary desktop UI acceptance are separate; the latter is deferred under project policy.

## Build and serve a fresh source experiment

Use fresh output and target directories; the offline build requires the repository's locked dependencies to be cached. Set `WASM_BINDGEN` to an existing0.2.129 executable. No tool/model/asset is downloaded by this script. The local execution used an owned bounded wefty snapshot; these are the underlying portable steps.

```sh
export SHOULDER80_OUTPUT="$(mktemp -d)"
export CARGO_TARGET_DIR="$(mktemp -d)"
export WASM_BINDGEN=/absolute/path/to/wasm-bindgen
sh experiments/79-shoulder-pose-corrective/build.sh
mkdir "$SHOULDER80_OUTPUT/site"
cp -R "$SHOULDER80_OUTPUT/pkg" "$SHOULDER80_OUTPUT/site/pkg"
cp -R assets "$SHOULDER80_OUTPUT/site/assets"
cp -R experiments/79-shoulder-pose-corrective/works "$SHOULDER80_OUTPUT/site/works"
cp experiments/79-shoulder-pose-corrective/index.html "$SHOULDER80_OUTPUT/site/index.html"
python3 -B experiments/79-shoulder-pose-corrective/browser/server.py --site "$SHOULDER80_OUTPUT/site" --contract experiments/79-shoulder-pose-corrective/evidence/source-contract.json --run-id fresh-source-001 --port 9205
```

Open `http://127.0.0.1:9205/helper.html?work=works/shoulder-rear-baseline-arms.nvwa.json&player=1&case=proofs`. The helper's default real Next button advances the three source modes; `&pace=45` is an explicit timed fallback. This is a new run, not a reproduction of the old raw bytes/epochs. Freeze its own site, request IDs and source contract. Never reuse old captures to acknowledge a new target.

## Recheck the retained one-target decision

The full exact captures and18 complete historical gzip inputs remain in the local evidence archive; their hashes and frozen input ledger are retained. They are not included in this clean checkout or implicitly downloaded. Public screenshots/hashes alone do not substitute for those raw inputs.

With that authenticated archive, the following commands reproduce validation and the expected rejected evaluation. INPUT_MANIFEST names each source mode's path, SHA and independent request ID; EXPECTED_IDS_JSON supplies the independent three-ID map.

```sh
python3 -B experiments/79-shoulder-pose-corrective/browser/verify_sources.py --input-root SOURCE_CAPTURE_DIR --contract experiments/79-shoulder-pose-corrective/evidence/source-contract.json --expected-ids EXPECTED_IDS_JSON
python3 -B experiments/79-shoulder-pose-corrective/derive_target.py --manifest INPUT_MANIFEST --contract experiments/79-shoulder-pose-corrective/evidence/source-contract.json --confirmed-source-correspondence --out NEW_AUTHORING_DIR
python3 -B experiments/79-shoulder-pose-corrective/evaluate_target.py --target experiments/79-shoulder-pose-corrective/evidence/rejected-target.json --history AUTHENTICATED_HISTORY_DIR --fresh ORIGINAL_COMBINED_RAW --out NEW_EVALUATION_DIR
```

Confirm actual source correspondence before authoring. The retained evaluator returns3 for REJECT; returning0 would require a separate quality assessment, not automatic admission. It uses analytical f64/f32 approximations on historical poses. Actual default corrected upload was verified separately. Complete collision, coplanar/tangent contacts, all parameters/cameras and independent actual per-normal vectors remain unverified.
