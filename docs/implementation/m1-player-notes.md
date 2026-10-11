# Thin M1 Player implementation checkpoint

Status: source implemented after root accepted #15; awaiting integration-owned tests, builds, fresh R2 review and native/Web acceptance. This checkpoint does not claim graphical or compiler success.

## Launch and document policy

- Native: `Nvwa --player --work /absolute/path/work.nvwa.json`. `--work ABS` also works in Studio mode for authored-sequence benchmarking. `--player` alone waits for manual Open.
- Web: `index.html?player=1&work=works/m1-sequence.nvwa.json`. `work` uses the same route with or without Player mode; `player=1` controls editor visibility. Query keys player/work/benchmark cannot repeat. Player/benchmark values are 0 or 1.
- Default launch remains Studio with the M0 fixture. Any explicit work, Player-without-work, or launch-parse error inserts runtime-only `StartupDocumentPolicy::WaitForOpen`; the runtime cannot substitute its default fixture during a pending or invalid work request.
- Native flags parse once with existing smoke/benchmark/capture/timeout support. Duplicate flags, missing values, nonfinite times, relative/non-UTF-8 work paths and unknown flags produce visible launch errors. Existing smoke time bounds remain. A malformed launch does not run a partially parsed benchmark/smoke configuration.
- A failed initial request leaves the editor without a document and permits manual Open recovery. A failed subsequent Open keeps the previous valid work and shows its error. Successful Open still creates a fresh asset-load generation, including same-profile reload.

## Source ownership and scope

Implemented only `crates/nvwa-studio/src/lib.rs`, `crates/nvwa-studio/src/platform.rs`, the minimal startup policy in `crates/nvwa-runtime/src/lib.rs`, and this note. `main.rs`, core schema, dependencies, manifests/lock, scripts, assets and publication are root-owned or unchanged by this worker.

Studio owns launch config, initial request, Player egui view and smoke evidence. PlatformIo owns all native/browser document access. Player remains in the same Rust app, renderer, event loop, animation transport and accepted #15 character interaction. No second frontend or model/API service exists.

The Player view receives immutable `EditorState` access. It shows Open, Play/Pause/Replay, Restart, global seek, actual active action, accepted chest/head click hint, loading state and errors. It has no editor panels, Save, shape or timeline commands, or Undo shortcut. Transport is disabled while #15 interaction is busy. The completed egui pass updates the existing pointer/keyboard guard; discarded passes cannot open files or apply transport effects. The full Studio path remains intact.

## Static Web boundary

The existing `web-sys 0.3.106`, wasm-bindgen, wasm-bindgen-futures and js-sys APIs provide the adapter. Root enabled/provides the requested feature gates: UrlSearchParams, RequestInit, RequestMode, RequestRedirect, RequestCredentials, Response, Headers, ReadableStream, ReadableStreamDefaultReader, ReadableStreamReadResult, AbortController and AbortSignal. No new dependency was requested.

Query decoding happens once through UrlSearchParams. The resulting work path accepts only ASCII letters, digits, `_`, `-`, `.`, `/` and nonempty non-dot path segments. Leading/trailing slash, `.`/`..`, duplicate slash, schemes/hosts, backslash, query/fragment delimiters, controls and remaining percent escapes fail before fetch. This rejects both decoded traversal and double-encoded escapes. Url::new_with_base resolves against the actual page URL, so a subdirectory deployment retains its own works/ directory.

PlatformIo::request_open_static uses RequestMode::SameOrigin, RequestRedirect::Error and RequestCredentials::Omit. HTTP failures, redirects and network errors become visible mailbox errors. A Response body is read through ReadableStreamDefaultReader with JsFuture. Each Uint8Array length is checked against the cumulative 2 MiB limit before it is copied into the Rust buffer; no Content-Length assumption is needed. The final bounded bytes require strict UTF-8. Core still owns strict JSON/schema/reference/overlap validation.

