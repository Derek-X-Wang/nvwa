# Production UI integration acceptance

Issue #26 integrates the accepted Shape/Profile tabs and adjustable timeline in
the existing Rust Studio. This production candidate has passed the native hand
gestures, reload/exchange and Player checks. A separate startup-size harness
also passed actual production-library native UI controls at1024×768. It is not
merged to main and issue #26 remains open pending promotion.

## Artifact identity

All checks below use the final source recorded in
[the build input inventory](build/build-inputs-final-before.json). Its 31 input
files matched after both builds. The temporary 1024-point headless diagnostic
was removed with exact-byte restoration before the later browser probe.
[The rebase checkpoint](rebase-checkpoint.json) verifies that the production
patch is byte-identical and all 31 measured inputs are unchanged after moving
the own unpushed commit onto current main. No build result is inferred from a
different product source.

| Artifact | SHA256 |
| --- | --- |
| Studio `lib.rs` | `876329eb625aed45ce4229ea0277c8949a1337d2ff147e5caa25e17e48981f8e` |
| `editor_layout.rs` | `da45cb7183d28e80cf8b15d1f08f8aa06463e0c5fe4af2b9067fbf8737878b5c` |
| Cargo.lock | `457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73` |
| Final native release executable | `87929040d808531df8b3553cfecc3b1cc0bce14d12d3187f23943bc4430183bb` |
| Final Web Wasm | `884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba` |

The locked native build took 166.28 seconds; the Web release build took 32.48
seconds on this local run. These are build records, not performance comparisons.
The native executable is 103,023,040 bytes and Wasm is 85,605,074 bytes. The Web
gzip first-screen payload is 20,558,369 bytes, or 20,558,892 with the finite Work.
The original release profile remains selected. Issue #27's B profile is not
adopted by this change. Both packages contain the exact pinned craft-ui MIT
notice. Native signing/notarization and hosted distribution are not verified.

## Actual checks

