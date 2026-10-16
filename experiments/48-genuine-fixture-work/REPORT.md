# 48 — Exact genuine sample fixture transport

The existing90frame raw experiment44 sample now has one fixture-specific playable container, profile and Work. This is a serialization and CLI transport result under root's local calibration admission. It does not establish native or Web UI playback, prompt quality or a product motion provider.

## Admission and unchanged inputs

The external [admission record](admission.json) is SHA25694676288d6e3f22886e4b08512aa9094e6e18cf21d50eac1d52e711d1cb365d6. The current [contract](CONTRACT.json) is SHA25658e82af4ab212627844a80a5279e855d5d3b67a535a586e930e3983c5a8d0b26. The admitted47 calibration hash is d730f372adc92d83931c23da84d8709dd8bfa7eb75d57964817577f4b034a6d0; its original PROPOSED_NOT_ADMITTED status remains an immutable pre-review snapshot.

The exporter checks the complete pinned47 manifest before loading only its pure mapper. It checks every pinned source input and the original successful raw receipt. The source generation remains the already completed44 trial:90frames,30fps, seed42,25steps. It is not replayed. Raw roots remain SHA256dcc221d506999a803b1d0fddef87abc0131b1e8f4e64187bc57fde3a63c204af and rotations67914c5d72c54429bf8a70d3f9ef43157fb5181fa36ab2c5f8ce7f9dc69d3a55. The successful generation receipt is554fd2e64e316d218fd699bbbe8d3e45351a7b3a3e08ef077cdc2c6cfaaa52c9. Source generation identities and the new transformation record are separate in the ledger. No preset substitutes for the raw values, and42's generated rejection remains unchanged.

## Serialized behavior

The derivative appends one animation at index3 named genuine44_calibrated47. All three old animations, old accessor/view arrays, scene/node/mesh/skin/morph/material values, inverse bind data and exact rest scales remain unchanged. The entire3,770,416byte original BIN chunk remains an exact byte prefix. The only changed preexisting JSON scalar is buffers[0].byteLength. JSON encoding and GLB header/chunk lengths necessarily change; the whole derivative is not claimed byte-identical to the original asset.

The new animation contains18 joint rotation channels and one translation channel,20new packed accessors/views including one shared time accessor. It writes no scale or morph channels. Source Left maps to physical fixture .R; source Right maps to .L under identity axes and the admitted static engineering gauges. The pelvis keeps its bind rotation. Only joint node17 receives root rotation/translation. Identity ancestor23 and the runtime's outer CharacterRoot do not receive the trajectory. Root translation is source Hips world minus mapped root rotation times exact pelvis bind translation, once.

All90 sample keys are binary32(i/30), i=0..89. Nominal requested length is3seconds; the final key is89/30, stored as2.9666666984558105seconds. No sample90, hold key, resampling, loop blend, endpoint fit or contact adjustment was added. The profile and explicit single nonlooping Work timeline use that final key. The Work does not depend on the profile's default idle selection.

Proper mapped matrices become normalized XYZW quaternions, with per-joint hemisphere continuity before binary32 output. This case required zero sign flips. Original raw quaternion bytes remain untouched. The new output, its insertion record, complete input identities, representation policy, admission and exporter hashes are bound in the transformation ledger. Matrix/affine checks run after reopening serialized GLB bytes.

| Historical primary serialized comparison across90frames, CPython3.9.6 | Maximum residual |
|---|---:|
| Rotation matrix component |7.871245816248873e-8|
| Target pelvis world versus raw Hips |7.409786746280263e-9m|
| Joint position versus admitted f64 mapping |3.3445869382219576e-8m|

The fixed2e-6 tolerances bound float32 transport, not anatomical or motion quality. Primary FK and expectations reuse the admitted47 mapper, so they do not replace the separately owned independent checker or establish official decoder parity.

## Python portability correction (v2)

