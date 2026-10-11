# M1.1 tab and timeline integration

The Character inspector now has Shape and Profile tabs. The timeline has a
resize handle, a height lock and a layout reset. Timeline content can scroll in
both directions when the window or the timeline is small.

The private `editor_layout` module isolates the pinned craft-ui controls. The app
owns the selected tab, preferred timeline height, lock and drag cancellation
state. These values belong to the current Studio session. They are not Work
fields, saved layout settings or command history. A temporary small window
clamps the displayed height without replacing the preferred height.

Studio clones layout state before drawing and installs it only after egui's
final pass. The existing preview, command and file actions still use that same
final-pass guard. Shape editing still previews during a drag and commits one
command on release. Player still has immutable access to the editor and draws
its existing transport without the editor layout controls. The default save
path remains `scene.nvwa.json`. The Bevy loop, runtime, Work schema, Web input
adapter and build profile are unchanged by this source integration.

Bevy's Studio system and the actual-control tests both call `draw_editor_ui`
with the same borrowed `EditorUiSession`. That session groups the editor,
playback, Studio state, platform file I/O and input guard references. The draw
function has four arguments. Its draw and commit body is byte-identical to the
preceding implementation checkpoint. A test initializer also uses a struct
literal. These changes resolved strict clippy findings without lint allowances.

`Reset layout` selects Shape and restores the 210-point preferred timeline
height. It retains the height-lock choice. Escape restores the height from the
start of an active split drag. Locking during a drag also restores that height.

## Headless verification

`CARGO_BUILD_JOBS=3 cargo test --workspace --locked` passed all 103 tests on the
final restored source, with
41 Studio tests: all 31 original tests plus 10 layout and input tests. The
original `lib.rs` test bodies are unchanged apart from formatting. The tests
exercise actual craft-ui tabs and split controls, Escape, preferred height
through a 300-point window and recovery, the production Studio pointer guards,
real slider drag/one revision/Undo/Redo, complete Work and retained history
preservation, and discarded-pass layout and Reset shape command intents.

The new Work-path regression clicks the production `scene.nvwa.json` TextEdit
and sends Space through the production draw path at 1280×720 and 1024×768.
Playback, Work and command history remain unchanged. Independent review found
that its Command-Z events did not arm the production shortcut condition:
egui 0.36 updates `InputState.modifiers` through `ModifiersChanged`, not the
modifiers attached to a key event. The test now sends both events, exercises
unfocused Undo/Redo as a positive control, and checks focused-tab shortcuts
with Z still unconsumed. The strengthened tests passed in a full workspace run
and in the final run after mutation trials. They do not change production
behavior.

The first workspace run retained one failed test: it assumed that a mouse click
on a Profile tab also gave the tab keyboard focus. That assumption does not
match egui's ordinary click behavior. This was a test error, not a product bug.
The corrected test reaches the actual Profile tab through real Tab-key focus
traversal, checks the focused widget's rectangle, then sends Space through the
production draw path and verifies that playback does not start. It does not
assign focus or input guards directly. The second workspace run passed.

Earlier logs and source hashes remain under `.work/ui26/`, including the first
failed run and the successful checkpoints before `EditorUiSession`. Their
public copies outside the `final/` evidence directory are earlier checkpoints.
They do not establish the identity of the final source.

The current source passed `tests-session.log`, strict
`cargo clippy --workspace --all-targets --locked -- -D warnings` in
`clippy-session.log`, and the final restored workspace run in
`tests-session-final.log`. Its report is `session-final-checkpoint.json`.
Sanitized copies are in [the final evidence directory](../evidence/m1-1-ui/final/README.md).

| Final source | SHA256 |
|---|---|
| `crates/nvwa-studio/src/lib.rs` | `876329eb625aed45ce4229ea0277c8949a1337d2ff147e5caa25e17e48981f8e` |
| `crates/nvwa-studio/src/editor_layout.rs` | `da45cb7183d28e80cf8b15d1f08f8aa06463e0c5fe4af2b9067fbf8737878b5c` |