| Status | Check | Evidence and limit |
| --- | --- | --- |
| VERIFIED | Headless production controls | [Final logs](final/README.md): all 93 original tests plus 10 regressions pass; strict clippy passes; five compiled source mutations fail at runtime and restore exactly. |
| VERIFIED | Independent source review | [Review record](build/independent-source-review.json); separate reviewer checked the final source and mutation evidence. GUI was outside that review. |
| VERIFIED | Independent publication review | [Final review](independent-publication-review.json): complete-Work verifier, 44 GUI inventory entries, 22 screenshots, exact redactions, build identity and diagnostic restoration checked. It approves the explicitly partial evidence; it does not establish pending native acceptance. |
| VERIFIED | Independent native follow-up review | [Later review](independent-native-followup-review.json):28 exact GUI copies,8 harness records, complete Work comparisons, actual geometry, method/dependency equivalence and limits pass; PR may be marked ready within #26's documented scope. |
| VERIFIED | Native and Web release builds | [Native](build/native-final-build.json), [Web](build/web-final-build.json), and unchanged before/after input hashes. |
| VERIFIED | Native Studio actual startup | [Screenshot](gui/native-edited-1280.jpg): real rig, 9 meshes, 9 skins, 18 joints, 4 morphs; 1280×720 logical content at 2× pixels. |
| VERIFIED | Native click edit, Save, Undo/Redo | [Complete saved Works](gui/native-json-checkpoint.json): jaw 0→0.73; revisions 1→2→3→4; all other content equal. Continuous native drag is not established by this click. |
| VERIFIED | Web Studio actual startup at two sizes | [1280×720](gui/web-initial-1280.jpg), [1024×768](gui/web-1024-left.jpg), both scale1; the real rig renders and animates. |
| VERIFIED | Actual Web drag and one command | [Edited view](gui/web-edited-1280.jpg) and saved Works: jaw 0→0.8, one revision; Undo restores the original content and Redo restores the edit. |
| VERIFIED | Web tab, split, lock/reset, scrolling | [1280 split](gui/web-split-1280.jpg), [1024 split](gui/web-1024-split-probe-after.jpg), [locked drag](gui/web-1024-split-probe-locked-drag.jpg), [reset retaining lock](gui/web-1024-split-probe-reset.jpg), [unlock/drag](gui/web-1024-split-probe-reset-unlock-drag.jpg), [vertical scroll](gui/web-1024-split-probe-scroll.jpg), [horizontal scroll](gui/web-1024-right.jpg). Complete Work, including revision, is unchanged. |
| VERIFIED | Web Open and native→Web exchange | Actual browser file chooser loads the saved Web edit, then the saved native redo. Downloads match each source Work in every field. [Comparison checkpoint](gui/web-json-checkpoint.json). |
| VERIFIED | Available Web input checks | Focused Work field owns Space; automated Unicode renders “女娲”; Command+A/V replaces/pastes correctly. [Input screenshot](gui/web-command-clipboard-1024.jpg). Unicode injection does not prove physical IME composition. |
| VERIFIED | Actual Web Player | [1280](gui/web-player-1280.jpg), [restart](gui/web-player-restart-1280.jpg), [1024 seek](gui/web-player-seek-1024.jpg): loads the real saved Work; editor hidden; transport works. |
| VERIFIED | Native continuous drag/Undo and split/Escape | Human confirmation on this final candidate: one Undo returns jaw to 0.73; Escape restores the separator's pre-drag height. The later saved Work preserves every other content field; revision4→8 reflects the full, uninstrumented hand session, not a measured single command. [Follow-up record](gui/followup/checkpoint.json). |
| VERIFIED | Web→native exchange and native reload | Actual native Open loads Web jaw0.8/revision4; Save matches the complete Web Work. A click changes only jaw0.6/revision5. Reopening and saving restores the complete original Web Work. [Saved Works and verifier](gui/followup/README.md). |
| VERIFIED | Actual native Player | [Replay](gui/followup/native-player-replay.jpg), [seek](gui/followup/native-player-seek-paused.jpg), [play](gui/followup/native-player-playing.jpg), [pause](gui/followup/native-player-paused.jpg), [stable pause](gui/followup/native-player-pause-stable.jpg) and [restart](gui/followup/native-player-restarted.jpg) show transport and real rig changes with the editor hidden. The source file is unchanged. |
| VERIFIED | Packaged native manual resize | The later manual window is1175×704 content points; Profile, lock/reset/unlock and animation controls work, and the entire saved Work/revision is unchanged. The earlier602×385 capture visibly clips some controls and establishes only human-reported usability. [Follow-up record](gui/followup/checkpoint.json). |
| VERIFIED | Production-library native UI at1024×768 | [Isolated harness report](../../../experiments/18-native-viewport-harness/REPORT.md): actual unchanged `build_app()` and389 identical dependency nodes, only startup resolution changed. Actual tabs, lock/reset/unlock, horizontal scrollbar and transport pass; saved Work/revision unchanged. A focused runtime observer reports1024×768 at scale1. Interactive CUA image pixels are not runtime DPI proof. Exact packaged-binary1024 startup/resize transition remain NOT-RUN. |
| NOT-RUN | Physical IME, browser DPR/zoom, other platforms | No claim from Unicode input, previous candidate checks or a build alone. |

Screenshots are observations of actual running artifacts. They are not a
substitute for a rig or animation system. The fixture animations are authored
idle/wave/turn presets; no AI generation is claimed.

## Small-window diagnostic

An initial browser drag started at y=570 and did not change height. This was
retained privately as an ineffective controller attempt, not classified as a
product defect. A temporary headless test exercised the actual production
controls at fresh1024 and 1280→1024, including lock/reset/unlock, and passed.
[Its patch and result](diagnostic/report.json) are diagnostic evidence only;
the patch is not in production and did not drive a browser.

The subsequent real browser probe used the observed separator at y=565. It
changed the timeline from 210 to 160 points. Lock blocked resizing; reset restored
210 while retaining lock; unlock and another drag reached 160 again. Scrolling
reached the lower status row, and a real Save download matched the original
Web redo Work in all fields. [Probe record](gui/web-small-split-checkpoint.json).
No product source change was needed. The earlier Web checkpoint's uncertainty
is retained verbatim; this later record resolves that specific browser check.

