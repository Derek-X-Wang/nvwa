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

## Pending comparison and limits

The physical plain-textarea/Nvwa pair is PENDING human input. Root prepared both
at125% Chrome. The selected OS input-method identity is still unknown. Root must
retain separately attributed candidate visibility/placement and once-only
canonical commit observations, plus two distinct complete captures. At most one
justified focused follow-up is allowed. Existing accepted physical observations
remain separately attributed; this diagnostic does not repeat or replace them.

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
20 checker tests,3 preparation tests and root's actual Chrome synthetic selftest.

PARTIAL — Physical plain/Nvwa IME comparison awaits the human; input-method
identity, candidate UI, committed-result comparison and event710 cause remain
unverified. No product fix, new compilation or physical acceptance is claimed.
Root owns all UI/server/GPU work and evidence/cleanup; this worker started no
server or browser and edited no product source or dependency.