Five bounded source mutations each made its targeted real-control test fail at
a runtime assertion. The original source bytes and hashes were restored after
each trial, then all 103 tests passed. No trial disabled a test or substituted a
different implementation seam. Exact diffs, commands, assertions and before/
after hashes for the current borrowed-session source are in
`.work/ui26/mutations-final/manifest.json` and its adjacent logs. The earlier
`.work/ui26/mutations/` records remain separate checkpoint evidence. Public
copies of the fresh trials are under `docs/evidence/m1-1-ui/final/mutations-final/`.

| Production mutation | Observed failure |
|---|---|
| Apply idle zero-delta resize clamping | Preferred height changed from 422.4 to 396 points after window shrink |
| Commit every changed slider frame | Actual slider no longer retained a preview during the drag |
| Remove only the Space keyboard guard | Space started playback while the production Work-path field had focus |
| Remove only the command keyboard guard | Armed, unconsumed Z on the focused Profile tab changed Work revision from 3 to 5 |
| Remove the final-pass side-effect guard | A discarded pass installed Profile instead of retaining Shape |

VERIFIED — final restored source passes 103 workspace tests; all original 31
Studio tests retained; five runtime-red trials with exact restores; rustfmt and
diff whitespace checks pass; strict workspace/all-targets clippy passes.

## Actual builds and GUI acceptance

Root built and started the exact final candidate on native macOS and Web.
The native click edit, Save and Undo/Redo passed complete-Work comparisons.
Web passed actual drag/one command, Undo/Redo, layout invariance, Open/reload,
native-to-Web exchange and Player startup/transport. Web tab/split, lock/reset
and scrolling passed at 1280×720 and 1024×768. The later small-window probe
resolved an ineffective pointer attempt by locating the actual separator;
no source change was required.

The human confirmed continuous native drag/one Undo and split/Escape on this
final production candidate. Actual native Open/reload, Web-to-native exchange
and native Player transport also passed. Complete saved Works verify the
exchange and reload. The small native handback was about602×385 content points
and visibly clipped some controls. A later packaged resize1175×704 passed
control checks and complete Work invariance. A separate startup-size harness
then ran the unchanged production UI at1024×768 and passed real controls plus
full Work invariance. Exact packaged-binary1024 sizing, physical IME and DPI
limits remain explicit. See the
[production acceptance report](../evidence/m1-1-ui/ACCEPTANCE.md) for artifact
hashes, individual evidence, commands and remaining checks.

The earlier experiment's evidence is separately scoped at the
[frozen prototype checkpoint](https://github.com/Derek-X-Wang/nvwa/blob/bb21905879d1fdd6dd3a37ba38400d90801a6b72/docs/evidence/m1-1/ACCEPTANCE.md).

For actual GUI checks:

- Use explicit task-owned Work paths or browser downloads. Compare every Work
  field after layout actions, including the revision, since layout does not
  issue a command. After a shape edit and Undo/Redo, compare complete content
  with only the expected monotonic revision change allowed.
- Locate the split from the current window geometry. Its height changes take
  effect in the next drawn frame. Drag it across multiple frames, then press
  Escape before releasing. Verify recovery, lock and reset at both required
  window sizes.
- The lock/reset row stays outside the scrolling timeline content. At 1024×768,
  use both scroll directions to reach transport, seek and sequence controls.
  Scrolling and layout changes must leave Work and history unchanged.
- Mouse-selected tabs normally leave Space available to transport when no
  widget has keyboard focus. A tab reached by keyboard traversal, or the
  focused Work-path TextEdit, must retain keyboard ownership.
- Recheck actual Player startup and transport with the editor hidden. Keep
  physical IME and device-pixel-ratio limits explicit unless performed on this
  production candidate.