## Reproduction

From the repository root, with the pinned toolchain and dependencies available:

```sh
CARGO_BUILD_JOBS=3 cargo test --workspace --locked
CARGO_BUILD_JOBS=3 cargo clippy --workspace --all-targets --locked -- -D warnings
python3 -B docs/evidence/m1-1-ui/gui/verify-work-snapshots.py
python3 -B docs/evidence/m1-1-ui/gui/followup/verify-followup.py
CARGO_BUILD_JOBS=3 cargo build -p nvwa-studio --release --locked
python3 scripts/package-native.py
bash scripts/build-web.sh release
python3 scripts/serve-web.py --port 9201
```

In another terminal, launch the packaged Studio with a task-owned Work path:

```sh
NVWA_UI_PROJECT="$PWD"
cp examples/m1-sequence.nvwa.json /tmp/nvwa-ui26-review.nvwa.json
"$NVWA_UI_PROJECT/dist/Nvwa.app/Contents/MacOS/Nvwa" --work /tmp/nvwa-ui26-review.nvwa.json
```

Open `http://127.0.0.1:9201/?work=works/m1-sequence.nvwa.json` in a WebGPU browser.
Test at 1280×720 and 1024×768. Click Profile then Shape; drag the separator,
lock it, reset and unlock. At a small timeline height use both scroll axes.
Save before and after layout changes and compare complete JSON including
revision. Drag jaw width once, release, Save, Undo, Save, Redo, Save. Only jaw
and the expected monotonic revision may change. Use actual Open/file chooser
and exchange the saved Works in both directions.

For Player, use the same native executable with `--player --work` and Web URL
`http://127.0.0.1:9201/?player=1&work=works/m1-sequence.nvwa.json`. Confirm the
editor is hidden and restart/pause/seek change playback. Reproduction commands
for pending checks are instructions, not evidence that those checks passed.

## Publication and retained resources

[GUI inventory](gui/MANIFEST.json) records original and public hashes. Screenshots
and saved Works retain exact bytes; two console copies replace only the exact
private Cargo registry prefix with `<CARGO_REGISTRY_SRC>`. The diagnostic log
replaces only the exact worktree prefix with `<UI_WORKTREE>`.
Failed/no-effect controller captures and full machine/process metadata remain
private. Historical test/build failures remain separately scoped and are not
rewritten as current successes. Public evidence contains no executables or
Wasm binaries.

Copied test logs retain Cargo's trailing blank line. Ordinary `git diff --check`
reports that preserved raw-output formatting; source/document checks pass with
logs excluded, and log checks pass with only `blank-at-eof` excluded. No log
content or test assertion is removed to silence the formatting report.

The temporary browser tabs, viewport override and loopback servers were
released. The earlier native window exited with unknown cause and exit code.
[The locked handoff status](handoff-status.json) retains that historical limit.
After manual unlock, the final candidate received the human gesture check and
the actual native exchange/reload and Player checks above. The later default
Studio inadvertently selected around a close/state observation had no edits;
it was stopped by exact task-owned PID before binding the actual Player. That
default Studio capture is excluded from Player proof. Native Player was stopped
after transport verification; the final1280×720 Studio was restarted with the
human's saved0.73/revision8 Work for the remaining target-size handback. Process
IDs, ineffective attempts and private-path screenshots remain private. The
integration worktree is retained. The target-size helper subsequently ran and
was stopped after GUI/geometry checks; the unchanged packaged Studio was
restored with the human's0.73/revision8 Work. No main merge is performed here.
[Current handoff](current-handoff-status.json) records the exact owned process
still running, but a later CUA action reports no available window. The cause is
unknown; no new rendering proof is inferred from that last restart. Completed
GUI acceptance remains scoped to the earlier captures. No further human unlock
or physical action is required for this completed validation stage.

VERIFIED — final-source tests, independent source review, both builds, Web
acceptance, native gestures/reload/exchange/Player and separately identified
production-library1024×768 controls pass. Listed exact packaged geometry,
physical-input/DPI/platform limits remain explicit.
