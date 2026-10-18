# B1 appearance Work contract

Scope: issue79; same admitted B1 body, existing approved CC0 skin/eyes/short04 only. No new downloads, model runs, arbitrary paths/URLs, gaze/blink, head-motion, physics, or full quality/performance admission. Old experiments62–64 remain frozen.

## Portable data and commands

- SceneDocument schema4 is the current write format. Read schemas1,2,3 with the exact previous shape; their absent appearance migrates to None. A legacy document containing appearance, including null, rejects. Schema4 requires an explicit non-null character.appearance field. Preserve the existing legacy backend, diagnostic_pose and stage rules.
- Public Rust type CharacterAppearance is a strict internally tagged enum. None serializes as `{"type":"none"}` and rejects extra keys. B1Cc0 serializes with exactly type=b1_cc0, schema_version=1, asset_set_id, asset_set_sha256 and booleans skin/eyes/hair. Unknown/duplicate/missing/null fields reject. At least one boolean must be true; use None for no appearance.
- Initial asset identity: mpfb-b1-cc0-appearance-v1; manifest SHA256 c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04. Source is assets/appearances/mpfb-b1-cc0-v1/manifest.json. Final pre-admission material A/B may require an explicit reviewed descriptor/hash revision; never silently reinterpret a published identity.
- None works on every existing backend. B1Cc0 is valid only on B1 and binds the existing fixed base asset identity. Skin, eyes and hair can be selected independently. No arbitrary unrecognized asset set or hash substitution.
- Public constants B1_APPEARANCE_ID, B1_APPEARANCE_MANIFEST_SHA256 and B1_APPEARANCE_MANIFEST_BYTES authenticate the descriptor. CharacterAppearance::b1_cc0(skin, eyes, hair) constructs the canonical selection (allfalse => None). CharacterAppearance::validate_for(&CharacterBackend) enforces support. b1_flags() returns Option<(bool,bool,bool)> for shared UI/runtime use.
- Add CharacterRecipe.appearance and Command::SetAppearance {character_id, appearance}. Use the existing atomic editor transaction/revision/idempotency/Undo/Redo path. CLI may apply the same JSON command and save it headlessly. Unsupported identities/backends fail before changing current Work/history/retry state as defined by existing transaction rules.

Example current appearance:

```json
{"type":"b1_cc0","schema_version":1,"asset_set_id":"mpfb-b1-cc0-appearance-v1","asset_set_sha256":"c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04","skin":true,"eyes":true,"hair":true}
```

## Runtime and assets

- Assets are already approved and copied byte-for-byte from experiment62, including CC0/provenance and original SOURCE.json. Authenticate descriptor and every fixed payload before use. The first bounded implementation may embed these shipped immutable bytes for identical native/Web resolution; no new network acquisition or arbitrary file path execution. Record the larger Wasm asset payload separately from unmeasured startup/performance.
- Port tested64 fitting/UV/full-positive-weight behavior into production runtime modules. Do not import an experiment as a production dependency, fork the Studio app, truncate to4weights, turn hair into a rigid cap, replace missing data, or change base B1 input identities.
- Selection is read from current Work each update, not preview state. Apply independent selected roles; baseline restores original material/UV and disposes accessories. Reload/new generation and Undo/Redo must rebind current body, not stale entity handles. Shape edits and continuous playback remain live.
- Invalid asset/decode/binding errors must be visible and invalidate stale successful appearance evidence. Do not report an unapplied selection as ready or silently fall back. Preserve an already valid Work/body on invalid Open as existing runtime semantics require.
- Export a bounded public runtime appearance status/snapshot sufficient to identify requested/applied selection, current generation/revision/body, actual bound CPU mesh/material/image state and errors for real acceptance. No fake GPU readback/current-world independent oracle claim. Avoid perframe full JSON body snapshot solely to drive attachment animation; use existing actual bone_frames route.

## UI, verification and ownership

Normal Studio and Player use the same saved selection; Studio exposes three clear controls in appearance/Profile area through SetAppearance, without experiment NOTsaved warnings. Do not change unrelated stage/transport/input ownership.

Required: legacy/current strict parser and atomic negative controls; CLI command/roundtrip; independent role selection/Undo/Redo/new document/load lifecycle tests; actual native->Web and Web->native save/open files with matching identity; actual shape/playback and malformed/unsupported Work rejection with recovery. Keep build, actual launch, CPU evidence, rendered inspection and performance separate.

Root owns this contract, shipped asset directory, root dependencies/Cargo.lock, Studio integration, CI, all actual GUI/GPU launches, external writes and merge. Core worker owns nvwa-core/nvwa-cli. Runtime worker owns nvwa-runtime only. Quality worker owns isolated experiment65 only. No worker starts a heavy build without root scheduling. Default jobs1; at most2 heavy compile jobs and1GPU test. No actor edits another ownership area.

#3 remains blocked. #4 retains gaps. Clothes/M2 motion quality HOLD remains.
