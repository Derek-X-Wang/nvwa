# Candidate A: fixed local weight smoothing

**REJECT/HOLD.** The core arm strain improves, but surrounding boundary strain regresses in six retained arm frames. This experimental recipe is frozen for comparison, not admitted into production. No tuning follows this result. Root stopped this cycle before a heavy Web build because the numerical no-regression gate failed. Actual graphical comparison is NOT-RUN; no viewer is being implemented this cycle.

`candidate.json` SHA256: `a37c255239723c3219d169e73796a37afdae962239721e0b27f2d0d62ef6a10d`.

## Fixed rule, declared before results

One simultaneous pass from original normalized positive source rows. Undirected adjacency comes from unchanged displayed garment source-ID triangles. Core `[182,244,246]` blends50% original row with50% mean original one-edge-neighbor rows. The immediate ring uses25% neighbor mean/75% original. Ring IDs: `[22,29,79,104,110,191,241,255,669,677,691,697,719]`. Exactly16 IDs receive overrides; all other source vertices remain exact identity. All original positive influences survive, neighbor positive influences can join, every row normalizes to1; maximum6 influences, no top4 and no negative-source coefficient clamp. Rest, body, rig, motion and foot rules remain unchanged.

The source helper-to-garment transfer sums signed coefficients first, retains positive final joint aggregates, then normalizes. Candidate rows are source-derived; each of30 actual captured row sets is checked against that independent transfer within1e-6. Candidate provenance contains only real repository-relative source/script hashes. All30 private capture hashes remain separately in evidence.json and evaluation summary.

## Reproduce

Python stdlib plus existing experiment60 geometry helpers; no compiler, renderer or external dependency installation.

```sh
python3 -B experiments/61-b1-garment-ab/weights/run.py --captures "$CAPTURES" --output "$OUTPUT"
python3 -B experiments/61-b1-garment-ab/weights/test_controls.py
python3 -B -O experiments/61-b1-garment-ab/weights/test_controls.py
```

CAPTURES is the directory containing the30 original r4 gzip keyframes. OUTPUT must be new. No machine path is embedded. Output: candidate.json, frames.json, triangle-details.json, summary.json and SHA256SUMS.json. Final private run is under `.work/garment61/weights/final-v1/`; its13.27-second wall time is diagnostic bookkeeping, not a performance result. Earlier same-rule evaluations were repeated only to add normal/absolute-geometry/provenance metadata after review. All candidate weight rows were checked identical; no strength sweep occurred.

Coverage is torso−1/0/+1, jaw0, both authored clips at0/1/2/3/4s. These are30 actual **baseline** source captures. Altered positions/normals are offline independent predictions using their actual bones/rest, not successful unmodified production snapshots or actual experimental GPU uploads. Full jaw-grid, intermediate33-time candidate matrix and actual candidate graphical behavior are NOT-RUN.

## Measured effect

| Torso, arm2s | Triangle200 original→A area/rest ratio | Full52-triangle max area ratio | Full52-triangle max edge ratio |
| --- | --- | --- | --- |
| −1 | 5.10750→4.34394 | 15.25890→10.83073 | 5.38645→4.83833 |
| 0 | 21.32761→18.96291 | 21.32761→18.96291 | 13.46382→9.57795 |
| +1 | 22.00564→19.57176 | 22.00564→19.57176 | 13.53450→9.62785 |

At torso+1 apex, triangle200 fitted rest area is unchanged1.884345974e-5m². Actual baseline posed area4.146623111e-4m² becomes predicted A3.687996983e-4m². The reduced ratio therefore reflects a smaller posed triangle, not a larger rest denominator. Both candidate-rest and original-rest ratios are identical forA. Its three edges change from `[19.6595,43.6777,52.3398]`mm to `[19.6836,38.5453,47.2086]`mm, with the original rest `[20.8573,20.3842,41.2009]`mm unchanged.

Every triangle incident to any changed16 ID is scored, including exterior faces:52 total,17 touching core,34 touching both affected and exterior vertices. Exact triangle IDs are in evidence/summary, and triangle-details.json retains absolute original/candidate rest/posed areas and edge lengths for every frame/triangle, plus both rest-denominator ratios.

Boundary max area ratio worsens for torso0 and+1 at arm1/2/3s (six frames). Torso0 apex6.74274→7.01605; torso+1 apex5.31541→5.54543. Local compression also worsens: torso+1 full52-triangle minimum area ratio.845709→.842669. These are beyond the review's1e-4 rounding-only comparison tolerance. They reject a claim of improvement without surrounding regression; that tolerance is not a garment acceptance threshold. No10x ratio acceptance gate is used.

Maximum modified displacement9.53030mm at torso−1 arm apex. Neutral/knee displacement is at most5.53e-8m from offline float reconstruction. Outside16 IDs, actual uploaded position values are copied exactly. Original rest arrays are used unchanged. Body arrays, skeleton and motion are never modified, so old foot bounds are structurally preserved; this is not a new actual-runtime foot test.

Full garment sharp-fold edge IDs stay unchanged in every selected frame, including neutral and the independent eight-vertex safety region. The16 changed source points have zero local negative nearest-full-body projections beyond2/5mm in both variants on these30 frames. This bounded point-query result does not prove collision-free garment triangles, global inside/outside or physical clearance. Adjacent-normal angles remain fold descriptors, not self-intersection tests. Cloth quality remains HOLD.

## Controls and normals

- Original independent full garment LBS versus uploaded POSITION maximum component error1.64971e-7m across30 captures; source row checks pass.
- Empty/no-op override preserves uploaded positions exactly. Outside-boundary comparator rejects an intentionally changed exterior point. Zero-strength control emits no overrides. Simultaneous-pass control checks the fixed arithmetic; seven-influence control proves no four-slot truncation; nonfinite row is rejected. Five tests pass normally and under `-O`.
- Captured indices, fitted-rest and original uploaded-normal hashes are retained per frame. Offline normalized LBS-normal diagnostics are finite/unit, with maximum4.72783degrees difference from original source normals. These are diagnostics only, not the contract's future visual normals.
- All visual variants MUST use the same contract policy: rebuild area-weighted smooth normals from current variant source-ID triangle adjacency; project/normalize baseline tangents with deterministic fallback and original handedness. That rendering policy and actual variant upload readback are not implemented or claimed by this worker.

## Scope and integration

Only `weights/` and private `.work/garment61/weights/` were written. The portable candidate has exactly the frozen contract keys; no capture alias or private absolute path is required by its provenance. Root's strict validator must still reject unknown schema/keys, bad IDs/bones/rows and stale source provenance before applying it. If a later experiment adds a viewer, it must restore untouched buffers, obtain a fresh valid original snapshot, then identify any altered GPU buffers as experimental. A/B/baseline controls, paused hold, nonmonotonic seek and torso switching require actual root-controlled graphical execution. No Work/profile upgrade, product fix or appearance admission is requested.
