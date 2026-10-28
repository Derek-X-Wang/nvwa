# #79 — one bounded same-scene A → B → A

Actual same-scene A/B/A completed. All three exact records, original source/CPU checks, cross-controls, A restoration and screenshot intervals passed. See [RESULTS.md](RESULTS.md) and [evidence/observations.json](evidence/observations.json). Independent image review recommends RETAIN A and no cohort expansion: current B benefit is insufficient in this source0 view. Current-group quality is INCONCLUSIVE / NO-ADOPT; overall #79 remains HOLD. Root owns the actual IAB/GPU and server9205. Worker used only CPU and ephemeral loopback test servers; no retained site build, model run or downloads.

The fixed contract is `contract.json`: `h79aba-v1-hold0`, then independently pinned requests `h79aba-v1-A1`, `h79aba-v1-B`, `h79aba-v1-A2`. All use the original `default-arms` Work, held source0, Combined/Textured, original1280×720 viewport. Only actual typed diagnostic variants change: `a_original` → `b_local_alpha` → `a_original`. This is the retained #78 local-alpha B, not experiment69's rejected mip proposal. No new hair candidate is authored.

`prepare_site.py` creates only `aba82.html` and `aba82-harness.js` beside the authenticated retained site. Original HTML SHA is `26c07697d0792c124537e2b8b8d91e9c06005c88b56523726083ba251d004b2e`. Original transfer-core substring remains byte-exact SHA `44698bd8f212ae656ccf6561b277ceb3bb4e9f01bbf9d51d1ceb3f318dbeab9a`. Wasm/assets/scenes/materials/cameras/dimensions/Work and the311-file validator capsule are copied and authenticated in `.work/hairline-aba79/INPUT-COPY.json`; no compiled target directory is copied.

## Supported replay from immutable observed source

The published documentation tree does **not** verify against the observed-runtime f9 freeze: its README prose changed after the actual run. Do not run the original f9 verifier/server from the published tree and do not overwrite the original freeze to hide that difference. The actual runtime used `SOURCE-FREEZE-v2.json`, SHA `f9b0f757c782297b3bc79125ab6240c7efa3e74f2405dbb95877de5fa50a4054`. Its exact15-file pre-publication source snapshot is retained locally under `frozen-actual-v2/source`. All runtime, generator, server, validator, contract and test bytes remain unchanged. Later additions are RESULTS/evidence; README is the only changed original file.

For an exact supported replay, set `NVWA79_RETAINED` to the retained local `hairline-aba79` bundle containing that source snapshot, original freeze, site, validator capsule and receipts. Set `NVWA79_REPLAY_ROOT` to a separate repository checkout in which both destination directories below are absent. Restore only the immutable15-file source snapshot and authenticated retained inputs. Do not copy any original `actual/` output. These commands are a reproduction recipe; they were not rerun for the documentation update.

```sh
# Both destinations must be absent; use a separate checkout.
test ! -e "$NVWA79_REPLAY_ROOT/experiments/82-hairline-aba"
test ! -e "$NVWA79_REPLAY_ROOT/.work/hairline-aba79"
mkdir -p "$NVWA79_REPLAY_ROOT/experiments/82-hairline-aba"
mkdir -p "$NVWA79_REPLAY_ROOT/.work/hairline-aba79"
cp -R "$NVWA79_RETAINED/frozen-actual-v2/source/." "$NVWA79_REPLAY_ROOT/experiments/82-hairline-aba/"
cp -R "$NVWA79_RETAINED/retained-r2-site" "$NVWA79_REPLAY_ROOT/.work/hairline-aba79/"
cp -R "$NVWA79_RETAINED/validator-root" "$NVWA79_REPLAY_ROOT/.work/hairline-aba79/"
cp "$NVWA79_RETAINED/INPUT-COPY.json" "$NVWA79_REPLAY_ROOT/.work/hairline-aba79/"
cp "$NVWA79_RETAINED/VALIDATOR-ROOT.json" "$NVWA79_REPLAY_ROOT/.work/hairline-aba79/"
cp "$NVWA79_RETAINED/frozen-actual-v2/SOURCE-FREEZE-v2.json" "$NVWA79_REPLAY_ROOT/.work/hairline-aba79/"
cd "$NVWA79_REPLAY_ROOT"
python3 -B experiments/82-hairline-aba/freeze.py --verify
```

The restored tree must print the exact f9 SHA and455 entries before a server is started. This path retains the original pinned request IDs in a separate, empty output tree. Any resulting capture is a **new replay**, not the already observed evidence. Editing a request contract, source or input requires a separately reviewed new freeze; it cannot be described as f9. Never mutate the retained snapshot, original freeze or original actual records.

After checking9205 is free and closing any earlier scene/server, launch from the restored replay checkout only:

```sh
python3 -B experiments/82-hairline-aba/server.py --contract experiments/82-hairline-aba/contract.json --port 9205
```

Freeze verification occurs before binding. Do not edit, retry or tune a measured chain. Stop on its first actual failure and retain partial output. Current review recommends no cohort expansion.

At exactly1280×720 open:
`http://127.0.0.1:9205/aba82.html?work=works/default-arms.nvwa.json&benchmark=1&player=1&case=aba&pace=60`

