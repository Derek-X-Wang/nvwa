# B1 temporary skin preview — experiment62

An isolated technical preparation for issue79 while issue78's native acceptance is unavailable. This does not admit appearance to the product, remove issue79's dependency, or authorize merging PR81 before its remaining native gate. It wraps the normal `nvwa_studio::build_app()` and the same real B1 character. Production code, root dependencies, profile/Work formats and character assets are unchanged.

## Current evidence

- Authenticated and selectively prepared the already approved CC0 archive. Exactly10 source payloads (6,769,409 bytes), plus selected metadata, full CC0 and a manifest. See [ASSETS.md](ASSETS.md).
- Full RGB/RGBA PNG scanline decoding and alpha statistics. Skin is opaque RGB2048²; eyes and short04 hair retain their real alpha. Eyes/hair are preparation only, not rendered/fitted in this slice.
- Eleven asset controls and nine loopback capture controls pass normally and with Python `-O` (20 unique tests,40 executions).
- Independent fresh Astra/high R1 source review of Sol-authored preview: no remaining P1/P2 findings after fixing rejected-command stale success and transport freshness. Review has not yet certified runtime behavior or pixels.
- Web/native compilation and actual rendering are pending the submitted bounded offline build. Native GUI will remain NOT-RUN while the user is away. No performance or appearance-quality result is claimed.

## Rendering contract

Use the fitted source body's actual duplicate-order `Mesh::ATTRIBUTE_UV_0`, matched through the current character/template/Cpu(0) source cache, original source IDs, all fitted rest positions and source/displayed triangle order. Copy UV verbatim; the existing OBJ reader has already flipped V. Never remap UV solely by source ID.

The overlay changes only UV/material/image bindings: fixed approved sRGB diffuse plus white tint, with other material properties preserved. Fresh successful production `b1_frame_snapshot` values before and after binding must be equal. That proves unchanged uploaded CPU geometry/bones/sample; it does not prove GPU pixels. Plain restores and reads back the original UV/material binding. Refit/reopen invalidate old bindings and proof. Rejected commands and changed transport invalidate the exported capture instead of returning an earlier green result.

The visible experiment label states **Experimental appearance · not saved**. Saving a Work does not persist this temporary skin choice. No appearance backend/profile version is introduced. Existing garment quality remains HOLD.

## Reproduce without new downloads

Use existing approved inputs and cached Rust dependencies:

```sh
python3 -B experiments/62-b1-appearance-preview/tools/pack_assets.py \
  --archive "$NVWA_APPROVED_CC0_ZIP" \
  --output experiments/62-b1-appearance-preview/assets --verify
python3 -B experiments/62-b1-appearance-preview/asset-tests/test_assets.py
python3 -B -O experiments/62-b1-appearance-preview/asset-tests/test_assets.py
python3 -B experiments/62-b1-appearance-preview/build/test_serve.py
python3 -B -O experiments/62-b1-appearance-preview/build/test_serve.py
```

Root schedules the long build with `wefty exec` and an exclusive absolute output path; each run uses a fresh disposable Cargo target. The driver creates a Web receipt as soon as that export is ready, then separately builds the native binary. Do not reuse a prior run's Cargo target or credit compilation as launch.

```sh
wefty exec --detach --json --max-runtime 90m -- \
  python3 -B experiments/62-b1-appearance-preview/build/build.py \
  --out "$NVWA_EXCLUSIVE_BUILD_OUT" --wasm-bindgen "$NVWA_EXISTING_WASM_BINDGEN"
```

For an actual Web session, create an exclusive empty capture directory and serve the exported `web/` at an unused assigned Nvwa loopback port. Preserve the user's9203 page. The root launch uses `?work=works/b1-motion.nvwa.json`.

```sh
python3 -B experiments/62-b1-appearance-preview/build/serve.py \
  --site "$NVWA_EXCLUSIVE_BUILD_OUT/web" --captures "$NVWA_EXCLUSIVE_CAPTURES" --port 9277
```

DOM controls call real Wasm exports. `Store current appearance record` submits the current full record to an exclusive bounded sink. The sink validates envelope consistency and refuses overwrites; it does not independently recompute Rust geometry hashes or certify pixels.

`build/cases.json` declares18 sampled skin cases: three diagonal torso/jaw recipes(-1,-1),(0,0),(+1,+1), two authored clips, and0/2/4seconds. It is not the full nine-recipe Cartesian grid. Additional actual toggle, playback, paused seek, rejection, restoration and reopening checks must be recorded separately. The capture checker compares actual source/display UV arrays and material/image identity, and passes the unchanged actual snapshot/request through experiment60's independently sourced f64 FK/full LBS/foot checks. Cloth surface quality is not reclassified by those checks.

```sh
python3 -B experiments/62-b1-appearance-preview/build/check_captures.py \
  --captures "$NVWA_EXCLUSIVE_CAPTURES" --asset-root assets --out "$NVWA_EXCLUSIVE_CHECK_OUT"
```

PARTIAL — Prepared assets,40 Python test executions and independent source review. Compilation, actual Web/native binding/rendering, live failure/recovery, appearance judgment and production admission remain unverified.
