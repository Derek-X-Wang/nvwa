# Issue 5: screenshot export boundary experiment

This is a throwaway page-instrumented diagnosis. It changes only this experiment
directory. It loads the existing frozen `dist/web/index.html`, JavaScript, Wasm,
and actual assets through the root-owned benchmark server. It does not compile,
replace, or draw runtime pixels. Character editing and animation stay in Rust.

## Ready handshake and reproduction

The experiment-24 server owner must map exactly these two experiment files next
to each run's frozen `index.html`:

- `/<run>/screenshot.html` → this directory's `screenshot.html`.
- `/<run>/export-probe.js` → this directory's `export-probe.js`.

No script or iframe uses a parent-directory path. No new server, process, browser,
or GPU work was started by this worker. Root owns the running server, browser,
download observation, and cleanup. Startup measurement must finish before these
extra runtime frames load.

1. Open `/<run>/screenshot.html?case=A` in the actual IAB. Only Start loads a
   runtime. The frame URL is `index.html?benchmark=1`.
2. Click **Start fresh runtime**. Require `hooks-ready` before the automatic
   `anchor-click-attempt`. If a Rust callback console event is captured, also
   require hook installation before that event. Hooks install on the iframe's
   load event. An export before hook installation makes that case invalid;
   unavailable console logs are not callback evidence or evidence of failure.
3. Wait for actual Rust readiness, its fixed 15-second warmup, and capture. Save
   `window.nvwaExportExperiment.records` and any actually captured Rust
   `NVWA_EVIDENCE` logs. State console availability separately for each run.
4. Observe downloads using the supported bounded download wait. Record its exact
   start/end and whether it began before the export attempt or callback; do not
   describe the total wait as time after a callback without that evidence.
   No file within a bounded wait means **no file observed in that window**. It
   does not prove a permanent browser failure.
5. Root independently checks each actual downloaded file's path, nonzero bytes,
   PNG signature, dimensions, and visible pixels. Logs and blob sizes cannot
   satisfy this step. A real canvas PNG is not AI motion evidence.
6. Click **Stop runtime and release probe URLs** before the next case. Retain
   each case's records externally before Start clears the in-memory buffer.
   Repeat on fresh frames with `?case=B`, `?case=D`, and `?case=C`.
7. For C, click the original **Download actual benchmark canvas PNG** control
   inside the runtime frame after real pixels render. Preserve the tool route
   and observed `event.isTrusted`/activation fields. Neither a scripted click
   nor a tool-generated click establishes human activation. C's frame also
   runs the baseline automatic Bevy capture; separate files by filename and
   `source`/`automatic` records.

| Case | Bytes | Anchor on automatic click | URL revocation |
|---|---|---|---|
| A | Actual Rust/Bevy screenshot encoding | Unchanged, unattached | Original synchronous request |
| B | Same actual Rust/Bevy screenshot encoding | Probe attaches original anchor | Original synchronous request; anchor removed afterward |
| D | Same actual Rust/Bevy screenshot encoding | Probe attaches original anchor | Probe defers original automatic revoke for 1000 ms |
| C | Original production button's real canvas `toBlob` | Original attached anchor | Original production 1000 ms timer |

A/B isolates attachment at the click boundary. B/D isolates revoke timing with
attachment held constant. A/D changes both and cannot identify which matters.
C additionally changes screenshot encoding source, trigger, and activation;
C alone cannot isolate attachment or revocation as the cause.

All cases run with instrumentation. A preserves the original download actions
but remains a page-instrumented environment. Hooks call the original browser
methods; they never replace a download with a fake file or simulated pixels.

## Records and verification limits

Records expose Start/button event trust, user activation at request/callback/
click/revoke, `toBlob` null/exception, blob byte size/type, canvas buffer size,
original/final anchor attachment, revoke policy, request time, actual revoke
time, URL lifetime, and Stop cleanup. Every adapter record remains
`durableFile: "NOT-VERIFIED"`. No record means persistent-file success.

`runtime-encoded-blob` means the blob did not come through the observed canvas
`toBlob` call. The actual `nvwa-web-benchmark.png` filename and inspected source
identify the automatic runtime export boundary. A separately observed Rust
callback additionally requires a captured matching console event; adapter
records alone do not provide it.
Empty blob MIME type is recorded as empty; it is not guessed to be PNG.

Read [SOURCE-BOUNDARY.md](SOURCE-BOUNDARY.md) for current primary source lines
and frozen file hashes. A missing adapter callback/download receipt is still a
runtime boundary to investigate, not permission to modify product behavior.

## Synthetic-only checks

```sh
node --test experiments/25-screenshot-export/export-probe.test.cjs
node --check experiments/25-screenshot-export/export-probe.js
```

Worker ran five synthetic tests: A/B attachment and original immediate revoke;
D's pending/1000 ms lifecycle; visible null/thrown `toBlob` outcomes; explicit
canvas bytes excluded from D's automatic delay; Stop cancellation, revocation,
adapter restoration, and idempotence. All five passed. These tests supply no
PNG pixels, actual browser events, trusted activation, download receipt, or
persistent file proof.

PARTIAL — current source and synthetic adapter/lifecycle checks verified.
NOT-RUN — actual IAB A/B/D/C and independent downloaded-PNG checks are root-owned
and pending. No actual symptom regression loop has run in this worker; diagnosis
phases for cause selection and a product fix remain pending.

The paragraph above records preparation-time status. [REPORT.md](REPORT.md)
contains the later root-run results, including successful top-level controls,
bounded iframe non-observations, and per-run console availability.
