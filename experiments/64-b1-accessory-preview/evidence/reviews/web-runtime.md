# Independent R1 actual Web runtime evidence review

**CLEAR for the bounded experiment64 temporary appearance preview. No P1/P2 rework finding in the reviewed scope. This is not production appearance-quality acceptance, persistent character identity acceptance, native acceptance, or permission to close #79.**

Reviewed the assigned checkout only, without Git, builds, live UI, GPU work, downloads, source edits, or external writes. The only new outputs are this report and `web-review-scratch/`. Root retains cleanup and integration ownership.

## Source and artifact provenance

- Verified every one of the 13 r5 frozen source hashes. The checker-defined canonical serialization hashes to `549ba3161723a92db3065fa79edd2d869dc06ea4c809558a8a2c6ef1f71303d4`. No unexpected source drift. Canonical hashing here uses the public checker's `json.dumps(..., sort_keys=True)` convention, including its spaces.
- Compared all current source paths in `.work/appearance64/build-r1/web-build-receipt.json` against the receipt. Only `build/serve.py` and `build/test_serve.py` differ, exactly the declared r5 capture-sink change. Rust, HTML, lockfile, production source and input assets remain byte-identical to the compiled receipt.
- Rehashed all 41 exported Web artifacts against that build receipt, including Wasm `f38e1d5fdcfd531204a098a2aba37798d4cbf8b22b8cba992b8c5f4b22a979ff`, JavaScript and HTML. All match. The root prelaunch receipt records the matching export/source verification; this reviewer did not relaunch the app.
- Verified all seven payload files of the eight-file public verification package against `verification/MANIFEST.json`; manifest SHA is `000f9e41e801780039b493b1051ae2caa370809037687f892b96abbff021b957`. The public checker SHA is `d75a9faf032e926a75ac5b5a8d867cb53a7924f834361874b18c375238b661c2`. Its freeze check authenticates the 12 pinned asset payloads and stable53 weights.
- Read the contract, README, checker and scalar reference, and primary source paths for capture, invalidation, fitting, full-positive weight transfer, actual mesh readback, material observation and live streaming. The reported arrays are read back from `Assets<Mesh>` through the entity's actual mesh handle. This supports the stated CPU upload observation, not GPU readback. The scalar reference recomputes attachment positions from source MHCLO/OBJ/weights and the captured cage/bone frames; the cage/bone freshness remains the same producer's evidence.

## Actual captured records

The separate acceptance worker's combined result is `1e41d1ace7d54ea70de5531be34db08c23fa71e461db39ee700e78c552d747a4`; lifecycle summary is `2001a8138d77d06f7eafcac07f96d19abdec03c7a6af8ec7b9f88c961d42b9d8`. Both supplied hashes match the files read. Verified all six matrix `EVIDENCE-HASHES.json` targets. The two matrix manifests contain exactly the unique 54-member Cartesian grid: torso -1/0/1, jaw 0/.5/1, arm/knee, source seconds 0/2/4. The reported 54 checker passes are the independent acceptance worker's complete run, not a new 54-case run by this reviewer.

Independently loaded these 14 original raw records, checked their actual bytes/SHA/size against the separately saved UI Store text and helper manifests, and compared the sender command, compact receipt, report and full-frame request:

`w64-t0-j0-arm-s0`, `w64-t0-j2-knee-s2`, `w64-t1-j0-arm-s4`, `w64-t1-j1-knee-s2`, `w64-t1-j2-arm-s0`, `w64-t2-j0-knee-s4`, `w64-t2-j1-arm-s2`, `w64-t2-j2-knee-s4`, `w64-compare-all-01`, `w64-compare-baseline-01`, `w64-compare-skin-01`, `w64-compare-restored-01`, `w64-after-reopen-01`, `w64-asset-recovered-01`.

Ran the unchanged public checker on the actual `t0-j0-arm-s0`, `t1-j1-knee-s2`, and `t2-j2-knee-s4` records: **3/3 PASS_WITH_LIMITS**. No synthesized receipt or artificial record was substituted. `w64-accessories-01` receives no matrix credit because its original separate Store text was not retained.

Recomputed whole `frame.snapshot` deep equality across all four appearance modes: **equal**, including core geometry, transforms, bones, sample and identity. Baseline has no active accessory runtime or body UV; the restored accessory mode returns the same core snapshot. Representative reopen and recovery records show generations 2 and 3 with new entity/asset identities after generation 1. Full per-record results and provenance are retained in `web-review-scratch/sample-verification.json`.

