# Issue32 bounded diagnostic result

Scope: experiment23 and private `.work/bounded-scale-ime/issue32/` preparation.
Root owns the actual Chrome UI and the published evidence packet. Early realm
instrumentation and a plain textarea control are ready. The prior untrusted
length2 `compositionend` at sequence710 remains origin UNKNOWN; no product defect
or fix is claimed.

Preparation validated the existing31-input frozen source manifest and prior Web
build/package bytes. Final package manifest SHA256:
`29939f0334137dbcc64c23d2c6237282f3bbc3c45cb7669b11500c3cf59a7b81`.
The staged `ime-nvwa.html` installs the synchronous hook before the production
module and includes a pre-module chronology marker. `ime-plain.html` and
`ime-selftest.html` use the same collector without production WebGPU/Wasm. Each
started capture has a unique UUID, explicit start/end checkpoint and stopped raw
UI download. The collector and staged package remain unchanged after the checker
repair.

## Actual Chrome synthetic control

Root clicked Start, known SYNTHETIC dispatch, Stop and Export in actual Chrome.
The exact [browser capture](../../docs/evidence/bounded-scale-ime/issue32/browser-selftest.json)
has run UUID `715f2932-f94d-45d8-ac5f-aa7c8e502c31`,15 rows, no drops, no
instrumentation errors and an intact hook. Observed sequences5,8,11 link
composition start/update/end to event IDs e1/e2/e3 and dispatch IDs d1/d2/d3.
All three are untrusted length2 events with `WITNESSED_REALM_DISPATCH`.

The repaired checker was run against that exact file with `--selftest` and
returned PASS/exit0. Root's [observations](../../docs/evidence/bounded-scale-ime/observations.json)
bind the exact UUID, synthetic page, root UI sequence and frozen package hash.
Independent review accepted this actual known synthetic control and repaired
checker. This proves the browser hook captures its owned local dispatch. It does
not prove physical IME, Nvwa input, OS candidates or event710's origin. The
selftest page loads no production module; its browser result does not establish
the Nvwa module marker at runtime.

## Local controls and chronology repair

JS syntax and the actual collector Node harness pass. The harness covers matching
event IDs/callstacks, exact receiver/arguments/thrown-value forwarding, native
false return, stopped-case protection, unique UUIDs and saved-native bypass.
Its known synthetic capture passes; bypass stays UNKNOWN/PARTIAL/exit2. The Node
DOM harness is not a browser or physical IME run.

The Python checker now passes20 tests; package preparation passes3 tests. An
independent review exposed chronology false PASS cases. Added tests produced35
pre-fix assertion/subtest failures in truncated tool output; no complete original
red log was saved. Current green output is archived by root and independently
reproduced. The repair rejects nonfinite, negative,
boolean or nonnumeric timestamps, hook/module/case inversions, rows outside the
case interval and contradictory boundary/interior checkpoint types and labels.
It enforces hook≤module(Nvwa)≤case start≤chronological rows≤case stop. Existing
known synthetic evidence remains PASS; absent-witness provenance remains UNKNOWN.
Only checker/tests changed for this repair.

Other expected-red controls reject missing stacks, wrong IDs/targets, fabricated
origin, raw input fields, sequence gaps, invalid selftest attribution and frozen
index/JS/Wasm mutations. A missing-stack control earlier exposed an exception;
it was repaired and rerun. These tests establish diagnostic/checker behavior,
not production regression or physical acceptance.

## Actual human pair and remaining limits

The human performed and exported one plain-textarea composition and one Nvwa
composition in the prepared125% Chrome pages. Root retained byte-exact files in
`.work/bounded-scale-ime/issue32/plain-textarea-physical-run1.json` and
`.work/bounded-scale-ime/issue32/nvwa-physical-run1.json`, with corresponding
`-check.json` reports. This is an actual pair with a modified confirmation
procedure, not the requested Space candidate-selection check.