R2 reproduced a real failure of the advertised verify command on CPython3.14.7. The old verifier compared the complete regenerated ledger bytes exactly. Its max_joint_position_error_m was3.3445869193683264e-8 on3.14, versus the historical3.9.6 ledger value3.3445869382219576e-8. The absolute difference is1.885363124038962e-16m. GLB, profile and Work bytes were identical. The original failure report and all26v1 files remain preserved under root's private before-ledger-portability-fix snapshot and CONTENT-FREEZE-v1. Their earlier receipts were not edited.

The correction treats primary_reload as historical artifact-creation diagnostics. Their stored3.9.6 values remain unchanged. Each live verify result now identifies its Python implementation/version. A recursive ledger comparator requires exact key order, lengths, types and values except three explicitly named float leaves: primary_reload/max_rotation_matrix_error, primary_reload/max_pelvis_world_error_m and primary_reload/max_joint_position_error_m. Those leaves must be actual floats, finite, nonnegative and strictly below the existing2e-6 transport bound. Their absolute difference from recomputation may be at most2e-15, approximately nine f64 machine epsilons at metre scale. Relative tolerance is zero. This is a fixed allowance for cancellation in affine diagnostic arithmetic; it is not an asset, provenance or general JSON tolerance.

All provenance, admission/calibration/exporter hashes, frame counts, discrete values, other numeric values, array shapes, JSON types and canonical ledger encoding remain exact. GLB/profile/Work comparison remains byte-exact. In v2, the ledger changed only exporter_sha256 to46e974f60ed255a525d3ad3b962cd40dcd2674eca8f2bbf125f1e5fbf7e3971d. Its v2 hash was9c633e7e5357cc29d96550f7b524324de18fbb9309de9268d2986bc038074394. No old diagnostic value was rewritten to match3.14.

| Actual runtime | Advertised verify | Controls normal / optimized | Recomputed max joint residual |
|---|---|---|---:|
|CPython3.9.6|PASS|9positive /50rejection each|3.3445869382219576e-8m|
|CPython3.14.7|PASS|9positive /50rejection each|3.3445869193683264e-8m|

Each runtime's normal and optimized control output is identical. New controls edit ledger bytes and invoke the actual verify_artifacts path. They accept a1e-16 perturbation at each named diagnostic leaf, then reject4e-15 changes, booleans, integers, nonfinite values, negative values and the physical bound itself. They also reject changed provenance, boolean/float frame counts and a tiny change to a nonallowlisted numeric field. Existing export/reload, source-pin, asset-byte and cleanup controls remain active. The six exact commands, exit codes, streams and hashes are retained in new private primary/portability-v2 receipts and summarized in verification.json. No CI or Python requirement was pinned to3.9, and no check was disabled.

## Signed-zero representation correction (v3)

R2 found a narrow representation gap in v2: Python float equality accepted a nonallowlisted +0.0 to -0.0 ledger change, such as transformation/basis/0/1. That change has no motion effect, but it violates the claim that only three diagnostic leaves permit different representations. Nonallowlisted float leaves now require exact struct.pack('>d') binary64 equality. The three diagnostic allowances, all other checks and all serialized asset bytes remain unchanged.

A new control writes +0.0 at that actual ledger leaf and calls verify_artifacts successfully. It then writes -0.0 and requires the same public verifier path to reject it. Both runtimes pass10positive/51rejection controls under normal and optimized execution, plus the advertised verify command. The v2 snapshot's28files still match their original hashes; all old receipts and freezes remain unchanged. New exact receipts and the v3 private freeze are retained under primary/signed-zero-v3. The live verification.json records this stage and identifies the retained v2 verification hash.

GLB, profile and Work remain byte-identical to v2. The ledger changes only exporter_sha256 to5cc3d8254a0e2ec2e92c92367d7dcf3a4f9b28a7f856c0010ae1086d7a3b425f, giving ledger SHA256d71e323362b750491f46f1f106a0079eefb015a0271a8460e8a9f11542febe6e. Historical3.9 residual values remain unchanged. No independent, old experiment, product, dependency, CI or runtime UI change is part of this correction.

## Real-path controls and CLI evidence