Wait for `SCREENSHOT A1`, capture the full canvas/status, then repeat for B and A2. With explicit `pace=60`, each qualified window automatically closes after60seconds and advances; no small Next click is required. The explicit Next button closes earlier when supported. Without `pace=60`, root must click Next within90seconds. A5second watch rechecks exact report/frame/token; expiration fails and invalidates. Root should screenshot promptly after each window opens. The final window closes through the same mechanism, invalidates the token, stops the timer and displays DONE with no continuing screenshot qualification.

Each case requires actual ready/current/acknowledged/succeeded request, typed candidate variant, stable2, held source0 and same-scene Work/identity/full-base/appearance/camera. The original prepare/exactText executes its existing readiness/cancel/overlap/stale gates. Original raw strings are concatenated unchanged, preserving Rust numeric tokens. Six currentness fences cover prepare/exactText and before/after manifest/raw responses; an additional fence covers currentness response. A snapshot receiver receipt never proves a current image by itself.

The `SCREENSHOT-WINDOW-OPEN` event follows successful post-currentness-response. `window-close.json` contains its opening timestamp and later exact closing fence. Root must retain a screenshot capture timestamp strictly inside that interval, with matching visible request/token and no FAILED event. Root image qualification is separate from the CPU validator; receiver files alone cannot assert that a screenshot exists. Full original canvas dimensions are retained; the small overlay does not resize it. Final DONE is outside all screenshot intervals.

The loopback receiver validates exact Host/Origin, IDs, order, request/variant/Work/source/stability, envelope/raw-substring SHA and create-only output. No arbitrary output path, CORS, or overwrite is accepted. Raw capture can survive later currentness failure without becoming admitted evidence. All actual output is `.work/hairline-aba79/actual/h79aba-v1/`.

## Source and comparison validation

Set `NVWA79_BASELINE_CAPTURE` to the local path of the authenticated retained prior-A capture described below. After the full chain closes, stop page/server only after pending event receipts drain. Keep screenshots/timestamps separately. Run once with a new create-only output path:

```sh
python3 -B experiments/82-hairline-aba/validate_aba.py \
  --contract experiments/82-hairline-aba/contract.json \
  --records .work/hairline-aba79/actual/h79aba-v1 \
  --baseline "$NVWA79_BASELINE_CAPTURE" \
  --out .work/hairline-aba79/VALIDATE-ABA-v1.json
```

The311-file capsule is verified against original receipt SHA `22b04ae622f3dd465522afebacaaf62bc043792116b4c1919881b0babe6db349`. Each original `check_captures.validate` call runs unchanged. Its original `check` group-comparison AST is executed verbatim for the distinct A1/B and B/A2 controls. The full original matrix admission is not invoked or claimed. This adapter changes no comparison statement. It retains same body/bones/full base/appearance/camera/environment, non-hair buffers, alpha-only hair geometry and source arrays, handles/material/image policy/placement invariants.

A1/A2 restoration compares the entire parsed envelope except exactly `report.request_id`, `frame.request_id`, `frame.stable_updates`. No body, identity, publication, texture, numeric value, camera or generation field is excluded. Different raw envelopes are expected because request IDs differ; all original raw bytes/hashes remain retained. A1 must also match the prior actual-A baseline under the predeclared historical semantic projection below. Baseline raw SHA is independently pinned `d79f44812cd6b840bd8d4f15d71b9f4d886ccc05bce062ea5be5232916c6f4d2`. For same-page A1/A2 no temporal serial is excluded. If any additional same-page difference occurs, stop and preserve it.

The historical semantic projection compares parsed Work and SHA, endpoint/fixed case, all full-base source content except `character_entity`, `generation`, `sample.serial`, and each part's `display_entity`/`mesh_handle`; all buffer content except `entity`/`material_handle`/`mesh_handle` and `bound_image.handle`; all candidate content except `entity`/`mesh_handle`/`material_handle`/`image_handle`/`generation`/`pre_visibility_publication`/`original_standard_material_debug` and `sample.serial`; camera except `entity`; full diagnostic content except target entity/material/mesh handles and material full debug strings. Material texture handles are compared as presence/absence; per-role decoded image hashes and complete image policies remain compared through buffers. Environment is compared from the captured identity. Report/base/appearance/publication runtime metadata are not part of this historical projection; each original validator independently checks the source/binding semantics. Historical page-local entity, resource handle and publication equality is never assumed. This projection is frozen before any new ABA data.

## Verification

```sh
python3 -B -m unittest discover -s experiments/82-hairline-aba -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/82-hairline-aba -p 'test_*.py'
```

Portable tests explicitly use synthetic transport data. They exercise original transfer and called controller readiness, wrong request/variant, Work mismatch, stale/cancel/overlap, exact negative-zero retention, post-network changes, finite windows, manual/pace60 and final stop. Actual loopback HTTP tests cover lifecycle GET/HEAD/config, complete three-stage record/currentness/window order and hostile origin/Host/hash/duplicate/missing-fence/window-bound controls. Normal and optimized runs are separate from retained actual-A source validation, which passed unchanged with position0, normal2.7364758848930516e-15 and UV0 replay errors.

One actual A/B/A is complete. Expand to a necessary frozen cohort only after transport and identity comparison pass and root sees credible B benefit. CPU validation does not score GPU pixels, establish winner/depth behavior or prove hairline improvement. Current #78 local-alpha B showed no new forehead/eye occlusion in this source0 view; the older #76 fringe-B occlusion failure belongs to a different candidate. Routine desktop acceptance remains NOT-RUN under the current policy.
