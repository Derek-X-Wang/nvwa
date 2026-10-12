# Issue32 bounded IME event provenance diagnostic

This experiment investigates the prior length2 `compositionend` at sequence710,
`trusted:false`, origin UNKNOWN. It is an uncertainty in the evidence, not a
reproduced product defect. Accepted Mac/Chrome physical input results remain
separately attributed. Experiment19 and its checker are unchanged.

The wrapper installs the same synchronous classic script in the head before the
production module. A second classic marker immediately before that module records
a timestamp and hook integrity. The existing production module text, JS, Wasm,
assets and Works are retained. `prepare.py` verifies all31 frozen source/build
inputs, frozen JS/Wasm/index bytes and the prior built package manifest before
staging copies. No Cargo build is requested or performed.

## Prepare and local controls

Run from the integration checkout:

```sh
python3 -B experiments/23-ime-event-provenance/prepare.py \
  --output .work/bounded-scale-ime/issue32/package-final
node --check experiments/23-ime-event-provenance/collector.js
node experiments/23-ime-event-provenance/test_collector.cjs \
  .work/bounded-scale-ime/issue32/controls
python3 -B experiments/23-ime-event-provenance/test_checker.py
python3 -B experiments/23-ime-event-provenance/test_prepare.py
```

The output must be empty. Preparation refuses changed frozen inputs and prior
output replacement. The completed staged package is immutable for this run.
Root owns its loopback server, browser tabs and every UI action. Serve the staged
directory, with one active Nvwa GPU page. The other pages load no production
module or Wasm. The superseded initial `package/` directory is preparation history;
use `package-final/` only. No worker started a server or a browser.

## Known local synthetic control, kept separate

1. Open `/ime-selftest.html` in a task-owned tab. The title and panel say SYNTHETIC.
2. Click **Start case**, then **Run known local SYNTHETIC dispatch**, then
   **Stop case**, then **Export exact raw JSON**. Use UI clicks; no console or
   mutating evaluation.
3. Preserve the exact downloaded JSON and run:

```sh
python3 -B experiments/23-ime-event-provenance/check.py \
  <exact-downloaded-selftest.json> --selftest
```

Expected green: exit0, exactly three untrusted length2 events with matched event
IDs and dispatch IDs, callstacks including `syntheticSelftest`, and start/stop
boundaries. This proves the known local dispatch hook in this browser only.
It is never a physical or product trace.

The Node harness executes the actual collector against a small DOM harness and
Node's native `EventTarget`, with a forwarding spy. It tests native false return,
exact receiver/arguments/thrown value forwarding, observer identity, stopped-case
protection, unique run UUIDs and a saved-native-method bypass yielding UNKNOWN.
It is not an actual browser or physical IME run. Its selftest JSON passes the
checker; its bypass JSON returns PARTIAL/exit2. Python checker controls reject
missing stacks, wrong IDs/targets, invented origins, raw text fields, sequence
gaps and invalid selftest attribution. Package controls reject changed index,
JS and Wasm bytes before any output is staged.

## One physical comparison in the same Chrome

Root must record the actual Chrome engine version, OS version, selected OS input
method identity and browser zoom. Use the same input method and125% Chrome zoom
on both owned tabs, matching the earlier ordinary zoom condition. Do not change
browser profiles, extensions, permissions or OS input-source configuration for
this diagnostic. A selected input method shown in actual UI and a separately
attributed physical report are needed; UA/trust flags do not supply that identity.

1. Open `/ime-plain.html`. Click **Start case**, click the owned textarea, and
   physically compose the agreed two-character task text once. Observe candidate
   visibility and placement, then use Space once to confirm. Observe whether the
   committed result is inserted once. Click **Stop case**, then **Export exact raw
   JSON**. Preserve that complete file and the separately attributed observation.
2. Open `/ime-nvwa.html?work=works/m1-sequence.nvwa.json`. Wait for the real Nvwa
   editor. Click **Start case**, click its real Work field, and physically compose
   the same agreed text once with the same confirmation action. Observe the
   candidate UI and canonical rendered Work result. Click **Stop case**, then
   **Export exact raw JSON**. Preserve the exact file and observation.
