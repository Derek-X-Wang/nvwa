# Proposed desktop Web input adapter contract

**Current accepted contract:** Browser textarea/OS IME owns uncommitted composition. The canvas Work field displays committed text only. Preedit/cancel send no canonical egui text event; a nonempty confirmed end sends one ImeCommit, followed by immediate-input dedupe. All inline-preview and rollback sections below are rejected historical design discussion. Final source has no snapshot/reconstruction/cleanup hook. The Work helper retains only a stable target ID; ordinary editing, selection and commands stay shared Rust/egui.

This records the diagnosis-era proposed contract. The coordinator subsequently authorized the implementation; the accepted bounded differences are recorded below and in REPORT.md.

## Minimal seam

Add a desktop-Web-only adapter after the pinned plugin has installed `input#egui_text_agent`. Reuse that element if practical; a separate textarea is an alternative, not necessary for the bounded Work-field fix. Keep the upstream mobile/Safari route as its existing owner. Adding desktop listeners and activation is necessary: unhiding the existing element alone cannot create its mobile-gated composition callbacks.

Use the public `bevy_egui::input::EguiInputEvent { context, event }` message as the integration seam. A browser callback enqueues an egui event plus the bound context identity in a small owned queue. A Bevy system drains the queue before `EguiInputSet::WriteEguiEvents` consumes it and before `EguiPreUpdateSet::BeginPass`. Request redraw when the queue changes. This reaches the same egui events verified by the executable.

`TextAgentChannel` is public but its sender/receiver fields are private in the pinned version. An external adapter cannot send through that resource without changing the dependency. Prefer its own queue and the public event message.

## Activation and context ownership

After egui produces `EguiOutput.platform_output.ime`, identify the context and its owning canvas/window. Enable, position and focus the agent only while that context owns editable text. Observe `should_interrupt_composition` if the focused text/cursor changes. Close the agent when the output no longer requests IME. Restrict focus changes to state transitions; do not call focus every frame or while an unrelated control/browser window owns focus.

DOM focus must be usable in a user gesture. A desktop pointer-up handler can schedule/perform agent focus after the UI has acquired text focus; a same-frame post-output system may work in desktop browsers but needs actual browser checks. Avoid transferring focus on pointer-down before egui has processed the Work-field click. The agent must be visually transparent and unobtrusive but focusable; `hidden=true`/`display:none` prevents physical IME. Avoid covering the rendered input or taking pointer hit tests.

Queue entries must retain the context/text-target ownership applicable when the event occurred. Drop/cancel stale entries after real blur, target change or adapter teardown. Do not route an old composition commit into a newly focused field.

## Composition and ordinary text: one owner

Map composition update to `egui::Event::Ime(Preedit { text, active_range_chars })` and composition end to `Ime(Commit(text))`. Begin clears only the agent's temporary DOM buffer and marks the composition session. Preedit is replacement state, not a series of appended `Text` events. End emits the committed string exactly once, then clears the temporary DOM buffer.

The following non-composing `input` event may repeat the same committed data (`insertFromComposition` or browser-specific final input). Deduplicate by the composition session/event sequence, not by suppressing every later occurrence of the same string. Handle browsers that report the final text only through input; this is an explicit alternative finalization path. Empty/canceled composition must clear preedit without inserting stale characters.

Ordinary text uses the DOM input event's committed data once. Do not also emit `Text` from printable keydown. This includes ASCII, Unicode, Space, and paste. While composition is active, suppress translation of composing/229 keyboard events and ordinary printable input; candidate navigation/Space/Enter belong to the IME.

The probe shows why ownership matters: `Ime::Commit("女娲")` followed by ordinary Unicode `Text` produces `女娲女娲`; `KeyboardInput.text` alone is ignored by the pinned keyboard translator. Reading the helper's value after composition rather than its committed event can also capture a stale/partial string.

## Keys, Command and clipboard

When the agent owns DOM focus, its keyboard events do not normally reach Winit's canvas listeners. The element is a sibling of the canvas; normal bubbling goes to body/document, not to the canvas. Forward navigation/edit/control keys directly to egui with per-event `shift/ctrl/alt/meta` modifiers and repeat state. Do not depend on synthetic key dispatch to the canvas or the pinned keyboard batch's final modifier state. The prior native probe demonstrates why a full Command chord in one batch can lose Command.

Preserve Arrow/Home/End, Backspace/Delete, Enter, Tab, Escape and the supported editor shortcuts. Prevent browser defaults only for handled keys. Tab/Enter/Escape must preserve egui's intended focus/submit behavior and then return DOM focus to the canvas when text editing ends. Pass Space as ordinary text while editing; the existing playback guard must continue to see keyboard interest. After real editing ends, Space should again reach viewport playback.

Command/Ctrl+A should send the egui selection shortcut, not select the temporary agent buffer. Copy/Cut should use egui Copy/Cut and its existing platform output/clipboard handling for the actual selected text; the temporary DOM buffer does not represent the Work field's selection. Paste should use one browser paste/input path and emit committed text once. Test only task-owned clipboard sentinels. Avoid emitting paste both from keydown and from the paste/input callback. Browser clipboard permission/focus restrictions remain browser acceptance cases.