The actual saved Work bytes match the ordinary Web Save receipt: **2294 bytes**, SHA `effeaab8d069bc4aec4b3ece716d26ec61bb6a3e3e49911f7300942f0e1674d5`, revision 52, torso .8, jaw 1, knee clip duration 4. The schema3 document has no temporary appearance or observation-camera persistence. Reopen demonstrates session preview rebinding; it does not establish saved appearance identity.

## Renderer and lifecycle evidence

Inspected original screenshot files under `.work/appearance64/web/screenshots/` using file-image inspection only. Root identifies these as unmodified actual CUA captures; this reviewer did not operate the UI or independently recreate the capture session. Hashes of the nine inspected files are in `web-review-scratch/manifest-and-image-verification.json`.

- `02-web-face.png` and `08-web-final-face-recovered.png`: eyes and textured short04 hair are visibly rendered on the actual Studio character; the persistent temporary/not-saved label is present. The final view shows torso .8 / jaw 1 / revision 52 after recovery.
- `04-web-back.png`: rear hair geometry and texture are visibly present. The large light crown facets/strips and cutout edges are observable quality limitations, not grounds for a shader-parity or polished-hair claim.
- `w64-arm-live-1.png` versus `w64-arm-live-7.png`: different arm poses and timeline values 1.0672 versus 1.4544 while Pause is visible. `w64-knee-live-1.png` versus `w64-knee-live-5.png`: different knee poses and timeline values .9443 versus 1.1983. These support actual rendered motion at successive instants. They do not measure sustained frame rate, prove every intermediate frame, or prove head-driven accessory deformation. The stale/proof-not-current label during transport changes correctly prevents crediting old numerical captures as current proof.
- `w64-compare-baseline-01.png`: visible baseline body/garment, no hair, with the baseline label and inactive accessory report; consistent with the raw mode-restoration evidence.
- `07-web-real-missing-asset.png`: explicit `asset_missing ... manifest.json: HTTP 404`, retained visible body/garment, temporary attachments removed, proof marked pending/not current and Store disabled. The separate failure receipt records the exact manifest SHA restored. This is useful real failure/recovery evidence, but there is no accepted full snapshot during the failed interval that independently proves retained entity identity or numeric freshness. The old Store receipt remains visible below a disabled button; it is not current success evidence.

The separate lifecycle report records 21 records, 19 accessory-checker passes and two manually inspected inactive modes, plus arm/knee terminal samples at source time 4 with serials 201/134. Those terminal records alone are not continuous playback evidence; the screenshots provide a separate limited visual observation. Root's additional live-time/torso-edit observations remain root-observed evidence beyond this reviewer's selected screenshots.

## Quality limits and acceptance boundary

1. **Actual Web temporary rendering and bounded CPU attachment arithmetic are supported.** This is stronger than compilation or artificial fixtures alone. The scalar checks preserve all positive normalized influences, including the reported two hair source vertices with five influences, exact source/UV corner identity and ordered triangle indices.
2. **Appearance quality remains open.** The close views visibly need evaluation of eye/eyelid fit, hairline cutout, crown geometry/shading and lighting. No accepted threshold or independent reference establishes those as production quality. Current finite/unit-normal checks do not validate smoothing or tangent parity. No GPU array readback was performed.
3. **Authored head motion, gaze and hair physics are NOT-RUN.** The arm/knee clips cannot establish these. Arithmetic/source preservation does not substitute for those product behaviors.
4. **Persistent appearance identity is NOT-RUN and intentionally unsupported.** The explicit not-saved labeling and ordinary Work bytes agree. #79 must remain open for production quality and persistence; #3 blocked, #4 gap and clothing/M2 HOLD remain unchanged.
5. **Native compilation, native GUI and native runtime are NOT-RUN for this review.** The ongoing native build receives no acceptance credit here. No CI or merge acceptance is implied by this report.

VERIFIED — r5 source/export provenance, public package manifest, 54-case manifest coverage, 14 actual raw-record provenance samples, three actual public-checker reruns, four-mode core equality, saved Work bytes, and nine original screenshot inspections. PARTIAL — full 54-case numerical result and full lifecycle details are the separately verified worker report; renderer review is selected still-frame inspection, not a fresh live run. Native and production-quality/persistent-identity acceptance remain NOT-RUN.