3. Run `check.py` separately on both exact files. Their `runId` UUIDs and
   start/stop intervals must differ. Keep plain, Nvwa and synthetic captures
   separate. Record event sequence, target, trust, lengths and provenance from
   each checker report. Complete composition/start/update/end/input/focus rows
   are collected when delivered; missing classes remain recorded limits.

No arbitrary text or clipboard contents are read. Composition/input payloads
are reduced to Unicode code-point lengths. Keys are reduced to fixed control
labels or `printable-or-other`. No textarea value is collected. Task-text
correctness and physical candidate UI must be observed separately. The DOM
proxy location is not candidate acceptance.

Space means confirming a candidate only while the OS candidate window is still
open and the selected input method uses Space for that action. If the Chinese
text has already committed through the user's normal selection method, pressing
Space afterward inserts a space; do not repeat it to claim candidate acceptance.
Preserve the actual procedure. The completed pair used that latter sequence,
so provenance comparison is complete while Space candidate-selection remains
NOT-RUN.

The collector starts only through **Start case**. It records no pre-start input.
**Stop case** adds an end checkpoint. Export requires Stop and downloads the exact
raw capture without flattening, summarizing or trimming. **Reset trace** is
allowed only after Stop and clears the trace, not input. Start after an existing
case asks for Reset. Export/reset buttons are focusable; their focus changes are
part of the end of the recorded interval, after the evaluated composition.

Permit at most one justified focused follow-up. If only Nvwa yields an untrusted
unwitnessed event, or a witnessed stack identifies a specific local caller, retain
both traces and choose the smallest repeat that tests that difference. Do not
repeat indefinitely, change production policy or weaken checker19. If physical
composition is unavailable through the tools, root requests Derek's one concrete
plain/Nvwa comparison only after these pages and synthetic control are ready.

## Meaning, blind spots and effects

A `dispatch-start` contains a stack, event constructor name, event ID and dispatch
ID. The document capture observer records the same event ID while that dispatch
is active. Checker validates ordering, active dispatch identity, matching event
metadata and return/throw boundaries. `WITNESSED_REALM_DISPATCH` proves only that
this page JS realm called the hooked method. Constructor name is descriptive
metadata; it does not identify the creator. No constructor is wrapped.

Every unwitnessed event remains **UNKNOWN**, including trusted events. `trusted`
is browser metadata, not proof of physical IME use. An untrusted unwitnessed event
returns PARTIAL/exit2. Checker PASS means diagnostic structure/control evidence;
its output always leaves physical acceptance NOT-RUN by the checker. Missing
start/stop, early module marker, lost hook, instrumentation errors or dropped rows
also return PARTIAL. Concrete contradictory metadata returns FAIL/exit1.

The hook cannot observe isolated JS worlds, another realm's method, previously
saved/native method references, browser internals, OS/provider composition paths
or code that replaces the hook. No absence of a stack identifies any of these as
the cause. It also does not capture detached/off-document observer events, prior
input, or events whose metadata failed inspection. Drops/errors and hook integrity
are exposed rather than hidden. No extension/provider cause is inferred.

The wrapper preserves the original property descriptor flags and forwards the
exact receiver and argument list with `Reflect.apply`; it returns the original
result or rethrows the same value. Diagnostic metadata errors are isolated and
counted. It changes the method's function identity/name/length and adds stack,
WeakMap and synchronous snapshot work during recording. These can perturb timing
or code that inspects function identity. It does not guarantee zero observer
effect. The fixed bottom-left controls cover some canvas area and alter focus when
clicked. Closing/reloading the diagnostic page removes all instrumentation.

PARTIAL — Frozen package preparation and local collector/checker controls pass;
actual Chrome synthetic control and plain/Nvwa physical comparison remain NOT-RUN
at the worker preparation stage. No product source, dependency or lockfile change.
