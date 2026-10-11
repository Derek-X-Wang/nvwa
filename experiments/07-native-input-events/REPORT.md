# Pinned native input event replay

The pinned library loses Command for the tested complete chord in one input frame. Holding Command across frames preserves it. This result proves a difference in library handling of the supplied Bevy messages. It does not establish which messages a physical keyboard or the native CUA adapter actually delivers.

## Scope and actual result

This small executable invokes `bevy_egui::input::write_modifiers_keys_state_system` followed by `write_keyboard_input_messages_system` in a real Bevy `World` and `Schedule`. The order matches the plugin's input sets. It collects the resulting library messages and supplies them to a real egui `TextEdit`. It does not reproduce either library's algorithm in the harness.

Every case starts with the task-owned text `jaw target` and the cursor at the end. Each case then applies a task-owned `SENTINEL` text event to check selection and replacement.

| Supplied messages | Command on egui A press | Selection | Text after sentinel | Assertion result |
| --- | --- | --- | --- | --- |
| A down/up in one frame | false | empty | `jaw targetaSENTINEL` | PASS |
| Command down, A down/up, Command up in one frame | false | empty | `jaw targetaSENTINEL` | PASS |
| Command down in frame 0; A down/up in frame 1; Command up in frame 2 | true | all `jaw target` | `SENTINEL` | PASS |

The one-frame case also emits `Text("a")`. The modifier resource has already reached its final released state when the keyboard system processes the batch. The held case emits A key events with `mac_cmd: true, command: true` and no `Text("a")`.

PASS means each assertion matches the observed dependency behavior. It does not mean the one-frame behavior is desirable or native acceptance passed.

## Reproduce

From `/Users/derekxwang/Development/incubator/Nvwa/nvwa`:

```sh
python3 experiments/07-native-input-events/run_probe.py --target-dir target
```

This requires existing project debug rlibs. The runner selects one compiled bevy_egui artifact and resolves its coherent Bevy and egui artifacts using Cargo fingerprint hashes. It verifies the pinned versions from the artifacts' dependency source paths. It compiles only `probe.rs` with `rustc`, then runs it. There is no Cargo/dependency build or network request. The binary is excluded by the experiment's `.gitignore`.

The exact `rustc` and executable commands, feature set, compiler version, artifact paths, and SHA-256 hashes are in `linked-artifacts.json`. The linked versions were bevy_egui 0.42.0, bevy_ecs/bevy_input 0.19.1, and egui 0.36.2; the Bevy umbrella crate is not directly linked by this probe.

Actual final stdout and `EXIT 0` are preserved in `run-output.txt`. Root reran the same command successfully; see `root-rerun.txt`. An independent cross-model R1 source review found no actionable findings; see [review](REVIEW.md).

## Source support

Cached source root: `/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`.

- `bevy_egui-0.42.0/src/lib.rs:953–961`: `InitReading` precedes `ReadBevyMessages`. Lines 1021–1026 and 1052–1062 place the modifier and keyboard systems in those respective sets.
- `bevy_egui-0.42.0/src/input.rs:375–406`: the modifier system consumes the whole keyboard batch; `Key::Super`/`Key::Meta` sets `win` to the message's pressed state.
- `bevy_egui-0.42.0/src/input.rs:672–730`: the keyboard system takes one modifier snapshot at line 684, allows text based on that final state at lines 699–704, then places that snapshot on each key event at lines 726–730.
- `egui-0.36.2/src/text_selection/cursor_range.rs:109–118`: A selects all only when `modifiers.command` is true. The probe checks this through the actual TextEdit output and replacement, not only source inspection.
- `bevy_egui-0.42.0/src/lib.rs:493–512,1530–1543`: `EguiClipboard::default()` stores a lazy clipboard container; provider initialization happens inside `get()`. This probe uses only A and never executes the C/X/V clipboard branches or `get()`. No actual clipboard is read or written.

## Why the unchanged native jaw drag is inconclusive

The root's native CUA evidence reports that `app.drag` left the pointer at the starting location and produced no edit at either coordinate scale. The same root evidence reports that a native slider click changed jaw `.53 → .71`, with revision `6 → 7`, and Undo/Redo restored/reapplied it. These are observations supplied by the coordinator, not GUI interactions performed by this probe.

The owning input code preserves pointer movement/button ordering: `bevy_egui-0.42.0/src/input.rs:446–483` updates cached pointer position and emits `PointerMoved`, while lines 534–541 stamp that cached position on `PointerButton`. Nvwa's `crates/nvwa-studio/src/lib.rs:625–638` uses egui Slider `changed()` for preview and `drag_stopped()` for a completed drag; line 775 calls `commit_preview()`.

An unchanged pointer and document after the adapter operation does not reveal whether movement events reached Nvwa, whether hit testing targeted the slider, or whether a release event arrived. These observations therefore do not establish a production continuous-drag defect. The keyboard replay supplies no new pointer-delivery evidence. Physical continuous drag remains a separate acceptance check.

## Failures retained and limits

`compile-first-attempt.txt` preserves a Rust path error: this egui version exposes the state at `egui::text_edit::TextEditState`, not the root namespace. The path was corrected without changing assertions.

`run-first-attempt.txt` preserves the initial headless runtime panic: egui requires intentional disposal of unused texture deltas. The probe now calls `output.textures_delta.clear()` because it has no renderer. Input and downstream selection/replacement assertions were unchanged.

The probe bypasses `write_egui_input_system` and its final `ModifiersChanged` event (`input.rs:1517–1519`), feeding a separate egui context. Event-local select-all assertions remain valid; full integration is not tested.

No production source, root manifest, root lockfile, GUI, machine configuration, process state, physical input, clipboard contents, paid API, or external system was changed by this experiment.

VERIFIED — All three actual pinned-library replay cases passed; final executable exit 0.

NOT-RUN — Physical keyboard/clipboard, OS/CUA event delivery, native continuous drag, full EguiPlugin/Winit integration, IME, and native acceptance. No production fix is proposed from synthetic delivery alone.