| Capture | Exact run UUID | Rows | Composition end | Space keydown |
| --- | --- | --- | --- | --- |
| Plain textarea | `07b64d4f-2e79-447f-a4e0-cb2c2888e8c8` |52|seq37, event e26|seq39, composing false|
| Nvwa | `72332e2c-39e7-4801-a80a-7f161fb8785e` |42|seq33, event e28|seq35, composing false|

Both captures contain start/end checkpoints, one trusted composition start,
four trusted composition updates and one untrusted composition end. The
start/update code-point lengths are0→1→2→4→2; the end length is2. Plain
composition sequences are18/19/24/29/34/37; Nvwa sequences are14/15/20/25/30/33.
Each capture includes five beforeinput and five input rows. Neither contains a
witnessed composition dispatch. Both retain intact early hooks, zero dropped
rows and zero instrumentation errors. The Nvwa capture records hook installation
at16ms and its intact pre-module marker at16.700000017881393ms, before case start.
Distinct stopped intervals and UUIDs keep these cases separate. The plain capture
spans approximately114 minutes of mostly idle elapsed time, not continuous input
testing or a composition-latency measurement. Generic page-state focus/blur rows
omit event targets and may include descendant focus; no complete window departure/
return acceptance is inferred from them. Composition-row focus snapshots remain
the selected input evidence.

Both exact checker reports are PARTIAL/exit2 with no contradiction problems:
plain reports untrusted e26 origin UNKNOWN; Nvwa reports untrusted e28 origin
UNKNOWN. The checker remains unchanged. The same observed untrusted length2 end
pattern therefore occurs in the plain page without loading the Nvwa runtime.
This narrows the observation beyond Nvwa-specific behavior. It does not establish
browser, OS or provider cause, identify who created either event, or establish the
origin of historical event710. Saved method/other realm/isolated-world and native
browser or OS paths remain instrumentation blind spots.

The human said the Space candidate instruction was unclear, pressed Space and
saw an added space. In both traces Space follows composition end with
`composing:false`. Root's plain accessibility observation shows one `女娲`
followed by one space; root's Nvwa screenshot
`.work/bounded-scale-ime/issue32/nvwa-after.png` shows one `女娲`. These are
root-attributed rendered observations, not payload text collected by the
length-only observer. They do not establish Space selecting an active candidate.
Space-selection acceptance is NOT-RUN in this pair.

The human identified the input method as 搜狗输入法 (Sogou). This is user-reported
identity; the exact installed IME version and provider internals were not
verified. Candidate placement was not answered and remains NOT-RUN for this pair.
No further human input repeat is requested for the bounded diagnostic exit.
Existing accepted physical observations remain separately attributed; this
diagnostic does not replace them. Identifying the input method does not establish
that Sogou created the untrusted events.

Dispatch starts link to observed events by event and dispatch identity. A
witness proves this page JS realm called the hooked method. Constructor names
are descriptive metadata only. Unwitnessed events remain UNKNOWN; an absent
stack cannot identify an isolated JS world, another realm, saved native method,
browser internals, OS or provider as the cause. Trust flags do not establish
physical IME use, and DOM proxy position does not establish candidate placement.
The hook changes function identity and adds timing work; visible controls cover
part of the canvas and change focus when clicked. README records these effects,
privacy limits and blind spots. No production policy or checker19 was changed.

VERIFIED — Frozen package/source checks, JS syntax, Node collector controls,
20 checker tests,3 preparation tests, root's actual Chrome synthetic selftest and
two complete separately identified human exports.

PARTIAL — Actual plain/Nvwa pair used a modified confirmation procedure. Both
untrusted composition ends remain UNKNOWN; Sogou identity is user-reported,
its installed version is unknown, candidate placement and Space candidate-selection
are NOT-RUN, and event710 cause is unverified. No product fix or new compilation
is claimed.
Root owns all UI/server/GPU work and evidence/cleanup; this worker started no
server or browser and edited no product source or dependency.
