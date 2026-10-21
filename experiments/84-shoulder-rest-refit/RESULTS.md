# #80 rest-refit attempt: blocked before authoring

**Decision: BLOCKED_BEFORE_AUTHORING. Candidate count: 0.**

The planned shoulder refit has not been generated or scored. Two bounded attempts
to obtain the required comparison inputs failed their unchanged exact identity
gates. This is an input-admission result, not a rejected clothing shape and not a
clothing-quality improvement. #80 remains HOLD.

## Actual execution

| Stage | Actual result | Limit |
| --- | --- | --- |
| Original neutral source fitting | All 22,077 body and 1,986 garment render rest rows match authenticated original f32 bytes exactly, including duplicates | Neutral source preflight only |
| Original historical18 raw arrays | Expected paths and bounded retained-copy search found no arrays | Exact historical replay NOT-RUN; hashes unchanged |
| Native production CPU host | Locked offline build passed in 15m35s; actual runtime executed | No window, renderer or GPU |
| Native hybrid input attempt | REJECT_CORPUS at default arm2 full-bone exact overlap | Nine raw records retained; zero accepted entries in the rejected manifest |
| Separate CPU-only Wasm host | Locked offline build and installed wasm-bindgen passed; Cargo took 12m01s | Actual 240-file build closure and four artifacts verified |
| Wasm input attempt | Real in-app-browser client and loopback receiver ran; first original fixture equality failed | One raw record retained, zero accepted cases; source unchanged |
| New control suites | 168 local control executions passed across normal and optimized Python; both Rust hosts formatted | Actual old rejected crossing witness enabled locally; synthetic tests are labelled |
| Independent review | Source, lifecycle, provenance and actual rejection evidence reviewed independently | No quality admission |
| Complete19 baseline, authoring, scoring | NOT-RUN | No complete admitted corpus |
| Candidate Web A/B, generated shading/upload parity and CLI save/reload | NOT-RUN | Offline prerequisites did not pass |

Native build run: `run_dd7f1fab7e0af557b44e4130b5a68b33`.
Native capture run: `run_de2df02c745c775910a5caf97e189bfb`.
Wasm build run: `run_2b910a53552c782553db43d6d8801d23`.
These are local execution observations, not application startup or GPU/performance
measurements. #4's measurement gaps remain open.

## What failed

The retained default anchor is Web output. The native producer uses the same
original requested torso/jaw/action/time recipes. Its body and garment source
IDs, indices, rest positions, rest normals, complete positive influence rows and
placement transforms match the anchor exactly. Eight lower-leg/finger bones have
494 differing matrix components; the maximum component difference is
`2.980232238769531e-7`. The full-bone exact gate rejects that input.

Separate diagnostic revalidation found eight preceding native raw records pass
the unchanged checks. That is not eight accepted manifest entries or a complete
corpus: the failed streaming collection returned no completed accepted ledger.
See [the derived native summary](evidence/native-rejection-summary.json).

One separately reviewed same-target Wasm attempt was then allowed. Its first case
is exactly torso−1, jaw0, arm0/k0, paused `probe-entry`, legacy backend2/profilev1.
Selected local-rest and local-posed fixture values match. Selected canonical-posed
matrices differ in 11 clavicle and 9 upper-arm components, with maximum absolute
component difference `3.5762786865234375e-7`. The unchanged fixture gate rejects
this input before a second case is accepted. See
[the derived Wasm summary](evidence/wasm-rejection-summary.json).

The original historical selected fixture and original Web anchor therefore did
not both hold under either observed producer. Target-specific f32 arithmetic is
a supported hypothesis. The first differing arithmetic operation and a product
regression are **not established**. These small differences do not measure cloth
penetration, visible quality or whether a candidate would improve the shoulder.

No values were rounded, matrices normalized, fields removed, old hashes replaced
or tolerances increased. No further platform or compiler-flag trial was started.

## Retained scope

The frozen mathematical policy describes one connected 30-source offset-only
rest edit with its own proposed asset identity. Original topology, weights,
material, UVs and deletion mask remain fixed. All 581 plane constraints, the one
amplitude choice, saved-text residual floor and all19 position gates remain in
the implementation. That implementation has not consumed an authoring attempt.

`geometry-policy.json` is the pre-corpus/native-kind policy template. No frozen
Wasm scoring policy or authoring GO was issued: an admitted manifest and complete
baseline receipt do not exist. It must not be passed off as a completed candidate
policy.

Original product source, assets, root dependencies and historical character
comparison inputs/guards remain unchanged. CI gains a shared local/hosted control group; existing command
bodies, tests, thresholds, jobs and gates remain. The cache workflow checkers
require the exact new step separately and retain their original historical
workflow hash. CI controls do not reconstruct
the missing historical18 or certify a complete new corpus. The private actual
old-witness control explicitly skips when its authenticated input is unavailable.

The actual compiled inputs, build outputs, source-before/at-run/after receipts,
raw rejected records and independent reviews are retained in the local archive
`2026-10-21-shoulder-rest-refit`. The committed summaries pin their hashes and
state that they are derived summaries. They are not replacement raw inputs.

## Reproduce and next boundary

Run the retained portable controls from the repository root:

```sh
python3 -B scripts/check-portable.py shoulder-rest-refit
```

The [README](README.md), [native replay contract](replay/README.md),
[Wasm receiver contract](replay/README-wasm.md) and
[evaluation interface](evaluation/README.md) describe actual build and collection
commands. Actual input replay requires the retained original anchor and completed
build receipts. A source/hash mismatch must fail rather than create a PASS file.

The next proposed scope is to design and independently review one consistent
execution identity for a complete current nineteen-slot baseline, while retaining
the historical exact controls separately. That proposal has not been designed, implemented or independently reviewed
here. It must establish its evidence boundary before another capture
or this single rest-fit candidate is attempted. It is not permission to loosen
the failed gates or reinterpret the rejected runs as passing.

**PARTIAL — both real input attempts are retained and rejected; no candidate or
quality result exists. #79 and M2 are not expanded; #3 stays blocked and #4 keeps
its gaps.**