A 30-second AbortController timer covers the whole fetch/body read. Terminal completion clears the timer, drops its closure, releases any stream reader lock, aborts failures and sends one existing FileCompletion::Opened or error. Browser handles live in the async closure, not Bevy Send/Sync resources. The existing mailbox enforces single flight; Open is disabled while pending and becomes available after an error/timeout is polled.

The 2 MiB bound describes application-copied document bytes, not the browser's internal network buffering. The adapter does not call Response::text or array_buffer to materialize an unbounded body. Work assets keep the existing packaged asset-root resolution and validation, independent of the selected work's parent directory.

## Smoke evidence

The real smoke record now includes `mode`, `document_revision`, `timeline_count`, `playing`, `completed`, and `interaction_busy`. Startup/file errors count as smoke failure rather than waiting only for runtime load errors. A nine-second work observed after a fifteen-second warmup reports its completed final pose; this is not evidence of continuing motion.

## Added meaningful regressions

- Native parser: work in Studio/Player, default fixture policy, Player waiting policy, existing smoke/capture/benchmark values, malformed/duplicate/unknown flags, relative and non-UTF-8 paths.
- Web parser: independent mode/work route, launch values, duplicate keys, traversal/external/encoded paths.
- Platform boundary: strict static paths, cumulative exact 2 MiB and one-byte-over cap before copying, overflow/UTF-8 rejection, and failed async mailbox completion releasing single-flight recovery.
- Runtime startup: WaitForOpen creates no fixture/document; default policy still opens M0.
- Startup error/recovery: missing native work is visible, has no authoritative document, releases file busy state, and accepts a valid manual completion.
- Actual egui Player view: Space changes transport, panel/scene pointer guards remain correct, complete document content/revision is unchanged and the prior authored transaction remains the next Undo.

Existing #14/#15 source and regressions are preserved. The new collector/mailbox tests do not substitute for real browser fetch/stream/timeout acceptance.

## Root acceptance still required

Run workspace regressions and native/Wasm builds, then fresh independent R2 review of static input, launch/mode integration and failure recovery.

Verify packaged native launch from an unrelated working directory with ABS work; direct static Web query launch and page refresh; subdirectory deployment; real GLB sequence poses, transport and accepted character click/restoration; hidden editor and no mutation; manual Open recovery. Exercise actual 404, redirect, oversize streamed body without a length assumption, invalid UTF-8/JSON, stalled request, and missing/hash-invalid GLB paths. Record actual requests/backend/package identity and completed-vs-playing evidence.

Root reports packages now copy the demo to Web works/ and native Contents/Resources/works/, and its benchmark wrapper forwards work/Player flags. Those scripts were not executed by this worker.

VERIFIED — owned Rust sources formatted with scoped rustfmt; exact installed API signatures inspected.

NOT-RUN — Cargo tests/builds, UI/GPU, static fetch, timeout, package execution, Git mutations and external writes. No worker-created processes or worktrees exist. Root owns next validation and publication.

## Actual redirect error display repair

Root's first release-Web pass verified positive Player/subdirectory/refresh/paused interaction behavior and 404/JSON/UTF-8/2 MiB failures. The redirect case exposed a concrete display defect: debug-formatting the JavaScript error included its entire Wasm/JS stack and expanded the Player panel. Root captured `player-error-redirect.png` before this repair.

`platform::js_error` now preserves the original error in the browser console, extracts its string/message for the UI, and applies a pure formatter that displays one nonempty line with at most 240 message characters. Unknown/empty errors receive a meaningful fallback. Failed operations still deliver an error and release pending state; no failure becomes success.

Added a pure regression for stack removal, unknown/blank fallback and Unicode-safe message bounds. Only platform error presentation and this note changed in this repair.

VERIFIED — scoped platform rustfmt. NOT-RUN — repaired tests/builds, actual redirect display and targeted R2 check remain root-owned.
