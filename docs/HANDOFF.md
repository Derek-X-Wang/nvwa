# M0 and thin M1 handoff

M0 was first published on `main` as [d74493d](https://github.com/Derek-X-Wang/nvwa/commit/d74493df0ab14f786e798cee03efe5ef9e2e4670). Thin M1's original implementation/evidence commit is [4af6a19](https://github.com/Derek-X-Wang/nvwa/commit/4af6a1963783199f2b4bf4e5d2b44ca694900ecb). [PR #17](https://github.com/Derek-X-Wang/nvwa/pull/17) received independent Standards and Spec reviews; a P3 transport-widget duplication was repaired in `976331d`, and the PR is merged to main at [96c00de](https://github.com/Derek-X-Wang/nvwa/commit/96c00dedf9a4a74038edb7abf20d99d89871ae6b). Thin M1 composes three authored actions over 5–10 seconds, plays/pauses/seeks, lets a chest/head click play one wave and restore the work, and opens the portable work in an editor-free native/Web Player. Both modes use the same Rust core and Bevy runtime. The humanoid has skeletal skinning and four real morphs. The authored actions are not AI generation.

All three user-approved slices are closed after their documented local acceptance, tracked as [#14](https://github.com/Derek-X-Wang/nvwa/issues/14), [#15](https://github.com/Derek-X-Wang/nvwa/issues/15), and [#16](https://github.com/Derek-X-Wang/nvwa/issues/16). [Issue index](ISSUES.md), [M1 verification checkpoint](M1-VERIFICATION.md), [PR #17 review](evidence/pr17-review/REVIEW.md), and [repair acceptance](evidence/pr17-review/ACCEPTANCE.md) preserve results. The 57-test and dual-release result is the pre-font PR17 repair snapshot; it does not validate the current font branch. The M1 checkpoint predates the native recovery screenshots linked below. `CLAUDE.md` is exactly `@AGENTS.md` plus a newline.

The current work branch is `fix/cjk-input-acceptance`. The pinned, OFL-licensed static Regular 400 fallback has now passed 59 workspace tests, strict native/Wasm checks, both release builds, actual native/Web Chinese rendering and Unicode GUI Save/Open. Both packages carry exact font notices. [Font/input acceptance](evidence/input-fonts/ACCEPTANCE.md), [manifest](evidence/input-fonts/build-manifest.json), [roadmap](ROADMAP.md) and [font experiment](../experiments/06-cjk-fonts/REPORT.md) separate these results from remaining physical-input checks. This branch is pending merge.

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

Open [Web Player](http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json) in a WebGPU-capable browser. The loopback server serves the ordinary static `dist/web` bundle. For current milestone status and proposed work, see the [roadmap](ROADMAP.md).

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

Rust 1.95.0 and dependencies are pinned. The Web tools installer supports the verified macOS arm64 host and installs project-local tools. Generated native/Web artifacts and caches are ignored by Git. The [M1 manifest](evidence/m1/build-manifest.json) records the original `4af6a19` snapshot; the [PR #17 repair manifest](evidence/pr17-review/build-manifest.json) records the later repaired release snapshot; the earlier [M0 manifest](evidence/build-manifest.json) remains historical. Each manifest names its source/artifact hashes and must not be relabelled as a test of the current font branch.

[CLI/GUI equivalence](evidence/m1/cli-gui-equivalence.md) contains executable replay and whole-document comparison commands. CLI edits an offline work file; reopen it in the GUI.

## Actual results

- On the PR #17 repair snapshot, **57 Rust tests passed**, zero failed/ignored. Fmt and strict native/Wasm clippy passed. Native and Web release builds and actual local runs passed. Independent Standards and Spec reviews accepted the scope; the one P3 transport suggestion was repaired and accepted in targeted rereviews. See [review](evidence/pr17-review/REVIEW.md), [acceptance](evidence/pr17-review/ACCEPTANCE.md), and [repair manifest](evidence/pr17-review/build-manifest.json). This evidence predates the current font integration.
- Actual native5 → Web6 → fresh native6 exchange retained the complete document; real CLI replay reproduces it. Native/Web Player load, completion, replay, pause/seek, click-triggered real wave and exact cursor restoration were observed. Interaction leaves document/history unchanged.
- Native packaged assets worked after copying the app and launching from `/tmp`. Static Web also worked from `/published/`. Actual Web invalid JSON/UTF-8, size overflow, redirect, missing files, hash mismatch and 30-second stalled-body timeout produced errors without a fallback character. Manual Web Open recovered. See [actual final Player screen](evidence/m1/player-final.png).
- [Performance](PERFORMANCE.md): physical1280×720, 600 recent cadence samples, finite revision6 work holding its completed pose. Native p50/p95 **8.327/8.924 ms**, peak child RSS **229.5 MiB**; Web **8.300/9.500 ms**. This does not measure continuous-animation GPU time. M0 continuous-idle measurements remain separately recorded. Unique gzip bytes for the measured work: **14,179,929**; duplicate GLB requests remain #6.
- [Seven isolated experiments](EXPERIMENTS.md) retain conclusions and reproduction. The original asset, atomic command core and shared runtime were adopted. Controlled A/B rejects naive joint-rotation copying; rest-basis correction passes numerical checks, without a general retargeting claim. True model inference is NOT-RUN because no usable local runtime/authorized weights were found; authored preset seam tests say `ai_generated=false`.

## Open limits and cleanup

The M0 acceptance issues remain tracked independently. Issue1's font fix has completed its bounded technical acceptance on the current branch, pending merge. The shared static fallback retains 30,890 mapped codepoints and 31,036 glyphs; rare supplementary Han remains unsupported. Actual same-file Web gzip sum is 20,497,855 bytes, up 6,314,437 from PR17's repaired pre-font bundle. The same demo Player total is 20,498,378 bytes; compression is not cold-network timing. See [font size impact](evidence/input-fonts/font-size-impact.json) and [source/license register](SOURCES-LICENSES.md).

Broader native/Web text, drag, clipboard, focus and viewport/DPR checks, bounded edit history, production weighting, dependency notices/signing, and additional platforms remain separate work. Full hotspot containment across every pose/morph/scale is unverified; current interaction is restricted to conservative chest/head regions of the original fixture. Public hosting, cold Web startup, exact first presentation, GPU timestamps and browser/GPU memory are NOT-RUN.

The native missing-work GUI recovery is now observed on the pre-font PR17 release binary: the Player showed an error with no fallback character; desktop automation triple-clicked the native file field, used `typeText` with an ASCII path to a temporary `.work` copy, then clicked Open; the real character loaded and played idle. See [missing-work screen](evidence/input-fonts/native-missing-main.jpg) and [recovered screen](evidence/input-fonts/native-recovered-main.jpg). This is a temporary local acceptance step, not a public fixture path. It confirms basic ASCII path-field entry and recovery only. CUA clipboard paste and `super+a` were attempted without the intended result; they do not establish physical-input failure. Native bulk Unicode `typeText` omitted Chinese characters, while the loaded Unicode filename rendered and GUI Save/Open worked. Native CUA continuous drag did not produce an edit; a longer attempt was blocked when the Mac locked. After manual unlock, two distinct drag-coordinate attempts still made no edit. Native track-click edit, one Undo, Redo and whole-document persistence passed separately; actual per-key Space focus protection and macOS window zoom/recovery passed. See [unlocked acceptance](evidence/input-fonts/UNLOCKED-ACCEPTANCE.md). Web one-drag/one-Undo whole-document checks and individual Space/key focus guards passed. See [input diagnosis](evidence/input-fonts/INPUT-DIAGNOSIS.md). Physical IME/clipboard/Command keys, native continuous drag and OS blur/refocus remain open under issue2.

PR #17's merge and release verification are complete. Current font acceptance is recorded, and issue2 remains partial. The desktop tool could not unlock the Mac; the user manually unlocked it and native acceptance continued, with no bypass or system change. New font-build performance, cold startup and memory measurements are NOT-RUN. Historical performance reports remain tied to their earlier artifacts. No hosted CI workflow is configured; hosted CI remains NOT-RUN. No paid API/cloud resource, public deployment, signing, or other-platform validation is claimed.

PARTIAL — M0 and approved thin M1 are merged and locally verified. PR #17 repair snapshot has 57 passing tests and dual-target release checks/runs. Native failed-startup recovery is now observed. Current font branch has 59 passing tests, both release builds and native/Web CJK/Unicode GUI acceptance. Native track-click edit/Undo/Redo/persistence, per-key focus protection and actual window zoom/recovery also passed after unlock. Remaining physical input, native continuous drag/OS focus, platform and performance gaps stay open.

Current checkpoint lifecycle: previous font builds and native renderers exited after evidence was preserved. The unlocked native renderer is retained paused for the user’s physical hand-test; its exit code is pending, not zero. A bounded dependency-event replay completed, was rerun by root and independently reviewed; [report](../experiments/07-native-input-events/REPORT.md). It does not verify physical keyboard delivery. Keep the existing loopback server on9201 for the user preview. The negative-response server remains stopped, no machine-wide permissions/settings changed, and no paid/cloud resource was used. The font PR is pending merge; #2’s remaining physical/native input checks are awaiting hand-test results.
