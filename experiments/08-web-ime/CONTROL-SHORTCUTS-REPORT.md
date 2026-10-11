# Desktop Web Control shortcuts repair

Bounded repair of PR18's final-review P2 at base HEAD
`44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`.
Production scope: `crates/nvwa-studio/src/web_input.rs` only.

## Cause and behavior

The proxy textarea intercepted keys but dropped Control+H/K/U/W. Its temporary
text cannot apply those operations to the canonical Work string. The retained
CPU red regression reproduces this defect. An initial parent browser attempt
left `abc` unchanged, but later event tracing proved that CUA's `ctrl+h` call
sent Meta+H. That attempt is not a valid Control+H reproduction. Explicit
Playwright `Control+h` on the rebuilt release sends Control and deletes the
character. The installed-callback results are recorded separately in
`docs/evidence/web-input-control/ACCEPTANCE.md`.

Pinned egui 0.36.2 owns the edit behavior:

- `src/widgets/text_edit/builder.rs:1431–1454`: Control+H deletes the previous
  character, K deletes after the cursor to paragraph end, U deletes before the
  cursor to paragraph start, and W deletes the previous word or selection.
  These branches require Control and permit additional modifiers, including Shift.
- `src/text_selection/cursor_range.rs:150–161,265–272`: macOS Control+A/E/B/F/P/N
  moves to row start/end, left/right, or up/down. These forms require macOS,
  Control, and no Shift. Command+A retains its earlier select-all branch.

The transport now forwards these letters in both cases, retains the event's
modifiers/pressed/repeat fields, and requests `preventDefault` for editor-owned
operations. Command+V still permits browser ClipboardEvent delivery. Plain
printable keys still use DOM input. The composition guard and clipboard
listeners are unchanged.

There was a separate setup gap for Mac navigation: egui's Web context defaults
to `OperatingSystem::Unknown`, and no existing context OS initialization was
found in the pinned integration. The parent authorized desktop Web input setup
in this file. The plugin now initializes each added context through the shared
`configure_web_os` function using pinned `OperatingSystem::from_user_agent` and
the existing UA. It runs after context creation and before event delivery.
The existing desktop-only Agent gates this system, so native/mobile behavior
does not change. Unrecognized desktop platforms stay Unknown. This metadata
newly enables egui's own macOS navigation conventions; it adds no editing logic.

## Red then green

The unit regressions were added before the transport repair. The frozen
`control-shortcuts-red-source.rs` is that exact production source plus the first
three regression tests. The runner compiles it without Cargo against a coherent
cached bevy_egui 0.42.0 / egui 0.36.2 artifact pair, verified using fingerprint
relationships and dependency source paths.

Commands from the repository root:

```sh
python3 experiments/08-web-ime/run_control_shortcuts_probe.py --stage red --source experiments/08-web-ime/control-shortcuts-red-source.rs
python3 experiments/08-web-ime/run_control_shortcuts_probe.py --stage green
CARGO_BUILD_JOBS=2 cargo test --locked -p nvwa-studio --lib web_input::tests
CARGO_BUILD_JOBS=2 cargo clippy --locked -p nvwa-studio --all-targets -- -D warnings
```

Red output: `FAILED. 8 passed; 3 failed`, exit 101. Control+H left `abc` instead
of `ab`; Control+A left the cursor at index 2 instead of 0; repeated Control+H
also left `abc`.

Green output: `ok. 12 passed; 0 failed`, exit 0. The added fourth regression
covers platform/Shift limits. Targeted Cargo test output: 12 passed, 19 filtered.
Strict native clippy completed successfully. Full outputs and exact rustc
commands are in the adjacent `control-shortcuts-*-output.txt`, Cargo/clippy logs,
and artifact JSON files. The runner removes temporary source wrappers/binaries
on exit and changes no Cargo dependencies.

The behavior tests exercise the actual production `key_event`, shared Work
TextEdit, and real pinned egui. They check text edits, selected-word deletion,
all six Mac cursor moves, event-level modifiers independent of RawInput defaults,
repeat/release, Command+A and event-based paste ownership, plain printable-key
fallthrough, and unsupported platform/Shift constraints. Final Mac fixtures use
the exact shared production OS initializer. Browser scheduling is not claimed
by these CPU tests.

## Source hashes and limits

- Final `crates/nvwa-studio/src/web_input.rs` SHA-256:
  `30ee884731913c0d65bbaccb9e29b06e5681d82e25a8a95c4337fa9a043cb2d7`.
- Frozen red source SHA-256:
  `06b1af3b9225017b3f0f51cdce0f73f1cc9745317086bc0b12ad9351f7b5f8f1`.
- Probe runner SHA-256:
  `dee0106b3c76793cd80d40f133e67c9df09d02e9c37a1d2f47b9fd9ed141fbd0`.

No native/editor implementation, manifests, dependencies, lockfile, root docs,
other experiments, commits, pushes, remote publication, user UI, or clipboard
were changed by this worker. Cargo used the one parent-approved compile slot
with two build jobs; that slot is now released. Temporary probe directories
were removed. Remaining task artifacts are only the owned production file and
new Control-shortcut experiment sources, logs, metadata, and this report.

PARTIAL — red/green pinned-egui regressions, targeted Cargo tests, native strict
clippy, rustfmt and diff whitespace check passed. Wasm/browser callbacks,
post-fix physical UI and final integration are parent-owned and NOT-RUN here.