## DOM focus versus egui focus

Pinned Winit `web/event_loop/window_target.rs:86–109` attaches blur/focus to the canvas. A focus transfer to the agent sends `WindowEvent::Focused(false)` and clears Winit modifiers. `bevy_winit/src/state.rs:360–363` updates `Window.focused`; `bevy_egui/src/input.rs:1501–1510` copies it to `EguiInput.focused`.

That event does **not** itself prove loss of egui widget selection. The real egui replay verified that `RawInput.focused=false` preserves the text widget's memory focus/selection and still accepts Commit. `Memory::has_focus` deliberately ignores whole-window focus (`egui/src/memory/mod.rs:881–890`); `TextEdit` processes events based on memory focus (`widgets/text_edit/builder.rs:570–573`). `Response::has_focus` and cursor painting additionally require viewport focus (`response.rs:344–351`, builder.rs:911–912). Explicitly surrendering egui widget focus loses the commit in the probe.

Treat canvas→owned-agent transfer as internal editor focus. Preserve the egui widget ID and selection; do not synthesize widget surrender or cancel its composition. Immediately before BeginPass, use a context-local composite `EguiInput.focused` condition when `document.hasFocus()` and the active element is this context's canvas or owned agent. Do not globally force `Window.focused=true`, and do not conceal real page/window blur. A real external blur clears adapter modifier/composition state and stale events. Restore canvas DOM focus only after editing ends or a canvas interaction requests it.

## Candidate placement

Use `EguiOutput.platform_output.ime.cursor_rect` (and `rect` when needed) for the agent position. Transform egui points to DOM CSS pixels using the context's actual pixels-per-point, backing canvas size, DOM bounding rectangle, and page scroll. Position the browser input at the text cursor so the OS candidate menu follows it. Do not assume physical pixels equal CSS pixels or hardcode the Work-field coordinate. Reposition on zoom, resize, scrolling and cursor movement. Native Winit IME methods are not usable for this on Web; they are no-ops in the pinned web backend.

## Lifetime and acceptance

Retain the exact Closure/listener handles until teardown. Remove each callback from the same element/document and event name where it was installed. Install once per owning canvas/context; a reload/context replacement must not duplicate listeners. If reusing the upstream-owned input, remove only adapter callbacks, not the plugin's element/mobile callbacks. A custom textarea is fully adapter-owned and should be removed on teardown.

Required browser checks: installed desktop callback replay changes the real Work field to the sentinel exactly once; ASCII and repeated identical committed strings; composition cancel/restart; nav/select-all; task-owned copy/cut/paste; Space while editing versus after edit; canvas↔agent internal focus; actual external blur/refocus; candidate menu position at zoom/device-pixel-ratio variants. Then repeat the user's physical Chinese IME test. Synthetic DOM composition and library replay do not replace that final physical check.

## Accepted implementation scope and cleanup contract

The adapter owns a separate `textarea#nvwa_text_input`. It activates only for the explicit shared Rust Work-field ID. Other mutable egui targets, including slider numeric edits, keep the existing canvas/Winit keyboard route. Web Player gains no new path input. Native rendering stays exactly the original TextEdit code. Mobile helper routing stays upstream-owned and has no new acceptance claim.

The canonical Work String remains `StudioUi.file_path`. egui inserts preedit directly into that String, so queued cancellation after widget focus changes is insufficient: the stale target is correctly filtered at drain, but its preview can remain. The shared Rust wrapper now captures the baseline String and isolated cursor/undo state on first nonempty preedit. Applied commit/ordinary text/paste/cut clears the snapshot. When focus changes, cleanup restores only if the String still matches the same session's last preview. It never replaces a newly loaded path or a committed edit. Cleanup runs around the Work draw and before Open/Save captures the path; it clamps/restores egui character cursor endpoints. This is a composition transaction guard, not a second UI/business model or text-edit algorithm.

Already queued commit retains its old widget ownership and is delivered while that widget remains memory-focused, including external window blur. Real widget surrender still drops stale delivery instead of sending it to the new widget; cleanup restores the old uncommitted preview. The suite verifies commit applied before same-pass focus surrender is preserved.

Paste emits Event::Paste, preserving egui's singleline CR/LF normalization. Own proxy clipboard listeners stop bubbling to the upstream document listeners. When another DOM control owns activeElement, its native clipboard defaults remain usable while upstream clipboard queue entries are discarded before conversion into egui input. External window blur keeps the proxy visible but stops acceptance; its ordinary focus/window-focus wake route permits natural return without programmatic focus theft. These DOM policy changes require actual browser callback verification.

The composition guard follows ordered events within a frame. When a completed composition is immediately followed by another preedit, its rollback baseline is rebased from egui's real final composing range. Focus loss then removes only the second uncommitted region and retains the first commit. The exact batched real-egui regression is recorded red/green in REPORT.md.
