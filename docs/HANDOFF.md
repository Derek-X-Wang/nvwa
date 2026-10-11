# M0 and thin M1 handoff

M0 is published on `main` as [d74493d](https://github.com/Derek-X-Wang/nvwa/commit/d74493df0ab14f786e798cee03efe5ef9e2e4670). Thin M1 is implemented on `feat/thin-m1`: compose three authored actions over 5–10 seconds, play/pause/seek, click the original character's chest/head for one wave and restore the work, and open the portable work in an editor-free native/Web Player. Both modes use the same Rust core and Bevy runtime. The actual humanoid has skeletal skinning and four real morphs. These authored actions are not AI generation.

The user approved the three slices, tracked as [#14](https://github.com/Derek-X-Wang/nvwa/issues/14), [#15](https://github.com/Derek-X-Wang/nvwa/issues/15), and [#16](https://github.com/Derek-X-Wang/nvwa/issues/16). [Issue index](ISSUES.md), [final verification](M1-VERIFICATION.md), and [Player acceptance](evidence/m1/player-acceptance.md) preserve the evidence and limits. `CLAUDE.md` is exactly `@AGENTS.md` plus a newline.

## Run the existing release artifacts

```sh
cd /Users/derekxwang/Development/incubator/Nvwa/nvwa
./dist/Nvwa.app/Contents/MacOS/Nvwa --player --work "$PWD/examples/m1-sequence.nvwa.json"
```

Omit `--player` to open the same work in Studio with editing and Save. Open the actual exchanged work using `--work "$PWD/docs/evidence/m1/web-sequence.nvwa.json"`. Native work paths must be absolute. Player has Open, playback and seek controls; Studio has editing and save controls.

```sh
cd /Users/derekxwang/Development/incubator/Nvwa/nvwa
python3 scripts/serve-web.py
```

Open [Web Player](http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json) in a WebGPU-capable browser. The loopback server serves the ordinary static `dist/web` bundle. This session retains the existing server on 9201 and its [exchanged-work Player preview](http://127.0.0.1:9201/?player=1&work=works/exchanged.nvwa.json); reuse it if already running. No future implementation work is scheduled.

To recreate the extra exchanged-work URL after rebuilding:

```sh
cp docs/evidence/m1/web-sequence.nvwa.json dist/web/works/exchanged.nvwa.json
gzip -n -9 -c dist/web/works/exchanged.nvwa.json > dist/web/works/exchanged.nvwa.json.gz
```

## Rebuild and test

```sh
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo clippy -p nvwa-studio --lib --target wasm32-unknown-unknown --locked -- -D warnings
python3 tools/blender/validate_fixture.py
cargo build -p nvwa-studio -p nvwa-cli --release --locked
python3 scripts/package-native.py
python3 scripts/install-web-tools.py
bash scripts/build-web.sh
```

Rust 1.95.0 and dependencies are pinned. The Web tools installer supports the verified macOS arm64 host and installs project-local tools. Generated native/Web artifacts and caches are ignored by Git. [M1 manifest](evidence/m1/build-manifest.json) records the tested source and release hashes; the earlier [M0 manifest](evidence/build-manifest.json) remains historical. The commit containing the M1 manifest identifies its source snapshot.

[CLI/GUI equivalence](evidence/m1/cli-gui-equivalence.md) contains executable replay and whole-document comparison commands. CLI edits an offline work file; reopen it in the GUI.

## Actual results

- Final **57 Rust tests passed**, zero failed/ignored. Fmt and strict native/Wasm clippy passed. Native and Web release builds passed. Independent cross-model R2 reviews accepted all three slices and their targeted repairs.
- Actual native5 → Web6 → fresh native6 exchange retained the complete document; real CLI replay reproduces it. Native/Web Player load, completion, replay, pause/seek, click-triggered real wave and exact cursor restoration were observed. Interaction leaves document/history unchanged.
- Native packaged assets worked after copying the app and launching from `/tmp`. Static Web also worked from `/published/`. Actual Web invalid JSON/UTF-8, size overflow, redirect, missing files, hash mismatch and 30-second stalled-body timeout produced errors without a fallback character. Manual Web Open recovered. See [actual final Player screen](evidence/m1/player-final.png).
- [Performance](PERFORMANCE.md): physical1280×720, 600 recent cadence samples, finite revision6 work holding its completed pose. Native p50/p95 **8.327/8.924 ms**, peak child RSS **229.5 MiB**; Web **8.300/9.500 ms**. This does not measure continuous-animation GPU time. M0 continuous-idle measurements remain separately recorded. Unique gzip bytes for the measured work: **14,179,929**; duplicate GLB requests remain #6.
- [Five isolated experiments](EXPERIMENTS.md) retain conclusions and reproduction. The original asset, atomic command core and shared runtime were adopted. Controlled A/B rejects naive joint-rotation copying; rest-basis correction passes numerical checks, without a general retargeting claim. True model inference is NOT-RUN because no usable local runtime/authorized weights were found; authored preset seam tests say `ai_generated=false`.

## Open limits and cleanup

All 13 M0 gap issues remain open. CJK font rendering, broader native/Web input checks, viewport/DPR scaling, bounded edit history, production weighting, dependency notices/signing and additional platforms remain separate work. Full hotspot containment across every pose/morph/scale is unverified; current interaction is restricted to conservative chest/head regions of the original fixture. Public hosting, cold Web startup, exact first presentation, GPU timestamps and browser/GPU memory are NOT-RUN.

The extra **native failed-startup manual-recovery GUI check is NOT-RUN to completion**: the desktop automation adapter lost its window binding while the actual app stayed alive. Normal native Open, headless native recovery and actual Web negative recovery passed; they do not substitute for that GUI check. This is recorded under #2. No product crash is inferred.

All implementation/review workers finished. No task-owned compiler or native renderer is retained. The negative-response server on9202 was stopped. The temporary relocated app was removed after binary/asset equality checks; evidence is retained and the standard `dist/Nvwa.app` remains. Only the loopback preview server/tab is retained. No paid API/cloud resource, hosted deployment, signing, merge or unlimited CI was used.

PARTIAL — Thin M1 local functionality, actual dual-platform release runs/exchange,57tests and cadence measurements verified; the explicit hand-test/platform/measurement limits remain open.