The normal and optimized outputs match within each of CPython3.9.6 and3.14.7. Ten positive checks and51rejection controls pass on each runtime. The controls exercise actual serialization/reload and actual exclusive publication. They reject root target23, root/pelvis confusion, side exchange, double root offset, XYZW changes, unrecorded sign reversal, an invented3second key, wrong sampler/index/count, altered old animation/BIN/rest scale, bad raw/receipt/calibration/admission pins and ledger bindings, duplicate/nonfinite JSON, input/output symlinks and an existing destination. Injected verifier failure and a real partial write fault both remove only invocation-owned new outputs. Existing output hashes remain unchanged.

The existing readiness CLI binary, SHA256c86518413dde4afe6000dda9092e09eaaf071d7a89924f621c0e051eeb5a102e, performed7actual operations on the new Work: inspect, validate with explicit isolated asset root, save, inspect saved Work, validate saved Work, missing asset rejection and corrupt asset hash rejection. Both positive validations returned asset_checked=true; failures returned asset_missing and asset_hash_mismatch. No compilation occurred. Exact argv, exit codes, streams and hashes are retained privately in .work/m2-genuine-work/primary/cli-receipt.json; sanitized command/hash evidence is in cli-verification.json.

The entire inspected document is JSON-value identical after CLI save/reopen. The input's Python JSON prints the exact widened float32 values; Rust emits shortest float32 spellings, such as2.9666667 instead of2.9666666984558105. All source-versus-CLI float values are identical after core float32 parsing. Original wider decimal spellings and saved file bytes are not claimed unchanged.

CLI validate checks the GLB hash and the product's limited structural contract. It alone does not prove channel data, source provenance, pose semantics or runtime animation. This experiment adds primary decoded checks; independent source/serialized checks remain a separate owner/gate.

## Artifacts and license scope

| File | Bytes | SHA256 |
|---|---:|---|
|assets/generated/genuine44-calibrated47.glb|3,859,752|c343f6cf47dc0a7c0b09f13ad7d21cf2706a08fb1cfdaca233f14edab02e44fc|
|character.profile.json|1,330|af8638e626c0ade115d94663f191621ab5753c1f970e8a337ecc03aad16429b0|
|genuine44-calibrated47.nvwa.json|1,977|7668eb7a2a2f87070500cbf49fa27d6794aa1fb83f5392b75a0ff51667cde779|
|transformation-ledger.json|8,370|d71e323362b750491f46f1f106a0079eefb015a0271a8460e8a9f11542febe6e|

The asset path is relative to artifacts/assets, not relative to the Work file. Native must use that isolated asset root. Web must stage identical GLB bytes under its served assets/generated path; selecting a Work JSON does not supply the referenced asset. No server or runtime UI was launched by this worker.

CC0 applies only to the original Nvwa fixture. The profile and ledger state a separate generated-motion scope and retain the existing experiment41 motion-model and encoder terms references. The generated motion or composite GLB is not relabelled CC0. This result supplies no new redistribution rights. No weights, vendor source, executable or library is included.

## Boundaries and cleanup

NOT-RUN — Native/Web actual UI playback, multi-frame root/pose observation, browser download completion and independent reopen, bidirectional native/Web Work exchange, official decoder-axis parity, original official SOMA bind/surface, certified palm/sole anatomy, contact/scale/proportion fit, arbitrary rigs, product provider adoption, prompt meaning, human motion quality and performance.

No inference, model/source download, dependency change, Blender/vendor/UI execution, server, extra machine, Git/GitHub action or old experiment/product edit was performed. Only synchronous bounded Python and the existing lightweight CLI ran. No persistent process or temporary negative-control asset remains. One private earlier development-artifact directory and private exact receipts are intentionally retained for root audit. The failed first build encountered Python3.9 pathlib slicing compatibility; the publisher removed its output and the compatibility fix was applied before the successful artifacts above.

VERIFIED — Primary serialized export and preservation,10positive/51rejection controls under normal and optimized CPython3.9.6 and3.14.7, and7actual native-CLI validation/save/reopen calls pass. Native/Web UI and independent verification remain separate gates.
